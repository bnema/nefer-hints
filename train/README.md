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
24G), low CPU/IO weight and nice 10. `finetune.py` caps its GPU memory with `--vram-gib` (default
10 of 16 GiB) so the compositor keeps room for its framebuffers; an uncapped run fills VRAM and
freezes the desktop session. The cap needs `--batch 2`; Ultralytics accumulates gradients to a
nominal batch of 64, so the effective batch is unchanged.

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
  train/results/sweep-ft-test-iou0.4.json --conf 0.01
```

Selection uses web val and terminal val, never eval TUNE (used in training) or TEST.
The grid is 0.01–0.04 by 0.01, then 0.05–0.5 by 0.025. Offline filtering is strictly
`score > conf`, matching the runner. For each IoU, selection takes the lowest confidence
passing all five checks against base conf 0.05 / IoU 0.7:

- web precision and recall each drop by at most 2 percentage points;
- terminal FP/screen is at most 1.0 and at most 20% of base;
- terminal link recall is at least 80%.

Across these per-IoU candidates, highest web precision wins; higher web recall breaks ties.
The frozen pair is evaluated once on eval TEST plus terminal test with the same checks.
Independent-subset web metrics are informational: a TEST scene is independent when no group
containing it also contains a TUNE scene (ungrouped scenes are independent).
`eval_all.sh` remains a legacy fixed-threshold report producer; it is not a selection gate.

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
