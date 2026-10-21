"""Manual coordinates recorded from inspected native captures; no detector-derived GT."""
import json
from pathlib import Path
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent
scenes=json.loads((R/'scenes.json').read_text())
def save(name,items,category):
 gt=dict(boxes=[b for b,k in items],kinds=[k for b,k in items],source='manual',notes='Single annotator; visually inspected original capture. Fictional files only; GIO_USE_VOLUME_MONITOR=unix prevents host volume labels. Disabled controls excluded. Partly occluded underlying targets excluded when centre is covered.',verified=True)
 (R/'gt'/f'{name}.json').write_text(json.dumps(gt,indent=2)+'\n')
 im=Image.open(R/'frames'/f'{name}.png');d=ImageDraw.Draw(im)
 for b,k in items:d.rectangle(b,outline='lime',width=2)
 im.save(R/'gt'/f'{name}_gt.png');scenes[name]={'category':category}
def boxes(bs,k):return [(b,k) for b in bs]
nav=boxes([[7,5,39,40],[239,5,274,40],[649,5,746,40],[747,5,863,40],[1478,5,1511,40],[1518,5,1555,40],[1817,5,1850,40],[1850,5,1876,40],[1880,5,1914,40]],'icon_button')+boxes([[8,y-17,270,y+17] for y in (70,108,146,184,222)],'row_file')
icons=boxes([[320+i*161,68,431+i*161,195] for i in range(6)],'row_file')
rows=boxes([[305,92+i*52,1848,135+i*52] for i in range(6)],'row_file')+boxes([[1856,102+i*52,1889,130+i*52] for i in range(6)],'icon_button')+boxes([[304,45,1630,79],[1640,45,1724,79],[1725,45,1895,79]],'icon_button')
save('nautilus',nav+icons,'native_gtk')
save('nautilus-list',nav+rows,'native_gtk')
context=boxes([[310,y-14,583,y+14] for y in (158,202,234,266,298,344,376,408,440,485)],'menu_item')
save('nautilus-context',nav+[item for item in rows if item[0][0]>600]+context,'menus')
menu=boxes([[145,y-14,367,y+14] for y in (74,106,138,260,292,324,356)],'menu_item')
save('nautilus-menu',[i for i in nav+rows if not (140<(i[0][0]+i[0][2])/2<374 and 50<(i[0][1]+i[0][3])/2<379)]+menu,'menus')
th=boxes([[x,0,x+w,27] for x,w in ((0,40),(42,41),(85,46),(135,36),(174,91),(268,48))],'menu_item')+boxes([[78,30,113,67],[115,30,151,67],[1880,30,1918,67]],'icon_button')+boxes([[158,31,1874,66]],'field')+boxes([[8,y-12,166,y+12] for y in (111,137,164,190,245,299)],'row_file')+boxes([[240+i*538,130,680+i*538,635] for i in range(3)]+[[240+i*538,668,1180 if i==1 else 680+i*538,1051] for i in range(3)],'row_file')
save('thunar',th,'native_gtk')
thmenu=boxes([[2,y-12,304,y+12] for y in (40,68,95,123,151,179,233,261,289)],'menu_item')
# Sidebar hidden in menu capture; icon grid shifts 170 pixels left.
thbase=[i for i in th if (i[0][0]+i[0][2])/2>306 or (i[0][1]+i[0][3])/2>302]
save('thunar-menu',thbase+thmenu,'menus')
ed=boxes([[3,3,81,42],[88,4,126,42],[1798,4,1835,42],[1838,4,1875,42],[1880,4,1916,42]],'icon_button')+boxes([[2,48,1917,1078]],'field')
save('editor',ed,'native_gtk')
em=boxes([[1710,66,1758,114],[1782,66,1830,114],[1853,66,1901,114],[1713,137,1751,168],[1859,137,1897,168]],'icon_button')+boxes([[1698,y-14,1911,y+14] for y in (198,243,275,352,384,428,474,506,538)],'menu_item')
save('editor-menu',[i for i in ed if i[1]!='field']+em+boxes([[2,48,1688,1078]],'field'),'menus')
(R/'scenes.json').write_text(json.dumps(scenes,indent=2)+'\n')
