#!/usr/bin/env python3
"""Score verified frames only. No network access; never imports old PoC scenes."""
import argparse
import importlib.util
import json
from pathlib import Path
import statistics
import time

ROOT = Path(__file__).resolve().parent
KINDS = {'text_link', 'icon_button', 'row_file', 'menu_item', 'field', 'tab', 'other'}


def match(predictions, targets):
    """Maximum bipartite centre-in-box matching; prediction index -> GT index."""
    edges = []
    for box in predictions:
        x, y = (box[0]+box[2])/2, (box[1]+box[3])/2
        edges.append([i for i, (a,b,c,d) in enumerate(targets) if a <= x <= c and b <= y <= d])
    owners = {}
    def augment(p, seen):
        for g in edges[p]:
            if g in seen:
                continue
            seen.add(g)
            if g not in owners or augment(owners[g], seen):
                owners[g] = p
                return True
        return False
    for p in range(len(predictions)):
        augment(p, set())
    return {p:g for g,p in owners.items()}


def metrics(rows):
    tp = sum(r['tp'] for r in rows)
    pred = sum(r['predictions'] for r in rows)
    gt = sum(r['targets'] for r in rows)
    return dict(tp=tp, predictions=pred, targets=gt,
                precision=tp/pred if pred else None, recall=tp/gt if gt else None,
                protocol_median_ms=statistics.median([r['protocol_ms'] for r in rows]) if rows else None)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runner-root', type=Path, required=True, help='Build/models checkout (tests/protocol.py client is reused)')
    parser.add_argument('--dataset', type=Path, default=ROOT)
    args = parser.parse_args()
    base = args.dataset.resolve()
    split = json.loads((base/'split.json').read_text())
    scenes = json.loads((base/'scenes.json').read_text())
    if not scenes:
        parser.error('no captured scenes; refusing to publish empty evaluation results')
    if set(split) != set(scenes) or any(v not in ('tune','test') for v in split.values()):
        parser.error('split must assign every scene exactly once to tune/test')
    # Validate all annotations before launching a detector or writing results.
    from PIL import Image, ImageDraw
    import numpy as np
    inputs = {}
    for name, meta in scenes.items():
        if Path(name).name != name:
            raise ValueError('scene names must be basenames')
        gt = json.loads((base/'gt'/f'{name}.json').read_text())
        if gt.get('verified') is not True or gt.get('source') not in ('dom','manual'):
            raise ValueError(f'{name}: unverified GT')
        if len(gt['boxes']) != len(gt['kinds']) or not set(gt['kinds']) <= KINDS:
            raise ValueError(f'{name}: invalid kinds')
        image = Image.open(base/'frames'/f'{name}.png').convert('RGB')
        w,h = image.size
        for a,b,c,d in gt['boxes']:
            if not (0 <= a < c <= w and 0 <= b < d <= h):
                raise ValueError(f'{name}: invalid box')
        inputs[name] = (gt, image)
    spec = importlib.util.spec_from_file_location('protocol', ROOT.parent/'tests/protocol.py')
    protocol = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(protocol)
    protocol.ROOT = args.runner_root.resolve()
    (protocol.ROOT/'weights').mkdir(exist_ok=True)
    (base/'results').mkdir(exist_ok=True)
    (base/'out').mkdir(exist_ok=True)
    client = protocol.Client(size=1280, extra=('--conf','0.05','--iou','0.7'))
    rows, predictions = [], {}
    try:
        for name, (gt,image) in inputs.items():
            rgb = np.array(image)
            bgra = np.concatenate((rgb[:,:,::-1], np.full((*rgb.shape[:2],1),255,dtype=np.uint8)),axis=2)
            for threshold in (.05,.25):
                start = time.perf_counter()
                response = client.request(bgra, seq=len(rows)+1, conf=threshold)
                elapsed = (time.perf_counter()-start)*1000
                if response['status']:
                    raise RuntimeError(response)
                boxes = response['boxes']
                pairs = match(boxes, gt['boxes'])
                row = dict(scene=name, split=split[name], category=scenes[name]['category'], threshold=threshold,
                           tp=len(pairs), predictions=len(boxes), targets=len(gt['boxes']),
                           protocol_ms=elapsed, inference_ms=response['inference_ms'])
                row['kinds'] = {k:dict(targets=gt['kinds'].count(k), tp=sum(gt['kinds'][g]==k for g in pairs.values())) for k in sorted(KINDS)}
                rows.append(row)
                predictions[f'{name}_{threshold}'] = dict(response=response, matching=pairs)
                overlay = image.copy()
                draw = ImageDraw.Draw(overlay)
                for g,box in enumerate(gt['boxes']):
                    draw.rectangle(box, outline='green' if g in pairs.values() else 'yellow',width=2)
                for p,box in enumerate(boxes):
                    draw.rectangle(box[:4], outline='blue' if p in pairs else 'red',width=2)
                overlay.save(base/'out'/f'{name}_{threshold}.png')
    finally:
        client.close()
    groups = {}
    for threshold in (.05,.25):
        selected = [r for r in rows if r['threshold']==threshold]
        for dimension in ('split','category','scene'):
            for value in sorted({r[dimension] for r in selected}):
                groups[f'{threshold}/{dimension}/{value}'] = metrics([r for r in selected if r[dimension]==value])
    kinds = {}
    for threshold in (.05,.25):
        for subset in ('tune','test'):
            selected = [r for r in rows if r['threshold']==threshold and r['split']==subset]
            for kind in sorted(KINDS):
                total = sum(r['kinds'][kind]['targets'] for r in selected)
                tp = sum(r['kinds'][kind]['tp'] for r in selected)
                kinds[f'{threshold}/{subset}/{kind}'] = dict(targets=total,tp=tp,misses=total-tp,recall=tp/total if total else None,
                    precision=None, note='Detector has no kind labels; unmatched predictions cannot be assigned a GT kind. Latency is frame-level.')
    result = dict(device=client.device, imgsz=1280, rows=rows, aggregates=groups, kinds=kinds,
                  latency_note='One request per scene/threshold; protocol includes transport, preprocessing and NMS; inference excludes them. No latency benchmark claim.',
                  miss_note='Kind counts are descriptive, not causal diagnoses; manually review tune overlays for merged links and small text.')
    (base/'results'/'scores.json').write_text(json.dumps(result,indent=2)+'\n')
    (base/'results'/'predictions.json').write_text(json.dumps(predictions,indent=2)+'\n')


if __name__ == '__main__':
    main()
