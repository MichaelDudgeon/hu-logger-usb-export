#!/system/bin/sh
# Read existing HU Logger output only. No logger/service/ADB commands.
export PATH=/sbin:/vendor/bin:/system/sbin:/system/bin:/system/xbin
export LD_LIBRARY_PATH=/vendor/lib:/system/lib
umask 077
USB=$PWD
SOURCE=/data/nemesis/hulog
case "$USB" in /|/data|/data/*|/system|/system/*|/proc|/proc/*|/dev|/dev/*) exit 1 ;; esac
STAMP=$(date -u +%Y%m%dT%H%M%SZ) || STAMP=undated
N=0
while [ "$N" -lt 100 ]; do
    OUT=$USB/HU-LOGGER-EXPORT-$STAMP-$$-$N
    if mkdir "$OUT"; then break; fi
    [ -e "$OUT" ] || [ -L "$OUT" ] || exit 1
    N=$((N + 1))
done
[ "$N" -lt 100 ] || exit 1
mkdir "$OUT/RAW-PRIVATE" || exit 1
exec > "$OUT/collector.log" 2>&1
DONE=0
result() { print -r -- "$*" > "$OUT/RESULT.tmp" && mv "$OUT/RESULT.tmp" "$OUT/RESULT.txt"; }
finish() {
    typeset RC=$1
    trap - EXIT HUP INT TERM
    if [ "$DONE" != 1 ]; then
        result 'PARTIAL: retrieval interrupted or a USB write failed; retain the entire directory.'
        [ "$RC" != 0 ] || RC=1
    fi
    exit "$RC"
}
trap 'finish $?' EXIT
trap 'exit 1' HUP INT TERM
result 'RUNNING: reading existing HU Logger files.' || exit 1
print -r -- 'PRIVATE: unredacted Bluetooth/projection logs. Keep local; do not publish. No automatic redaction is performed on these unknown log formats.' > "$OUT/PRIVACY.txt" || exit 1
print -r -- 'status	relative-path' > "$OUT/INVENTORY.tsv" || exit 1
: > "$OUT/CAPTURED.md5" || exit 1
case "$(id)" in uid=0\(*) ;; *) result 'PARTIAL: root execute context unavailable.'; DONE=1; exit 1 ;; esac
for CMD in cat mkdir mv md5 sync cmp ls; do command -v "$CMD" >/dev/null 2>&1 || exit 1; done
print -r -- 'USB readback' > "$OUT/probe-a" && cat "$OUT/probe-a" > "$OUT/probe-b" && cmp "$OUT/probe-a" "$OUT/probe-b" && sync || exit 1
for P in /data /data/nemesis "$SOURCE"; do
    if [ -L "$P" ]; then result 'PARTIAL: HU Logger source path is linked; nothing followed.'; DONE=1; exit 1; fi
done
if [ ! -d "$SOURCE" ]; then result 'PARTIAL: /data/nemesis/hulog is absent; no logger was started or reconfigured.'; DONE=1; exit 1; fi

# Subshell recursion isolates traversal variables even on the OEM shell.
# Do not follow symlinks or open FIFOs/devices/sockets. Stream regular files:
# the OEM copy utility can silently omit data when stat reports size zero.
walk() (
    trap - EXIT HUP INT TERM
    DIR=$1
    REL=$2
    RC=0
    mkdir -p "$OUT/RAW-PRIVATE/$REL" || exit 1
    for P in "$DIR"/* "$DIR"/.[!.]* "$DIR"/..?*; do
        [ -e "$P" ] || [ -L "$P" ] || continue
        NAME=${P##*/}
        R=$REL/$NAME
        if [ -L "$P" ]; then
            print -r -- "SKIPPED_LINK	$R" >> "$OUT/INVENTORY.tsv" || exit 1
            RC=1
        elif [ -d "$P" ]; then
            walk "$P" "$R" || RC=1
        elif [ -f "$P" ]; then
            ls -ln "$P" >> "$OUT/source-before.txt" 2>&1
            if cat "$P" > "$OUT/RAW-PRIVATE/$R"; then
                GOT=$(md5 "$OUT/RAW-PRIVATE/$R") || exit 1
                print -r -- "${GOT%% *}  RAW-PRIVATE/$R" >> "$OUT/CAPTURED.md5" || exit 1
                print -r -- "COPIED	$R" >> "$OUT/INVENTORY.tsv" || exit 1
            else
                print -r -- "READ_OR_WRITE_FAILED	$R" >> "$OUT/INVENTORY.tsv" || exit 1
                RC=1
            fi
            ls -ln "$P" >> "$OUT/source-after.txt" 2>&1
        else
            print -r -- "SKIPPED_NONREGULAR	$R" >> "$OUT/INVENTORY.tsv" || exit 1
            RC=1
        fi
    done
    exit "$RC"
)
RC=0
walk "$SOURCE" pass-1 || RC=1
walk "$SOURCE" pass-2 || RC=1
print -r -- 'Two full read passes are retained separately. HU Logger keeps running. This is not an atomic snapshot or continuous recording; repeated rotations between reads cannot be recovered. No size/line cap or original-file deletion. Hashes describe captured bytes. Return PARTIAL exports too.' > "$OUT/CAPTURE-NOTES.txt" || exit 1
sync || exit 1
if [ "$RC" = 0 ]; then
    if [ -s "$OUT/CAPTURED.md5" ]; then
        result 'SUCCESS: existing HU Logger files retrieved in two passes; raw data is private.' || exit 1
    else
        result 'SUCCESS: HU Logger directory exists but contains no regular files.' || exit 1
    fi
else
    result 'PARTIAL: some entries failed or were skipped; retain the complete export and inventory.' || exit 1
fi
sync || exit 1
DONE=1
exit "$RC"
