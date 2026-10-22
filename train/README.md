# Fine-tuning icon_detect for terminals

The fine-tuned model detects only links (URLs, `file://`, `www.`, `domain.tld/path`, emails) inside
terminal text and keeps detecting GUI targets. Bare paths, prompts and status bars are hard negatives.

## Data

| Set | Train | Val | Test | Labels |
|---|---:|---:|---:|---|
| Synthetic terminal screens (`terminal/`) | 500 | 60 | 40 | magenta-diff link boxes, see `terminal/README.md` |
| Web pages (`web/`) | 264 | 39 | - | DOM clickables, see `web/README.md` (includes the 13 eval TUNE scenes) |

The web pages stop the model from forgetting GUI targets. The eval TEST scenes are never trained on.

## Training

```sh
venv/bin/python train/finetune.py --batch 4 --workers 2     # runs/ft/weights/best.pt
```

Start: `weights/base.pt` (OmniParser v2 icon_detect). 1280 px, AdamW lr0 0.002, 40 epochs, patience 10,
light augmentation (no flips, no mosaic), fp32 (`amp=False`: fp16 with MIOpen gives wrong results).
About 2 min/epoch on an RX 9070 XT; run it as a memory-capped systemd user unit.

## Export and evaluation

```sh
NAME=terminal-v1 CONF=0.075 IOU=0.4 train/export_ft.sh runs/ft/weights/best.pt                         # models-ft/ (ncnn), runner hello check
venv/bin/python train/sweep.py --model models-ft --name ft --iou 0.4
python3 train/gate.py --sweep train/results/sweep-base.json train/results/sweep-ft.json
```

`sweep.py` runs the runner once per image at conf 0.01 and filters scores offline (0.01 to 0.5), on
the eval TEST split and the terminal test set. `gate.py --sweep` picks the lowest fine-tuned conf that
passes every check against the base model at its shipped settings (conf 0.05, NMS IoU 0.7):

- eval TEST precision and recall each drop by at most 2 points;
- terminal false positives at most 1.0 per screen and at least 80 % below base;
- terminal link recall at least 80 %.

`eval_all.sh` and `gate.py` without `--sweep` give the fixed 0.05/0.25 report.

## Results

| Model | conf | IoU | Eval TEST P | Eval TEST R | Terminal link R | Terminal FP/screen |
|---|---:|---:|---:|---:|---:|---:|
| base | 0.05 | 0.7 | 55.9 % | 64.9 % | 44.1 % | 44.0 |
| fine-tuned | 0.05 | 0.7 | 46.2 % | 68.0 % | 100 % | 0.28 |
| **fine-tuned (shipped)** | **0.075** | **0.4** | **55.4 %** | **63.6 %** | **100 %** | **0.25** |

The fine-tuned model passes the gate only with NMS IoU 0.4: at 0.7 it emits overlapping duplicates that
cost precision. Base at IoU 0.4 reaches P 62.5 % / R 63.7 % at conf 0.05, so the fine-tuned model still
trails the best base setting on GUI precision. Per scene, it gains on dense text and Mattermost and
loses on GitHub, MDN, forms and the GTK editor.

The shipped model directory carries `model.json` with name `terminal-v1`, conf 0.075
and IoU 0.4; the runner uses these defaults without flags. Export accepts optional
`NAME`, `CONF` and `IOU` environment variables (any subset) and writes `model.json`
only when at least one is supplied. Explicit runner flags override the metadata.

## Model versions

- **terminal-v1** = `runs/ft/weights/best.pt` (epoch 39 of 40).
  SHA-256 of `models-ft/icon_detect-1280.ncnn.bin`:
  `184b0c0d23c77b276664cdf7cf1192d7a06b2d2e5096610f90428c9c4b0cf4f2`.

## Next steps

- More and more varied web/GTK training data (the web collection stalled at 264 of 500 pages).
- GUI terminal chrome (GNOME Console, Ptyxis, Ghostty) screens, not yet in the data.
