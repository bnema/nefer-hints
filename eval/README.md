# Extended detector evaluation — partial implementation

## Present state

No evaluation scenes have been captured or annotated here. `scenes.json` and
`split.json` are intentionally empty; there are **no measured dataset results**.
Do not substitute historical PoC scores or the synthetic integration test for
extended-set accuracy. Capture/DOM extraction, native annotation, visual review,
stratified assignment and tune miss analysis remain unfinished.

Privacy cleanup removed both historical `nautilus-home` and `nautilus-menu`
frames, annotated frames, hint dumps and GT from the OmniParser PoC. The latter
also showed the real home directory. No result images existed there. Historical
numeric results were not recomputed. This does not erase earlier Git history.

## Implemented scoring

```sh
python -m venv --system-site-packages venv
venv/bin/python -m unittest discover -s eval -v
venv/bin/python eval/score.py --runner-root ../ncnn-runner
```

Pillow and NumPy are required (available in the system Python during checks).
The final command deliberately fails until scenes exist. Supply a checkout with
`build/nefer-hints` and `models/`; the existing `tests/protocol.py` client is reused
without modifying its public contract. Its stderr log is written under that
checkout's ignored `weights/` directory.

For each scene, add:

- `frames/<scene>.png`: original capture, target 1920×1080.
- `gt/<scene>.json`: `boxes`, parallel `kinds`, `source` (`dom` or `manual`),
  `notes`, and `verified: true` **only after visual inspection**.
- `gt/<scene>_gt.png`: inspected overlay (capture tooling still pending).
- `scenes.json`: mapping scene name to `{"category": "dense_text"}` etc.
- `split.json`: mapping each scene to `"tune"` or `"test"`.

Scoring uses whole-frame 1280 inference at .05 and .25, IoU NMS .7, and maximum
bipartite centre-inside matching. Duplicate predictions remain in the precision
denominator. `results/scores.json` contains scene/split/category micro P/R,
frame-level inference/protocol latency and kind recall/miss counts;
`results/predictions.json` preserves raw responses and matching.
`out/<scene>_<threshold>.png`: GT green, missed GT yellow, TP blue, FP red.

Kind precision is explicitly null: this detector has no kind labels, and false
positives have no ground-truth kind. Latency is frame-level, not attributable to
individual kinds. Timing is one sample per scene/threshold, not a benchmark.
Miss-by-kind counts do not establish causes such as merged adjacent links;
those require manual tune-overlay review. No cause counts are claimed yet.

## Checks completed

- Six unit tests: augmenting path, duplicate denominator, empty sets,
  centre-vs-IoU, boundary inclusion, micro aggregation.
- Empty dataset is rejected before launching the detector.
- Temporary synthetic white 1920×1080 frame exercised both thresholds against
  the real ncnn Vulkan runner (RX 9070 XT), JSON results and both PNG overlays.
  The synthetic frame is not part of the dataset.

## Capture privacy requirements (not yet exercised)

Every app must run under `dbus-run-session`, in headless NeferWL only, with fresh
`HOME=/tmp/nh-eval/home`, XDG config/data/cache below it, fictional files, fresh
Chromium/Firefox profiles, and `env -u NEFERWL_STATE -u NEFERWL_SLOT` plus the
headless `WAYLAND_DISPLAY`. Never capture real profiles/accounts. Review every
frame and GT overlay before adding it. Public pages must be logged out.
Mattermost must use only seeded fictional users/posts and a disposable rootless
container, removed at the end. No app/container was launched during these checks.

## Pending scene inventory

| Category | Planned scenes | Captured | Split / GT source |
|---|---|---:|---|
| Web | HN, Reddit (or fallback), Lobsters, Wikipedia Wayland, MDN article, Arch, news, GitHub Linux, login, forms, YouTube, Go docs | 0 | pending / DOM |
| Theme variants | Two web dark variants | 0 | pending / DOM |
| Mattermost | Channel, thread panel, switcher/menu | 0 | pending / DOM |
| Native GTK | Nautilus icons/list/context/main menu + light/dark variants; Thunar window/menu; text editor window/menu | 0 | pending / manual |
| Firefox | Page/chrome with hamburger menu | 0 | pending / manual |
| Scale variants | Three scenes at 1.5 | 0 | pending |

NeferWL `docs/config.md` documents `output.<name>.scale` (1–4, including 1.5);
headless operation at that scale has **not** been tested, so variants are pending,
not classified as unsupported. The headless documentation was read.
Missing installed apps: VSCodium, Dolphin, gnome-control-center remain pending;
do not install them for this evaluation.

## Results

| Split | Threshold | Precision | Recall |
|---|---:|---:|---:|
| tune | .05 | not measured | not measured |
| tune | .25 | not measured | not measured |
| test | .05 | not measured | not measured |
| test | .25 | not measured | not measured |

The requested extended evaluation is not complete. No detector tuning, public
contract changes, dependency installation, model copying, push or merge occurred.
