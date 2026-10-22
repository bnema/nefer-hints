#!/usr/bin/env bash
# usage: train/run_train.sh <unit-name> [finetune.py args...]
# Runs train/finetune.py as a transient systemd user unit that cannot starve the
# desktop session: RAM capped, low CPU and IO weight, nice 10. GPU memory is
# uncapped by default; --vram-gib optionally caps it inside finetune.py.
# Log: /tmp/nh-train/<unit-name>.log. Stop: systemctl --user stop <unit-name>
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: $0 <unit-name> [finetune.py args...]" >&2; exit 2; }
R="$(cd "$(dirname "$0")/.." && pwd)"
unit=$1; shift
if [ -L /tmp/nh-train ] || { [ -e /tmp/nh-train ] && { [ ! -d /tmp/nh-train ] || [ ! -O /tmp/nh-train ]; }; }; then
  echo 'Unsafe scratch directory /tmp/nh-train: requires an owned directory, not a symlink' >&2
  exit 1
fi
install -d -m 700 /tmp/nh-train
log=/tmp/nh-train/$unit.log
args=; (($#)) && args=$(printf ' %q' "$@")
systemd-run --user --unit "$unit" --collect \
  -p MemoryMax="${MEMORY_MAX:-24G}" -p CPUWeight=20 -p IOWeight=20 -p Nice=10 \
  -p WorkingDirectory="$R" \
  /usr/bin/env bash -c "exec venv/bin/python train/finetune.py$args > $(printf %q "$log") 2>&1"
echo "started $unit; log: $log"
