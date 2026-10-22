# Fine-tuning icon_detect for terminals

The fine-tuned model detects only links (URLs, `file://`, `www.`, `domain.tld/path`, emails) inside
terminal text and keeps detecting GUI targets. Bare paths, prompts and status bars are hard negatives.

## Data

| Set | Train | Val | Test | Labels |
|---|---:|---:|---:|---|
| Synthetic terminal screens (`terminal/`) | 500 | 60 | 40 | magenta-diff link boxes, see `terminal/README.md` |
| Web pages (`web/`) | 894 | 39 | - | DOM clickables, see `web/README.md` (includes the 13 eval TUNE scenes) |
| Native GUI (`native/`) | 520 | 100 | - | synthetic GTK/Qt clickables |

The web pages stop the model from forgetting GUI targets. Exact eval TEST scenes are never
trained on, but some TEST scenes share a page/app session with trained TUNE scenes; see
`eval/groups.json`. Splits are regrouped by page/session at the next dataset iteration.
The 39 web validation pages come from sites held out from training.

## Training

```sh
train/run_train.sh nh-train --name ft     # runs/ft/weights/best.pt, log /tmp/nh-train/nh-train.log
```

`run_train.sh` starts `finetune.py` as a systemd user unit with capped RAM (`MEMORY_MAX`, default
24G), low CPU/IO weight and nice 10. `--vram-gib N` optionally caps GPU memory (default: no cap);
a cap below about 9 GiB needs `--batch 2`. Ultralytics accumulates gradients to a nominal batch of
64, so the effective batch does not depend on `--batch`.

Start: `weights/base.pt` (OmniParser v2 icon_detect). 1280 px, AdamW lr0 0.002, 40 epochs, patience 10,
light augmentation (no flips, no mosaic), fp32 (`amp=False`: fp16 with MIOpen gives wrong results).
About 2 to 3.5 min/epoch on an RX 9070 XT, depending on the dataset size.

## Export and evaluation

Set `NEFER_HINTS_RUNNER` to the runner binary (default: repository `build/nefer-hints`).
The runner uses CPU inference here; explicit conf 0.01 and IoU override model metadata.

```sh
train/export_ft.sh runs/ft/weights/best.pt
# BASE_MODELS points to the base ncnn model directory.
venv/bin/python train/sweep.py --model "$BASE_MODELS" --name base --set select --iou 0.7
venv/bin/python train/sweep.py --model "$BASE_MODELS" --name base --set test --iou 0.7
for iou in 0.7 0.5 0.4; do
  venv/bin/python train/sweep.py --model models-ft --name ft --set select --iou "$iou"
done
venv/bin/python train/gate.py select train/results/sweep-base-select-iou0.7.json \
  train/results/sweep-ft-select-iou0.7.json train/results/sweep-ft-select-iou0.5.json \
  train/results/sweep-ft-select-iou0.4.json
# Read the frozen IoU before the single TEST sweep:
FROZEN_IOU=$(venv/bin/python -c 'import json; print(format(json.load(open("train/results/frozen-ft.json"))["iou"], "g"))')
venv/bin/python train/sweep.py --model models-ft --name ft --set test --iou "$FROZEN_IOU"
venv/bin/python train/gate.py final train/results/sweep-base-test-iou0.7.json \
  "train/results/sweep-ft-test-iou${FROZEN_IOU}.json" --frozen train/results/frozen-ft.json
```

Training uses terminal train twice (oversampling) plus web train and native train.
Ultralytics preserves repeated directory entries. Validation combines terminal, web
and native val once each. Empty/missing native directories are omitted and included
paths are printed; batch 4 and no VRAM cap remain the defaults.

## Selection

Selection uses web val and native val when present, alongside terminal val, never
eval TUNE (used in training) or TEST. All selection files require identical `gui_sets`.
For every fine-tuned (IoU, conf) row, the matched base threshold is the smallest
base validation threshold at IoU 0.7 with equal-or-higher web-only precision.
A row fails if base cannot reach its precision. At that matched operating point:

- web-only recall drops by at most 2 percentage points;
- native precision and recall each drop by at most 2 points when `native/val` is included;
- terminal FP/screen is at most 1.0 and at most 20% of matched base;
- terminal link recall is at least 80%.

All passing rows rank by absolute web-only recall, then web-only precision, then
native recall (zero when absent), all descending. Ranking by the margin over base
would favour high thresholds where base collapses, which makes the TEST comparison
weak and ships a lower-recall operating point.
The grid is 0.01–0.04 by 0.01, then 0.05–0.5 by 0.025. Offline filtering is strictly
`score > conf`, matching the runner. Selection writes `train/results/frozen-<name>.json` with `name`, `conf`, `iou`,
`base_conf` and SHA-256 hashes of every selection input. `final --frozen` requires
the TEST name and IoU to match and uses only the frozen thresholds. TEST sweeps
refuse to overwrite results unless `--force` is explicit.

TEST compares ft at its frozen conf against base at the base conf frozen on validation: pooled GUI `web_precision` and `web_recall` each drop
by at most 2 points, with the same terminal checks. The frozen pair is evaluated
once on eval TEST plus terminal test. Per-category TEST web/native metrics and
independent-subset metrics are informational. A TEST scene is independent when no
group containing it also contains a TUNE scene (ungrouped scenes are independent).
`eval_all.sh` produces the fixed-threshold terminal report, not a selection gate.

### Selection rule history

- **v1:** web-only validation (ft1).
- **v2:** pooled web+native, box-weighted validation (ft2 data stage).
- **v3:** per-source constraints, web-only primary. This rule is decided on
  **2026-10-22 before any ft3 evaluation**, motivated by ft1's TEST GUI precision
  failure and the TEST GUI box mix: web 514 boxes (≈78%), native/menus 145 (≈22%),
  versus pooled validation (~25% web). The commitment is not to change the rule
  after ft3's select sweep.
- **v4 matched operating point**, adopted **2026-10-22** after seeing ft3's v3
  select sweep (v3 failed only on web-only recall at base's fixed 0.05 point while
  matched-precision recall was equal): a deviation from the commitment not to
  change the rule after the select sweep; TEST still unseen for ft3 and run once.
  Its first ranking (recall margin over base) picked conf 0.125 against base 0.45,
  where base recall collapses; the ranking uses absolute web-only recall instead,
  also decided before any ft3 TEST run.

TEST runs per model: **base 1, ft1 1, ft2 0, ft3 1**.

ft3 TEST (frozen conf 0.04, IoU 0.4, base conf 0.175): **FAIL** on pooled GUI precision
(57.0% vs base 64.2%, drop 7.2 pts); pooled GUI recall 62.1% vs 51.6% (pass); terminal
FP/screen 0.47 vs 16.3 and link recall 98.4% (pass). Informational: TEST web P 54.4% /
R 59.7%, TEST native P 66.7% / R 70.3%.

### Limitations

- Web val has 805 boxes: precision SE is ≈1.7 points, so the 2-point tolerance is ≈1 SE.
- Synthetic native val is a regression guard, not a proxy for real apps; its boxes
  are 3–15× larger than TEST native boxes.
- TUNE/TEST page/session sharing (`eval/groups.json`) is kept; independent metrics
  are informational.
- About 6% of web boxes are tiny.

## Results

### terminal-v2 (ft3, shipped as experimental)

Validation (rule v4) freezes **conf 0.04 / IoU 0.4** against base at conf 0.175. The
TEST gate **fails** on pooled GUI precision (drop 7.2 points, allowance 2); every other
check passes. It ships as the experimental default model because it is the only one
usable on terminals, web and native apps alike: compared with base at the same
precision on validation, it finds as many web targets, far more native targets, and
nearly all terminal links with under one false box per screen.

| Set | Model | conf | IoU | Web-only P / R | Native P / R | GUI P / R (pooled) | Terminal link R | Terminal FP/screen |
|---|---|---:|---:|---|---|---|---:|---:|
| Selection | base | 0.175 | 0.7 | 55.1% / 64.5% | 50.1% / 33.6% | — | 27.9% | 18.33 |
| Selection | ft3 (frozen) | 0.04 | 0.4 | 54.8% / 64.6% | 49.2% / 80.5% | — | 98.5% | 0.50 |
| TEST | base | 0.175 | 0.7 | — | — | 64.2% / 51.6% | 27.4% | 16.30 |
| TEST | ft3 (frozen) | 0.04 | 0.4 | 54.4% / 59.7% | 66.7% / 70.3% | 57.0% / 62.1% | 98.4% | 0.47 |

### terminal-v1 (ft1)

Validation freezes **conf 0.01 / IoU 0.4**. The final TEST gate **fails**: full web
precision drops 9.13 percentage points, beyond the 2-point allowance. All other checks pass.
No TEST-driven retuning follows this result.

| Set | Model | conf | IoU | Web P | Web R | Terminal link R | Terminal FP/screen |
|---|---|---:|---:|---:|---:|---:|---:|
| Selection | base | 0.05 | 0.7 | 39.88% | 77.14% | 47.57% | 51.050 |
| Selection | ft (frozen) | 0.01 | 0.4 | 41.74% | 77.89% | 99.76% | 0.583 |
| TEST full | base | 0.05 | 0.7 | 55.87% | 64.95% | 44.09% | 44.025 |
| TEST full | ft (frozen) | 0.01 | 0.4 | 46.74% | 77.24% | 100.00% | 0.625 |
| TEST independent | base | 0.05 | 0.7 | 66.67% | 58.04% | — | — |
| TEST independent | ft (frozen) | 0.01 | 0.4 | 54.26% | 69.10% | — | — |

Stored `*_independent` metrics use grouping without the github/login and mdn/mdn-forms
groups. They include github and mdn, which share hosts with TUNE pages, so they are
optimistic. The truly independent scenes are lobsters, go, httpbin-form and firefox-menu.
The added groups affect future sweep subset membership only; stored TEST metrics stay unchanged.
“Web” includes native GUI scenes in the eval TEST split. Terminal columns use the entire
corresponding terminal split, not the independent web subset.

Export accepts optional `NAME`, `CONF` and `IOU` variables and writes `model.json` only
when at least one is supplied. Explicit runner flags override metadata.

## Model versions

- **terminal-v2** (experimental, shipped) = `runs/ft3/weights/best.pt` (epoch 30 of 40),
  metadata `{"name":"terminal-v2","conf":0.04,"iou":0.4}`.
  SHA-256 of `models-ft3/icon_detect-1280-rect.ncnn.bin`:
  `b345bf739f00ce8eec67333a33140ace2d1d4fe6e0ad3f6c1d96d4589e8b7ac3`.

- **terminal-v1** = `runs/ft/weights/best.pt` (epoch 39 of 40).
  SHA-256 of `models-ft/icon_detect-1280.ncnn.bin`:
  `184b0c0d23c77b276664cdf7cf1192d7a06b2d2e5096610f90428c9c4b0cf4f2`.

## Next steps

- A larger web validation set (about 150 pages from 15 held-out sites): 39 pages did not
  predict TEST web precision for terminal-v2.
- Real native app captures outside the TEST sessions, beyond the synthetic GTK/Qt templates.
- GUI terminal chrome (GNOME Console, Ptyxis, Ghostty) screens, not yet in the data.
