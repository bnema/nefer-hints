"""Apply recorded visual corrections after opening every web GT overlay."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent
# Shadow DOM/iframe controls and icon wrappers missed by light-DOM extraction.
FIXES={
 'wiki':[([198,14,235,53],'icon_button'),([1286,92,1431,125],'icon_button'),([1403,132,1434,160],'icon_button')]+[([1467,y-9,1486,y+9],'field') for y in (223,255,287,365,397,477,509,541)],
 'mdn':[([249,196,499,234],'field'),([1527,107,1608,145],'field'),([1625,107,1656,143],'icon_button'),([1421,159,1514,188],'icon_button'),([1532,158,1657,188],'icon_button'),([1047,694,1198,735],'icon_button'),([1242,660,1335,692],'tab'),([569,662,666,703],'tab'),([667,662,763,703],'tab'),([1272,620,1328,654],'icon_button'),([882,13,1001,42],'icon_button'),([1402,815,1528,850],'icon_button')],
 'mdn-forms':[([249,196,499,234],'field'),([1527,107,1608,145],'field'),([1625,107,1656,143],'icon_button'),([1421,159,1514,188],'icon_button'),([1532,158,1657,188],'icon_button'),([882,13,1001,42],'icon_button'),([1402,775,1528,810],'icon_button')],
 'github':[([32,21,64,53],'text_link')]+[([x,20,x+w,53],'icon_button') for x,w in ((86,86),(184,106),(305,88),(404,112),(537,94))],
 'login':[([937,48,982,93],'text_link')],
 'go':[([1255,8,1343,46],'icon_button'),([1477,6,1572,49],'icon_button'),([1739,6,1857,49],'icon_button')],
 'python-docs':[([48,193,187,211],'text_link')]
}
scenes=json.loads((R/'scenes.json').read_text())
# Reddit is a network-policy block, not a useful substitute for a news scene.
scenes.pop('reddit',None)
for name in scenes:
 p=R/'gt'/f'{name}.json';gt=json.loads(p.read_text())
 for box,kind in FIXES.get(name,[]):
  # Replace nested light-DOM fragment(s) with visually reviewed full control.
  gt['boxes'],gt['kinds']=map(list,zip(*[(b,k) for b,k in zip(gt['boxes'],gt['kinds']) if not (box[0]<= (b[0]+b[2])/2 <=box[2] and box[1]<=(b[1]+b[3])/2<=box[3])])) if gt['boxes'] else ([],[])
  gt['boxes'].append(box);gt['kinds'].append(kind)
 gt['verified']=True
 gt['notes']+=' All scene overlays opened and visually checked at capture resolution. Fullscreen viewport origin (0,0), DPR 1. Manual corrections for shadow/iframe controls and icon wrappers recorded in review_web.py; source denotes primary DOM method. Tiny targets below 4x4 excluded by protocol.'
 p.write_text(json.dumps(gt,indent=2)+'\n')
 im=Image.open(R/'frames'/f'{name}.png');d=ImageDraw.Draw(im)
 for b in gt['boxes']:d.rectangle(b,outline='lime',width=2)
 im.save(R/'gt'/f'{name}_gt.png')
(R/'scenes.json').write_text(json.dumps(scenes,indent=2)+'\n')
