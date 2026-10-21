#!/usr/bin/env python3
"""Confidence sweep over the eval TEST split and the terminal test set.

  venv/bin/python train/sweep.py --model <models-dir> --name <name> [--gpu cpu] [--iou 0.7]

Runs the runner once per image at conf 0.01 and filters boxes by score offline
(NMS suppressors always score higher, so this equals a run at the higher conf).
Writes train/results/sweep-<name>.json: per threshold, eval TEST precision/recall
and terminal link recall / FP per screen.
"""
import argparse, importlib.util, json, shutil, sys, tempfile
from pathlib import Path
import numpy as np
from PIL import Image

R = Path(__file__).resolve().parents[1]
BIN = Path('$HOME/.local/share/nefer-hints-test/bin/nefer-hints')
GRID = [0.01, 0.02, 0.03, 0.04] + [round(0.05 + 0.025 * i, 3) for i in range(19)]  # 0.01 .. 0.5


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def bgra(im):
    rgb = np.array(im.convert('RGB'))
    return np.concatenate((rgb[:, :, ::-1], np.full((*rgb.shape[:2], 1), 255, np.uint8)), axis=2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--gpu', default='cpu')
    ap.add_argument('--iou', default='0.7', help='runner NMS IoU')
    a = ap.parse_args()
    protocol = load(R / 'tests/protocol.py', 'protocol')
    score = load(R / 'eval/score.py', 'score')
    tmp = Path(tempfile.mkdtemp(prefix='nh-sweep-'))
    (tmp / 'build').mkdir(); (tmp / 'weights').mkdir()
    (tmp / 'build/nefer-hints').symlink_to(BIN); (tmp / 'models').symlink_to(a.model.resolve())
    protocol.ROOT = tmp
    split = json.loads((R / 'eval/split.json').read_text())
    evals, terms = [], []  # (boxes, gt)
    client = protocol.Client(size=1280, extra=('--conf', '0.01', '--iou', a.iou, '--gpu', a.gpu))
    try:
        seq = 0
        for name in sorted(n for n, s in split.items() if s == 'test'):
            gt = json.loads((R / 'eval/gt' / f'{name}.json').read_text())['boxes']
            seq += 1
            r = client.request(bgra(Image.open(R / 'eval/frames' / f'{name}.png')), seq=seq, conf=0.01)
            if r['status']:
                raise RuntimeError(r)
            evals.append(([b[:5] for b in r['boxes']], gt))
        d = R / 'data/terminal/test'
        for img in sorted((d / 'images').glob('*.png')):
            im = Image.open(img); W, H = im.size
            lab = (d / 'labels' / (img.stem + '.txt')).read_text().split()
            gt = []
            for i in range(0, len(lab), 5):
                _, cx, cy, w, h = map(float, lab[i:i + 5])
                gt.append(((cx - w / 2) * W, (cy - h / 2) * H, (cx + w / 2) * W, (cy + h / 2) * H))
            seq += 1
            r = client.request(bgra(im), seq=seq, conf=0.01)
            if r['status']:
                raise RuntimeError(r)
            terms.append(([b[:5] for b in r['boxes']], gt))
    finally:
        client.close(); shutil.rmtree(tmp, ignore_errors=True)
    out = {'name': a.name, 'model': str(a.model), 'thresholds': {}}
    for t in GRID:
        tp = pred = tgt = 0
        for boxes, gt in evals:
            b = [x for x in boxes if x[4] >= t]
            tp += len(score.match(b, gt)); pred += len(b); tgt += len(gt)
        ttp = ttgt = fp = 0
        for boxes, gt in terms:
            b = [x for x in boxes if x[4] >= t]
            ttp += len(score.match(b, gt)); ttgt += len(gt)
            fp += sum(not any(g[0] <= (x[0] + x[2]) / 2 <= g[2] and g[1] <= (x[1] + x[3]) / 2 <= g[3] for g in gt) for x in b)
        out['thresholds'][f'{t:.3f}'] = dict(
            eval_test_precision=tp / pred if pred else 0.0, eval_test_recall=tp / tgt,
            terminal_recall=ttp / ttgt, terminal_fp_per_screen=fp / len(terms))
    (R / 'train/results').mkdir(exist_ok=True)
    (R / 'train/results' / f'sweep-{a.name}.json').write_text(json.dumps(out, indent=1) + '\n')
    print('thr    evalP  evalR  termR  termFP')
    for t, m in out['thresholds'].items():
        print(f"{t}  {m['eval_test_precision']:.3f}  {m['eval_test_recall']:.3f}  {m['terminal_recall']:.3f}  {m['terminal_fp_per_screen']:.2f}")


if __name__ == '__main__':
    sys.exit(main())
