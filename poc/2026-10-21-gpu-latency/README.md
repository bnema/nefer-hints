# icon_detect GPU latency — 2026-10-21

## Decision

Use **PyTorch ROCm FP32 in a persistent subprocess** for this AMD PoC: exact CPU box agreement, 25.7 ms model / 37.0 ms end-to-end median at 1280. Do not spawn per hint request (first result 8–12 s). This is a local runner recommendation, not a compositor integration design.

**ncnn/Vulkan is the promising portable deployment candidate**, not yet the accuracy-equivalent default: 27.9 ms model / 41.6 ms e2e at 1280, small C++ runtime (~17 MiB libncnn plus Vulkan driver), no Python/ROCm requirement. Vulkan can support AMD, Intel and NVIDIA, but only AMD was tested. It changes some boxes; validate before shipping. PyTorch ROCm and MIGraphX are AMD-specific; PyTorch can use CUDA elsewhere with a different installation. ONNX CPU is a portable fallback.

## Setup

CachyOS/Arch; Ryzen 9 7900X3D; Radeon RX 9070 XT (gfx1201). Python 3.14.8, system torch 2.14.1, torchvision 0.29.0, ROCm 7.2.4, ONNX 1.22.0, ONNX Runtime 1.29.0, ncnn 20261020, RADV 26.2.4. Ultralytics 8.4.183. Exact relevant pacman versions: `packages.txt`; venv additions: `requirements-local.txt`.

`torch.cuda.is_available()` is true; device is `AMD Radeon RX 9070 XT`. ORT advertises MIGraphX, Dnnl and CPU; **no ROCMExecutionProvider**. MIGraphX works without a gfx override. No CPU-fallback warnings observed (CPU remains registered as fallback; per-node placement was not profiled).

System torch was reused, never replaced. Offline flags enabled. Installed packages with `--no-deps` only. ROCm SDK occupies ~30 GiB on this host (not a minimal deployment-size estimate); libtorch_cpu/hip/python alone ~674 MiB. These sizes are not download sizes.

## Measurements

Seven GT scenes (595 regions), excluding dumber-hn; batch 1, conf .05, IoU .7, max_det 1000, eight CPU threads. **Static square** letterboxing to 640×640 / 1280×1280 for identical inputs across all backends. Five warmups per scene, twenty inference and twenty separate e2e runs per scene; table pools 140 samples. Raw samples and predictions are retained in JSON.

Inference excludes preprocessing/NMS; torch GPU is synchronized and input already resident. ORT `session.run` includes host/device transfers. ncnn is timed inside C++ around extractor input/forward/output (includes GPU transfers); e2e additionally includes Python↔C++ pipe transport. E2E starts from decoded BGR memory, includes resize, normalization, transfers, output decoding, NumPy NMS and coordinate scaling; excludes PNG read. These are not pure device-kernel timings.

First-result time starts at Python script entry, includes imports, model/session loading and decoding all seven frames; excludes interpreter launch and uses warm OS/driver caches, not machine-reboot cold start. ncnn cold/RSS figures describe the Python harness, **not a production C++ runner**. RSS excludes the ncnn child. Torch peak allocated GPU memory is in JSON, not total VRAM; full GPU/RAM peaks were not sampled. Background desktop load and frequency variation were not controlled.

| Backend | Size | Inference med/p95 ms | E2E med/p95 ms | First result s | RSS MiB | Box agreement |
|---|---:|---:|---:|---:|---:|---|
| torch-cpu | 640 | 105.1/108.0 | 108.6/111.5 | 1.25 | 1218 | 574/574; IoU 1.0000 |
| torch-cpu | 1280 | 426.7/443.8 | 438.6/454.4 | 1.60 | 1582 | 694/694; IoU 1.0000 |
| torch-gpu-fp32 | 640 | 9.3/15.7 | 13.2/18.5 | 8.01 | 1921 | 574/574; IoU 1.0000 |
| torch-gpu-fp32 | 1280 | 25.7/34.6 | 37.0/42.3 | 11.60 | 1793 | 694/694; IoU 1.0000 |
| torch-gpu-fp16 | 640 | 7.3/8.4 | 10.0/11.4 | 7.30 | 1750 | 64/574; IoU 0.7838 |
| torch-gpu-fp16 | 1280 | 22.6/24.4 | 34.1/37.6 | 9.76 | 1309 | 30/694; IoU 0.7491 |
| torch-gpu-fp16-nomiopen | 640 | 10.7/14.9 | 14.9/18.1 | 1.38 | 1259 | 571/574; IoU 0.9781 |
| torch-gpu-fp16-nomiopen | 1280 | 32.9/38.2 | 45.4/48.7 | 1.40 | 1295 | 680/694; IoU 0.9719 |
| ort-cpu | 640 | 84.2/85.5 | 87.0/89.0 | 1.20 | 1402 | 574/574; IoU 1.0000 |
| ort-cpu | 1280 | 345.0/349.2 | 352.4/356.7 | 1.46 | 1827 | 694/694; IoU 1.0000 |
| ort-gpu | 640 | 15.2/16.2 | 17.8/19.4 | 90.78 | 2931 | 574/574; IoU 1.0000 |
| ort-gpu | 1280 | 28.5/36.9 | 35.9/41.5 | 172.18 | 2937 | 694/694; IoU 1.0000 |
| ort-gpu-slim | 640 | 15.6/16.4 | 18.1/19.8 | 91.48 | 2377 | 574/574; IoU 1.0000 |
| ort-gpu-slim | 1280 | 28.1/38.7 | 35.4/43.6 | 169.48 | 2447 | 694/694; IoU 1.0000 |
| ncnn | 640 | 7.0/8.4 | 11.5/14.5 | 1.34 | 941 | 567/574; IoU 0.9753 |
| ncnn | 1280 | 27.9/31.7 | 41.6/45.6 | 1.37 | 983 | 678/694; IoU 0.9700 |

Agreement uses descending greedy IoU ≥ .5 matching; table IoU is the unweighted mean of scene matched-box means. Counts and flags are per scene in `results.json`; flag if count/unmatched differs or mean IoU < .99. Identical clipped zero-area boxes are treated as equal (IoU otherwise undefined). FP32 torch and both ONNX variants match CPU at every scene/size. Vulkan differs slightly (1280: 698 vs 694 boxes, P 67.48%, R 79.16%, versus CPU P 67.72%, R 78.99%).

### Original precision/recall reproduced

The old Ultralytics prediction path uses **rectangular minimal padding**, not static square inputs. Thus square CPU scores are not expected to equal the previous README. A separate ROCm FP32 rectangular validation at 1280/.05 produces **639 boxes, 453 true positives, P 70.89%, R 76.13%**, identical counts and mean IoU > .99999 against the checked-in original CPU predictions in every scene. It confirms accuracy equivalence; rectangular latency was not benchmarked. GT scoring copies the original maximum bipartite centre-in-box matching (`scripts/score.py`), requiring verified annotations.

## Failures and workarounds

- **ROCm FP16 with MIOpen enabled is invalid on this setup**: only P 12.48%, R 12.61% at 1280. Do not interpret its speed as usable. One workaround, `torch.backends.cudnn.enabled=False` (disables MIOpen on HIP), restores near-CPU output (P 67.82%, R 78.99%) but loses speed and is still not exact. The kernel-level cause is not established; no architecture override used.
- Ultralytics ncnn export fails exactly with `ModuleNotFoundError: No module named 'ncnn'`; system ncnn supplies no Python binding. Workaround: Ultralytics TorchScript export, installed pnnx CLI conversion (`fp16=0` export), then link system ncnn C++. Runtime uses ncnn default precision options (including supported reduced precision). GPU 0 selected: `AMD Radeon RX 9070 XT (RADV GFX1201)`. RADV warns it is not a conformant implementation, testing use only; logs retained.
- MIGraphX compiles each fresh session: **91–172 seconds** to first result. Simplification does not materially improve this. No serialized compiled-model cache tested; unsuitable for per-request spawning as measured. Full logs retain compile warnings.
- Initial C++ build needed explicit `-I/usr/include/ncnn`; pkg-config alone did not supply the required include directory.

## Reproduce (from worktree root)

```bash
python -m venv --system-site-packages venv
# Install only missing packages, never resolve/replace system torch:
venv/bin/pip install --no-deps -r poc/2026-10-21-gpu-latency/requirements-local.txt
mkdir -p weights
cp /tmp/omniparser-eval/weights/icon_detect/model.pt weights/model.pt
c++ -O2 -I/usr/include/ncnn poc/2026-10-21-gpu-latency/scripts/ncnn_runner.cpp -o venv/ncnn_runner -lncnn
venv/bin/python poc/2026-10-21-gpu-latency/scripts/export.py
venv/bin/python poc/2026-10-21-gpu-latency/scripts/bench.py
for size in 640 1280; do
  venv/bin/python poc/2026-10-21-gpu-latency/scripts/bench.py --backend torch-gpu-fp16-nomiopen --size "$size"
done
venv/bin/python poc/2026-10-21-gpu-latency/scripts/validate_rect.py
venv/bin/python poc/2026-10-21-gpu-latency/scripts/report.py
venv/bin/python poc/2026-10-21-gpu-latency/scripts/test_results.py
```

Exports, weights and executables live in ignored `weights/` and `venv/`. No GitHub download was needed. `results.json` is the combined deliverable; individual JSON/log files preserve backend evidence, `export.json` preserves conversion errors/workaround logs. All new tracked material stays in this PoC directory. No integration changes, pushes or merges.
