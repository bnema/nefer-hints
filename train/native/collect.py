#!/usr/bin/env python3
"""Deterministic native GUI collection under isolated headless NeferWL workers."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess as sp
import sys
import time
from multiprocessing import Pool

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from train.web.collect_web import stop_process
from train.tmpdirs import private_dir

OUT = ROOT / 'data/native'
MANIFEST = ROOT / 'train/native/manifest.json'
FAKE = Path('/tmp/nh-native')
TEMPLATES = ('files-grid', 'files-list', 'settings', 'preferences-dialog', 'table',
             'editor', 'context-menu', 'app-menu', 'sidebar-nav', 'form')
PALETTE = ('#3584e4', '#9141ac', '#26a269', '#e66100', '#c01c28')


def split_for(template):
    if template not in TEMPLATES:
        raise ValueError(template)
    return 'val' if template in ('preferences-dialog', 'table') else 'train'


def variant(toolkit, template, seed):
    rng = random.Random(seed)
    row = dict(toolkit=toolkit, template=template, seed=seed,
               theme=rng.choice(('light', 'dark')), accent=rng.choice(PALETTE),
               font_scale=round(rng.uniform(0.9, 1.25), 6),
               size='1920x1080' if rng.random() < 0.8 else '2560x1440',
               split=split_for(template))
    row['id'] = toolkit + '-' + template + '-' + hashlib.sha256(
        json.dumps(row, sort_keys=True).encode()).hexdigest()[:16]
    return row


def plan():
    rows = []
    for toolkit in ('gtk', 'qt'):
        train_index = 0
        for template in TEMPLATES:
            if split_for(template) == 'val':
                count = 25
            else:
                count = 33 if train_index < 4 else 32
                train_index += 1
            rows.extend(variant(toolkit, template, seed) for seed in range(count))
    return rows


def yolo_boxes(boxes, width, height):
    if width <= 0 or height <= 0:
        raise ValueError('invalid dimensions')
    result = []
    for box in boxes:
        a, b, c, d = map(float, box[:4])
        if not all(math.isfinite(v) for v in (a, b, c, d)):
            raise ValueError('non-finite box')
        a, c = (max(0, min(width, v)) for v in (a, c))
        b, d = (max(0, min(height, v)) for v in (b, d))
        if c - a >= 4 and d - b >= 4:
            result.append(((a+c)/2/width, (b+d)/2/height, (c-a)/width, (d-b)/height))
    return result


def merge_manifest(existing, new):
    rows = {r['id']: r for r in existing}
    rows.update((r['id'], r) for r in new)
    return [rows[k] for k in sorted(rows)]


def save_manifest(rows):
    tmp = MANIFEST.with_suffix('.tmp')
    tmp.write_text(json.dumps(rows, indent=2) + '\n')
    tmp.replace(MANIFEST)


def env_for(base, wayland=None):
    # Mirror web's allowlisted environment, but isolate HOME as well as state/runtime.
    env = dict(PATH=os.environ['PATH'], LANG='C.UTF-8')
    for key, sub in (('HOME', 'home'), ('XDG_CONFIG_HOME', 'config'),
                     ('XDG_DATA_HOME', 'data'), ('XDG_CACHE_HOME', 'cache'),
                     ('XDG_STATE_HOME', 'state'), ('XDG_RUNTIME_DIR', 'run')):
        directory = base / sub
        directory.mkdir(parents=True, exist_ok=True)
        env[key] = str(directory)
    os.chmod(base / 'run', 0o700)
    if wayland:
        env['WAYLAND_DISPLAY'] = wayland
    return env


def hard_timeout(signum, frame):
    raise TimeoutError('screen hard timeout (60 seconds)')


def worker(job):
    from PIL import Image
    index, tasks = job
    private_dir(FAKE)
    base = private_dir(FAKE / str(index))
    env = env_for(base)
    cfg = base / 'native.conf'
    cfg.write_text('terminal.auto-open = off\nborder.width = 0\nfocus.flash = off\nhint.enable = off\n')
    executable = shutil.which(os.environ.get('NEFERWL', 'neferwl'))
    if not executable:
        raise RuntimeError('Set NEFERWL to the compositor executable')
    comp = app = None
    size = wayland = None
    screens = 0
    results = []
    signal.signal(signal.SIGALRM, hard_timeout)
    with (base / 'collector.log').open('w') as log:
        try:
            for task in tasks:
                try:
                    signal.alarm(60)
                    if comp is None or comp.poll() is not None or size != task['size'] or screens >= 50:
                        stop_process(comp)
                        comp = None
                        lp = base / 'state/neferwl/runs/headless/latest.log'
                        lp.unlink(missing_ok=True)
                        size = task['size']
                        comp = sp.Popen([executable, '--backend=headless', '--size', size,
                                         '--no-xwayland', '--no-terminal', '--config', str(cfg),
                                         '--timeout', '7200s'], env=env, stdout=log, stderr=log,
                                        stdin=sp.DEVNULL, start_new_session=True)
                        deadline = time.monotonic() + 15
                        wayland = None
                        while time.monotonic() < deadline:
                            if comp.poll() is not None:
                                raise RuntimeError('compositor exited; see ' + str(base / 'collector.log'))
                            text = lp.read_text() if lp.exists() else ''
                            match = re.search(r'wayland-\d+', '\n'.join(l for l in text.splitlines() if 'listening' in l))
                            if match:
                                wayland = match[0]
                                break
                            time.sleep(0.1)
                        if not wayland:
                            raise TimeoutError('no listening entry')
                        screens = 0
                    screens += 1
                    screen = base / task['id']
                    screen.mkdir(exist_ok=True)
                    (screen / 'ready').unlink(missing_ok=True)
                    (screen / 'labels.json').unlink(missing_ok=True)
                    app_env = dict(env_for(base, wayland), GDK_BACKEND='wayland', QT_QPA_PLATFORM='wayland')
                    app_path = ROOT / 'train/native' / (task['toolkit'] + '_app.py')
                    command = ['/usr/bin/python3', str(app_path)]
                    for key in ('seed', 'template', 'theme', 'accent', 'font_scale'):
                        command.extend(['--' + key.replace('_', '-'), str(task[key])])
                    command.extend(['--out', str(screen)])
                    app = sp.Popen(command, env=app_env, stdout=log, stderr=log,
                                   stdin=sp.DEVNULL, start_new_session=True)
                    deadline = time.monotonic() + 30
                    while not (screen / 'ready').exists():
                        if app.poll() is not None:
                            raise RuntimeError('app exited before ready')
                        if time.monotonic() >= deadline:
                            raise TimeoutError('app readiness')
                        time.sleep(0.1)
                    capture = screen / 'capture.png'
                    sp.run(['grim', str(capture)], env=app_env, check=True, timeout=10,
                           stdout=log, stderr=log)
                    labels = json.loads((screen / 'labels.json').read_text())
                    for key in ('toolkit', 'template', 'seed', 'theme', 'accent', 'font_scale'):
                        if labels.get(key) != task[key]:
                            raise ValueError('label metadata mismatch: ' + key)
                    with Image.open(capture) as image:
                        width, height = image.size
                        if (width, height) != tuple(map(int, size.split('x'))) or (width, height) != (labels['width'], labels['height']):
                            raise ValueError('label/screenshot/plan size mismatch')
                        boxes = yolo_boxes(labels['boxes'], width, height)
                        if len(boxes) < 3:
                            raise ValueError('fewer than three usable boxes')
                        dest = OUT / task['split']
                        for sub in ('images', 'labels'):
                            (dest / sub).mkdir(parents=True, exist_ok=True)
                        (dest / 'labels' / (task['id'] + '.txt')).write_text(''.join(
                            '0 %.6f %.6f %.6f %.6f\n' % b for b in boxes))
                        image_path = dest / 'images' / (task['id'] + '.png')
                        temporary = image_path.with_suffix('.tmp')
                        image.save(temporary, format='PNG')
                        temporary.replace(image_path)
                    results.append(dict(task, n_boxes=len(boxes)))
                    checkpoint = base / 'results.json'
                    tmp = checkpoint.with_suffix('.tmp')
                    tmp.write_text(json.dumps(results))
                    tmp.replace(checkpoint)
                    print('OK', task['id'], flush=True)
                except Exception as exc:
                    print('FAIL', task['id'], str(exc), flush=True)
                    stop_process(comp)
                    comp = None
                finally:
                    signal.alarm(0)
                    stop_process(app)
                    app = None
        finally:
            signal.alarm(0)
            stop_process(app)
            stop_process(comp)
    return results


def run(workers, toolkit=None, limit=None):
    if not 1 <= workers <= 32 or (limit is not None and limit < 1):
        raise ValueError('workers must be 1..32; limit must be positive')
    tasks = plan()
    existing = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
    planned = {t['id'] for t in tasks}
    for checkpoint in FAKE.glob('*/results.json'):
        recovered = [r for r in json.loads(checkpoint.read_text()) if r['id'] in planned
                     and (OUT / r['split'] / 'images' / (r['id'] + '.png')).exists()]
        existing = merge_manifest(existing, recovered)
    save_manifest(existing)
    tasks = [t for t in tasks if (not toolkit or t['toolkit'] == toolkit)
             and not (OUT / t['split'] / 'images' / (t['id'] + '.png')).exists()]
    if limit:
        tasks = tasks[:limit]
    if not tasks:
        print('No pending screens')
        return
    jobs = [(i, tasks[i::workers]) for i in range(min(workers, len(tasks)))]
    with Pool(len(jobs)) as pool:
        for rows in pool.imap_unordered(worker, jobs):
            existing = merge_manifest(existing, rows)
            save_manifest(existing)
    completed = {r['id'] for r in existing}
    if any(t['id'] not in completed for t in tasks):
        raise RuntimeError('Some screens failed; rerun to retry')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('command', choices=('plan', 'run', 'stats'))
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--toolkit', choices=('gtk', 'qt'))
    ap.add_argument('--limit', type=int)
    args = ap.parse_args()
    if args.command == 'plan':
        print(json.dumps(plan(), indent=2))
    elif args.command == 'run':
        run(args.workers, args.toolkit, args.limit)
    else:
        rows = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else []
        for toolkit in ('gtk', 'qt'):
            for split in ('train', 'val'):
                print(toolkit, split, sum(r['toolkit'] == toolkit and r['split'] == split for r in rows))


if __name__ == '__main__':
    main()
