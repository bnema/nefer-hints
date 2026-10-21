#!/usr/bin/env python3
"""Terminal test-set evaluation of a runner model dir through the binary protocol.

  python train/eval_terminal.py --model DIR --name NAME [--gpu cpu]

Whole frame (nregions=0) at conf 0.05 and 0.25. Metrics per threshold:
  recall        GT link box matched by a predicted centre inside it (one-to-one,
                bipartite matching from eval/score.py)
  fp_per_screen predictions whose centre is in no GT box, averaged over screens
  fp_nolink     same, over screens with zero GT links
  fp_status     FPs in the status-bar row. The manifest has no window geometry, so
                the fallback rule applies: on screens where any window has a status
                bar, FPs whose centre lies in the bottom 3 % of the frame (the
                status row is the last row of the lowest window; windows that do not
                reach the frame bottom are not covered).
Writes train/results/terminal-NAME.json and <=6 overlays in train/out/NAME/.
"""
import argparse, importlib.util, json, shutil, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

R = Path(__file__).resolve().parents[1]
BIN = Path('$HOME/.local/share/nefer-hints-test/bin/nefer-hints')
BAND = 0.03
THRESHOLDS = (0.05, 0.25)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--gpu', default='cpu')
    ap.add_argument('--data', type=Path, default=R / 'data/terminal/test')
    a = ap.parse_args()
    protocol = load(R / 'tests/protocol.py', 'protocol')
    score = load(R / 'eval/score.py', 'score')
    manifest = {m['id']: m for m in json.loads((R / 'data/terminal/manifest_test.json').read_text())}
    tmp = Path(tempfile.mkdtemp(prefix='nh-evalterm-'))
    (tmp / 'build').mkdir(); (tmp / 'weights').mkdir()
    (tmp / 'build/nefer-hints').symlink_to(BIN); (tmp / 'models').symlink_to(a.model.resolve())
    protocol.ROOT = tmp
    out_dir = R / 'train/out' / a.name
    shutil.rmtree(out_dir, ignore_errors=True); out_dir.mkdir(parents=True)
    (R / 'train/results').mkdir(exist_ok=True)
    client = protocol.Client(size=1280, extra=('--conf', '0.05', '--iou', '0.7', '--gpu', a.gpu))
    screens = {t: [] for t in THRESHOLDS}
    try:
        seq = 0
        for img in sorted((a.data / 'images').glob('*.png')):
            sid = img.stem
            im = Image.open(img).convert('RGB'); W, H = im.size
            lab = (a.data / 'labels' / (sid + '.txt')).read_text().split()
            gt = []
            for i in range(0, len(lab), 5):
                _, cx, cy, w, h = map(float, lab[i:i + 5])
                gt.append(((cx - w / 2) * W, (cy - h / 2) * H, (cx + w / 2) * W, (cy + h / 2) * H))
            rgb = np.array(im)
            bgra = np.concatenate((rgb[:, :, ::-1], np.full((H, W, 1), 255, np.uint8)), axis=2)
            has_status = any(w['status'] for w in manifest[sid]['wins']) if sid in manifest else False
            for t in THRESHOLDS:
                seq += 1
                r = client.request(bgra, seq=seq, conf=t)  # nregions=0: whole frame
                if r['status']:
                    raise RuntimeError(r)
                boxes = [b[:5] for b in r['boxes']]
                pairs = score.match(boxes, gt)
                fp = []
                for i, b in enumerate(boxes):
                    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                    if not any(g[0] <= cx <= g[2] and g[1] <= cy <= g[3] for g in gt):
                        fp.append(i)
                sfp = [i for i in fp if has_status and (boxes[i][1] + boxes[i][3]) / 2 >= H * (1 - BAND)]
                screens[t].append(dict(id=sid, targets=len(gt), tp=len(pairs), predictions=len(boxes), fp=len(fp),
                                       status_fp=len(sfp), has_status=has_status, boxes=boxes, gt=gt, pairs=pairs, fp_idx=fp))
    finally:
        client.close(); shutil.rmtree(tmp, ignore_errors=True)
    res = dict(model=str(a.model), name=a.name, gpu=a.gpu, screens=len(screens[THRESHOLDS[0]]), status_rule=f'bottom {BAND:.0%} of frame on screens with a status-bar window (no window geometry in manifest)')
    for t in THRESHOLDS:
        s = screens[t]; nl = [x for x in s if x['targets'] == 0]
        gtn = sum(x['targets'] for x in s)
        res[f'{t:.2f}'] = dict(
            link_recall=sum(x['tp'] for x in s) / gtn if gtn else None, targets=gtn, tp=sum(x['tp'] for x in s),
            fp_per_screen=sum(x['fp'] for x in s) / len(s), fp_total=sum(x['fp'] for x in s),
            nolink_screens=len(nl), fp_per_nolink_screen=sum(x['fp'] for x in nl) / len(nl) if nl else None,
            status_bar_fp=sum(x['status_fp'] for x in s),
            per_screen=[{k: x[k] for k in ('id', 'targets', 'tp', 'predictions', 'fp', 'status_fp')} for x in s])
    (R / 'train/results' / f'terminal-{a.name}.json').write_text(json.dumps(res, indent=1) + '\n')
    # overlays: up to 6 worst screens at 0.05 (most FP + misses)
    worst = sorted(screens[0.05], key=lambda x: -(x['fp'] + x['targets'] - x['tp']))[:6]
    for x in worst:
        im = Image.open(a.data / 'images' / (x['id'] + '.png')).convert('RGB'); d = ImageDraw.Draw(im)
        for g, box in enumerate(x['gt']):
            d.rectangle(box, outline='green' if g in x['pairs'].values() else 'yellow', width=3)
        for i, b in enumerate(x['boxes']):
            d.rectangle(b[:4], outline='red' if i in x['fp_idx'] else 'blue', width=2)
        im.save(out_dir / (x['id'] + '.png'))
    print(json.dumps({k: {m: v for m, v in res[k].items() if m != 'per_screen'} for k in ('0.05', '0.25')}, indent=1))


if __name__ == '__main__':
    sys.exit(main())
