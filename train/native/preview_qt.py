"""Bounded headless Qt alignment capture; run with a Python containing Pillow.

NEFERWL selects the compositor binary. All generated state stays in /tmp.
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from qt_app import TEMPLATES

BASE = Path('/tmp/nh-native-qt')


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from train.tmpdirs import private_dir


def stop(process):
    if process is not None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def wait_for(predicate, process, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'Process exited with {process.returncode}; inspect {BASE}/capture.log')
        result = predicate()
        if result:
            return result
        time.sleep(.1)
    raise TimeoutError(f'Timed out after {seconds}s')


def main():
    from PIL import Image, ImageDraw
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--size', default='1920x1080')
    parser.add_argument('--templates', nargs='+', choices=TEMPLATES, default=list(TEMPLATES))
    parser.add_argument('--seeds', nargs='+', type=int, default=[11, 28])
    parser.add_argument('--themes', nargs='+', choices=['light', 'dark'], default=['light', 'dark'])
    args = parser.parse_args()
    binary = shutil.which(os.environ.get('NEFERWL', 'neferwl'))
    if not binary:
        parser.error('Set NEFERWL to the compositor executable')
    private_dir(BASE)
    env = os.environ.copy()
    for key in ('NEFERWL_STATE', 'NEFERWL_SLOT', 'DISPLAY', 'WAYLAND_DISPLAY'):
        env.pop(key, None)
    for key, directory in [('HOME', 'home'), ('XDG_CONFIG_HOME', 'config-home'),
                           ('XDG_DATA_HOME', 'data'), ('XDG_CACHE_HOME', 'cache'),
                           ('XDG_STATE_HOME', 'state'), ('XDG_RUNTIME_DIR', 'run')]:
        path = BASE / directory
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    (BASE / 'run').chmod(0o700)
    env.update(QT_QPA_PLATFORM='wayland', QT_SCALE_FACTOR='1', QT_AUTO_SCREEN_SCALE_FACTOR='0')
    config = BASE / 'config'
    config.write_text('')
    log_path = BASE / 'state/neferwl/runs/headless/latest.log'
    if log_path.exists():
        log_path.unlink()
    overlays = BASE / 'overlays'
    overlays.mkdir(exist_ok=True)
    app = comp = None
    with (BASE / 'capture.log').open('w') as log:
        try:
            comp = subprocess.Popen([binary, '--backend=headless', '--size', args.size,
                                     '--no-xwayland', '--no-terminal', '--config', str(config),
                                     '--timeout', '600s'], env=env, stdout=log, stderr=log)

            def listening():
                if not log_path.exists():
                    return None
                for line in log_path.read_text().splitlines():
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if 'listening' in json.dumps(entry):
                        match = re.search(r'wayland-[\w-]+', json.dumps(entry))
                        if match:
                            return match.group(0)
                return None

            env['WAYLAND_DISPLAY'] = wait_for(listening, comp, 15)
            for template in args.templates:
                for theme in args.themes:
                    for seed in args.seeds:
                        name = f'{template}-{seed}-{theme}'
                        out = BASE / 'samples' / name
                        out.mkdir(parents=True, exist_ok=True)
                        (out / 'ready').unlink(missing_ok=True)
                        app = subprocess.Popen(['/usr/bin/python3', str(Path(__file__).with_name('qt_app.py')),
                                                '--seed', str(seed), '--template', template,
                                                '--theme', theme, '--accent', '#6c87d9',
                                                '--font-scale', '0.95' if seed % 2 else '1.2',
                                                '--out', str(out)], env=env, stdout=log, stderr=log)
                        wait_for(lambda: (out / 'ready').exists(), app, 30)
                        shot = out / 'screen.png'
                        subprocess.run(['grim', str(shot)], env=env, check=True, timeout=10)
                        labels = json.loads((out / 'labels.json').read_text())
                        image = Image.open(shot).convert('RGB')
                        assert image.size == (labels['width'], labels['height'])
                        assert image.size == tuple(map(int, args.size.split('x')))
                        draw = ImageDraw.Draw(image)
                        for x, y, r, b, kind in labels['boxes']:
                            assert 0 <= x < r <= image.width and 0 <= y < b <= image.height
                            draw.rectangle((x, y, r - 1, b - 1), outline='#ff3050', width=2)
                        path = overlays / f'{name}.png'
                        image.save(path)
                        # Contract's short path is retained as an alias to the last theme.
                        image.save(overlays / f'{template}-{seed}.png')
                        print(path, len(labels['boxes']), flush=True)
                        stop(app)
                        app = None
        finally:
            stop(app)
            stop(comp)


if __name__ == '__main__':
    main()
