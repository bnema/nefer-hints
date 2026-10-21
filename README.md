# nefer-hints

Local clickable-UI candidate detector for NeferWL hint mode, using OmniParser v2
`icon_detect` (YOLO). A persistent C++17 subprocess runs ncnn on Vulkan, with CPU
fallback; NeferWL stays Go with `CGO_ENABLED=0`. No screen content leaves the host.
This runner proposes boxes, not calibrated clickability: classifier filtering,
AT-SPI merging and compositor integration are not implemented here.

## Build

Requires a C++17 compiler, CMake and system ncnn built with Vulkan (Arch: `ncnn`).
No Python or torch dependency at runtime; dynamic linking to system ncnn.

```bash
cmake -S runner -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j8
```

## Export (offline weights)

Python is only needed for export and validation. Reuse system torch; never replace
it with pip. The pinned local additions are from the GPU experiment.

```bash
python -m venv --system-site-packages venv
venv/bin/pip install --no-deps -r poc/2026-10-21-gpu-latency/requirements-local.txt
mkdir -p weights
cp /tmp/omniparser-eval/weights/icon_detect/model.pt weights/model.pt
YOLO_OFFLINE=true HF_HUB_OFFLINE=1 OMP_NUM_THREADS=8 venv/bin/python export/export_ncnn.py
```

Produces ignored `models/icon_detect-{640,1280}[-rect].ncnn.{param,bin}` via
Ultralytics TorchScript and the pnnx CLI, `fp16=0`. Dynamic pnnx export left an
unsupported expression layer; the reproducible fixed-shape fallback uses square
and 16:9 rectangular graphs. Explicit crops and non-16:9 frames use square
letterboxing; 16:9 whole frames match Ultralytics minimal rectangular padding.

## Run and protocol

```bash
build/nefer-hints --model models --imgsz 1280 --conf 0.05 --iou 0.7 --gpu auto
```

This is not a PNG command-line reader: stdin/stdout carry the binary protocol.
After load and warmup, `NHNT` announces readiness and the device. Each `NHRQ`
contains a sequence number, BGRA frame and optional independent crop regions;
`NHRS` returns scored boxes in frame coordinates or an error. All fields are
little-endian; stderr is logs only. EOF between requests exits cleanly.
See [the complete protocol](docs/protocol.md) and [Python client](tests/protocol.py).

## Verify

```bash
venv/bin/python -m unittest discover -s tests -v
venv/bin/python tests/validate.py
```

Seven verified scenes, CPU torch comparison, protocol latency and memory results:
[poc/2026-10-21-ncnn-runner](poc/2026-10-21-ncnn-runner/README.md).
Earlier experiments, frames and annotations live under `poc/`.

## License

AGPL-3.0: detector weights and Ultralytics are AGPL. NeferWL (GPLv3) can call it
as a subprocess.
