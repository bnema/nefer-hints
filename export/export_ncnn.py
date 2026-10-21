#!/usr/bin/env python3
"""Offline TorchScript -> pnnx -> ncnn, FP32 weights, fixed-shape fallback.
Dynamic export with inputshape=[1,3,1280,1280]f32 and
inputshape2=[1,3,640,640]f32 leaves unsupported pnnx.Expression layers on
ncnn 20261020. Export fixed rectangular and square graphs instead.
"""
import os
os.environ.update(YOLO_OFFLINE='true', HF_HUB_OFFLINE='1', YOLO_AUTOINSTALL='false')
import argparse
from pathlib import Path
import subprocess
import sys
from ultralytics import YOLO
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--weights', type=Path, default=ROOT/'weights/model.pt')
p.add_argument('--output', type=Path, default=ROOT/'models')
a = p.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
for size in (640, 1280):
    for shape, suffix in [((size, size), ''), ((384 if size == 640 else 736, size), '-rect')]:
        h, w = shape
        script = YOLO(str(a.weights.resolve())).export(format='torchscript', imgsz=[h,w], device='cpu')
        prefix = a.output.resolve()/f'icon_detect-{size}{suffix}'
        subprocess.run([str(Path(sys.executable).parent/'pnnx'), str(Path(script).resolve()),
                        f'inputshape=[1,3,{h},{w}]f32', 'fp16=0',
                        f'ncnnparam={prefix}.ncnn.param', f'ncnnbin={prefix}.ncnn.bin'], check=True)
