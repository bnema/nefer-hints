# Native GUI training data

`collect.py` generates fullscreen GTK4/libadwaita (`gtk_app.py`) and Qt6/PySide6
(`qt_app.py`) screenshots with single-class YOLO clickable labels in
`data/native/{train,val}/{images,labels}`. The apps are synthetic: they build a
seeded window from one of ten templates and export the geometry of every enabled,
visible interactive widget. Label rules follow [CONTRACT.md](CONTRACT.md): widget
allocations clipped to the output, boxes under 4×4 px dropped, disabled controls,
static text and text-view bodies never labelled, targets under an open popup
removed, scrolled targets kept only when at least half visible. Each screen needs
at least three boxes and matching screenshot/label sizes.

Validation holds out the entire `preferences-dialog` and `table` templates in both
toolkits; the other eight templates are training only. The deterministic plan has
260 train and 50 validation screens per toolkit (620 total). Theme, accent, font
scale and output size (1920×1080 or 2560×1440) vary by seed. Actual collected
counts: 260 train and 50 validation screens per toolkit (620), no failed screens. `manifest.json` records successful screens; reruns
skip existing images and recover worker checkpoints.

```sh
venv/bin/python train/native/collect.py plan
# Set NEFERWL to a headless-capable executable if it is not on PATH.
venv/bin/python train/native/collect.py run --workers 3
venv/bin/python train/native/collect.py run --workers 3 --toolkit gtk --limit 10
venv/bin/python train/native/collect.py stats
```

Apps run with system Python (PyGObject + GTK4/libadwaita, or PySide6); collection
uses the venv and `grim`. Each worker isolates HOME/XDG under `/tmp/nh-native`,
uses a 60-second screen timeout, and restarts the compositor on failure, size
changes or every 50 screens.

## Alignment previews

`preview.py` (GTK) and `preview_qt.py` (Qt) capture templates under an isolated
headless compositor and draw the label boxes over the screenshot, in
`/tmp/nh-native-gtk/overlays` and `/tmp/nh-native-qt/overlays`. Run them with a
Python that has Pillow after changing an app, and inspect the overlays.

```sh
python train/native/preview.py --size 2560x1440 --templates context-menu --seeds 3 --themes dark
python train/native/preview_qt.py
```

## Limits

- Each launch exports one settled frame; labels do not follow later interaction.
- One output at scale 1 only.
- GTK: programmatic popovers do not autohide (no input serial); `Adw.Dialog` is
  hosted in the main window so modal geometry shares its coordinate space;
  ColumnView header/row discovery walks GTK internals (verified on GTK 4.24).
- Qt on Wayland: menus use non-grabbing tooltip-type popups, and dialog positions
  come from the centred transient anchor, since Wayland exposes no global
  toplevel coordinates.
