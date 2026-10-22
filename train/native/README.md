# Synthetic native GTK captures

`CONTRACT.md` is the supplied shared native-app contract, copied verbatim.
The GTK app requires system PyGObject, GTK4 and libadwaita. It never reads user
files or fetches network content. Use an isolated HOME for captures.

```sh
/usr/bin/python3 train/native/gtk_app.py --seed 1 --template context-menu \
  --theme dark --accent '#3584e4' --font-scale 1.0 --out /tmp/native-sample
/usr/bin/python3 -m unittest discover -s train/native -p 'test_*.py'
```

Under the capture environment the window is fullscreen. The app waits four frame
ticks, settles scrolling/popup placement, then waits another 1.3 seconds before
writing labels and the readiness marker. Geometry comes from widget allocations,
not text extents. Registered composite controls stop recursive discovery to avoid
duplicate labels. Internal ColumnView titles/rows and scrollbar ranges are found
in the widget tree. Adw.Dialog is hosted inside Adw.ApplicationWindow, keeping
modal geometry in the same coordinate space without assuming compositor placement.
Popup allocations use their Gdk.Popup surface positions. Disabled controls,
under-half-visible scroll targets, small clipped boxes, and parent targets whose
centres fall beneath the popup surface are excluded.

## Preview

Set `NEFERWL` to the compositor executable in your environment. Run with a Python
that has Pillow; the app itself is always launched with `/usr/bin/python3`.

```sh
python train/native/preview.py
python train/native/preview.py --size 2560x1440 --templates context-menu \
  preferences-dialog --seeds 3 --themes dark --font-scale 1.25 --accent '#a65cce'
```

The default preview makes 40 captures: ten templates, light/dark, seeds 1/2.
It creates isolated HOME/XDG directories in `/tmp/nh-native-gtk`, starts one bounded
headless compositor, reads its JSON listening log, waits at most 30 seconds for
each app, captures with grim, draws allocation outlines, and terminates each app.
Overlays are `/tmp/nh-native-gtk/overlays/<template>-<seed>-<theme>.png`;
raw screenshots and labels are in the corresponding `captures` directory.
Runs are sequential: do not run two previews concurrently against this directory.
Repeated runs overwrite the same sample names, including when changing size.

## Verification and limits

Verified with GTK 4.24 / Adw 1.10: all 40 default captures and visual overlay
inspection, plus 2560x1440 dark popup and modal captures at font scale 1.25.
Inspection caught and corrected unmapped programmatic popovers and missing
ColumnView headers. Programmatic popovers deliberately do not autohide (there is
no physical input event/grab serial in the synthetic launch).

This is a static synthetic capture app, not a functional file manager/editor.
It exports one settled frame per launch; subsequent interaction does not refresh
labels. The geometry extractor supports the single popup used by these scenes,
not arbitrary nested popup chains. Output scale 1 and a single output are the
contract; other scaling/multi-output configurations are not supported. Internal
ColumnView discovery is GTK-version-sensitive and was verified on the versions
above. Scrollbar allocations may overlap row allocations, as GTK overlay
scrollbars do. Text-view bodies are deliberately never labelled.
