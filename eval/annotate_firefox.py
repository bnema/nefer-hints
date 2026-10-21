"""Manual Firefox hamburger scene, inspected at full resolution."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent
items=[]
def add(box,kind):items.append((box,kind))
for a,b in ((0,226),(228,450),(451,674)):add([a,0,b,43],'tab')
for x,y in ((208,22),(433,22),(658,22),(692,22),(1897,22),(21,64),(129,64),(1607,64),(1795,64),(1825,64),(1863,64),(1898,64),(1879,110),(951,161),(942,330)):
 add([x-13,y-13,x+13,y+13],'icon_button')
add([265,48,1625,80],'field');add([631,105,932,138],'field');add([940,105,966,137],'icon_button')
for y in (212,258,302,348,420,466):add([40,y-18,269,y+18],'row_file')
for b in ([302,273,388,291],[348,360,431,379],[333,528,377,545],[380,609,479,628],[382,752,465,770],[333,992,383,1011]):add(b,'text_link')
for y in (527,610,754,994):add([825,y-17,953,y+17],'icon_button')
add([1560,89,1857,147],'icon_button')
for y in (184,218,252,295,328,363,397,431,474,508,575,652,686,721,765):add([1554,y-15,1906,y+15],'menu_item')
for x in (1780,1820,1860,1884):add([x-12,598,x+12,622],'icon_button')
gt=dict(boxes=[b for b,k in items],kinds=[k for b,k in items],source='manual',verified=True,notes='Fresh fictional Firefox profile, logged out. Add-ons Manager and hamburger menu; disabled back/forward and Translate excluded. Manual visual annotation, single annotator.')
(R/'gt/firefox-menu.json').write_text(json.dumps(gt,indent=2)+'\n')
im=Image.open(R/'frames/firefox-menu.png');d=ImageDraw.Draw(im)
for b,k in items:d.rectangle(b,outline='lime',width=2)
im.save(R/'gt/firefox-menu_gt.png')
s=json.loads((R/'scenes.json').read_text());s['firefox-menu']={'category':'menus'};(R/'scenes.json').write_text(json.dumps(s,indent=2)+'\n')
