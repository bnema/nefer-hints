# Extended clickable-target evaluation

## Present state

22 captured, annotated 1920×1080 scenes: 13 Chromium web (including two dark
variants), 8 native GTK, one Firefox hamburger scene. 1,440 targets. Primary GT
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

`scenes.json` maps scene to category; `split.json` assigns 11 tune/11 test,
covering dense text, content, modern web, forms, sidebar docs, themes, GTK and
menus. HN light/dark stay in tune, but Arch light/dark cross splits: the test is
scene-level, **not independent by site/application**. No tuning was performed.
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
| tune | .05 | 62.77% | 57.68% | 28.55 |
| test | .05 | 62.81% | 66.35% | 26.74 |
| tune | .25 | 77.75% | 37.08% | 26.82 |
| test | .25 | 78.16% | 49.30% | 26.70 |

One timing sample per scene/threshold, excluding PNG decode; not a stable latency
benchmark. Protocol includes transport/preprocessing/NMS, inference excludes them.
`out/`: GT green, TP blue, FP red, missed yellow. Raw predictions and matching
are preserved in `results/predictions.json`.

Tune misses at .05: 240 small text links, 76 other fragments, 6 other text links,
6 icons/buttons, 6 menu items, 4 fields, 1 row/file (339 total). At .25: 325 small
text links, 133 other fragments, 16 icons/buttons, 12 other links, 10 fields,
6 menu items, 2 rows (504 total). Small = height <18 or width <16. These are
reproducible **morphology proxies**, not experimentally established causes;
merged-adjacent-link attribution remains pending manual prediction review.

## Failed / pending work

- Reddit returned “Your request has been blocked due to a network policy”;
  excluded, Lobsters used. Guardian/BBC/W3Schools/YouTube produced no visible
  targets after the bounded wait; skipped, httpbin form and Python docs added.
  `results/web-capture-errors.json` records failures.
- Mattermost preview image digest and exact failure in
  `results/mattermost-status.json`. Rootless localhost container started; seed
  created five fictional users, one team, four channels, 32 posts, 16 replies,
  eight reactions. Initial signup 403 fixed with environment configuration.
  CDP login navigation returned no `value` (KeyError) for all three captures;
  no Mattermost scene admitted. Container removed with `docker rm -f`.
  Seed: run `seed_mattermost.py` against a **new disposable** preview container
  published only at `127.0.0.1:8065`, with
  `MM_TEAMSETTINGS_ENABLEOPENSERVER=true` and
  `MM_SERVICESETTINGS_ENABLELOCALMODE=true`. Always remove it afterwards.
- GTK light/dark paired variants not completed (captured Nautilus is dark).
- Scale 1.5 documented as `output.<name>.scale` in NeferWL config, not yet
  exercised; three scale variants pending, not declared unsupported.
- VSCodium, Dolphin, gnome-control-center not installed; pending, not installed.
- Target ~26 scenes not reached; 22 admitted. Manual annotation quality and
  full causal miss review would benefit from a second annotator.

Six matching/aggregation unit tests pass, and the scorer ran successfully on all
22 frames at both thresholds. No public contracts changed, no push or merge.
