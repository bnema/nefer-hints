"""Generate measured tables and reproducible tune miss morphology counts."""
import json
from collections import Counter
from pathlib import Path
R=Path(__file__).resolve().parent
s=json.loads((R/'results/scores.json').read_text());p=json.loads((R/'results/predictions.json').read_text())
lines=['# Measured results','', '| Split | Threshold | TP / predictions / GT | Precision | Recall | Protocol median ms |','|---|---:|---:|---:|---:|---:|']
for t in (.05,.25):
 for split in ('tune','test'):
  v=s['aggregates'][f'{t}/split/{split}'];lines.append(f"| {split} | {t} | {v['tp']} / {v['predictions']} / {v['targets']} | {v['precision']:.2%} | {v['recall']:.2%} | {v['protocol_median_ms']:.2f} |")
lines+=['','## Tune miss analysis','','Counts below are mutually exclusive morphology proxies, not proven model causes.', 'A merged-link diagnosis requires additional manual prediction review. Small means', 'GT height <18 pixels or width <16 pixels. Prediction/GT matching is preserved in JSON.','', '| Threshold | Miss morphology | Count |','|---:|---|---:|']
counts={}
for t in (.05,.25):
 c=Counter()
 for row in s['rows']:
  if row['split']!='tune' or row['threshold']!=t:continue
  name=row['scene'];gt=json.loads((R/'gt'/f'{name}.json').read_text());matched=set(p[f'{name}_{t}']['matching'].values())
  for i,(b,k) in enumerate(zip(gt['boxes'],gt['kinds'])):
   if i in matched:continue
   key='small text links' if k=='text_link' and (b[3]-b[1]<18 or b[2]-b[0]<16) else {'text_link':'other text links','icon_button':'icons / buttons','row_file':'rows / files','field':'fields','menu_item':'menu items','tab':'tabs'}.get(k,'other')
   c[key]+=1
 counts[str(t)]=dict(c)
 for key,n in c.most_common():lines.append(f'| {t} | {key} | {n} |')
lines+=['','## Scene inventory','','| Scene | Category | Split | Primary GT | Targets |','|---|---|---|---|---:|']
scenes=json.loads((R/'scenes.json').read_text());split=json.loads((R/'split.json').read_text())
for name,meta in scenes.items():
 gt=json.loads((R/'gt'/f'{name}.json').read_text());lines.append(f"| {name} | {meta['category']} | {split[name]} | {gt['source']} | {len(gt['boxes'])} |")
(R/'results/table.md').write_text('\n'.join(lines)+'\n');(R/'results/tune-misses.json').write_text(json.dumps(counts,indent=2)+'\n')
print('\n'.join(lines[:9]));print(counts)
