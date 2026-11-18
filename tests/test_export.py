"""Synthetic host checks. These do not emulate the HU's OEM shell or NEMESIS UI."""

import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("usb_export_build", ROOT / "build.py")
BUILDER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUILDER)
SOURCE = (ROOT / "NEMESIS.sh").read_text(encoding="utf-8")
BASH = shutil.which("bash")


def snapshot(root):
    result = {}
    for item in root.rglob("*"):
        info = item.lstat()
        value = (os.readlink(item) if stat.S_ISLNK(info.st_mode) else
                 hashlib.sha256(item.read_bytes()).hexdigest() if stat.S_ISREG(info.st_mode)
                 else "nonregular")
        result[str(item.relative_to(root))] = (info.st_mode, value)
    return result


class Fixture:
    def __init__(self, root):
        self.usb = root / "usb"
        self.device = root / "device"
        self.logs = self.device / "data/nemesis/hulog"
        self.bin = root / "bin"
        for path in (self.usb, self.logs, self.bin):
            path.mkdir(parents=True)
        (self.device / "unrelated-settings").write_bytes(b"DO NOT EXPORT OR CHANGE")
        (self.logs / "current.log").write_bytes(b"synthetic log line\n" * 40000)
        (self.logs / "seg-000001.log.gz").write_bytes(b"\x1f\x8b\x00" + bytes(range(256)) * 2000)
        (self.logs / "nested folder").mkdir()
        (self.logs / "nested folder/.hidden").write_bytes(b"synthetic hidden log\n")
        self.wrapper("id", 'echo "uid=0(root) gid=0(root)"')
        code = ('import hashlib,sys; '
                'print(hashlib.md5(open(sys.argv[1], "rb").read()).hexdigest() + "  " + sys.argv[1])')
        self.wrapper("md5", "exec " + shlex.quote(sys.executable) + " -c " + shlex.quote(code) + ' "$1"')
        # Synthetic USB: do not flush the host's actual disks during tests.
        self.wrapper("sync", "exit 0")
        translated = re.sub(
            r"(?<![A-Za-z0-9_/])/(data|system|proc|dev)(?=/|\b)",
            lambda match: str(self.device / match[1]), SOURCE)
        translated = translated.replace(str(self.device / "dev/null"), "/dev/null")
        translated = re.sub(r"^export PATH=.*$", "export PATH=" + shlex.quote(str(self.bin)) +
                            ":/usr/bin:/bin:/usr/sbin:/sbin", translated, flags=re.M)
        translated = re.sub(r"^export LD_LIBRARY_PATH=.*$", "unset LD_LIBRARY_PATH",
                            translated, flags=re.M)
        self.script = self.usb / "NEMESIS.sh"
        self.script.write_text(translated, encoding="utf-8")

    def wrapper(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
        path.chmod(0o755)

    def run(self):
        # Provide only mksh's print spelling; Bash still isn't the OEM interpreter.
        command = ('print() { [ "$1" != -r ] || shift; [ "$1" != -- ] || shift; '
                   'builtin printf "%s\\n" "$*"; }; . "$1"')
        return subprocess.run([BASH, "--posix", "-c", command, "fixture", str(self.script)],
                              cwd=self.usb, capture_output=True, text=True, timeout=30)

    def exports(self):
        return sorted(self.usb.glob("HU-LOGGER-EXPORT-*"))


class BuildTests(unittest.TestCase):
    def test_execute_metadata_and_reproducible_allowlisted_bundle(self):
        meta = BUILDER.descriptor()
        self.assertEqual(meta["type"], "execute")
        self.assertEqual(meta["depends"], "hu.logger@>=1.0.0")
        with tempfile.TemporaryDirectory(prefix="hu-export-build-") as directory:
            target, first_hash = BUILDER.build(directory)
            first_bytes = target.read_bytes()
            _, second_hash = BUILDER.build(directory)
            self.assertEqual(first_bytes, target.read_bytes())
            self.assertEqual(first_hash, second_hash)
            with zipfile.ZipFile(target) as archive:
                self.assertIsNone(archive.testzip())
                self.assertEqual(tuple(archive.namelist()), BUILDER.FILES)
                self.assertEqual(archive.read("NEMESIS.sh"), (ROOT / "NEMESIS.sh").read_bytes())
                self.assertEqual(archive.read("NEMESIS.data"), (ROOT / "NEMESIS.data").read_bytes())
                self.assertIn(b"MIT License", archive.read("USB-INSTRUCTIONS.txt"))
                self.assertFalse(archive.comment)
                self.assertTrue(all(not item.extra and not item.comment
                                    for item in archive.infolist()))


@unittest.skipUnless(BASH, "Host Bash is required for translated fixtures")
class CollectorTests(unittest.TestCase):
    def test_shell_syntax(self):
        subprocess.run([BASH, "--posix", "-n", str(ROOT / "NEMESIS.sh")], check=True)

    def test_complete_bytes_checksums_private_scope_and_repeat_runs(self):
        with tempfile.TemporaryDirectory(prefix="hu-export-copy-") as directory:
            fixture = Fixture(Path(directory))
            before = snapshot(fixture.device)
            original = {str(path.relative_to(fixture.logs)): path.read_bytes()
                        for path in fixture.logs.rglob("*") if path.is_file()}
            for _ in range(2):
                result = fixture.run()
                self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(len(fixture.exports()), 2)
            self.assertEqual(snapshot(fixture.device), before)
            for export in fixture.exports():
                self.assertTrue((export / "RESULT.txt").read_text().startswith("SUCCESS:"))
                for phase in ("pass-1", "pass-2"):
                    copied = {str(path.relative_to(export / "RAW-PRIVATE" / phase)): path.read_bytes()
                              for path in (export / "RAW-PRIVATE" / phase).rglob("*") if path.is_file()}
                    self.assertEqual(copied, original)
                receipts = (export / "CAPTURED.md5").read_text().splitlines()
                self.assertEqual(len(receipts), len(original) * 2)
                for line in receipts:
                    checksum, relative = line.split("  ", 1)
                    self.assertEqual(hashlib.md5((export / relative).read_bytes()).hexdigest(), checksum)
                self.assertFalse(any(path.name == "unrelated-settings" for path in export.rglob("*")))

    def test_empty_and_partial_cases_leave_source_unchanged(self):
        cases = ("empty", "missing", "root-link", "parent-link", "nested-link", "fifo",
                 "partial-read", "hash-fail", "destination-mkdir-fail", "final-sync-fail", "nonroot")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory(prefix="hu-export-fault-") as directory:
                root = Path(directory)
                fixture = Fixture(root)
                if case in ("empty", "missing"):
                    shutil.rmtree(fixture.logs)
                    if case == "empty":
                        fixture.logs.mkdir()
                elif case == "root-link":
                    moved = fixture.device / "other-logs"
                    shutil.move(fixture.logs, moved)
                    fixture.logs.symlink_to(moved, target_is_directory=True)
                elif case == "parent-link":
                    parent = fixture.logs.parent
                    moved = fixture.device / "other-parent"
                    shutil.move(parent, moved)
                    parent.symlink_to(moved, target_is_directory=True)
                elif case == "nested-link":
                    (fixture.logs / "linked-secret").symlink_to(fixture.device / "unrelated-settings")
                elif case == "fifo":
                    os.mkfifo(fixture.logs / "pipe")
                elif case == "partial-read":
                    fixture.wrapper("cat", 'case "$1" in */hulog/current.log) echo partial; exit 1;; esac\n'
                                    'exec /bin/cat "$@"')
                elif case == "hash-fail":
                    fixture.wrapper("md5", "exit 1")
                elif case == "destination-mkdir-fail":
                    fixture.wrapper("mkdir", 'case "$*" in *RAW-PRIVATE/pass-*/nested*) exit 1;; esac\n'
                                    'exec /bin/mkdir "$@"')
                elif case == "final-sync-fail":
                    counter = shlex.quote(str(root / "sync-count"))
                    fixture.wrapper("sync", 'n=0\n[ ! -f ' + counter + ' ] || read n < ' + counter +
                                    '\nn=$((n + 1))\necho "$n" > ' + counter + '\n[ "$n" -lt 3 ]')
                elif case == "nonroot":
                    fixture.wrapper("id", 'echo "uid=2000(shell) gid=2000(shell)"')
                before = snapshot(fixture.device)
                result = fixture.run()
                self.assertEqual(result.returncode == 0, case == "empty", result.stderr)
                self.assertEqual(snapshot(fixture.device), before)
                self.assertEqual(len(fixture.exports()), 1)
                export = fixture.exports()[0]
                status = (export / "RESULT.txt").read_text()
                self.assertTrue(status.startswith("SUCCESS:" if case == "empty" else "PARTIAL:"), status)
                if case == "empty":
                    self.assertIn("contains no regular files", status)
                if case in ("nested-link", "fifo"):
                    skipped = "linked-secret" if case == "nested-link" else "pipe"
                    for phase in ("pass-1", "pass-2"):
                        self.assertFalse((export / "RAW-PRIVATE" / phase / skipped).exists())


if __name__ == "__main__":
    unittest.main()
