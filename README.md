# nefer-hints

Finds every clickable element of a screen image (links, buttons, menu items, list rows, files) for NeferWL's hint mode, from pixels only.

- Input: a screenshot of the focused output.
- Output: boxes with a calibrated "clickable" probability.
- Runs locally on the GPU. No screen content leaves the machine.
- NeferWL calls it as a subprocess, like tesseract; the compositor stays `CGO_ENABLED=0`.

## Pipeline

1. **Propose**: a UI element detector (OmniParser v2 `icon_detect`, YOLO) at 1280 px with a low threshold returns every candidate.
2. **Filter**: a small classifier scores each candidate crop and keeps the clickable ones.
3. AT-SPI targets from NeferWL, when an app exposes them, take priority.

## Layout

- `poc/`: dated experiments, each with its scripts, frames, ground truth and results.

## License

AGPL-3.0: the detector weights and Ultralytics are AGPL. NeferWL (GPLv3) can call it.
