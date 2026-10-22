#!/usr/bin/env bash
# usage: train/export_ft.sh <weights.pt> [output-dir=models-ft]
# Optional metadata: NAME=terminal-v1 CONF=0.075 IOU=0.4 (any subset).
# Exports ncnn (icon_detect-{640,1280}[-rect]) and checks the runner loads them.
set -euo pipefail
[ $# -ge 1 ] || { echo "usage: $0 <weights.pt> [out-dir]" >&2; exit 2; }
R="$(cd "$(dirname "$0")/.." && pwd)"
PT="$(realpath "$1")"; OUT="${2:-$R/models-ft}"
PY="${PY:-$R/venv/bin/python}"
BIN="${NEFER_HINTS_RUNNER:-$R/build/nefer-hints}"
mkdir -p "$OUT"; OUT="$(realpath "$OUT")"
OMP_NUM_THREADS="${OMP_NUM_THREADS:-4}" "$PY" "$R/export/export_ncnn.py" --weights "$PT" --output "$OUT"
for s in 640 1280; do for x in "" -rect; do for e in param bin; do
  [ -s "$OUT/icon_detect-$s$x.ncnn.$e" ] || { echo "missing icon_detect-$s$x.ncnn.$e" >&2; exit 1; }
done; done; done
# Leave existing metadata untouched unless at least one setting is supplied.
if [[ ${NAME+x} || ${CONF+x} || ${IOU+x} ]]; then
  "$PY" - "$OUT/model.json" <<'PYMETA'
import json
import math
import os
from pathlib import Path
import sys

metadata = {}
if 'NAME' in os.environ:
    metadata['name'] = os.environ['NAME']
for env, key in [('CONF', 'conf'), ('IOU', 'iou')]:
    if env in os.environ:
        value = float(os.environ[env])
        if not math.isfinite(value) or value > 1 or (value <= 0 if key == 'conf' else value < 0):
            raise SystemExit(f'invalid {env}: {os.environ[env]}')
        metadata[key] = value
Path(sys.argv[1]).write_text(json.dumps(metadata, allow_nan=False) + '\n')
PYMETA
fi
# hello check on CPU: runner must emit NHNT with status 0
for s in 640 1280; do
  head -c 12 < <(sleep 20 | "$BIN" --model "$OUT" --imgsz "$s" --gpu cpu 2>/dev/null) | python3 -c "
import sys,struct; d=sys.stdin.buffer.read(12)
ok=d[:4]==b'NHNT' and struct.unpack('<II',d[4:12])==(1,0)
print('hello $s', 'OK' if ok else 'FAIL'); sys.exit(0 if ok else 1)"
done
