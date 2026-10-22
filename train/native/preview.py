"""Bounded isolated compositor capture. Requires NEFERWL, grim and Pillow."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import time
from PIL import Image, ImageDraw
from gtk_app import TEMPLATES


def stop(process):
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def wait_for(test, process, seconds):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'process exited: {process.returncode}')
        value = test()
        if value:
            return value
        time.sleep(.1)
    raise TimeoutError('capture readiness timeout')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--size', default='1920x1080')
    parser.add_argument('--accent', default='#3584e4')
    parser.add_argument('--font-scale', type=float, default=1.)
    parser.add_argument('--templates', nargs='+', choices=TEMPLATES, default=TEMPLATES)
    parser.add_argument('--seeds', nargs='+', type=int, default=[1, 2])
    parser.add_argument('--themes', nargs='+', choices=['light', 'dark'], default=['light', 'dark'])
    args = parser.parse_args()
    base = Path('/tmp/nh-native-gtk')
    env = os.environ.copy()
    for key in ('NEFERWL_STATE', 'NEFERWL_SLOT', 'DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
        env.pop(key, None)
    for key, folder in [('HOME', 'home'), ('XDG_CONFIG_HOME', 'config-home'), ('XDG_DATA_HOME', 'data'), ('XDG_CACHE_HOME', 'cache'), ('XDG_STATE_HOME', 'state'), ('XDG_RUNTIME_DIR', 'run')]:
        path = base/folder
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    (base/'run').chmod(0o700)
    cfg = base/'config'
    cfg.write_text('')
    logfile = base/'state/neferwl/runs/headless/latest.log'
    previous = logfile.stat().st_mtime_ns if logfile.exists() else None
    with (base/'preview.log').open('w') as log:
        comp = subprocess.Popen([os.environ.get('NEFERWL', 'neferwl'), '--backend=headless', '--size', args.size, '--no-xwayland', '--no-terminal', '--config', str(cfg), '--timeout', '600s'], env=env, stdout=log, stderr=log)
        try:
            def listening():
                if not logfile.exists() or logfile.stat().st_mtime_ns == previous:
                    return None
                for line in logfile.read_text().splitlines():
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if 'listening' in json.dumps(item):
                        match = re.search(r'wayland-[\w-]+', json.dumps(item))
                        if match:
                            return match.group()
            env.update(WAYLAND_DISPLAY=wait_for(listening, comp, 15), GDK_BACKEND='wayland', GIO_USE_VOLUME_MONITOR='unix')
            for template in args.templates:
                for theme in args.themes:
                    for seed in args.seeds:
                        name = f'{template}-{seed}-{theme}'
                        out = base/'captures'/name
                        out.mkdir(parents=True, exist_ok=True)
                        (out/'ready').unlink(missing_ok=True)
                        app = subprocess.Popen(['/usr/bin/python3', str(Path(__file__).with_name('gtk_app.py')), '--template', template, '--seed', str(seed), '--theme', theme, '--accent', args.accent, '--font-scale', str(args.font_scale), '--out', str(out)], env=env, stdout=log, stderr=log)
                        try:
                            wait_for(lambda: (out/'ready').exists(), app, 30)
                            subprocess.run(['grim', str(out/'capture.png')], env=env, check=True, timeout=10)
                            data = json.loads((out/'labels.json').read_text())
                            image = Image.open(out/'capture.png').convert('RGB')
                            assert image.size == (data['width'], data['height']), (image.size, data)
                            assert data['boxes']
                            draw = ImageDraw.Draw(image)
                            for x0, y0, x1, y1, kind in data['boxes']:
                                draw.rectangle((x0, y0, x1-1, y1-1), outline='#ff2060', width=2)
                            dest = base/'overlays'/f'{name}.png'
                            dest.parent.mkdir(exist_ok=True)
                            image.save(dest)
                            print(dest, len(data['boxes']), flush=True)
                        finally:
                            stop(app)
        finally:
            stop(comp)


if __name__ == '__main__':
    main()
