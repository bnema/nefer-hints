from pathlib import Path
import json
from PIL import Image,ImageDraw
R=Path('/tmp/omniparser-eval'); scenes={}
def add(s,b,label='',category='text_links',region='page_content'):
 scenes.setdefault(s,[]).append(dict(box=b,label=label,category=category,region=region))
def chrome(s):
 for b,l in [([0,0,198,42],'restore tab'),([198,10,220,33],'close restore'),([229,0,421,42],'active tab'),([423,10,445,33],'close active'),([455,10,480,34],'new tab'),([10,52,34,77],'sidebar'),([46,52,70,77],'back'),([83,52,106,77],'forward'),([117,52,142,77],'reload'),([268,49,294,80],'site security'),([296,49,1590,80],'address'),([1594,51,1619,78],'bookmark'),([1746,50,1805,79],'VPN'),([1814,50,1839,79],'account'),([1850,50,1875,79],'extensions'),([1884,49,1915,80],'menu'),([1850,9,1877,34],'window utility'),([1886,9,1911,34],'close window')]: add(s,b,l,'icons_buttons','web_chrome')
# HN manually transcribed row boundaries from enlarged strips.
s='firefox-hn';chrome(s)
for b,l in [([153,94,173,116],'logo'),([178,96,265,114],'Hacker News'),([270,96,297,114],'new'),([309,96,338,114],'past'),([351,96,416,114],'comments'),([430,96,452,114],'ask'),([468,96,499,114],'show'),([514,96,541,114],'jobs'),([553,96,600,114],'submit'),([1731,96,1764,115],'login')]:add(s,b,l)
# title end, site end; username start/end, age end, hide start, comments start/end
rows=[(294,396,244,285,340,350,379,445),(540,594,236,282,350,360,389,423),(567,660,238,254,323,334,363,396),(405,478,245,264,322,332,360,426),(608,653,245,255,315,325,354,419),(702,792,243,275,330,340,369,429),(324,404,244,292,348,358,387,440),(238,294,244,264,324,334,363,429),(428,558,245,284,344,354,383,449),(584,697,244,277,337,347,376,436),(498,610,243,291,345,355,384,444),(525,605,244,281,340,350,379,445),(349,423,245,274,329,339,368,428),(345,443,245,278,332,342,371,431),(495,575,245,263,316,326,355,415),(329,423,244,271,325,335,364,417),(530,621,243,298,351,361,390,450),(468,538,242,283,337,347,376,436),(391,502,244,285,339,349,378,438),(607,751,244,264,324,334,363,423),(507,582,243,291,337,347,376,409),(439,548,244,295,349,359,388,448),(352,443,244,286,346,356,385,451),(692,820,245,281,341,351,380,440),(310,395,244,286,332,342,371,435),(525,630,245,270,330,340,369,435)]
for i,(te,se,us,ue,ae,hs,cs,ce) in enumerate(rows):
 y=130+i*37
 add(s,[173,y+2,182,y+12],f'vote {i+1}','icons_buttons')
 add(s,[184,y,te,y+16],f'title {i+1}')
 add(s,[te+3,y+2,se,y+15],f'site {i+1}')
 if y+19<1080:
  for a,b,l in [(us,ue,'user'),(ue+2,ae,'age'),(hs,hs+21,'hide'),(cs,ce,'comments')]:add(s,[a,y+18,b,min(y+29,1080)],f'{l} {i+1}')
# Arch firefox page, native-resolution manually read.
s='firefox-arch';chrome(s)
arch=[]
def ar(b,l='',cat='text_links'):arch.append((b,l,cat))
ar([16,95,208,135],'logo','icons_buttons')
for a,b,l in [(1287,1330,'Home'),(1359,1426,'Packages'),(1454,1509,'Forums'),(1537,1569,'Wiki'),(1598,1645,'GitLab'),(1673,1731,'Security'),(1760,1791,'AUR'),(1819,1891,'Download')]:ar([a,109,b,129],l)
ar([1727,183,1862,207],'package search','icons_buttons')
for b,l in [([803,249,1054,267],'community repos'),([981,281,1021,299],'forums'),([1053,281,1127,299],'mail lists'),([1406,281,1432,299],'wiki'),([1448,323,1525,340],'learn more'),([48,416,620,433],'news1'),([784,440,963,458],'systemd v261'),([1184,464,1219,482],'TPM2'),([226,488,362,507],'systemd cryptenroll'),([410,488,648,507],'ArchWiki'),([873,488,988,507],'pcrlock'),([48,545,431,563],'news2'),([48,700,305,717],'news3'),([48,895,303,912],'news4'),([905,919,1078,937],'leader'),([89,943,198,961],'election rules'),([436,967,597,985],'responsibilities'),([48,1049,545,1067],'news5'),([1713,251,1765,271],'updates more'),([1852,252,1868,269],'updates RSS'),([1521,383,1534,398],'news RSS')]:ar(b,l)
# Each package name and architecture are independent links.
for y,end in [(279,1686),(298,1674),(316,1815),(335,1653),(353,1724),(372,1704),(390,1685),(409,1657),(427,1731),(446,1731),(464,1770),(483,1705),(501,1661),(520,1686),(538,1683),(556,1716)]:
 # package names are black plain text, not links
 if y!=335:ar([1818,y,1863,y+16],'architecture')
for y,end,l in [(626,1612,'Wiki'),(645,1673,'Manual'),(663,1693,'Install'),(723,1660,'mail'),(741,1665,'IRC'),(759,1656,'Planet'),(778,1750,'International'),(838,1631,'Donate'),(856,1712,'Freewear'),(874,1719,'HELLOTUX'),(935,1695,'Mirror tool'),(953,1648,'Mirror list'),(972,1666,'Mirror status'),(1032,1686,'Get involved'),(1051,1635,'Dev blog'),(1070,1670,'Projects')]:ar([1585,y,end,min(y+17,1080)],l)
for b,l,c in arch:add(s,b,l,c)
s='firefox-menu';chrome(s)
# Preserve visible underlying page controls. Popup covers right sidebar and nav from x1545.
for b,l,c in arch:
 if b[2]<=1545 or b[1]>=800:add(s,b,l,c)
for y,l in [(171,'New Tab'),(205,'New Window'),(239,'Private'),(282,'History'),(316,'Bookmarks'),(350,'Downloads'),(384,'Passwords'),(418,'Extensions'),(461,'Print'),(495,'Save'),(529,'Translate'),(563,'Find'),(640,'Settings'),(674,'More Tools'),(708,'Help'),(751,'Quit')]:add(s,[1557,y,1900,y+27],l,'menu_items','web_chrome')
for b,l in [([1605,119,1654,138],'sign in'),([1868,99,1892,123],'dismiss sync'),([1769,597,1793,623],'zoom out'),([1797,597,1840,623],'reset zoom'),([1848,597,1871,623],'zoom in'),([1874,597,1898,623],'fullscreen')]:add(s,b,l,'icons_buttons','web_chrome')
# Nautilus icons + names counted once, partial last-row icons included.
for s in ['nautilus-home','nautilus-menu']:
 for y,l in [(53,'Home'),(91,'Recent'),(129,'Starred'),(167,'Network'),(205,'Trash'),(256,'Pictures'),(294,'Downloads'),(332,'Videos')]:add(s,[8,y,236,y+34],l,'list_rows_files','native')
 for b,l in [([9,10,36,37],'Search'),([242,8,272,38],'main menu'),([291,9,317,37],'back'),([330,9,356,37],'forward'),([650,6,1483,41],'location'),([1484,8,1508,38],'path menu'),([1522,8,1551,38],'search folder'),([1820,8,1849,38],'view'),([1850,8,1875,38],'view menu'),([1882,8,1913,39],'close'),([235,426,260,450],'unmount')]:add(s,b,l,'icons_buttons','native')
 for row in range(4):
  for col in range(5):
   x=350+322*col;y=85+298*row
   # Clip occluded upper-left icon to visible lower section in menu scene.
   if s.endswith('menu') and row==0 and col==0:y=279
   add(s,[x,y,x+212,min(1080,85+298*row+266)],f'file {row},{col}','list_rows_files','native')
 if s.endswith('menu'):
  for y,l in [(53,'New Folder'),(85,'New Document'),(117,'Open With'),(194,'Select All'),(239,'Properties')]:add(s,[288,y,499,y+31],l,'menu_items','native')
# Dumber Arch, distinct CSS sizing from Firefox.
s='dumber-arch'
for b,l in [([19,14,290,72],'logo'),([1040,34,1099,62],'Home'),([1135,34,1229,62],'Packages'),([1268,34,1343,62],'Forums'),([1383,34,1425,62],'Wiki'),([1466,34,1529,62],'GitLab'),([1570,34,1648,62],'Security'),([1689,34,1733,62],'AUR'),([1773,34,1868,62],'Download'),([1013,226,1342,251],'community repo'),([1274,297,1336,320],'forums'),([60,322,154,345],'mail lists'),([519,322,550,345],'wiki'),([1274,358,1374,380],'learn'),([48,486,821,508],'news1'),([1067,520,1281,542],'systemd'),([249,579,300,602],'TPM'),([284,614,465,638],'cryptenroll'),([526,614,840,638],'ArchWiki'),([1146,614,1293,638],'pcrlock'),([48,694,558,717],'news2'),([48,936,430,960],'news3'),([1634,230,1700,254],'more'),([1835,232,1853,252],'RSS'),([1371,440,1388,459],'RSS')]:add(s,b,l,'icons_buttons' if l=='logo' else 'text_links')
add(s,[1660,136,1848,168],'search','icons_buttons')
for y,end in [(266,1588),(292,1567),(317,1782),(369,1635),(394,1625),(420,1597),(445,1551),(470,1643),(495,1652),(521,1700),(547,1608),(572,1572),(598,1604),(624,1600),(650,1644)]:
 add(s,[1788,y,1851,y+24],'architecture')
for y,end,l in [(750,1497,'Wiki'),(777,1577,'Manual'),(801,1603,'Install'),(887,1562,'Mail'),(913,1575,'IRC'),(939,1557,'Planet'),(965,1674,'International'),(1048,1521,'Donate')]:add(s,[1458,y,end,y+24],l)
# Scrollbar is an actionable control, counted once on Dumber pages.
add(s,[1910,0,1920,1080],'scrollbar','icons_buttons')
# Wikipedia manually transcribed visible blue links and UI.
s='dumber-wiki'
for b,l,c in [([55,27,86,58],'main menu','icons_buttons'),([108,17,293,67],'logo','icons_buttons'),([345,23,872,63],'search field','icons_buttons'),([873,23,963,63],'Search','icons_buttons'),([1597,30,1657,55],'Donate','text_links'),([1667,30,1792,55],'Create account','text_links'),([1800,30,1852,55],'Log in','text_links'),([1396,128,1570,159],'languages','icons_buttons'),([344,177,395,204],'Article','text_links'),([413,177,449,204],'Talk','text_links'),([1312,177,1359,204],'Read','text_links'),([1378,177,1411,204],'Edit','text_links'),([1429,177,1529,204],'history','text_links'),([1547,174,1570,205],'tools','icons_buttons'),([172,176,222,207],'hide contents','icons_buttons'),([1740,176,1791,207],'hide appearance','icons_buttons')]:add(s,b,l,c)
for y,l in [(228,'Top'),(265,'Overview'),(301,'Software'),(337,'Comparison'),(393,'Compositors'),(430,'Adoption'),(466,'History'),(502,'See also'),(538,'References'),(574,'External links')]:add(s,[77,y,284,y+(44 if l=='Comparison' else 27)],l)
for y in [300,337,394,430,466]:add(s,[55,y,72,y+23],'expand','icons_buttons')
for y,l in [(274,'Small'),(316,'Standard text'),(358,'Large'),(459,'Standard width'),(501,'Wide'),(603,'Automatic'),(645,'Light'),(686,'Dark')]:add(s,[1620,y,1737,y+29],l,'icons_buttons')
for b,l in [([472,277,692,301],'communication'),([343,310,470,334],'display server'),([728,310,745,334],'C'),([1102,304,1130,325],'ref10'),([831,345,1019,369],'Wayland compositor'),([660,379,935,402],'compositing manager'),([343,467,379,490],'free'),([425,467,542,490],'open-source'),([1048,467,1145,490],'X Window 1'),([343,500,413,524],'X Window 2'),([541,496,568,516],'ref11'),([570,496,596,516],'ref12'),([598,496,624,516],'ref13'),([625,496,651,516],'ref14'),([768,500,939,524],'windowing'),([973,500,1025,524],'Linux'),([343,535,422,558],'Unix-like'),([604,530,632,549],'ref10'),([633,530,660,549],'ref15'),([458,568,574,592],'MIT'),([598,568,899,592],'permissive'),([902,564,930,584],'ref15'),([930,564,950,584],'ref7'),([504,602,646,626],'implementation'),([945,602,1018,626],'Weston'),([1021,596,1050,618],'ref10'),([490,683,521,705],'edit overview'),([824,731,904,755],'Red Hat'),([514,761,542,782],'ref16'),([343,853,431,877],'rendering'),([699,853,781,877],'X server'),([868,888,1027,911],'Direct Rendering 1'),([343,922,468,945],'Infrastructure'),([532,922,775,945],'DRM'),([941,983,970,1005],'ref17'),([636,1045,771,1069],'extension to X'),([1176,706,1307,731],'Original author'),([1176,740,1265,764],'Developer'),([1337,740,1465,764],'freedesktop'),([1176,832,1300,857],'Stable release'),([1418,798,1435,817],'ref1'),([1473,829,1491,849],'ref2'),([1492,833,1509,852],'edit release'),([1466,888,1484,907],'ref3'),([1485,890,1504,910],'edit weston'),([1372,969,1391,988],'ref4'),([1392,971,1410,991],'edit protocols'),([1337,1033,1353,1058],'C'),([1402,1069,1446,1080],'Linux bottom'),([1175,1069,1333,1080],'Operating system')]:add(s,b,l)
add(s,[1320,326,1418,447],'Wayland logo','icons_buttons');add(s,[1205,460,1532,644],'screenshot','icons_buttons')
add(s,[1195,646,1255,670],'Weston caption');add(s,[1297,646,1507,670],'reference implementation')
add(s,[1910,0,1920,1080],'scrollbar','icons_buttons')
for s,entries in scenes.items():
 notes=['Single visual annotator; exploratory. Boxes in original 1920x1080 pixels.','Wrapped Wikipedia X Window link represented by two visible fragments (two actionable regions); partial bottom controls included.','Disabled-looking back/forward and selected tabs included as ambiguous controls; GTK Paste disabled excluded.','Menu scenes retain visible background controls: clicking outside dismisses popup; background semantics are ambiguous.','File icon+label one target; partially visible bottom-row icons included; whitespace excluded.','HN logged-out upvote arrows included; points and story rank excluded.']
 obj={'boxes':[e['box'] for e in entries],'elements':entries,'notes':notes,'verified':True}
 (R/'gt'/f'{s}.json').write_text(json.dumps(obj,indent=2))
 im=Image.open(R/'frames'/f'{s}.png').convert('RGB');d=ImageDraw.Draw(im)
 for i,e in enumerate(entries):d.rectangle(e['box'],outline='#00b000',width=2);d.text(tuple(e['box'][:2]),str(i),fill='red')
 im.save(R/'gt'/f'{s}_gt.png')
 print(s,len(entries))
