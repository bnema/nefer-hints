"""Reproduce the original rectangular Ultralytics path on ROCm FP32."""
import os
os.environ.update(YOLO_OFFLINE='true',HF_HUB_OFFLINE='1',YOLO_AUTOINSTALL='false')
import json
from pathlib import Path
import torch
from ultralytics import YOLO
from score import score
P=Path(__file__).resolve().parents[1]
ROOT=P.parents[1]
REF=P.parent/'2026-10-21-omniparser'
torch.set_num_threads(8)
m=YOLO(str(ROOT/'weights/model.pt'))
pred={}
for p in sorted((REF/'gt').glob('*.json')):
    r=m.predict(str(REF/'frames'/f'{p.stem}.png'),imgsz=1280,conf=.05,iou=.7,max_det=1000,device='cuda',half=False,verbose=False)[0]
    pred[p.stem]=r.boxes.xyxy.cpu().tolist()
(P/'rect-validation.json').write_text(json.dumps(dict(score=score(pred),predictions=pred),indent=2))
