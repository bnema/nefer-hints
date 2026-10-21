#!/usr/bin/env python3
"""Collect DOM-labelled public web pages (anti-forgetting data), same pipeline as eval/capture_web.py.

Headless NeferWL + Chromium (fullscreen, F11) + CDP; boxes from eval/dom.js (identical clickable
definition). Screenshot = compositor frame (shots/latest.png) because grim is refused by the
headless compositor here. Zoom is the real browser zoom (Ctrl+-/Ctrl+=); dom.js boxes are CSS px
and are multiplied by devicePixelRatio (= zoom). Dark = prefers-color-scheme + auto-dark override
(as eval). Privacy: env -i, fake HOME /tmp/nh-term/home, fresh profile, logged-out public pages.
Eval domains (eval/scenes.json) are excluded.

  venv/bin/python train/web/collect_web.py plan     # discover pages (plain HTTP GET, public) -> data/web/plan.json
  venv/bin/python train/web/collect_web.py run --workers 5
"""
import json, os, random, re, shutil, signal, subprocess as sp, sys, time, urllib.request, urllib.parse
from html.parser import HTMLParser
from multiprocessing import Pool
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/web'
FAKE = Path('/tmp/nh-term')
NEFERWL = '$HOME/.local/share/nefer-hints-test/bin/neferwl'
DOM_JS = (ROOT / 'eval/dom.js').read_text()
EVAL_HOSTS = ('news.ycombinator.com', 'lobste.rs', 'wikipedia.org', 'developer.mozilla.org', 'archlinux.org', 'github.com', 'go.dev', 'httpbin.org', 'docs.python.org', '127.0.0.1')
SITES = {  # name -> home URL
 'lwn': 'https://lwn.net/', 'kernel': 'https://www.kernel.org/', 'debian': 'https://www.debian.org/', 'rustlang': 'https://www.rust-lang.org/',
 'docsrs': 'https://docs.rs/', 'cratesio': 'https://crates.io/', 'pypi': 'https://pypi.org/', 'npmjs': 'https://www.npmjs.com/',
 'stackoverflow': 'https://stackoverflow.com/questions', 'freedesktop': 'https://www.freedesktop.org/', 'gnome': 'https://www.gnome.org/', 'kde': 'https://kde.org/',
 'codeberg': 'https://codeberg.org/explore/repos', 'srht': 'https://sr.ht/', 'w3': 'https://www.w3.org/', 'rfceditor': 'https://www.rfc-editor.org/',
 'osm': 'https://www.openstreetmap.org/about', 'gutenberg': 'https://www.gutenberg.org/', 'apnews': 'https://apnews.com/', 'bbc': 'https://www.bbc.com/news',
 'guardian': 'https://www.theguardian.com/uk', 'nasa': 'https://www.nasa.gov/', 'weathergov': 'https://www.weather.gov/', 'imdb': 'https://www.imdb.com/chart/top/',
 'goodreads': 'https://www.goodreads.com/', 'archiveorg': 'https://archive.org/', 'wiktionary': 'https://en.wiktionary.org/wiki/Wiktionary:Main_Page',
 'commons': 'https://commons.wikimedia.org/wiki/Main_Page', 'ietf': 'https://www.ietf.org/', 'haskell': 'https://www.haskell.org/', 'ziglang': 'https://ziglang.org/',
 'nixos': 'https://nixos.org/', 'fedora': 'https://fedoraproject.org/', 'ubuntu': 'https://ubuntu.com/', 'mozilla': 'https://www.mozilla.org/en-US/',
}
EXTRA = {'stackoverflow': ['https://stackoverflow.com/questions/11227809', 'https://stackoverflow.com/questions/927358', 'https://stackoverflow.com/questions/503093'],
         'imdb': ['https://www.imdb.com/title/tt0111161/'], 'cratesio': ['https://crates.io/crates/serde'], 'npmjs': ['https://www.npmjs.com/package/express'],
         'debian': ['https://www.debian.org/distrib/'], 'w3': ['https://www.w3.org/standards/'], 'freedesktop': ['https://www.freedesktop.org/wiki/Software/'],
         'archiveorg': ['https://archive.org/about/']}
VAL_SITES = ['kde', 'nasa', 'ziglang', 'rfceditor', 'osm']
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
BAD_EXT = re.compile(r'\.(pdf|zip|gz|xz|bz2|tar|png|jpe?g|gif|svg|mp4|webm|iso|exe|dmg|rss|xml|json|txt|css|js|ico|webp|mp3|ogg|torrent|asc|sig)(\?|$)', re.I)


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.h = []
    def handle_starttag(self, t, a):
        if t == 'a':
            for k, v in a:
                if k == 'href' and v:
                    self.h.append(v)


def plan(per_site=6):
    rng = random.Random(7)
    tasks = []
    info = {}
    for name, home in SITES.items():
        host = urllib.parse.urlparse(home).netloc
        assert not any(host.endswith(e) for e in EVAL_HOSTS), host
        urls = [home]
        try:
            req = urllib.request.Request(home, headers={'User-Agent': UA})
            html = urllib.request.urlopen(req, timeout=20).read(2_000_000).decode('utf8', 'replace')
            p = Links(); p.feed(html)
            cands = []
            for h in p.h:
                u = urllib.parse.urljoin(home, h).split('#')[0]
                pu = urllib.parse.urlparse(u)
                if pu.scheme in ('http', 'https') and pu.netloc == host and not BAD_EXT.search(u) and not re.search(r'login|logout|signup|register|account|cart|download', u, re.I) and u.rstrip('/') != home.rstrip('/'):
                    cands.append(u)
            cands = sorted(set(cands))
            rng.shuffle(cands)
            urls += cands[:per_site - 1] if name != 'stackoverflow' else cands[:per_site]
            info[name] = len(cands)
        except Exception as e:
            info[name] = 'ERR %r' % (e,)
        urls += EXTRA.get(name, [])
        for u in urls:
            for v in range(4):
                tasks.append(dict(site=name, url=u, size=rng.choice(['1920x1080'] * 3 + ['2560x1440']), zoom=rng.choice([90, 100, 100, 110]),
                                  dark=rng.random() < 0.3, scroll=rng.choice(['top', 'middle']) if v else 'top', v=v))
    # dedupe identical (url,scroll,zoom,dark)
    seen, out = set(), []
    for t in tasks:
        k = (t['url'], t['scroll'], t['zoom'], t['dark'], t['size'])
        if k not in seen:
            seen.add(k); out.append(t)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'plan.json').write_text(json.dumps(out, indent=1))
    print(len(out), 'tasks;', json.dumps(info))


def env_for(tag, wayland=None):
    base = FAKE / tag
    e = dict(PATH=os.environ['PATH'], HOME=str(FAKE / 'home'), XDG_CONFIG_HOME=str(FAKE / 'home/config'), XDG_DATA_HOME=str(FAKE / 'home/data'),
             XDG_CACHE_HOME=str(FAKE / 'home/cache'), XDG_STATE_HOME=str(base / 'state'), XDG_RUNTIME_DIR=str(base / 'run'), LANG='C.UTF-8',
             GDK_BACKEND='wayland', MOZ_ENABLE_WAYLAND='1')
    if wayland:
        e['WAYLAND_DISPLAY'] = wayland
    return e


def blocked(title, text):
    s = (title + ' ' + text[:600]).lower()
    return bool(re.search(r'just a moment|access denied|attention required|captcha|are you a robot|verify you are human|403 forbidden|404|not found|too many requests', s))


def worker(args):
    w, size, tasks = args
    import websocket
    from PIL import Image
    tag = 'web%d' % w
    base = FAKE / tag
    for sub in ('state', 'run', 'shots'):
        shutil.rmtree(base / sub, ignore_errors=True); (base / sub).mkdir(parents=True)
    os.chmod(base / 'run', 0o700)
    cfg = base / 'n.conf'; cfg.write_text('terminal.auto-open = off\nborder.width = 0\nfocus.flash = off\nhint.enable = off\n')
    fifo = base / 'in'
    if not fifo.exists():
        os.mkfifo(fifo)
    fd = os.open(fifo, os.O_RDWR)
    log = open(base / 'log', 'w')
    comp = sp.Popen([NEFERWL, '--backend=headless', '--size', size, '--no-xwayland', '--no-terminal', '--config', str(cfg), '--input', str(fifo),
                     '--screenshot', str(base / 'shots'), '--timeout', '7200s'], env=env_for(tag), stdout=log, stderr=log, stdin=sp.DEVNULL, start_new_session=True)
    W, H = map(int, size.split('x'))
    port = 9300 + w
    browser = None
    results = []
    try:
        time.sleep(2)
        lp = base / 'state/neferwl/runs/headless/latest.log'
        wd = re.search(r'wayland-\d+', ''.join(l for l in lp.read_text().splitlines(True) if 'listening' in l)).group(0)
        profile = FAKE / 'home' / ('chromium-%s-%d' % (tag, int(time.time())))
        browser = sp.Popen(['chromium', '--ozone-platform=wayland', '--no-first-run', '--no-default-browser-check', '--disable-sync', '--disable-session-crashed-bubble',
                            '--disable-features=Translate', '--password-store=basic', '--use-mock-keychain',
                            '--remote-debugging-port=%d' % port, '--remote-allow-origins=http://localhost:%d' % port, '--user-data-dir=%s' % profile,
                            '--start-fullscreen', '--app=about:blank'], env=env_for(tag, wd), stdout=log, stderr=log, stdin=sp.DEVNULL, start_new_session=True)
        time.sleep(5)
        os.write(fd, b'key F11\nsleep 1s\n'); time.sleep(2)
        targets = json.load(urllib.request.urlopen('http://localhost:%d/json' % port, timeout=5))
        target = next(t for t in targets if t['type'] == 'page')
        ws = websocket.create_connection(target['webSocketDebuggerUrl'], origin='http://localhost:%d' % port, timeout=40)
        seq = 0
        def call(method, params={}):
            nonlocal seq
            seq += 1; ws.send(json.dumps(dict(id=seq, method=method, params=params)))
            for _ in range(5000):
                msg = json.loads(ws.recv())
                if msg.get('id') == seq:
                    if 'error' in msg:
                        raise RuntimeError(msg)
                    return msg.get('result', {})
            raise RuntimeError('too many events')
        def ev(js):
            r = call('Runtime.evaluate', dict(expression=js, returnByValue=True, awaitPromise=True))
            if 'exceptionDetails' in r:
                raise RuntimeError(str(r['exceptionDetails'])[:200])
            return r.get('result', {}).get('value')
        cur_zoom = 100
        for t in tasks:
            tid = t['id']
            try:
                call('Emulation.setEmulatedMedia', {'features': [{'name': 'prefers-color-scheme', 'value': 'dark' if t['dark'] else 'light'}]})
                call('Emulation.setAutoDarkModeOverride', {'enabled': bool(t['dark'])})
                call('Page.navigate', {'url': t['url']})
                dl = time.time() + 25
                time.sleep(2)
                while time.time() < dl and ev('document.readyState') != 'complete':
                    time.sleep(0.5)
                time.sleep(3)
                # zoom: reset then step
                os.write(fd, b'key Ctrl+0\n'); time.sleep(0.4)
                if t['zoom'] == 90:
                    os.write(fd, b'key Ctrl+minus\n')
                elif t['zoom'] == 110:
                    os.write(fd, b'key Ctrl+equal\n')
                time.sleep(1.2)
                dpr = ev('devicePixelRatio')
                if abs(dpr - t['zoom'] / 100) > 0.02:
                    raise RuntimeError('zoom not applied: dpr=%s want %s' % (dpr, t['zoom'] / 100))
                if t['scroll'] == 'middle':
                    ev('window.scrollTo(0,Math.max(0,(document.documentElement.scrollHeight-innerHeight)/2))')
                ev("document.querySelectorAll('video,audio').forEach(e=>e.pause()); document.documentElement.style.scrollBehavior='auto';")
                time.sleep(1.5)
                gt = ev(DOM_JS)
                if abs(gt['viewport']['width'] * dpr - W) > 3 or abs(gt['viewport']['height'] * dpr - H) > 3:
                    raise RuntimeError('viewport %s dpr %s != %s' % (gt['viewport'], dpr, size))
                body = ev('document.body?document.body.innerText.slice(0,600):""') or ''
                wall = blocked(gt.get('title') or '', body)
                if not gt['boxes']:
                    raise RuntimeError('no boxes; title=%s' % gt.get('title'))
                shutil.copy(base / 'shots/latest.png', base / 'cap.png')
                time.sleep(0.2)
                img = Image.open(base / 'cap.png').convert('RGB')
                if img.size != (W, H):
                    raise RuntimeError('image size %s' % (img.size,))
                boxes = []
                for x1, y1, x2, y2 in gt['boxes']:
                    a, b, c, d = [max(0, min(v * dpr, lim)) for v, lim in ((x1, W), (y1, H), (x2, W), (y2, H))]
                    if c - a >= 4 and d - b >= 4:
                        boxes.append((a, b, c, d))
                split = 'val' if t['site'] in VAL_SITES else 'train'
                (OUT / split / 'images').mkdir(parents=True, exist_ok=True); (OUT / split / 'labels').mkdir(parents=True, exist_ok=True)
                img.save(OUT / split / 'images' / (tid + '.png'))
                (OUT / split / 'labels' / (tid + '.txt')).write_text(''.join('0 %.6f %.6f %.6f %.6f\n' % ((a + c) / 2 / W, (b + d) / 2 / H, (c - a) / W, (d - b) / H) for a, b, c, d in boxes))
                results.append(dict(t, split=split, boxes=len(boxes), title=gt.get('title'), wall=wall, ok=True))
                print(tid, len(boxes), flush=True)
            except Exception as e:
                results.append(dict(t, ok=False, error=str(e)[:300]))
                print('FAIL', tid, str(e)[:150], flush=True)
                try:
                    ws.close()
                except Exception:
                    pass
                try:
                    targets = json.load(urllib.request.urlopen('http://localhost:%d/json' % port, timeout=5))
                    target = next(x for x in targets if x['type'] == 'page')
                    ws = websocket.create_connection(target['webSocketDebuggerUrl'], origin='http://localhost:%d' % port, timeout=40)
                except Exception as e2:
                    results.append(dict(error='reconnect failed %r' % (e2,))); break
    finally:
        if browser:
            try:
                os.killpg(browser.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        try:
            os.killpg(comp.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        os.close(fd); log.close()
    return results


def run(nworkers, limit=None):
    tasks = json.loads((OUT / 'plan.json').read_text())
    for i, t in enumerate(tasks):
        t['id'] = '%s_%04d' % (t['site'], i)
    if limit:
        tasks = tasks[:limit]
    groups = {}
    for t in tasks:
        groups.setdefault(t['size'], []).append(t)
    jobs = []
    wid = 0
    n2560 = max(1, nworkers * len(groups.get('2560x1440', [])) // max(1, len(tasks)))
    n1920 = max(1, nworkers - n2560)
    for size, n in (('1920x1080', n1920), ('2560x1440', n2560)):
        ts = groups.get(size, [])
        for k in range(n):
            jobs.append((wid, size, ts[k::n])); wid += 1
    with Pool(len(jobs)) as p:
        res = [r for chunk in p.map(worker, jobs, chunksize=1) for r in chunk]
    (OUT / 'manifest.json').write_text(json.dumps(res, indent=1))
    ok = [r for r in res if r.get('ok')]
    print('ok', len(ok), 'fail', len(res) - len(ok))


if __name__ == '__main__':
    if sys.argv[1] == 'plan':
        plan()
    else:
        import argparse
        ap = argparse.ArgumentParser(); ap.add_argument('cmd'); ap.add_argument('--workers', type=int, default=5); ap.add_argument('--limit', type=int)
        a = ap.parse_args(); run(a.workers, a.limit)
