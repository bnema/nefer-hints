# Web anti-forgetting data (DOM labels)

`collect_web.py` reuses the eval pipeline (headless NeferWL + Chromium fullscreen + CDP, `eval/dom.js`
clickable definition, boxes pad 0, multiplied by devicePixelRatio for 90/110 % browser zoom).
Differences from eval: the frame is the compositor screenshot (`--screenshot latest.png`, grim is
refused by the headless compositor), and dark mode is prefers-color-scheme + auto-dark (as eval's `-dark`
scenes, ~33 % of images). Eval domains (hn, lobste.rs, wikipedia, mdn, archlinux, github, go.dev,
httpbin, python docs, local Mattermost) are excluded. The blocked set combines the existing
exclusions with URL hostnames from `eval/scenes.json`, including subdomains. Redirects to
blocked hosts are logged and skipped before saving images or labels. New manifest entries
include `final_url` (null if navigation failed before it could be read).
`add_eval_tune.py` adds the 13 eval TUNE scenes
(never TEST) to train.

## Final counts
- train: 251 collected pages (27 sites) + 13 eval TUNE scenes = **264 images**
- val: **39 pages** from 5 held-out sites (kde, nasa, osm, rfceditor, ziglang); split by site.
- Sizes: 1920x1080 all but 39 images at 2560x1440 (see stall below); zoom 90/100/110 = 76/145/69.
- `manifest.json` lists every kept page (url, site, size, zoom, dark, scroll, box count). Not all
  pages are guaranteed block/consent-free; no automatic wall filtering was applied beyond titles.

## Stall (target 500 + 50 not reached)
Collection ran 18:00-19:23. About 250 images arrived in the first 30 minutes, then the headless
Chromium/CDP connections died (every later attempt: `Connection timed out`, ~277 attempts), not the
sites. The orchestrator decided to stop and not retry; the run was killed. Earlier failures also came
from sites returning no clickable boxes. Sites that blocked or timed out most: bbc, guardian,
weathergov, codeberg, osm, gutenberg. Several sites therefore have few or no images.

## Executable configuration

Set `NEFERWL` to the compositor executable; by default `neferwl` is resolved on
`PATH` (a missing executable is an error). Evaluation/export scripts use
`NEFER_HINTS_RUNNER`, defaulting to `<repo>/build/nefer-hints`. Shell scripts
accept `PY` for Python, defaulting to `<repo>/venv/bin/python`.
