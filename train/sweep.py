#!/usr/bin/env python3
"""Sweep confidence on validation (select) or held-out TEST data.

Inference runs at conf 0.01; strict offline score filtering mirrors the runner.
No eval TUNE scene is used. NEFER_HINTS_RUNNER overrides build/nefer-hints.
"""
import argparse
import importlib.util
import json
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

R = Path(__file__).resolve().parents[1]
GRID = [0.01, 0.02, 0.03, 0.04] + [round(0.05 + 0.025 * i, 3) for i in range(19)]


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def bgra(im):
    rgb = np.array(im.convert('RGB'))
    return np.concatenate((rgb[:, :, ::-1], np.full((*rgb.shape[:2], 1), 255, np.uint8)), axis=2)


def yolo_inputs(directory):
    images = sorted((directory / 'images').glob('*.png'))
    if not images:
        raise ValueError(f'No images in {directory}')
    for image in images:
        with Image.open(image) as im:
            width, height = im.size
        gt = []
        for line in (directory / 'labels' / (image.stem + '.txt')).read_text().splitlines():
            _, cx, cy, w, h = map(float, line.split())
            gt.append(((cx-w/2)*width, (cy-h/2)*height, (cx+w/2)*width, (cy+h/2)*height))
        yield image, gt, False


def web_metrics(rows, threshold, match):
    tp = pred = tgt = 0
    for boxes, gt, _ in rows:
        filtered = [b for b in boxes if b[4] > threshold]
        tp += len(match(filtered, gt))
        pred += len(filtered)
        tgt += len(gt)
    return tp / pred if pred else 0.0, tp / tgt if tgt else 0.0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--model', type=Path, required=True)
    ap.add_argument('--name', required=True)
    ap.add_argument('--set', choices=('select', 'test'), required=True)
    ap.add_argument('--gpu', default='cpu')
    ap.add_argument('--iou', type=float, default=0.7)
    a = ap.parse_args()
    runner = Path(os.environ.get('NEFER_HINTS_RUNNER', R / 'build/nefer-hints')).resolve()
    model = a.model.resolve()
    protocol = load(R / 'tests/protocol.py', 'protocol')
    score = load(R / 'eval/score.py', 'score')
    if a.set == 'select':
        web = list(yolo_inputs(R / 'data/web/val'))
        web_only_count = len(web)
        gui_sets = ['web/val']
        if any((R / 'data/native/val/images').glob('*.png')):
            web.extend(yolo_inputs(R / 'data/native/val'))
            gui_sets.append('native/val')
    else:
        scenes = json.loads((R / 'eval/scenes.json').read_text())
        split = json.loads((R / 'eval/split.json').read_text())
        groups = json.loads((R / 'eval/groups.json').read_text())
        contaminated = {scene for group in groups.values() if any(split[s] == 'tune' for s in group) for scene in group}
        web = [(R / 'eval/frames' / f'{name}.png',
                json.loads((R / 'eval/gt' / f'{name}.json').read_text())['boxes'],
                name not in contaminated)
               for name in sorted(split) if split[name] == 'test']
    if a.set == 'test':
        native_test = [scenes[image.stem]['category'] in ('native_gtk', 'menus')
                       for image, _, _ in web]
    terminal = list(yolo_inputs(R / 'data/terminal' / ('val' if a.set == 'select' else 'test')))
    rows = [[], []]
    with tempfile.TemporaryDirectory(prefix='nh-sweep-') as directory:
        tmp = Path(directory)
        (tmp / 'build').mkdir()
        (tmp / 'weights').mkdir()
        (tmp / 'build/nefer-hints').symlink_to(runner)
        (tmp / 'models').symlink_to(model)
        protocol.ROOT = tmp
        client = protocol.Client(size=1280, extra=('--conf', '0.01', '--iou', str(a.iou), '--gpu', a.gpu))
        try:
            seq = 0
            for inputs, output in zip((web, terminal), rows):
                for image, gt, independent in inputs:
                    seq += 1
                    with Image.open(image) as im:
                        response = client.request(bgra(im), seq=seq, conf=0.01)
                    if response['status']:
                        raise RuntimeError(response)
                    output.append(([b[:5] for b in response['boxes']], gt, independent))
        finally:
            client.close()
    model_label = str(model.relative_to(R)) if model.is_relative_to(R) else model.name
    out = dict(name=a.name, set=a.set, iou=a.iou, runner=runner.name, model=model_label, thresholds={})
    if a.set == 'select':
        out['gui_sets'] = gui_sets
    for t in GRID:
        precision, recall = web_metrics(rows[0], t, score.match)
        ttp = ttgt = fp = 0
        for boxes, gt, _ in rows[1]:
            filtered = [b for b in boxes if b[4] > t]
            ttp += len(score.match(filtered, gt))
            ttgt += len(gt)
            fp += sum(not any(g[0] <= (b[0]+b[2])/2 <= g[2] and g[1] <= (b[1]+b[3])/2 <= g[3] for g in gt) for b in filtered)
        metrics = dict(web_precision=precision, web_recall=recall,
                       terminal_recall=ttp/ttgt if ttgt else 0.0,
                       terminal_fp_per_screen=fp/len(rows[1]))
        if a.set == 'select':
            p, r = web_metrics(rows[0][:web_only_count], t, score.match)
            np_, nr = web_metrics(rows[0][web_only_count:], t, score.match)
            metrics.update(web_only_precision=p, web_only_recall=r,
                           native_precision=np_, native_recall=nr)
        if a.set == 'test':
            p, r = web_metrics([row for row in rows[0] if row[2]], t, score.match)
            metrics.update(web_precision_independent=p, web_recall_independent=r)
            for source, is_native in (('web', False), ('native', True)):
                subset = [row for row, native in zip(rows[0], native_test) if native == is_native]
                p, r = web_metrics(subset, t, score.match)
                metrics.update({f'{source}_test_precision': p, f'{source}_test_recall': r})
        out['thresholds'][f'{t:.3f}'] = metrics
    destination = R / 'train/results' / f'sweep-{a.name}-{a.set}-iou{a.iou:g}.json'
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(out, indent=1) + '\n')
    print(destination.relative_to(R))
    print(json.dumps(out['thresholds'], indent=1))


if __name__ == '__main__':
    main()
