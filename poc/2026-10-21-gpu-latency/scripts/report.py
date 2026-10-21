"""Aggregate measured files, greedy IoU agreement and a reproducible result table."""
import json
from pathlib import Path
import numpy as np
from score import score
P=Path(__file__).resolve().parents[1]
REF=P.parent/'2026-10-21-omniparser'

def agreement(pred,ref):
    a=np.asarray(pred,dtype=float).reshape(-1,4);b=np.asarray(ref,dtype=float).reshape(-1,4)
    pairs=[]
    for i,x in enumerate(a):
        for j,y in enumerate(b):
            inter=np.maximum(np.minimum(x[2:],y[2:])-np.maximum(x[:2],y[:2]),0).prod()
            union=np.maximum(x[2:]-x[:2],0).prod()+np.maximum(y[2:]-y[:2],0).prod()-inter
            pairs.append((inter/union if union else float(np.allclose(x,y,atol=0.01)),i,j))
    useda=set();usedb=set();values=[]
    for v,i,j in sorted(pairs,reverse=True):
        if v<.5:break
        if i not in useda and j not in usedb: useda.add(i);usedb.add(j);values.append(v)
    mean=float(np.mean(values)) if values else None
    return dict(count=len(a),reference_count=len(b),matched=len(values),mean_iou=mean,flag=len(a)!=len(b) or len(values)!=len(b) or (mean is not None and mean<.99))

def main():
    runs=[]
    for backend in ['torch-cpu','torch-gpu-fp32','torch-gpu-fp16','torch-gpu-fp16-nomiopen','ort-cpu','ort-gpu','ort-gpu-slim','ncnn']:
        for size in [640,1280]:
            r=json.loads((P/f'{backend}-{size}.json').read_text())
            baseline=json.loads((P/f'torch-cpu-{size}.json').read_text())['predictions']
            r['agreement']={s:agreement(b,baseline[s]) for s,b in r['predictions'].items()}
            runs.append(r)
    old=json.loads((REF/'results/predictions.json').read_text())['scenes']
    rect=json.loads((P/'rect-validation.json').read_text())
    rect['agreement_with_original']={s:agreement(b,old[s]['omniparser']['0.05/1280']['boxes']) for s,b in rect['predictions'].items()}
    result=dict(runs=runs,rect_validation=rect,protocol=dict(conf=.05,iou=.7,max_det=1000,warmup=5,runs_per_scene=20,scenes=7,threads=8,shape='square static',percentiles='pooled 140 samples per configuration',cold_start='Python entry to first result; includes imports and loading all seven PNGs, warm filesystem/driver caches; not a machine-reboot cold start',memory='ru_maxrss of Python process; ncnn child excluded. torch GPU allocation is not total VRAM.'))
    (P/'results.json').write_text(json.dumps(result,indent=2))
    lines=['| Backend | Size | Inference med/p95 ms | E2E med/p95 ms | First result s | RSS MiB | Box agreement |','|---|---:|---:|---:|---:|---:|---|']
    for r in runs:
        a=r['inference_ms'];b=r['e2e_ms'];ag=r['agreement'];matched=sum(x['matched'] for x in ag.values());n=sum(x['reference_count'] for x in ag.values());means=[x['mean_iou'] for x in ag.values() if x['mean_iou'] is not None]
        lines.append(f"| {r['backend']} | {r['imgsz']} | {a['median']:.1f}/{a['p95']:.1f} | {b['median']:.1f}/{b['p95']:.1f} | {r['cold_start_ms']/1000:.2f} | {r['peak_rss_mib']:.0f} | {matched}/{n}; IoU {np.mean(means):.4f} |")
    (P/'table.md').write_text('\n'.join(lines)+'\n')
if __name__=='__main__':main()
