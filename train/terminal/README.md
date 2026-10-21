# Terminal dataset (labelled by colour diff)

Goal: inside terminal text areas the detector must box only **links** (URLs, `www.…`,
`domain.tld/path`, e-mails), never prompts, status bars, commands or plain paths.

## Pipeline
- `gen.py`: seeded generator of fake screens (prompts `❯` / `user@host:~/proj$`, git log/status/diff,
  compiler errors, test output, tables, JSON, code, box-drawing panels, progress bars, logs, tmux-like
  coloured status bar `DP-2 [x] C 29% M 86% 17:25`, `[0] 1:fish* 2:nvim-`). Links in ~60 % of windows
  (0-6, fictional domains); bare paths such as `/usr/lib/x`, `src/main.go:12` are hard negatives.
  All text is synthetic; it reaches the terminal through `cat` of a generated file.
- `themes.py`: 4 dark + 2 light schemes, no colour near #FF00FF (asserted).
- `make_data.py`: headless NeferWL (`layout.max-columns=2`, overflow fixed, no bars, hint off) +
  kitty / foot / alacritty, 1-4 tiled windows, 1920x1080 (75 %) or 2560x1440, fonts 10-16 pt.
  Everything runs under `env -i` with a fake HOME in `/tmp/nh-term`.
- Labelling: each screen is captured twice with identical text/layout. A = normal colours (training
  image). B = links painted truecolor fg=bg `#FF00FF` (`#F700F7` on odd rows so that a link wrapped
  over two rows stays two separable boxes). Pixels within ±3 of those colours, connected components
  (one box per link segment per text row), 2 px padding. Cursor hidden, blink disabled.
- Automatic checks per scene (3 retries): A and B differ only inside link boxes (the compositor
  pointer area is ignored), number of boxes >= number of generated links, no box when 0 links.
  Manual check: `overlays/` (labels drawn on A) was opened and inspected for alignment.

## Splits
| split | screens | fonts | seeds | without links |
|---|---|---|---|---|
| train | 500 | JetBrains Mono, DejaVu Sans Mono, Hack, FiraCode Nerd Font Mono | 1000.. | 88 |
| val | 60 | same | 5000.. | 7 |
| test | 40 | **IBM Plex Mono only** | 9000.. | 15 (34 with status bar) |

`manifests/manifest_*.json` list terminal, font, size, theme, cols/rows, link and box counts.
Generated images/labels are in `data/terminal/{train,val,test}/{images,labels}` (git-ignored).

Out of scope for now (pending): Ghostty, GUI terminals (gnome-console, ptyxis) and their window chrome.

```sh
venv/bin/python train/terminal/make_data.py --out data/terminal --split train --n 500 --seed0 1000 --workers 6 --overlays 10
venv/bin/python train/terminal/make_data.py --out data/terminal --split val   --n 60  --seed0 5000 --workers 6
venv/bin/python train/terminal/make_data.py --out data/terminal --split test  --n 40  --seed0 9000 --workers 6
```
