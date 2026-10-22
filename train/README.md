# Fine-tuning icon_detect for terminals

The fine-tuned model detects only links (URLs, `file://`, `www.`, `domain.tld/path`, emails) inside
terminal text and keeps detecting GUI targets. Bare paths, prompts and status bars are hard negatives.

## Data

| Set | Train | Val | Test | Labels |
|---|---:|---:|---:|---|
| Synthetic terminal screens (`terminal/`) | 500 | 60 | 40 | magenta-diff link boxes, see `terminal/README.md` |
| Web pages (`web/`) | 264 | 39 | - | DOM clickables, see `web/README.md` (includes the 13 eval TUNE scenes) |

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
# Freeze the printed pair before the single fine-tuned TEST sweep:
venv/bin/python train/sweep.py --model models-ft --name ft --set test --iou 0.4
venv/bin/python train/gate.py final train/results/sweep-base-test-iou0.7.json \
  train/results/sweep-ft-test-iou0.4.json --conf 0.01 --base-conf 0.05
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
`score > conf`, matching the runner. The final JSON line records frozen `conf`, `iou`, and `base_conf`.

TEST compares ft at its frozen conf against base at the base conf frozen on validation: pooled GUI `web_precision` and `web_recall` each drop
by at most 2 points, with the same terminal checks. The frozen pair is evaluated
once on eval TEST plus terminal test. Per-category TEST web/native metrics and
independent-subset metrics are informational. A TEST scene is independent when no
group containing it also contains a TUNE scene (ungrouped scenes are independent).
`eval_all.sh` remains a legacy fixed-threshold report producer, not a selection gate.

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

TEST runs per model: **base 1, ft1 1, ft2 0, ft3 0 (planned 1)**.

### Limitations

- Web val has 805 boxes: precision SE is ≈1.7 points, so the 2-point tolerance is ≈1 SE.
- Synthetic native val is a regression guard, not a proxy for real apps; its boxes
  are 3–15× larger than TEST native boxes.
- TUNE/TEST page/session sharing (`eval/groups.json`) is kept; independent metrics
  are informational.
- About 6% of web boxes are tiny.

## Results

Validation freezes **conf 0.01 / IoU 0.4**. The final TEST gate **fails**: full web
precision drops 9.13 percentage points, beyond the 2-point allowance. All other checks pass.
No TEST-driven retuning follows this result; installed model metadata remains unchanged.

| Set | Model | conf | IoU | Web P | Web R | Terminal link R | Terminal FP/screen |
|---|---|---:|---:|---:|---:|---:|---:|
| Selection | base | 0.05 | 0.7 | 39.88% | 77.14% | 47.57% | 51.050 |
| Selection | ft (frozen) | 0.01 | 0.4 | 41.74% | 77.89% | 99.76% | 0.583 |
| TEST full | base | 0.05 | 0.7 | 55.87% | 64.95% | 44.09% | 44.025 |
| TEST full | ft (frozen) | 0.01 | 0.4 | 46.74% | 77.24% | 100.00% | 0.625 |
| TEST independent | base | 0.05 | 0.7 | 66.67% | 58.04% | — | — |
| TEST independent | ft (frozen) | 0.01 | 0.4 | 54.26% | 69.10% | — | — |

The independent scenes are lobsters, mdn, github, go, httpbin-form and firefox-menu.
“Web” includes native GUI scenes in the eval TEST split. Terminal columns use the entire
corresponding terminal split, not the independent web subset.

The installed `terminal-v1` metadata remains conf 0.075 / IoU 0.4; this historical setting
is not validated by the new frozen-pair gate. Export accepts optional `NAME`, `CONF` and
`IOU` variables and writes `model.json` only when at least one is supplied. Explicit runner
flags override metadata.

## Model versions

- **terminal-v1** = `runs/ft/weights/best.pt` (epoch 39 of 40).
  SHA-256 of `models-ft/icon_detect-1280.ncnn.bin`:
  `184b0c0d23c77b276664cdf7cf1192d7a06b2d2e5096610f90428c9c4b0cf4f2`.

## Next steps

- More and more varied web/GTK training data (the web collection stalled at 264 of 500 pages).
- GUI terminal chrome (GNOME Console, Ptyxis, Ghostty) screens, not yet in the data.
