# Native GUI training data

`collect.py` generates fullscreen GTK4 and Qt6 screenshots and single-class YOLO
clickable labels in `data/native/{train,val}/{images,labels}`. Widget allocation,
visibility, disabled-control and popup rules follow [CONTRACT.md](CONTRACT.md).
Boxes are clipped to the output; boxes smaller than 4×4 pixels are dropped.
Each screen requires at least three usable boxes and matching screenshot/label sizes.

Validation holds out the entire `preferences-dialog` and `table` templates in both
toolkits; the other eight templates are training only. The deterministic plan has
260 train and 50 validation screens per toolkit (620 total). Theme, accent, font
scale and output size vary by seed. Actual collected counts: **pending collection**.
`manifest.json` records successful screens; reruns skip existing images and recover
worker checkpoints. Stub verification data is not part of the dataset or manifest.

```sh
venv/bin/python train/native/collect.py plan
# Set NEFERWL to a headless-capable executable if it is not on PATH.
venv/bin/python train/native/collect.py run --workers 3
venv/bin/python train/native/collect.py run --workers 3 --toolkit gtk --limit 10
venv/bin/python train/native/collect.py stats
```

Apps run with system Python (GTK4/libadwaita or PySide6); collection uses the venv
and `grim`. Each worker isolates HOME/XDG under `/tmp/nh-native`, uses a 60-second
screen timeout, and restarts the compositor on failure, size changes or 50 screens.
