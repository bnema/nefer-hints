import os
os.environ.update(YOLO_CONFIG_DIR='/tmp/omniparser-eval/yolo-config',YOLO_OFFLINE='true',HF_HUB_OFFLINE='1',UV_PYTHON_DOWNLOADS='never',UV_NO_MANAGED_PYTHON='1')
import json,time,statistics,hashlib,platform
from pathlib import Path
import torch,ultralytics
from ultralytics import YOLO
R=Path('/tmp/omniparser-eval'); E=R/'eval'; E.mkdir(exist_ok=True)
torch.set_num_threads(8)
m=YOLO(str(R/'weights/icon_detect/model.pt'))
result={'status':'PARTIAL: predictions only; ground truth not annotated; no precision/recall claims','versions':{'python':platform.python_version(),'torch':torch.__version__,'ultralytics':ultralytics.__version__},'threads':8,'model_sha256':hashlib.sha256((R/'weights/icon_detect/model.pt').read_bytes()).hexdigest(),'scenes':{}}
for p in sorted((R/'frames').glob('*.png')):
 if '.annotated.' in p.name or p.stem=='dumber-hn': continue
 scene={'neferwl':json.loads(p.with_suffix('.json').read_text()),'omniparser':{}}
 for size in (640,1280):
  for conf in (.05,.25):
   kw=dict(conf=conf,iou=.7,imgsz=size,device='cpu',verbose=False,max_det=1000)
   m.predict(str(p),**kw)
   times=[]
   for _ in range(3):
    t=time.perf_counter(); r=m.predict(str(p),**kw)[0]; times.append((time.perf_counter()-t)*1000)
   scene['omniparser'][f'{conf}/{size}']={'settings':kw,'runs_ms':times,'median_ms':statistics.median(times),'boxes':[b.xyxy[0].tolist() for b in r.boxes],'confidence':[float(b.conf[0]) for b in r.boxes]}
 result['scenes'][p.stem]=scene
 print(p.stem,[(k,len(v['boxes']),round(v['median_ms'])) for k,v in scene['omniparser'].items()],flush=True)
 (E/'predictions.json').write_text(json.dumps(result,indent=2))
