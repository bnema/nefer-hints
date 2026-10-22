# Native GUI sample app contract (nefer-hints train/native)

Purpose: synthetic GTK4/libadwaita and Qt6 (PySide6) windows whose clickable widgets
are known programmatically, captured under the NeferWL headless compositor to train and
select a single-class "clickable" YOLO detector. Labels must match the eval definition of
a clickable target (eval/README.md, eval/dom.js): text_link, icon_button, row_file,
menu_item, field, tab, other. Disabled controls are NOT labelled. Targets whose centre is
covered by another surface (popover/menu) are NOT labelled. Static text, separators,
the text body of text views, window background are NOT labelled.

## Command line (system python: /usr/bin/python3)

  /usr/bin/python3 train/native/<gtk_app|qt_app>.py --seed N --template T \
      --theme light|dark --accent '#RRGGBB' --font-scale F --out DIR

- Deterministic from --seed (content strings, counts, which widgets are disabled,
  scroll offset). Content: fictional names only, no real user/host data.
- The window is fullscreen on the single headless output (GTK: Gtk.Window.fullscreen();
  Qt: showFullScreen()), so window coordinates == output pixels (scale 1).
- After the window and any opened popover/menu are mapped and laid out (wait for a few
  frame clock ticks plus ~1 s idle), write DIR/labels.json then DIR/ready (empty file).
  Stay open until killed (SIGTERM).
- Exit non-zero on any error (no ready file).

## DIR/labels.json

  {"toolkit": "gtk"|"qt", "template": T, "seed": N, "theme": ..., "accent": ..,
   "font_scale": F, "width": W, "height": H,
   "boxes": [[x0, y0, x1, y1, "kind"], ...]}

- Pixel coordinates in the output, integers, x1 > x0, y1 > y0, clipped to the output;
  drop boxes smaller than 4x4 after clipping. Box = the widget's allocated bounds
  (the clickable area), not its text.
- Only enabled, visible, mapped, sensitive widgets, and only the visible part of
  scrolled content (clip to the scrolled viewport; drop if < 50% visible).
- Popover / menu items: coordinates in the output (fullscreen toplevel at 0,0 plus the
  popup surface offset relative to its parent; GTK: Gdk.Popup position_x/position_y of
  the popover's surface + compute_bounds inside it; Qt: QMenu geometry/mapToGlobal).
  When a popup is open, drop toplevel targets whose centre lies under the popup rect.

## Templates (same names in both toolkits)

files-grid, files-list, settings, preferences-dialog, table, editor, context-menu,
app-menu, sidebar-nav, form

- files-grid / files-list: headerbar/toolbar icon buttons, path bar, search field,
  sidebar places list, grid icons or list rows of fictional files.
- settings: preference rows with switches, check boxes, radio groups, spin buttons,
  dropdowns/combos, sliders, expanders; some disabled.
- preferences-dialog: a modal dialog/window over a main window (only the dialog's targets
  and the main window targets not covered by it; a modal dialog makes the main window
  non-interactive: label only the dialog).
- table: dense table (GTK ColumnView / Qt QTableView) with sortable header buttons,
  rows (row_file), toolbar.
- editor: headerbar/menubar + tabs + a large text view (text body not labelled).
- context-menu: files-list with a context popover/menu open at a seeded position.
- app-menu: main/primary menu (GTK popover menu from a MenuButton; Qt menubar menu) open.
- sidebar-nav: sidebar + stack/view switcher/tab bar + content with links (GTK
  LinkButton / Qt QLabel links are fine) and buttons.
- form: entries, password, text area, combo, check/radio, submit/cancel buttons.

Randomize per seed inside a template: widget counts, labels, which rows are disabled,
window chrome (headerbar vs toolbar/menubar), icon-only vs labelled buttons, density.
Theme: light/dark (GTK: Adw.StyleManager color scheme; Qt: Fusion style + palette),
accent colour, font scale 0.9-1.25.

## Split (owned by the collector, listed here for awareness)

Validation holds out whole templates: preferences-dialog and table (both toolkits).
All other templates are training only.
