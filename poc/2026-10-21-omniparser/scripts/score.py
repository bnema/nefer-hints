"""Score manually verified gt/<scene>.json against eval/predictions.json.
GT schema: {"boxes": [[x1,y1,x2,y2],...], "notes": "...", "verified": true}.
No GT is inferred from either detector. Fail closed on absent/unverified annotations.
"""
import json
from pathlib import Path
from PIL import Image,ImageDraw
R=Path('/tmp/omniparser-eval')
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

def main():
    data=json.loads((R/'eval/predictions.json').read_text()); scores={}; missing=[]
    for scene,s in data['scenes'].items():
        path=R/'gt'/f'{scene}.json'
        if not path.exists(): missing.append(scene); continue
        gt=json.loads(path.read_text())
        if not gt.get('verified'): missing.append(scene); continue
        boxes=gt['boxes']; meta=s['neferwl']; scale=meta['scale'] or 1
        def click(t):
            x,y,x2,y2=t['rect']
            return ((x+(x2-x)/2)*scale,(y+(y2-y)/2)*scale)
        allp=[click(t) for t in meta['targets']]
        ocr=[click(t) for t in meta['targets'] if t['source']=='ocr']
        methods={'neferwl-all':(allp,meta['capture_ms']+meta['scan_ms']), 'neferwl-ocr':(ocr,None)}
        for k,v in s['omniparser'].items():
            methods['omni-'+k]=([((a+c)/2,(b+d)/2) for a,b,c,d in v['boxes']],v['median_ms'])
        methods['union']=(ocr+methods['omni-0.25/1280'][0],None)
        scores[scene]={}
        for name,(points,latency) in methods.items():
            owners,labels=match(points,boxes); tp=len(owners); n=len(points)
            scores[scene][name]={'gt':len(boxes),'predictions':n,'tp':tp,'dup':labels.count('dup'),'fp':labels.count('fp'),'precision':tp/n if n else None,'recall':tp/len(boxes) if boxes else None,'latency_ms':latency,'matched_gt':sorted(owners),'prediction_labels':labels,'points':points,'category_recall':{c:{'matched':sum(j in owners for j,e in enumerate(gt['elements']) if e['category']==c),'gt':sum(e['category']==c for e in gt['elements'])} for c in sorted(set(e['category'] for e in gt['elements']))}}
            im=Image.open(R/'frames'/f'{scene}.png').convert('RGB'); d=ImageDraw.Draw(im)
            for j,b in enumerate(boxes): d.rectangle(b,outline='green' if j in owners else 'yellow',width=2)
            for (x,y),label in zip(points,labels): d.ellipse((x-4,y-4,x+4,y+4),fill='blue' if label=='tp' else 'red')
            im.save(R/'eval'/f'{scene}_{name.replace("/","-")}.png')
    totals={}
    for name in next(iter(scores.values())) if scores else []:
        rows=[s[name] for s in scores.values()]; t={k:sum(r[k] for r in rows) for k in ['gt','predictions','tp','dup','fp']}
        t.update(precision=t['tp']/t['predictions'] if t['predictions'] else None,recall=t['tp']/t['gt'],category_recall={})
        for c in ['text_links','icons_buttons','list_rows_files','menu_items']:
            n=sum(r['category_recall'].get(c,{}).get('gt',0) for r in rows); hit=sum(r['category_recall'].get(c,{}).get('matched',0) for r in rows)
            t['category_recall'][c]={'gt':n,'matched':hit,'recall':hit/n if n else None}
        totals[name]=t
    regions={}
    for scene in scores:
        for e in json.loads((R/'gt'/f'{scene}.json').read_text())['elements']: regions[e['region']]=regions.get(e['region'],0)+1
    result={'totals':totals,'gt_regions':regions,'status':'PARTIAL' if missing else 'DONE','missing_verified_gt':missing,'scenes':scores,'notes':['Union concatenates predictions, retaining duplicates.','NeferWL OCR-only latency cannot be isolated from dump scan_ms; null, not zero.','Empty-prediction precision is undefined (null).']}
    (R/'eval/scores.json').write_text(json.dumps(result,indent=2))
    if missing: raise SystemExit('Missing verified manual GT: '+', '.join(missing))
if __name__=='__main__': main()
