# Extended clickable-target evaluation

## Present state

25 captured, annotated 1920×1080 scenes: 13 Chromium web (including two dark
variants), 8 native GTK, one Firefox hamburger scene and 3 Mattermost scenes.
1,704 targets. Primary GT
is DOM for web (with recorded visual corrections), manual for native/Firefox.
Web `_gt.png` overlays support visual mapping review. Fullscreen viewport
origin is (0,0), DPR 1; F11 removes the Chromium toolbar.
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
venv/bin/python eval/score.py --runner-root .
venv/bin/python eval/report.py
```

Capture scripts use the provided NeferWL binary and grim. External pages change:
manual coordinates and GT must be reviewed anew after recapture, never blindly
reapplied. DOM extraction uses innermost matching elements, per-client-rect boxes,
viewport/overflow clipping, ancestor visibility/opacity, minimum 4×4 dimensions,
and centre hit testing. Light DOM misses shadow DOM and iframe controls; visible
corrections are explicitly recorded in `review_web.py`. Computed pointer cursor
is inherited; some innermost fragments are consequently classified `other`.
GT construction uses no detector predictions.

`scenes.json` maps scene to category; `split.json` assigns 13 tune/12 test,
covering dense text, content, modern web, forms, sidebar docs, themes, GTK and
menus. HN light/dark stay in tune, but Arch light/dark cross splits: the test is
scene-level, **not independent by site/application**. TUNE scenes are used for training data; confidence and NMS IoU are selected on
separate web and terminal validation sets, then frozen before the final TEST gate.
`groups.json` records shared hosts/pages/app sessions for informational independent-subset
metrics in `train/sweep.py`: a TEST scene is independent if no group containing it
also contains a TUNE scene; ungrouped scenes are independent. `score.py` does not
read this metadata. Stored `*_independent` metrics use grouping without github/login
and mdn/mdn-forms, so they include github and mdn despite sharing hosts with TUNE
pages and are optimistic. Truly independent scenes are lobsters, go, httpbin-form
and firefox-menu. Stored TEST metrics stay unchanged.
No old PoC scenes are included.

## Privacy

Capture scripts run under a private dbus-run-session and headless Wayland display, with
HOME `/tmp/nh-eval/home`, XDG config/data/cache/state below it, fresh Chromium
profiles and a dedicated fresh Firefox profile, no accounts except fictional
local Mattermost users. The environment allowlists PATH and a fixed locale, uses a private 0700 runtime
directory, and excludes host display variables and credentials such as SSH_AUTH_SOCK.
File managers open only `Fictional/` with Documents, Music, Pictures, Projects,
notes.txt and a fictional report. `GIO_USE_VOLUME_MONITOR=unix` disables GVfs
host-volume names. No weights, venvs, builds or browser profiles are tracked.

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
FP when the modal covers them. One sample per scene is not a stable performance comparison.

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
onboarding are dismissed before capture. The three overlays show a channel with three visible reply groups, RHS with
root plus two replies, and a Ctrl+K switcher. Channel/RHS go to tune; switcher to test. Same app spans the splits.
Only fictional users/posts belong in the capture container; remove it after capture.

## Failed / pending work

- `results/web-capture-errors.json` contains three Mattermost entries
  (`mattermost-channel`, `mattermost-thread`, `mattermost-switcher`), each with
  the error `"'value'"`; it does not record public-site failures.
  `mattermost-capture-errors.json` is empty. Diagnostic details are in
  `results/mattermost-status.json`.
- GTK light/dark paired variants not completed (captured Nautilus is dark).
- Scale 1.5 documented as `output.<name>.scale` in NeferWL config, not yet
  exercised; three scale variants pending, not declared unsupported.
- VSCodium, Dolphin, gnome-control-center not installed; pending, not installed.
- Target ~26 scenes: 25 admitted. Manual annotation quality and
  full causal miss review would benefit from a second annotator.
