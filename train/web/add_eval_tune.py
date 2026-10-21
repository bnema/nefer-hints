#!/usr/bin/env python3
"""Copy eval TUNE scenes (never TEST) into data/web/train as YOLO labels from their GT boxes."""
import json, shutil
from pathlib import Path
from PIL import Image
R = Path(__file__).resolve().parents[2]
split = json.loads((R / 'eval/split.json').read_text())
out = R / 'data/web/train'
(out / 'images').mkdir(parents=True, exist_ok=True); (out / 'labels').mkdir(exist_ok=True)
n = 0
for name, s in split.items():
    if s != 'tune':
        continue
    gt = json.loads((R / 'eval/gt' / (name + '.json')).read_text())
    im = Image.open(R / 'eval/frames' / (name + '.png')); W, H = im.size
    shutil.copy(R / 'eval/frames' / (name + '.png'), out / 'images' / ('evaltune_%s.png' % name))
    (out / 'labels' / ('evaltune_%s.txt' % name)).write_text(''.join('0 %.6f %.6f %.6f %.6f\n' % ((a + c) / 2 / W, (b + d) / 2 / H, (c - a) / W, (d - b) / H) for a, b, c, d in gt['boxes']))
    n += 1
print(n, 'tune scenes added')
