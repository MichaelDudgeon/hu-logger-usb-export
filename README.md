# HU Logger USB Export

Copy existing **HU Logger** logs to a USB drive, without ADB. Insert the prepared
drive, approve the NEMESIS execute prompt, and take the collected files back to
your computer.

This is a USB companion script for **HU Logger** (`hu.logger`), developed by
Gor Mirzoyan ([xwtk.cloud](https://xwtk.cloud/services/nemesis/)). It uses
NEMESIS's `type=execute` workflow. It does not install an application or service,
and it does not install, start, stop, or reconfigure HU Logger.

## Requirements

- A NEMESIS-capable Gen5W head unit with NEMESIS already installed.
- HU Logger already installed and having recorded the relevant activity.
- A clean USB drive the head unit can read and write, with enough free space
  for two copies of `/data/nemesis/hulog`, plus small copy reports.

## Use

1. Download `hu-logger-usb-export-1.0.0-usb.zip` from this repository's releases,
   or build it using the instructions below. A release must be uploaded by the
   repository maintainer; GitHub's automatic source ZIP is not the USB bundle.
2. Extract all three files directly to the USB root. Do not copy the ZIP itself
   onto the drive and do not leave the files in a subfolder.
3. Insert the USB, approve the NEMESIS **execute** prompt, and wait for the
   completion dialog. Keep the drive connected and the head unit powered.
4. On your computer, open the new `HU-LOGGER-EXPORT-<UTC>-<pid>-<suffix>` folder.
   Read `RESULT.txt` and retain the whole folder, including PARTIAL exports.

The prepared drive contains:

```text
USB root/
  NEMESIS.data
  NEMESIS.sh
  USB-INSTRUCTIONS.txt
```

Use a drive without another NEMESIS installer or script. This bundle is for
**download, extraction, and USB execution**. Do not install its ZIP through
NEMESIS Manager's package installer. A store listing would serve as a companion
download; it would need to explain this workflow.

## What it copies

The script reads only the existing `/data/nemesis/hulog` tree as its log source.
It copies regular files recursively, including hidden files, rotated logs,
compressed segments, and binary captures, in two separate passes. It adds
`RESULT.txt`, a file inventory, MD5 checksums of captured bytes, source listing
metadata, privacy/capture notes, a collector log, and a small USB readback probe.
It also reads the current time and root identity for collection bookkeeping.

It does not collect separate HMG diagnostics, process lists, network state,
Android logcat output, or device settings. It does not clear or delete source
logs. Symlinks and special files are skipped and reported as PARTIAL.

The logger continues running, so the two passes can differ. This is not an
atomic snapshot or continuous recording; repeated rotations between reads
cannot be recovered. There is no file-size or line-count cutoff. MD5 checksums
identify copied bytes for comparison; they are not signatures or privacy checks.

## Understanding the result

| Result | Meaning |
| --- | --- |
| `SUCCESS: ... retrieved in two passes` | Both passes finished without a reported copy/hash failure. |
| `SUCCESS: ... contains no regular files` | The directory exists, but no regular files were found to copy. |
| `PARTIAL: ...` | Something was absent, skipped, interrupted, or failed. Keep the full export for diagnosis. |
| No export folder | The script may not have run, or the drive may not have been writable. |

A NEMESIS failure dialog can accompany a useful PARTIAL export. Check
`RESULT.txt`, `INVENTORY.tsv`, and `collector.log` on the computer.

## Reporting an issue

Tell the developer the approximate **date, time, and time zone** of the issue,
and describe what happened. Export soon afterward. This tool can retrieve only
the files still present; it cannot restore logs HU Logger has already rotated
away, and it does not change the logger's retention policy.

## Privacy

The distributed bundle contains scripts and instructions, not captured vehicle
data. The collected export is **private, unredacted, and unencrypted**. Logs and
reports can contain names, device/session identifiers, location text, or other
personal information. Share them privately only after reviewing them.

Do not attach exports to public issues or commit them to this repository.
There is no automatic redaction, upload, or network transmission in this tool.

## Build and check

Python 3 is needed only on the development computer, not on the head unit.
The host tests additionally need Bash; they supply a Python MD5 adapter.

```sh
python3 -m unittest discover -s tests -v
python3 build.py
```

The build writes `dist/hu-logger-usb-export-1.0.0-usb.zip` and
`dist/SHA256SUMS`. It includes exactly the three USB files above, from an
explicit allowlist. Rebuilding unchanged inputs produces identical ZIP bytes.
Build outputs, test caches, and captured export folders are ignored by Git.

The collector is unchanged from the earlier HU Logger-only USB tool. Host
tests use synthetic files and a translated Bash fixture to check copied bytes,
failure handling, repeat runs, and unchanged source data. They do not establish
execution under the head unit's OEM shell. This public-repo bundle and its
expanded descriptor still need a head-unit run before being described as
vehicle-tested. No store submission or acceptance is claimed.

## NEMESIS metadata and store review

`NEMESIS.data` includes descriptor version `1.1`, ID `hu.logger.usb-export`,
name, type, package version, descriptions, OS/model fields, dependency, and the
script path. **`type=execute` is intentional.** The extra descriptive fields do
not convert it into an installable package. `depends=hu.logger@>=1.0.0` records
the prerequisite; the USB execute handler does not install or enforce it.
The script reports a missing log directory instead.

`os=any` and `models=any` avoid a car-specific restriction. They are metadata,
not a claim that every head unit has been tested. The intended environment is
a compatible NEMESIS installation with HU Logger's output at the path above.

See [docs/SUBMISSION.md](docs/SUBMISSION.md) for listing text and the review
notes. The portal's normal package installation flow is different from a USB
execute download, so the listing must be reviewed as that kind of companion.

## Credits and references

HU Logger and NEMESIS are developed by Gor Mirzoyan
([xwtk.cloud](https://xwtk.cloud/services/nemesis/)). This repository provides a
separate log-export companion and does not bundle HU Logger itself.

- [NEMESIS repository](https://github.com/xwtk/hmg_nemesis)
- [USB execute guide](https://github.com/xwtk/hmg_nemesis/blob/main/06-Run-Scripts.md)
- [Package metadata guide](https://github.com/xwtk/hmg_nemesis/blob/main/05-Packages.md)
- [NEMESIS store](https://xwtk.cloud/services/nemesis/)

## License

MIT; see [LICENSE](LICENSE).
