import os
os.environ['YOLO_CONFIG_DIR']='/tmp/omniparser-eval/yolo-config'
os.environ['YOLO_OFFLINE']='true'
import pathlib,time,statistics,json,hashlib,platform
import torch,ultralytics
from ultralytics import YOLO
from PIL import Image,ImageDraw
R=pathlib.Path('/tmp/omniparser-eval'); (R/'out').mkdir(exist_ok=True)
torch.set_num_threads(8)
m=YOLO(str(R/'weights/icon_detect/model.pt'))
shots=sorted((R/'shots').glob('*.png'))
kw=dict(conf=.05,iou=.7,imgsz=640,device='cpu',verbose=False,max_det=1000)
m.predict(str(shots[0]),**kw)
results={'versions':{'python':platform.python_version(),'torch':torch.__version__,'ultralytics':ultralytics.__version__},'settings':kw,'threads':8,'model_sha256':hashlib.sha256((R/'weights/icon_detect/model.pt').read_bytes()).hexdigest(),'images':[]}
for p in shots:
    times=[]
    for _ in range(3):
        t=time.perf_counter(); r=m.predict(str(p),**kw)[0]; times.append((time.perf_counter()-t)*1000)
    boxes=[{'index':i,'xyxy':b.xyxy[0].tolist(),'confidence':float(b.conf[0]),'class':int(b.cls[0])} for i,b in enumerate(r.boxes)]
    high=m.predict(str(p),**dict(kw,conf=.25))[0]
    im=Image.open(p).convert('RGB'); d=ImageDraw.Draw(im)
    for b in boxes:
        x,y,x2,y2=b['xyxy']; d.rectangle((x,y,x2,y2),outline='#ff2020',width=2); d.text((x,y),str(b['index']),fill='white',stroke_width=2,stroke_fill='black')
    im.save(R/'out'/p.name)
    entry={'name':p.stem,'size':list(im.size),'boxes_005':len(boxes),'boxes_025':len(high.boxes),'latency_ms':statistics.median(times),'runs_ms':times,'boxes':boxes}
    results['images'].append(entry); print(p.stem,len(boxes),len(high.boxes),round(entry['latency_ms'],1),flush=True)
(R/'results.json').write_text(json.dumps(results,indent=2))
