# Persistent ncnn runner validation — 2026-10-21

## Outcome

The C++17 runner serves BGRA frames over the v1 binary protocol, loads and warms
models once, and uses system ncnn/Vulkan. Both sizes meet the **±1 percentage
point** precision/recall criterion against fresh Ultralytics CPU predictions.
This is accuracy-equivalent within that tolerance, **not box-identical**.

Host: CachyOS/Arch, Ryzen 9 7900X3D, RX 9070 XT / RADV GFX1201,
ncnn 20261020, system torch 2.14.1, Ultralytics 8.4.183.

## Accuracy

Seven verified 1920x1080 scenes, 595 GT targets, excluding dumber-hn.
Confidence .05, class-agnostic IoU .7, max_det 1000, scaleup enabled, minimal
rectangular stride-32 padding: 640x384 and 1280x736. Ground-truth scoring imports
the existing maximum bipartite centre-inside-box matcher; each GT is matched
at most once. Predictions are in descending confidence order. Agreement uses
greedy IoU >= .5, with a separate matched-box mean IoU for every scene in JSON.

| Size | Backend | Boxes | TP | Precision | Recall | Matched to torch |
|---|---|---:|---:|---:|---:|---:|
| 640 | torch CPU | 565 | 356 | 63.01% | 59.83% | reference |
| 640 | ncnn Vulkan | 565 | 355 | 62.83% | 59.66% | 561/565 |
| 1280 | torch CPU | 639 | 453 | 70.89% | 76.13% | reference |
| 1280 | ncnn Vulkan | 636 | 453 | 71.23% | 76.13% | 631/639 |

1280 CPU reproduces the original reference exactly in aggregate. Mean matched
IoU ranges .9720–.9927 at 640 and .9679–.9849 at 1280.

## Latency and memory

Three per-scene warmups, then 20 sequential requests per scene (140 samples per
size). Timing includes building the binary request, copying 8,294,400 pixel bytes
through pipes, C++ preprocessing, GPU transfers/inference, NMS, and reading the
response. Excludes PNG decode and BGR-to-BGRA conversion. Same harness/process
runs CPU reference predictions between scenes. Background desktop activity is
not controlled; these are local measurements, not hardware-independent promises.

| Size | Inference med/p95 ms | Protocol med/p95 ms | Spawn → hello ms | RSS/HWM MiB | VRAM MiB |
|---|---:|---:|---:|---:|---:|
| 640 | 5.71 / 6.43 | 11.17 / 13.71 | 510.6 | 125.0 | 219.8 |
| 1280 | 14.86 / 16.80 | 25.07 / 28.03 | 536.7 | 287.4 | 379.8 |

Cold start is one fresh subprocess per size with warm OS/driver caches, including
both square and rectangular model loads and warmups. RSS/HWM comes from the
runner's `/proc/PID/status`, not the Python parent. VRAM is the largest
`drm-memory-vram` fdinfo counter at the end (snapshot, not a peak or whole-device
measurement). No Python runtime is required by the deployed runner.

## Options, failures and limits

- Export weights FP32 (`pnnx fp16=0`); runtime **ncnn defaults**, Vulkan GPU 0,
  eight CPU threads. Disabling fp16 was unnecessary: both P/R deltas <1 point.
  `--fp32` remains available for diagnosis.
- First dynamic attempt with a static TorchScript failed shape inference.
  `dynamic=True` TorchScript plus two pnnx input shapes converted successfully,
  but retained `pnnx.Expression`, rejected by system ncnn at load.
- Authorized fallback: fixed 640x640 / 1280x1280 and 640x384 / 1280x736 graphs.
  Whole-frame 16:9 requests use rectangular graphs. Explicit regions and other
  frame aspects use square padding; arbitrary-aspect rectangular equivalence
  is not claimed. Both graphs remain resident, increasing memory use.
- ncnn bilinear resize is not bit-identical to OpenCV. Together with default
  reduced precision this can change individual boxes; no exact raw-tensor
  equivalence or attribution of every difference is claimed.
- RADV prints its non-conformance warning to stderr, never the protocol stream.
- Eight unittest methods pass: bad/truncated magic, bad version, truncated
  payload, unsafe dimensions/stride, EOF, recovery after malformed requests,
  zero/multiple/clipped regions, 64-bit sequence echo, explicit CPU inference.
  CPU auto-fallback on a genuinely Vulkan-less host was not physically tested.

## Reproduce

Follow root README build/export setup, then:

```bash
venv/bin/python -m unittest discover -s tests -v
venv/bin/python tests/validate.py
# Optional diagnostic comparison, separate output file:
venv/bin/python tests/validate.py --fp32
```

`results.json` contains final options, fresh torch/ncnn predictions, per-scene
counts and agreement, all timing samples, scores and runner memory snapshots.
Export logs are local under ignored weights/; exports and build products are
ignored. No compositor changes, push or merge.
