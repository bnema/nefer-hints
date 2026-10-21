"""Seven-scene CPU reference, protocol accuracy and 20-run latency validation."""
import os
os.environ.update(YOLO_OFFLINE='true', HF_HUB_OFFLINE='1', YOLO_AUTOINSTALL='false')
import argparse
import json
from pathlib import Path
import sys
import time
import cv2
import numpy as np
import torch
from ultralytics import YOLO
from protocol import Client, ROOT
sys.path.insert(0,str(ROOT/'poc/2026-10-21-gpu-latency/scripts'))
from score import score
REF=ROOT/'poc/2026-10-21-omniparser'
OUT=ROOT/'poc/2026-10-21-ncnn-runner'

def agreement(a,b):
    remaining=list(range(len(b))); matches=[]
    for x in a:
        best=-1; value=0
        for j in remaining:
            y=b[j]; lo=np.maximum(x[:2],y[:2]); hi=np.minimum(x[2:],y[2:]); inter=np.maximum(hi-lo,0).prod()
            union=np.maximum(np.array(x[2:])-x[:2],0).prod()+np.maximum(np.array(y[2:])-y[:2],0).prod()-inter
            v=float(inter/union) if union else float(np.allclose(x,y))
            if v>value: best=j;value=v
        if value>=.5: remaining.remove(best);matches.append(value)
    return dict(matched=len(matches),reference=len(a),candidate=len(b),mean_iou=float(np.mean(matches)) if matches else None)
def stats(a): return dict(median=float(np.median(a)),p95=float(np.percentile(a,95)))
def memory(pid):
    status=Path(f'/proc/{pid}/status').read_text()
    rss={line.split(':')[0]:int(line.split()[1])/1024 for line in status.splitlines() if line.startswith(('VmRSS:','VmHWM:'))}
    vram=[]
    for f in Path(f'/proc/{pid}/fdinfo').glob('*'):
        try:
            for line in f.read_text().splitlines():
                if line.startswith('drm-memory-vram:'): vram.append(int(line.split()[1])/1024)
        except OSError: pass
    return dict(rss_mib=rss,drm_vram_mib=max(vram) if vram else None)
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--fp32',action='store_true');a=ap.parse_args()
    torch.set_num_threads(8)
    model=YOLO(str(ROOT/'weights/model.pt'))
    images={p.stem:cv2.imread(str(REF/'frames'/f'{p.stem}.png')) for p in sorted((REF/'gt').glob('*.json')) if p.stem!='dumber-hn'}
    output=dict(options=dict(fp32=a.fp32,conf=.05,iou=.7,max_det=1000,threads=8),runs=[])
    for size in (640,1280):
        c=Client(size,('--fp32',) if a.fp32 else ())
        ref={};pred={};rows={}
        for name,im in images.items():
            r=model.predict(im,imgsz=size,conf=.05,iou=.7,max_det=1000,device='cpu',half=False,verbose=False,agnostic_nms=True)[0]
            ref[name]=r.boxes.xyxy.tolist()
            bgra=cv2.cvtColor(im,cv2.COLOR_BGR2BGRA)
            for _ in range(3): assert c.request(bgra)['status']==0
            times=[];inf=[]
            for i in range(20):
                start=time.perf_counter();result=c.request(bgra,seq=i+1);times.append((time.perf_counter()-start)*1000)
                assert result['status']==0,result
                inf.append(result['inference_ms'])
            pred[name]=[list(b[:4]) for b in result['boxes']]
            rows[name]=dict(shape=list(im.shape),agreement=agreement(ref[name],pred[name]),e2e_ms=times,inference_ms=inf)
            print(size,name,len(ref[name]),len(pred[name]),flush=True)
        run=dict(imgsz=size,device=c.device,cold_start_ms=c.cold_ms,memory=memory(c.p.pid),torch_score=score(ref),ncnn_score=score(pred),torch_predictions=ref,ncnn_predictions=pred,scenes=rows,e2e_ms=stats([t for row in rows.values() for t in row['e2e_ms']]),inference_ms=stats([t for row in rows.values() for t in row['inference_ms']]))
        run['within_one_point']=all(abs(run['torch_score'][k]-run['ncnn_score'][k])<=.01 for k in ('precision','recall'))
        assert c.close()==0
        output['runs'].append(run)
        (OUT/('results-fp32.json' if a.fp32 else 'results.json')).write_text(json.dumps(output,indent=2))
        print(run['torch_score'],run['ncnn_score'],flush=True)
if __name__=='__main__': main()
