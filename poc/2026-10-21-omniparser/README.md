# PoC 2026-10-21: OmniParser v2 vs NeferWL OCR

Seven NeferWL headless captures (1920×1080, scale 1), 595 clickable regions annotated by hand (single annotator, exploratory).

- Detector: `microsoft/OmniParser-v2.0`, `icon_detect/model.pt` (Hugging Face), Ultralytics 8.4, CPU torch, Ryzen 9 7900X3D.
- OCR: NeferWL `main` hint mode with `NEFERWL_HINT_DEBUG=1` (no AT-SPI targets in the private D-Bus session).
- Match: a prediction is a true positive when its centre falls in an unmatched ground-truth box.

## Results

| Method | Precision | Recall | CPU latency |
|---|---:|---:|---:|
| NeferWL OCR | 57 % | 5 % | 470–1700 ms |
| OmniParser 640 px, conf 0.25 | 87 % | 44 % | ~60 ms |
| OmniParser 1280 px, conf 0.05 | 71 % | 76 % | ~195 ms |
| OmniParser 1280 px, conf 0.25 | 90 % | 57 % | ~195 ms |
| OCR ∪ OmniParser 1280/0.25 | 85 % | 61 % | — |

Recall by kind at 1280 px, conf 0.05: files and rows 97 %, menu items 95 %, icons and buttons 76 %, text links 72 %.

Weak spot: dense text pages (Hacker News: 43 % recall). Main false positives: HN ranks, numbers in dates and code.

## Files

- `frames/`: captures, NeferWL hint dumps (`.json`, `.annotated.png`).
- `gt/`: ground truth per scene (`<scene>.json`, visual check `<scene>_gt.png`).
- `results/`: `predictions.json`, `scores.json`, `table.md`, FP reviews.
- `scripts/`: capture, detection, annotation and scoring scripts. Paths point to the original `/tmp/omniparser-eval` workspace.
- `neferwl-config`: config used for the headless runs.
