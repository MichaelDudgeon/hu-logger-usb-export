# Companion download submission

## Suggested listing

**Name:** HU Logger USB Export

**ID:** `hu.logger.usb-export` (proposed; not reserved or submitted)

**Version:** `1.0.0`

**Short description:** Copy existing HU Logger logs to a USB drive

**Listing text:**

Retrieve existing HU Logger logs without ADB. Download the USB bundle, extract
its three files to a clean USB root, insert the drive, and approve the NEMESIS
execute prompt. The tool copies `/data/nemesis/hulog` and writes copy reports
to the drive. Original logs stay in place. NEMESIS and HU Logger must already
be installed. Collected logs are private and unredacted.

**Download:** `hu-logger-usb-export-1.0.0-usb.zip`

**Repository:** Supply this repository's HTTPS URL after publishing it.

## Note to the reviewer

This is intended as a discoverable companion download for HU Logger, using
NEMESIS's existing USB execute workflow. It is not an installable application
or a service. The descriptor includes the listing fields but deliberately uses
`type=execute` and `path=NEMESIS.sh`.

Users must download and extract this bundle onto USB; installing its ZIP through
Manager would not provide a launchable tool. Please consider it for a companion
download listing if the store can distinguish that from normal installation.
No store API, installer, or Manager changes are included here.

The tool reads existing logs in two passes and leaves the source files in place.
It does not start or configure the logger, enable ADB, or collect unrelated
head-unit diagnostics. The metadata dependency documents the prerequisite but
is not enforced by the USB execute handler.

## Before submitting

- Publish the source repository and upload the built ZIP as a release asset.
- Run the bundle on a head unit with HU Logger installed. Check the completion
  dialog, `RESULT.txt`, and both raw copy passes. Keep real exports private.
- Confirm source logs remain available and the logger continues operating.
- Remove the USB; no tool application/service should have been installed.
- Record the tested NEMESIS version, HU Logger version, firmware, date, and
  outcome in the repository without including vehicle identifiers or raw logs.
- Supply the repository's real HTTPS URL in the portal submission.

The site's install/uninstall test step applies to installable packages. For this
execute-only bundle, report the actual execution/removal checks rather than
claiming an installation or uninstall test. Host tests and successful ZIP
construction do not replace the head-unit run.
