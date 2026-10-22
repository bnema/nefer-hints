# Extended clickable-target evaluation

## Present state

25 captured, annotated 1920×1080 scenes: 13 Chromium web (including two dark
variants), 8 native GTK, one Firefox hamburger scene and 3 Mattermost scenes.
1,704 targets. Primary GT
is DOM for web (with recorded visual corrections), manual for native/Firefox.
Every web `_gt.png` was opened for visual mapping review. Fullscreen viewport
origin is (0,0), DPR 1; Chromium startup alone left an 87px toolbar, fixed by F11.
Single-annotator exploratory set, not a comprehensive clickability benchmark.
[Scene inventory, measurements and miss counts](results/table.md).

## Reproduce

```sh
python -m venv --system-site-packages venv
venv/bin/pip install websocket-client==1.9.2
# Pillow and NumPy supplied by system site packages; never replace system torch.
dbus-run-session -- venv/bin/python eval/capture_web.py
# Capture saves verified:false. Open every overlay before setting true.
# review_web.py records the corrections for THESE saved frames, not future pages.
dbus-run-session -- venv/bin/python eval/capture_native.py
# annotate_native.py / annotate_firefox.py record manual coordinates for saved frames.
venv/bin/python -m unittest discover -s eval -v
venv/bin/python eval/score.py --runner-root ../ncnn-runner
venv/bin/python eval/report.py
```

Capture scripts use the provided NeferWL binary and grim. External pages change:
manual coordinates and GT must be reviewed anew after recapture, never blindly
reapplied. DOM extraction uses innermost matching elements, per-client-rect boxes,
viewport/overflow clipping, ancestor visibility/opacity, minimum 4×4 dimensions,
and centre hit testing. Light DOM misses shadow DOM and iframe controls; visible
corrections are explicitly recorded in `review_web.py`. Computed pointer cursor
is inherited; some innermost fragments are consequently classified `other`.
No detector predictions were used to construct GT.

`scenes.json` maps scene to category; `split.json` assigns 13 tune/12 test,
covering dense text, content, modern web, forms, sidebar docs, themes, GTK and
menus. HN light/dark stay in tune, but Arch light/dark cross splits: the test is
scene-level, **not independent by site/application**. TUNE scenes are used for training data; confidence and NMS IoU are selected on
separate web and terminal validation sets, then frozen before the final TEST gate.
`groups.json` records shared pages/app sessions for informational independent-subset metrics.
No old PoC scenes are included.

## Privacy

Apps ran under a private dbus-run-session and headless Wayland display, with
HOME `/tmp/nh-eval/home`, XDG config/data/cache/state below it, fresh Chromium
profiles and a dedicated fresh Firefox profile, no accounts except fictional
local Mattermost users. NEFERWL_STATE, NEFERWL_SLOT and DISPLAY are removed.
File managers opened only `Fictional/` with Documents, Music, Pictures, Projects,
notes.txt and a fictional report. `GIO_USE_VOLUME_MONITOR=unix` disables GVfs
host-volume names; initial captures exposing those labels were overwritten and
never committed. No weights, venvs, builds or browser profiles are tracked.
Historical real-home PoC images and associated GT/dumps were removed, including
nautilus-menu; old numeric scores were not recomputed. Git history is unchanged.

## Scoring and results

Persistent ncnn Vulkan runner, RX 9070 XT; whole frames, imgsz 1280, IoU NMS .7,
thresholds .05/.25. Maximum bipartite centre-inside matching; duplicates count in
the prediction denominator. Micro P/R aggregates by scene, split, category;
kind recall/miss counts in `results/scores.json`. Kind precision is null because
unmatched predictions have no GT kind; latency is frame-level, not per kind.

| Split | Threshold | Precision | Recall | Protocol median ms |
|---|---:|---:|---:|---:|
| tune | .05 | 64.45% | 57.61% | 90.35 |
| test | .05 | 55.84% | 65.25% | 88.45 |
| tune | .25 | 77.49% | 40.19% | 89.67 |
| test | .25 | 66.81% | 48.25% | 90.58 |

One timing sample per scene/threshold, excluding PNG decode; not a stable latency
benchmark. Protocol includes transport/preprocessing/NMS, inference excludes them.
`out/`: GT green, TP blue, FP red, missed yellow. Raw predictions and matching
are preserved in `results/predictions.json`.

Tune misses at .05: 240 small text links, 165 other fragments, 19 icons/buttons,
6 fields, 6 other links, 6 menu items, 1 row/file (443 total). At .25: 325 small
links, 230 other fragments, 38 icons/buttons, 12 fields, 12 other links,
6 menu items, 2 rows (625 total). Small = height <18 or width <16. These are
morphology proxies, not proven causes; merged-link attribution remains pending.
The switcher has 20 innermost DOM fragments, and background detections count as
FP when the modal covers them. The fresh timing run was slower than the previous
run; one sample per scene is not a stable performance comparison.

### Mattermost reproduction

Start a new rootless preview container on `127.0.0.1:8065` with
`MM_TEAMSETTINGS_ENABLEOPENSERVER=true` and `MM_SERVICESETTINGS_ENABLELOCALMODE=true`,
then run `venv/bin/python eval/seed_mattermost.py`. Capture with:

```sh
dbus-run-session -- venv/bin/python - <<'PYTHON'
import sys
sys.path.insert(0, 'eval')
import capture_web as c
c.PAGES = [(n, 'http://127.0.0.1:8065/fictional-demo/channels/planning', 'mattermost')
           for n in ('mattermost-channel', 'mattermost-thread', 'mattermost-switcher')]
c.main()
PYTHON
docker rm -f nh-eval-mattermost
```

REST login supplies MMAUTHTOKEN; explicit cookie path `/` and MMUSERID are needed
by this preview. CDP evaluation awaits promises, reports JS exceptions and maps
undefined to None. Channel DOM waits are bounded to 30s. Browser-app chooser and
onboarding are dismissed before capture. All three final overlays were opened:
channel with three visible reply groups, RHS with root plus two replies, Ctrl+K
switcher. Channel/RHS go to tune; switcher to test. Same app spans the splits.
Only fictional users/posts were present; container removed after capture.

## Failed / pending work

- Reddit returned “Your request has been blocked due to a network policy”;
  excluded, Lobsters used. Guardian/BBC/W3Schools/YouTube produced no visible
  targets after the bounded wait; skipped, httpbin form and Python docs added.
  `results/web-capture-errors.json` records failures.
- Mattermost initial CDP error resolved in this follow-up. Historical diagnostics,
  image digest and completion status are in `results/mattermost-status.json`;
  `mattermost-capture-errors.json` is empty for the successful final capture.
- GTK light/dark paired variants not completed (captured Nautilus is dark).
- Scale 1.5 documented as `output.<name>.scale` in NeferWL config, not yet
  exercised; three scale variants pending, not declared unsupported.
- VSCodium, Dolphin, gnome-control-center not installed; pending, not installed.
- Target ~26 scenes: 25 admitted. Manual annotation quality and
  full causal miss review would benefit from a second annotator.

Six matching/aggregation unit tests pass, and the scorer ran successfully on all
25 frames at both thresholds. No public contracts changed, no push or merge.
