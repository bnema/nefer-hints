"""Score manually verified gt/<scene>.json against eval/predictions.json.
GT schema: {"boxes": [[x1,y1,x2,y2],...], "notes": "...", "verified": true}.
No GT is inferred from either detector. Fail closed on absent/unverified annotations.
"""
import json
from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parents[2]/'2026-10-21-omniparser'
def match(points,boxes):
    # Maximum bipartite matching avoids arbitrary errors for overlapping GT boxes.
    edges=[[j for j,(x1,y1,x2,y2) in enumerate(boxes) if x1<=x<x2 and y1<=y<y2] for x,y in points]
    owners={}
    def augment(i,seen):
        for j in edges[i]:
            if j in seen: continue
            seen.add(j)
            if j not in owners or augment(owners[j],seen): owners[j]=i; return True
        return False
    for i in range(len(points)): augment(i,set())
    tp=set(owners.values())
    labels=['tp' if i in tp else 'dup' if e else 'fp' for i,e in enumerate(edges)]
    return owners,labels

def score(predictions):
    totals = dict(gt=0, predictions=0, tp=0)
    for scene, boxes in predictions.items():
        gt=json.loads((R/'gt'/f'{scene}.json').read_text())
        if not gt.get('verified'): raise ValueError(f'Unverified GT: {scene}')
        points=[((a+c)/2,(b+d)/2) for a,b,c,d in boxes]
        owners,_=match(points,gt['boxes'])
        totals['gt']+=len(gt['boxes']); totals['predictions']+=len(boxes); totals['tp']+=len(owners)
    totals['precision']=totals['tp']/totals['predictions'] if totals['predictions'] else None
    totals['recall']=totals['tp']/totals['gt']
    return totals
