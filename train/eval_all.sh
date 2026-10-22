#!/usr/bin/env bash
# usage: train/eval_all.sh <models-dir> <name> [gpu=cpu]
# eval/score.py (TEST split, 0.05/0.25) + train/eval_terminal.py -> train/results/<name>-summary.json
set -euo pipefail
[ $# -ge 2 ] || { echo "usage: $0 <models-dir> <name> [gpu]" >&2; exit 2; }
R="$(cd "$(dirname "$0")/.." && pwd)"
MODELS="$(realpath "$1")"; NAME="$2"; GPU="${3:-cpu}"
PY="${PY:-$R/venv/bin/python}"
BIN="${NEFER_HINTS_RUNNER:-$R/build/nefer-hints}"
T="$(mktemp -d /tmp/nh-evalall.XXXXXX)"; trap 'rm -rf "$T"' EXIT
# score.py writes results/out into its dataset dir: use a scratch copy (symlinked inputs)
mkdir -p "$T/ds" "$T/root/build" "$T/root/weights"
for f in frames gt scenes.json split.json; do ln -s "$R/eval/$f" "$T/ds/$f"; done
ln -s "$BIN" "$T/root/build/nefer-hints"; ln -s "$MODELS" "$T/root/models"
"$PY" "$R/eval/score.py" --runner-root "$T/root" --dataset "$T/ds" --gpu "$GPU"
mkdir -p "$R/train/results"
"$PY" "$R/train/eval_terminal.py" --model "$MODELS" --name "$NAME" --gpu "$GPU"
"$PY" - "$T/ds/results/scores.json" "$R/train/results/terminal-$NAME.json" "$R/train/results/$NAME-summary.json" "$NAME" <<'P'
import json, sys
sc, tm, out, name = sys.argv[1:]
agg = json.load(open(sc))['aggregates']; t = json.load(open(tm))
s = {'name': name}
for th in ('0.05', '0.25'):
    a = agg[f'{float(th)}/split/test']
    s[th] = dict(eval_test_precision=a['precision'], eval_test_recall=a['recall'],
                 terminal_recall=t[th]['link_recall'], terminal_fp_per_screen=t[th]['fp_per_screen'],
                 terminal_fp_nolink_screens=t[th]['fp_per_nolink_screen'], terminal_status_bar_fp=t[th]['status_bar_fp'])
json.dump(s, open(out, 'w'), indent=1); open(out, 'a').write('\n'); print(json.dumps(s, indent=1))
P
