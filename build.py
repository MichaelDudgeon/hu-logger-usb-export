#!/usr/bin/env python3
"""Build a reproducible, execute-only USB ZIP from an explicit file allowlist."""

import argparse
import configparser
import hashlib
from pathlib import Path
import re
import zipfile


ROOT = Path(__file__).resolve().parent
FILES = ("NEMESIS.data", "NEMESIS.sh", "USB-INSTRUCTIONS.txt")


def descriptor():
    config = configparser.ConfigParser(interpolation=None)
    config.read(ROOT / "NEMESIS.data", encoding="utf-8")
    if config.sections() != ["nemesis"]:
        raise ValueError("Expected only an execute descriptor, without apps or services")
    meta = config["nemesis"]
    for key in ("id", "name", "package-version", "short-desc", "detailed-desc",
                "os", "models", "depends"):
        if not meta.get(key, "").strip():
            raise ValueError("Missing metadata field: " + key)
    if (meta.get("version"), meta.get("type"), meta.get("path")) != (
            "1.1", "execute", "NEMESIS.sh"):
        raise ValueError("Must remain a version 1.1 USB execute bundle")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", meta["id"]) or ".." in meta["id"]:
        raise ValueError("Invalid ID")
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)*", meta["package-version"]):
        raise ValueError("Invalid package-version")
    for key, limit in (("short-desc", 64), ("detailed-desc", 256)):
        if len(meta[key].encode("utf-8")) > limit:
            raise ValueError(key + " is too long")
    return dict(meta)


def build(output_dir=None):
    meta = descriptor()
    payload = {}
    for name in FILES:
        source = ROOT / name
        if source.is_symlink() or not source.is_file():
            raise ValueError("Expected an ordinary source file: " + name)
        payload[name] = source.read_bytes()
    if not payload["NEMESIS.sh"].startswith(b"#!/system/bin/sh\n"):
        raise ValueError("Collector must use the HU shell")
    # Keep the USB bundle at three files; put the redistribution license in its
    # instructions rather than adding another item for users to extract.
    payload["USB-INSTRUCTIONS.txt"] += (
        "\n--- SOFTWARE LICENSE ---\n\n" + (ROOT / "LICENSE").read_text(encoding="utf-8")
    ).encode("utf-8")
    output = Path(output_dir) if output_dir is not None else ROOT / "dist"
    output.mkdir(parents=True, exist_ok=True)
    target = output / ("hu-logger-usb-export-" + meta["package-version"] + "-usb.zip")
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in payload.items():
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    with zipfile.ZipFile(target) as archive:
        if archive.testzip() is not None or tuple(archive.namelist()) != FILES:
            raise ValueError("Archive verification failed")
        if any(archive.read(name) != data for name, data in payload.items()):
            raise ValueError("Archive payload mismatch")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    (output / "SHA256SUMS").write_text(digest + "  " + target.name + "\n", encoding="utf-8")
    return target, digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Destination (default: dist beside this script)")
    args = parser.parse_args()
    path, sha256 = build(args.output_dir)
    print(path)
    print("SHA256 " + sha256)
