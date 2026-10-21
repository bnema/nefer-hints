#!/usr/bin/env python3
"""Generate labelled terminal screenshots with headless NeferWL + kitty/foot/alacritty.

Labelling: every scene is captured twice with identical text/layout (A normal, B with
links painted #FF00FF/#F700F7 fg=bg); boxes come from B, image from A.
Privacy: all child processes run under `env -i` with a fake HOME in /tmp/nh-term.

  venv/bin/python train/terminal/make_data.py --out data/terminal --split train --n 500 --seed0 1000 --workers 5
"""
import argparse, json, os, random, re, shutil, signal, subprocess as sp, sys, time
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import cv2
sys.path.insert(0, str(Path(__file__).parent))
import gen
from themes import THEMES, DARK, LIGHT

NEFERWL = '$HOME/.local/share/nefer-hints-test/bin/neferwl'
FAKE = Path('/tmp/nh-term')
TERMS = ['kitty', 'foot', 'alacritty']
TRAIN_FONTS = ['JetBrains Mono', 'DejaVu Sans Mono', 'Hack', 'FiraCode Nerd Font Mono']
TEST_FONTS = ['IBM Plex Mono']
COLORS = ('FF00FF', 'F700F7')
SCRIPT = '''#!/bin/bash
d="$1"
while [ ! -e "$d/ask" ]; do sleep 0.05; done
stty size > "$d/size.tmp"; mv "$d/size.tmp" "$d/size"
while [ ! -e "$d/A" ]; do sleep 0.05; done
cat "$d/A"; touch "$d/ra"
while [ ! -e "$d/gob" ]; do sleep 0.05; done
cat "$d/B"; touch "$d/rb"
sleep 300
'''


def hexn(c):
    return c.lstrip('#')


def write_conf(term, path, font, pt, th):
    t = THEMES[th]
    if term == 'foot':
        s = '[main]\nfont=%s:size=%d\npad=6x6\n[cursor]\nblink=no\n[colors]\nalpha=1.0\nforeground=%s\nbackground=%s\n' % (font, pt, hexn(t['fg']), hexn(t['bg']))
        for i, c in enumerate(t['c'][:8]):
            s += 'regular%d=%s\n' % (i, hexn(c))
        for i, c in enumerate(t['c'][8:]):
            s += 'bright%d=%s\n' % (i, hexn(c))
    elif term == 'alacritty':
        names = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']
        s = '[font]\nsize = %d\n[font.normal]\nfamily = "%s"\n[window]\ndecorations = "None"\npadding = {x = 6, y = 6}\n[cursor]\nstyle = {shape = "Block", blinking = "Never"}\n[colors.primary]\nbackground = "%s"\nforeground = "%s"\n' % (pt, font, t['bg'], t['fg'])
        s += '[colors.normal]\n' + ''.join('%s = "%s"\n' % (n, c) for n, c in zip(names, t['c'][:8]))
        s += '[colors.bright]\n' + ''.join('%s = "%s"\n' % (n, c) for n, c in zip(names, t['c'][8:]))
    else:
        s = 'font_family %s\nfont_size %d\nforeground %s\nbackground %s\ncursor_blink_interval 0\nwindow_padding_width 6\nconfirm_os_window_close 0\nenable_audio_bell no\nshell_integration disabled\nupdate_check_interval 0\nbackground_opacity 1.0\nallow_remote_control no\n' % (font, pt, t['fg'], t['bg'])
        for i, c in enumerate(t['c']):
            s += 'color%d %s\n' % (i, c)
    Path(path).write_text(s)


def term_cmd(term, conf, script, d):
    if term == 'foot':
        return ['foot', '-c', conf, 'bash', script, d]
    if term == 'alacritty':
        return ['alacritty', '--config-file', conf, '-e', 'bash', script, d]
    return ['kitty', '-c', conf, 'bash', script, d]


def env_for(w, wayland=None):
    base = FAKE / ('w%d' % w)
    e = dict(PATH=os.environ['PATH'], HOME=str(FAKE / 'home'), XDG_CONFIG_HOME=str(FAKE / 'home/config'),
             XDG_DATA_HOME=str(FAKE / 'home/data'), XDG_CACHE_HOME=str(FAKE / 'home/cache'),
             XDG_STATE_HOME=str(base / 'state'), XDG_RUNTIME_DIR=str(base / 'run'), LANG='C.UTF-8', TERM='xterm-256color')
    if wayland:
        e['WAYLAND_DISPLAY'] = wayland
    return e


def make_spec(split, i, seed0):
    seed = seed0 + i
    r = random.Random(seed)
    fonts = TEST_FONTS if split == 'test' else TRAIN_FONTS
    size = r.choice(['1920x1080'] * 3 + ['2560x1440'])
    n = r.choice([1, 1, 2, 2, 3, 4])
    mode = 'rand'
    if split == 'test':
        mode = 'status' if i < 14 else ('nolinks' if i < 26 else 'rand')
    wins = []
    for k in range(n):
        links = r.randint(1, 6) if r.random() < 0.6 else 0
        status = r.random() < 0.6
        if mode == 'status':
            status = True
            links = r.randint(1, 5) if r.random() < 0.8 else 0
        elif mode == 'nolinks':
            links = 0
        th = r.choice(DARK) if r.random() < 2 / 3 else r.choice(LIGHT)
        wins.append(dict(term=r.choice(TERMS), font=r.choice(fonts), pt=r.randint(10, 16), theme=th,
                         links=links, status=status, seed=seed * 10 + k))
    return dict(id='%s_%04d' % (split, i), split=split, seed=seed, size=size, wins=wins)


def wait_until(fn, timeout, what):
    t = time.time()
    while time.time() - t < timeout:
        v = fn()
        if v:
            return v
        time.sleep(0.1)
    raise TimeoutError(what)


def load_png(p):
    # screenshot may be mid-write: retry until PIL can decode
    for _ in range(20):
        try:
            im = Image.open(p); im.load()
            return im.convert('RGB')
        except Exception:
            time.sleep(0.1)
    raise IOError(p)


def boxes_from(imB, pad=2):
    a = np.asarray(imB).astype(int)
    h, w = a.shape[:2]
    out = []
    for col in ((255, 0, 255), (247, 0, 247)):
        m = (np.abs(a - np.array(col)).max(axis=2) <= 3).astype(np.uint8)
        n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        for k in range(1, n):
            x, y, bw, bh, area = st[k]
            if area < 30 or bw < 6 or bh < 6:
                continue
            out.append((max(0, x - pad), max(0, y - pad), min(w, x + bw + pad), min(h, y + bh + pad)))
    return sorted(out, key=lambda b: (b[1], b[0]))


def capture(spec, w, work):
    shutil.rmtree(work, ignore_errors=True)
    for sub in ('shots', 'cfg'):
        (work / sub).mkdir(parents=True)
    base = work.parent
    for sub in ('state', 'run'):
        shutil.rmtree(base / sub, ignore_errors=True)
        (base / sub).mkdir()
    os.chmod(base / 'run', 0o700)
    (work / 'term.sh').write_text(SCRIPT)
    log = open(work / 'comp.log', 'w')
    cfg = work / 'neferwl.conf'
    cfg.write_text('terminal.auto-open = off\nborder.width = 0\nfocus.flash = off\nhint.enable = off\nlayout.max-columns = 2\nlayout.overflow = fixed\n')
    comp = sp.Popen([NEFERWL, '--backend=headless', '--size', spec['size'], '--no-xwayland', '--no-terminal', '--config', str(cfg),
                     '--screenshot', str(work / 'shots'), '--timeout', '150s'], env=env_for(w), stdout=log, stderr=log, stdin=sp.DEVNULL, start_new_session=True)
    procs = []
    try:
        lp = base / 'state/neferwl/runs/headless/latest.log'
        def listening():
            if lp.exists():
                m = re.search(r'wayland-\d+', ''.join(l for l in lp.read_text().splitlines(True) if 'listening' in l))
                return m.group(0) if m else None
        wd = wait_until(listening, 20, 'compositor')
        for k, win in enumerate(spec['wins']):
            d = work / ('win%d' % k); d.mkdir()
            win['dir'] = d
            conf = work / 'cfg' / ('t%d.conf' % k)
            write_conf(win['term'], conf, win['font'], win['pt'], win['theme'])
            mapped = lambda: lp.read_text().count('window mapped')
            before = mapped()
            procs.append(sp.Popen(term_cmd(win['term'], str(conf), str(work / 'term.sh'), str(d)), env=env_for(w, wd), stdout=log, stderr=log, stdin=sp.DEVNULL, start_new_session=True))
            wait_until(lambda: mapped() > before, 20, 'window %d (%s) mapped' % (k, win['term']))
            time.sleep(0.5)
        time.sleep(2.0)  # layout settles (tiling resize after last map)
        for win in spec['wins']:
            (win['dir'] / 'ask').touch()
        for win in spec['wins']:
            wait_until(lambda: (win['dir'] / 'size').exists(), 20, 'size')
        for win in spec['wins']:
            rows, cols = map(int, (win['dir'] / 'size').read_text().split())
            g = gen.generate(dict(seed=win['seed'], links=win['links'], status=win['status']), cols, rows)
            win['gen'] = dict(cols=cols, rows=rows, links=g['links'])
            (win['dir'] / 'B').write_text(g['B'])
            (win['dir'] / 'A.tmp').write_text(g['A']); os.rename(win['dir'] / 'A.tmp', win['dir'] / 'A')
        for win in spec['wins']:
            wait_until(lambda: (win['dir'] / 'ra').exists(), 20, 'A printed')
        time.sleep(1.2)
        shutil.copy(work / 'shots/latest.png', work / 'A.png')
        imA = load_png(work / 'A.png')
        for win in spec['wins']:
            (win['dir'] / 'gob').touch()
        for win in spec['wins']:
            wait_until(lambda: (win['dir'] / 'rb').exists(), 20, 'B printed')
        time.sleep(1.2)
        shutil.copy(work / 'shots/latest.png', work / 'B.png')
        imB = load_png(work / 'B.png')
        return imA, imB
    finally:
        for p in procs + [comp]:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        log.close()


def one(args):
    spec, out, w, keep_overlay = args
    work = FAKE / ('w%d' % w) / 'work'
    last = None
    for attempt in range(3):
        try:
            imA, imB = capture(spec, w, work)
            a, b = np.asarray(imA).astype(int), np.asarray(imB).astype(int)
            boxes = boxes_from(imB)
            diff = (np.abs(a - b).max(axis=2) > 0)
            m = np.zeros(diff.shape, np.uint8)
            for x1, y1, x2, y2 in boxes:
                m[max(0, y1 - 6):y2 + 6, max(0, x1 - 6):x2 + 6] = 1
            H0, W0 = diff.shape
            m[H0 // 2 - 40:H0 // 2 + 60, W0 // 2 - 40:W0 // 2 + 60] = 1  # compositor pointer (shape may change over a terminal)
            outside = int((diff & (m == 0)).sum())
            exp = sum(win['gen']['links'] for win in spec['wins'])
            if outside > 40:
                raise RuntimeError('A/B differ outside link boxes: %d px' % outside)
            if exp > 0 and len(boxes) < exp:
                raise RuntimeError('missing link boxes: %d < %d' % (len(boxes), exp))
            if exp == 0 and boxes:
                raise RuntimeError('unexpected magenta boxes')
            break
        except Exception as e:
            last = e
            time.sleep(1)
    else:
        return dict(id=spec['id'], error=repr(last))
    sid = spec['id']
    (out / 'images').mkdir(parents=True, exist_ok=True); (out / 'labels').mkdir(exist_ok=True)
    imA.save(out / 'images' / (sid + '.png'))
    W, H = imA.size
    lines = ['0 %.6f %.6f %.6f %.6f' % ((x1 + x2) / 2 / W, (y1 + y2) / 2 / H, (x2 - x1) / W, (y2 - y1) / H) for x1, y1, x2, y2 in boxes]
    (out / 'labels' / (sid + '.txt')).write_text('\n'.join(lines) + ('\n' if lines else ''))
    if keep_overlay:
        ov = imA.copy(); dr = ImageDraw.Draw(ov)
        for bx in boxes:
            dr.rectangle(bx, outline=(0, 255, 0), width=2)
        (out.parent / 'overlays').mkdir(exist_ok=True)
        ov.save(out.parent / 'overlays' / (sid + '.png'))
    return dict(id=sid, split=spec['split'], size=spec['size'], boxes=len(boxes), expected_links=exp, outside_px=outside,
                status=any(x['status'] for x in spec['wins']),
                wins=[{k: x[k] for k in ('term', 'font', 'pt', 'theme', 'links', 'status')} | x['gen'] for x in spec['wins']])


def run_slot(js):
    return [one(j) for j in js]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True); ap.add_argument('--split', required=True)
    ap.add_argument('--n', type=int, required=True); ap.add_argument('--seed0', type=int, required=True)
    ap.add_argument('--workers', type=int, default=4); ap.add_argument('--start', type=int, default=0)
    ap.add_argument('--overlays', type=int, default=0, help='save overlays for the first N scenes')
    a = ap.parse_args()
    out = Path(a.out) / a.split
    for w in range(a.workers):
        (FAKE / ('w%d' % w)).mkdir(parents=True, exist_ok=True)
    specs = [make_spec(a.split, i, a.seed0) for i in range(a.start, a.start + a.n)]
    jobs = [(s, out, k % a.workers, k < a.overlays) for k, s in enumerate(specs)]
    from multiprocessing import Pool
    # one scene at a time per worker slot: partition jobs by slot
    res = []
    with Pool(a.workers) as p:
        for chunk in p.imap_unordered(run_slot, [[j for j in jobs if j[2] == k] for k in range(a.workers)]):
            res += chunk
    res.sort(key=lambda r: r['id'])
    Path(a.out).mkdir(parents=True, exist_ok=True)
    man = Path(a.out) / ('manifest_%s.json' % a.split)
    man.write_text(json.dumps(res, indent=1))
    errs = [r for r in res if 'error' in r]
    print('done', len(res) - len(errs), 'ok', len(errs), 'errors')
    for e in errs:
        print(e)


if __name__ == '__main__':
    main()
