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

## Current dataset

- Train: **881 collected pages across 58 sites + 13 eval TUNE scenes = 894 images**.
  This expansion adds **630 kept pages from 31 new sites** (251 collected pages previously).
- Validation: **39 pages**, frozen byte-for-byte (images and labels):
  kde 9, nasa 5, osm 8, rfceditor 11, ziglang 6. Collection never writes validation.
- The expanded plan contains 725 new tasks and is exhausted: 684 initial captures,
  41 collection failures, then 54 quality rejections (46 Bulma promotional modals and
  8 Open Library Chromium error pages). No Bulma captures remain.
- Bootstrap (56) and Pico (33) include form controls, validation, navigation, tables,
  and component examples. Other additions cover registries, forums, search results,
  wiki pages, documentation sidebars, and GitLab project lists.
- Ten new images receive visual box-overlay checks; the recurring Bulma pattern also
  receives a full contact-sheet review. These are spot checks, not exhaustive certification.
- `manifest.json` preserves all 290 original entries and records new successes and failures,
  including final URLs and quality rejection reasons. The 13 TUNE scenes are separate.
- `data/` (including plan, images, labels) is ignored and has no tracked files; the manifest,
  collector, tests, and this README are tracked. Existing filenames remain unchanged.

### Train images per site

Site | Images
--- | ---:
apnews | 3
bootstrap | 56
caddy | 19
codeberg | 9
commons | 7
cratesio | 7
debian | 23
debianwiki | 4
distrowatch | 23
docsrs | 21
eval_TUNE | 13
fedora | 5
flathub | 19
freedesktop | 5
gitlabexplore | 3
gnome | 5
gnomediscourse | 21
goodreads | 4
gtkdocs | 22
gutenberg | 9
haskell | 5
hexdocs | 3
htmx | 23
ietf | 4
imdb | 2
kernel | 21
kerneldocs | 21
lwn | 23
marginalia | 22
metacpan | 23
mozilla | 4
nginx | 22
nixos | 7
npmjs | 6
nprtext | 18
openlibrary | 7
packagist | 23
pico | 33
postgresdocs | 20
pypi | 17
pythondiscuss | 23
readthedocs | 19
repology | 21
requestsdocs | 19
rubygems | 22
rustbook | 20
rustlang | 22
rustusers | 21
sqlite | 21
srht | 11
stackoverflow | 11
svelte | 22
tailwind | 21
ubuntu | 5
vue | 23
w3 | 4
weathergov | 6
wikidata | 16
wiktionary | 5

## Collection and recovery

```sh
venv/bin/python train/web/collect_web.py plan --new-sites
venv/bin/python train/web/collect_web.py run --new-sites --workers 5
venv/bin/python -m unittest train.web.test_collect
```

Planning appends only missing variants; `--new-sites` limits discovery/collection to the
32 additions in `NEW_SITES`. Legacy IDs retain their original plan indices; new IDs use
site + a short SHA-256 of URL, size, zoom, dark mode, and scroll. Existing images in either
split are skipped. Eval-domain exclusions guard planned URLs, discovery redirects, and
final URLs (including subdomains). Validation sites are skipped even if files are absent.

Each page has a 60-second hard deadline, including session startup. A page failure
invalidates the CDP session; the next task kills/relaunches Chromium and the compositor
with a fresh profile. Sessions also restart every 40 attempts. Fake HOME/config/cache
directories are recreated automatically. Worker count is restricted to 1–5.
Workers checkpoint after every attempt; `run` recovers checkpoints and atomically merges
results into the tracked manifest without replacing existing successes or quality rejections.
Interrupted tasks without images remain eligible on the next run.

Title/body challenge checks, at least three usable boxes, viewport/DPR checks, HTTP(S)
final URLs, and visible modal checks reject unusable pages. Bulma's recurring promotional
wall has an additional text-pattern check. Chromium error pages are rejected. Small
non-blocking banners are not universally removed; Open Library's donation banner remains.

Collection failures by site (before visual rejections): Pico 18, Open Library 6,
Read the Docs 3, Rust Book 4, Wikidata 4, NPR text 3, SQLite 1, Repology 1, Caddy 1.
Two old docs.rs smoke attempts also fail with empty titles/no boxes. Failures are mostly
low-box pages and title/body filters, not a persistent CDP stall. Browser-kill and injected
modal smoke checks verify that a rejected/failed page is followed by a successful capture.
No retraining or precision evaluation is part of this collection change.

## Executable configuration

Set `NEFERWL` to the compositor executable; by default `neferwl` is resolved on
`PATH` (a missing executable is an error). Evaluation/export scripts use
`NEFER_HINTS_RUNNER`, defaulting to `<repo>/build/nefer-hints`. Shell scripts
accept `PY` for Python, defaulting to `<repo>/venv/bin/python`.
