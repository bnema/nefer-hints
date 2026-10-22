#!/usr/bin/env bash
# usage: train/run_train.sh <unit-name> [finetune.py args...]
# Runs train/finetune.py as a transient systemd user unit that cannot starve the
# desktop session: RAM capped, low CPU and IO weight, nice 10. GPU memory is
# capped inside finetune.py (--vram-gib, default 10 GiB).
# Log: /tmp/nh-train/<unit-name>.log. Stop: systemctl --user stop <unit-name>
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: $0 <unit-name> [finetune.py args...]" >&2; exit 2; }
R="$(cd "$(dirname "$0")/.." && pwd)"
unit=$1; shift
mkdir -p /tmp/nh-train
log=/tmp/nh-train/$unit.log
args=$(printf ' %q' "$@")
systemd-run --user --unit "$unit" --collect \
  -p MemoryMax="${MEMORY_MAX:-24G}" -p CPUWeight=20 -p IOWeight=20 -p Nice=10 \
  -p WorkingDirectory="$R" \
  /usr/bin/env bash -c "exec venv/bin/python train/finetune.py$args > $(printf %q "$log") 2>&1"
echo "started $unit; log: $log"
