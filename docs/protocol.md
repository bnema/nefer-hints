# Nefer hints protocol v1

Persistent synchronous subprocess; stdin requests, stdout binary responses only,
stderr diagnostics. All integers and IEEE-754 floats are little-endian. There is
no implicit alignment or terminator. Strings are u32 byte length + UTF-8 bytes.
Clients must handle short reads/writes and wait for hello before sending pixels.
No request pipelining is needed; consume each response before the next request.

## Startup

`nefer-hints --model DIR_OR_PREFIX [--imgsz 1280] [--conf 0.05] [--iou 0.7]
[--max-det 1000] [--gpu auto|N|cpu] [--fp32]`

Directory selects `icon_detect-<imgsz>`. A prefix (or `.ncnn.param` path)
selects that graph and its sibling `<prefix>-rect.ncnn.{param,bin}`. Both graphs
are loaded once and warmed before hello. Supported exports: 640 and 1280.
`auto` chooses Vulkan device 0, otherwise CPU when no Vulkan device exists.
Explicit invalid GPU indices fail startup. `--fp32` disables fp16 packed,
storage and arithmetic; otherwise ncnn defaults apply. Eight CPU threads.

Optional model defaults come from `DIR/model.json` for a directory, or
`<prefix>.json` then the prefix directory's `model.json` for a prefix or
`.ncnn.param` path (the first existing file wins). The file is a flat JSON object
of strings and numbers, e.g. `{"name":"terminal-v1","conf":0.075,"iou":0.4}`.
The file is at most 64 KiB (65536 bytes), strings contain valid UTF-8, and
duplicate keys (after decoding escapes) are rejected. Violations fail hello with
status 1 and an error string. All keys are optional; unknown keys are ignored.
`name` is a string, `conf` is finite in (0,1], and `iou` is finite in [0,1].
Invalid metadata fails hello.
Precedence is built-in conf 0.05 / IoU 0.7 < metadata < explicit CLI flags,
regardless of argument order. Per-request confidence still overrides the startup
default. Startup stderr includes effective conf/IoU and the model name, if given.

Hello success: `"NHNT", u32 version=1, u32 status=0, string device, u32 imgsz`.
Hello failure: `"NHNT", u32 version=1, u32 status=1, string error`, exit 1.

## Request

In order:

- `"NHRQ"`, u32 version=1, u64 seq (echoed unchanged)
- u32 width, height, stride (bytes per row), format=1, nregions
- nregions records: i32 x, i32 y, u32 w, u32 h
- f32 confidence override (finite <=0 uses startup default)
- exactly height*stride bytes; format 1 is XRGB8888, **B,G,R,ignored** bytes

Stride may include row padding. Maximum 64 regions; regions are clipped to the
frame. Empty clipped regions fail the entire request. Zero regions means one
whole-frame detection with region index 0. Explicit regions are independent;
no cross-region NMS, deduplication or global max-det limit. Indices are zero-based
in request order. `--max-det` applies per region.

Preprocessing scales up/down to imgsz on the long axis, bilinear resize,
BGR-to-RGB, padding value 114 and division by 255. A whole 16:9 frame uses
Ultralytics centered minimal stride-32 padding (1280x736 / 640x384), with
rounding `round(pad/2 - .1)` on the top/left. **Fixed-shape fallback:** all
explicit crops and non-16:9 whole frames use centered square letterboxing.
This is not rectangular-equivalent for arbitrary aspect ratios. ncnn's integer
bilinear resize can differ slightly from OpenCV; accuracy is measured, not
bit-exact. Filter score > conf, stable descending score order, class-agnostic
IoU NMS, up to 30000 candidates and max-det survivors. Clip output to crop bounds
and translate to frame pixels. No classifier or AT-SPI merge is implemented.

## Response

Common header: `"NHRS", u32 version=1, u64 seq, u32 status`.

Success (status 0): f32 inference_ms, u32 nboxes, then nboxes records:
`f32 x1, y1, x2, y2, score; u32 region_index` (24 bytes each).
Coordinates are frame pixels. Inference time sums ncnn forward/input/output
transfers across regions; excludes pipe transport, preprocessing and NMS.

Failure: string error, **no timing or box count**.
Status 1 = bad request; status 2 = internal/inference error.

## Recovery and limits

Recoverable errors (format, empty regions, >64 regions, invalid confidence,
zero dimensions) consume the complete request before responding; serving resumes.
Framing errors (bad magic/version, truncated data, unsafe dimensions) log and
exit 2, sending status 1 first only if seq was fully read. EOF between requests
exits 0; EOF mid-frame exits 2. No response is possible without a known seq.

Reject >2^28 pixels, stride < width*4, and additionally >1 GiB pixel payloads
(including row padding) or >65536 region records as unsafe framing. These extra
bounds prevent unbounded discard/allocation on hostile headers. Length products
use 64-bit arithmetic. Startup model errors exit 1. The caller should close or
terminate an abandoned subprocess rather than leave an incomplete frame open.
