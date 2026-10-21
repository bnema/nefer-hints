"""AGPL-3.0-only. Run from worktree root; each configuration is a fresh process."""
import os
os.environ.update(YOLO_OFFLINE='true', HF_HUB_OFFLINE='1', YOLO_AUTOINSTALL='false')
import time
START=time.perf_counter()
import argparse
import json
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parents[1]
REF=ROOT/'poc/2026-10-21-omniparser'

def worker(backend,size):
    import numpy as np
    import cv2
    import resource
    import torch
    from score import score
    torch.set_num_threads(8)
    images={p.stem:cv2.imread(str(REF/'frames'/f'{p.stem}.png')) for p in sorted((REF/'gt').glob('*.json'))}
    def prep(im):
        h,w=im.shape[:2]; r=min(size/w,size/h); nw,nh=round(w*r),round(h*r)
        im=cv2.resize(im,(nw,nh)); left=(size-nw)//2; top=(size-nh)//2
        im=cv2.copyMakeBorder(im,top,size-nh-top,left,size-nw-left,cv2.BORDER_CONSTANT,value=(114,114,114))
        return np.ascontiguousarray(im[:,:,::-1].transpose(2,0,1)[None],dtype=np.float32)/255
    def post(raw,im):
        if isinstance(raw,(list,tuple)): raw=raw[0]
        a=np.asarray(raw).squeeze()
        if a.shape[0]==5: a=a.T
        a=a[a[:,4]>=.05]; boxes=a[:,:4].copy(); boxes[:,:2]-=boxes[:,2:]/2; boxes[:,2:]+=boxes[:,:2]
        order=np.argsort(-a[:,4],kind='stable'); keep=[]
        while len(order) and len(keep)<1000:
            i=order[0];keep.append(i);order=order[1:]
            lo=np.maximum(boxes[i,:2],boxes[order,:2]);hi=np.minimum(boxes[i,2:],boxes[order,2:])
            inter=np.maximum(hi-lo,0).prod(1);areas=np.maximum(boxes[:,2:]-boxes[:,:2],0).prod(1)
            order=order[inter/(areas[i]+areas[order]-inter+1e-9)<=.7]
        boxes=boxes[keep];h,w=im.shape[:2];r=min(size/w,size/h)
        boxes[:,[0,2]]-= (size-round(w*r))//2;boxes[:,[1,3]]-=(size-round(h*r))//2;boxes/=r
        boxes[:,[0,2]]=boxes[:,[0,2]].clip(0,w);boxes[:,[1,3]]=boxes[:,[1,3]].clip(0,h)
        return boxes.tolist()
    info={}
    ncnn_ms=[0.0]
    if backend.startswith('torch'):
        from ultralytics import YOLO
        device='cuda' if 'gpu' in backend else 'cpu';half='fp16' in backend
        if 'nomiopen' in backend: torch.backends.cudnn.enabled=False
        m=YOLO(str(ROOT/'weights/model.pt')).model.fuse().eval().to(device)
        if half:m.half()
        def convert(x):return torch.from_numpy(x).to(device=device,dtype=torch.float16 if half else torch.float32)
        def sync():
            if device=='cuda':torch.cuda.synchronize()
        def forward(x):
            with torch.inference_mode(): y=m(x)[0]
            sync();return y
        def host(y):return y.float().cpu().numpy()
        info['device']=torch.cuda.get_device_name(0) if device=='cuda' else 'CPU'
    elif backend.startswith('ort'):
        import onnxruntime as ort
        provider='MIGraphXExecutionProvider' if 'gpu' in backend else 'CPUExecutionProvider'
        if provider not in ort.get_available_providers():raise RuntimeError(f'{provider} unavailable: {ort.get_available_providers()}')
        opts=ort.SessionOptions();opts.intra_op_num_threads=8
        m=ort.InferenceSession(str(ROOT/f'weights/model-{size}{"-slim" if "slim" in backend else ""}.onnx'),sess_options=opts,providers=[provider])
        info['providers']=m.get_providers()
        convert=lambda x:x
        forward=lambda x:m.run(None,{m.get_inputs()[0].name:x})[0]
        host=lambda x:x
        sync=lambda:None
    else:
        folder=ROOT/f'weights/model-{size}_ncnn_model'
        p=subprocess.Popen([str(ROOT/'venv/ncnn_runner'),str(folder/'model.ncnn.param'),str(folder/'model.ncnn.bin'),str(size)],stdin=subprocess.PIPE,stdout=subprocess.PIPE)
        def forward(x):
            p.stdin.write(x.tobytes());p.stdin.flush()
            timing=p.stdout.read(8)
            if len(timing)!=8:raise RuntimeError(f'ncnn exited: {p.poll()}')
            ncnn_ms[0]=float(np.frombuffer(timing,dtype=np.float64)[0])
            hdr=p.stdout.read(12)
            if len(hdr)!=12:raise RuntimeError(f'ncnn exited: {p.poll()}')
            w,h,c=np.frombuffer(hdr,dtype=np.int32);n=int(w*h*c)*4
            data=p.stdout.read(n)
            return np.frombuffer(data,dtype=np.float32).reshape(int(c*h),int(w))
        convert=lambda x:x;host=lambda x:x;sync=lambda:None
    first=next(iter(images.values())); post(host(forward(convert(prep(first)))),first)
    cold=(time.perf_counter()-START)*1000
    rows={}; predictions={}
    for scene,im in images.items():
        x=convert(prep(im))
        for _ in range(5):forward(x)
        inf=[];e2e=[]
        for _ in range(20):
            sync();t=time.perf_counter();y=forward(x);inf.append(ncnn_ms[0] if backend=='ncnn' else (time.perf_counter()-t)*1000)
            sync();t=time.perf_counter();boxes=post(host(forward(convert(prep(im)))),im);e2e.append((time.perf_counter()-t)*1000)
        predictions[scene]=boxes
        rows[scene]={'inference_ms':inf,'e2e_ms':e2e,'count':len(boxes)}
    def stats(key):
        a=[v for row in rows.values() for v in row[key]]
        return dict(median=float(np.median(a)),p95=float(np.percentile(a,95)))
    result=dict(backend=backend,imgsz=size,cold_start_ms=cold,inference_ms=stats('inference_ms'),e2e_ms=stats('e2e_ms'),peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,scenes=rows,predictions=predictions,score=score(predictions),**info)
    if backend.startswith('torch-gpu'):result['peak_torch_allocated_mib']=torch.cuda.max_memory_allocated()/2**20
    (OUT/f'{backend}-{size}.json').write_text(json.dumps(result,indent=2))
    if backend=='ncnn':p.stdin.close();p.wait(timeout=10)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--backend');ap.add_argument('--size',type=int);args=ap.parse_args()
    if args.backend:worker(args.backend,args.size);return
    results=[]
    for backend in ['torch-cpu','torch-gpu-fp32','torch-gpu-fp16','ort-cpu','ort-gpu','ort-gpu-slim','ncnn']:
        for size in [640,1280]:
            t=time.perf_counter()
            try:
                r=subprocess.run([sys.executable,__file__,'--backend',backend,'--size',str(size)],cwd=ROOT,capture_output=True,text=True,timeout=240)
                log=r.stdout+r.stderr;(OUT/f'{backend}-{size}.log').write_text(log)
                result=json.loads((OUT/f'{backend}-{size}.json').read_text()) if r.returncode==0 else dict(backend=backend,imgsz=size,error=log,returncode=r.returncode)
            except subprocess.TimeoutExpired as e:result=dict(backend=backend,imgsz=size,error='240s timeout',stdout=str(e.stdout),stderr=str(e.stderr))
            result['process_wall_ms']=(time.perf_counter()-t)*1000;results.append(result)
            (OUT/'results.json').write_text(json.dumps({'runs':results},indent=2))
            print(backend,size,result.get('inference_ms',result.get('error','')),flush=True)
if __name__=='__main__':main()
