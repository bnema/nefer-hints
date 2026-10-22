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
import hashlib, json, os, random, re, shutil, signal, subprocess as sp, time, urllib.request, urllib.parse
from html.parser import HTMLParser
from multiprocessing import Pool
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'data/web'
FAKE = Path('/tmp/nh-term')

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
NEW_SITES = {
 'gtkdocs': 'https://docs.gtk.org/', 'kerneldocs': 'https://docs.kernel.org/',
 'debianwiki': 'https://wiki.debian.org/', 'readthedocs': 'https://docs.readthedocs.io/en/stable/',
 'requestsdocs': 'https://requests.readthedocs.io/en/latest/', 'hexdocs': 'https://hexdocs.pm/',
 'rubygems': 'https://rubygems.org/', 'packagist': 'https://packagist.org/',
 'metacpan': 'https://metacpan.org/', 'flathub': 'https://flathub.org/',
 'repology': 'https://repology.org/', 'distrowatch': 'https://distrowatch.com/',
 'gitlabexplore': 'https://gitlab.com/explore/projects', 'gnomediscourse': 'https://discourse.gnome.org/',
 'pythondiscuss': 'https://discuss.python.org/', 'rustusers': 'https://users.rust-lang.org/',
 'sqlite': 'https://sqlite.org/docs.html', 'postgresdocs': 'https://www.postgresql.org/docs/current/',
 'nginx': 'https://nginx.org/en/docs/', 'caddy': 'https://caddyserver.com/docs/',
 'tailwind': 'https://tailwindcss.com/docs/', 'svelte': 'https://svelte.dev/docs/svelte/overview',
 'vue': 'https://vuejs.org/guide/introduction.html', 'bootstrap': 'https://getbootstrap.com/docs/5.3/forms/overview/',
 'bulma': 'https://bulma.io/documentation/form/', 'pico': 'https://picocss.com/docs/forms',
 'htmx': 'https://htmx.org/docs/', 'rustbook': 'https://doc.rust-lang.org/book/',
 'openlibrary': 'https://openlibrary.org/', 'wikidata': 'https://www.wikidata.org/wiki/Wikidata:Main_Page',
 'marginalia': 'https://search.marginalia.nu/search?query=linux', 'nprtext': 'https://text.npr.org/',
}
SITES.update(NEW_SITES)
EXTRA = {'stackoverflow': ['https://stackoverflow.com/questions/11227809', 'https://stackoverflow.com/questions/927358', 'https://stackoverflow.com/questions/503093'],
         'imdb': ['https://www.imdb.com/title/tt0111161/'], 'cratesio': ['https://crates.io/crates/serde'], 'npmjs': ['https://www.npmjs.com/package/express'],
         'debian': ['https://www.debian.org/distrib/'], 'w3': ['https://www.w3.org/standards/'], 'freedesktop': ['https://www.freedesktop.org/wiki/Software/'],
         'archiveorg': ['https://archive.org/about/']}
EXTRA.update({
 'bootstrap': ['https://getbootstrap.com/docs/5.3/' + p + '/' for p in
               ('forms/form-control', 'forms/select', 'forms/checks-radios', 'forms/range',
                'forms/input-group', 'forms/validation', 'components/dropdowns', 'components/navbar', 'content/tables')],
 'bulma': ['https://bulma.io/documentation/' + p + '/' for p in
           ('form/input', 'form/select', 'form/checkbox', 'form/radio', 'form/textarea', 'components/menu', 'elements/table')],
 'pico': ['https://picocss.com/docs/' + p for p in
          ('input', 'select', 'checkboxes', 'radio', 'range', 'dropdown', 'modal', 'table')],
})
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


def normalized_host(host):
    host = host.lower().rstrip('.')
    return host.removeprefix('www.')


def excluded(host, blocked):
    host = normalized_host(host)
    return any(host == d or host.endswith('.' + d)
               for d in map(normalized_host, blocked))


def blocked_domains():
    scenes = json.loads((ROOT / 'eval/scenes.json').read_text())
    hosts = {urllib.parse.urlparse(scene['url']).hostname
             for scene in scenes.values() if scene.get('url')}
    return {normalized_host(host) for host in hosts if host} | set(EVAL_HOSTS)


def plan(per_site=6, sites=None):
    domains = blocked_domains()
    rng = random.Random(7)
    existing = json.loads((OUT / 'plan.json').read_text()) if (OUT / 'plan.json').exists() else []
    tasks = []
    info = {}
    for name, home in (sites or SITES).items():
        if name in VAL_SITES:
            continue
        host = urllib.parse.urlparse(home).netloc
        assert not excluded(urllib.parse.urlparse(home).hostname or '', domains), host
        urls = [home]
        try:
            req = urllib.request.Request(home, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=20) as response:
                if excluded(urllib.parse.urlparse(response.url).hostname or '', domains):
                    raise ValueError('excluded discovery redirect: ' + response.url)
                html = response.read(2_000_000).decode('utf8', 'replace')
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
    seen, out = {task_key(t) for t in existing}, list(existing)
    for t in tasks:
        k = task_key(t)
        if k not in seen:
            seen.add(k)
            t['id'] = t['site'] + '_' + hashlib.sha256(json.dumps(k).encode()).hexdigest()[:12]
            out.append(t)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'plan.json').write_text(json.dumps(out, indent=1))
    print(len(out), 'tasks;', json.dumps(info))


def task_key(task):
    return tuple(task[k] for k in ('url', 'scroll', 'zoom', 'dark', 'size'))


def task_id(task, index):
    return task.get('id', '%s_%04d' % (task['site'], index))


def merge_results(existing, new):
    """Keep successes and unrelated history; replace a failed attempt with its retry."""
    result = {r['id']: r for r in existing if r.get('id')}
    for row in new:
        previous = result.get(row.get('id'), {})
        if row.get('id') and not (previous.get('ok') or previous.get('boxes') or previous.get('quality_rejected')):
            result[row['id']] = row
    return [r for r in existing if not r.get('id')] + list(result.values())


def stop_process(process):
    if process is not None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=5)


def page_timeout(signum, frame):
    raise TimeoutError('page hard timeout (60 seconds)')


def env_for(tag, wayland=None):
    base = FAKE / tag
    for directory in ('home', 'home/config', 'home/data', 'home/cache'):
        (FAKE / directory).mkdir(parents=True, exist_ok=True)
    e = dict(PATH=os.environ['PATH'], HOME=str(FAKE / 'home'), XDG_CONFIG_HOME=str(FAKE / 'home/config'), XDG_DATA_HOME=str(FAKE / 'home/data'),
             XDG_CACHE_HOME=str(FAKE / 'home/cache'), XDG_STATE_HOME=str(base / 'state'), XDG_RUNTIME_DIR=str(base / 'run'), LANG='C.UTF-8',
             GDK_BACKEND='wayland', MOZ_ENABLE_WAYLAND='1')
    if wayland:
        e['WAYLAND_DISPLAY'] = wayland
    return e


# Reject visible modal backdrops, not small non-blocking banners or inline examples.
OVERLAY_JS = """(() => [...document.querySelectorAll('[aria-modal="true"], dialog[open], .modal.is-active')]
.some(e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
return s.display !== 'none' && s.visibility !== 'hidden' && Number(s.opacity) !== 0
    && r.width * r.height > innerWidth * innerHeight * 0.2; }) ||
    (location.hostname.endsWith('bulma.io') && /learn CSS with.*online interactive/is.test(document.body.innerText)))()"""


def blocked(title, text):
    s = (title + ' ' + text[:600]).lower()
    return bool(re.search(r'just a moment|access denied|attention required|captcha|are you a robot|verify you are human|403 forbidden|404|not found|too many requests|site can.t be reached|err_connection|err_name_not_resolved', s))


def worker(args):
    NEFERWL = shutil.which(os.environ.get('NEFERWL', 'neferwl'))
    if not NEFERWL:
        raise SystemExit('NeferWL executable not found; set NEFERWL or add neferwl to PATH')
    w, size, tasks = args
    domains = blocked_domains()
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
    W, H = map(int, size.split('x'))
    port = 9300 + w
    browser = comp = ws = None
    profile = None
    results = []
    signal.signal(signal.SIGALRM, page_timeout)

    def restart():
        nonlocal browser, comp, ws, profile
        if ws is not None:
            try:
                ws.close()
            except Exception:
                pass
        ws = None
        stop_process(browser); browser = None
        stop_process(comp); comp = None
        if profile:
            shutil.rmtree(profile, ignore_errors=True)
        comp = sp.Popen([NEFERWL, '--backend=headless', '--size', size, '--no-xwayland', '--no-terminal', '--config', str(cfg), '--input', str(fifo),
                         '--screenshot', str(base / 'shots'), '--timeout', '7200s'], env=env_for(tag), stdout=log, stderr=log, stdin=sp.DEVNULL, start_new_session=True)
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
    try:
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
        pages = 40
        for t in tasks:
            tid = t['id']
            final_url = None
            try:
                signal.alarm(60)
                if ws is None or pages >= 40 or comp.poll() is not None or browser.poll() is not None:
                    restart()
                    pages = 0
                pages += 1
                if excluded(urllib.parse.urlparse(t['url']).hostname or '', domains):
                    raise ValueError('excluded planned URL: ' + t['url'])
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
                if ev(OVERLAY_JS):
                    raise ValueError('visible blocking modal')
                gt = ev(DOM_JS)
                final_url = gt.get('url') or ev('location.href')
                if urllib.parse.urlparse(final_url).scheme not in ('http', 'https'):
                    raise ValueError('browser error URL: ' + final_url)
                if excluded(urllib.parse.urlparse(final_url).hostname or '', domains):
                    reason = 'excluded final URL: %s' % final_url
                    results.append(dict(t, final_url=final_url, ok=False, error=reason))
                    print('SKIP', tid, reason, flush=True)
                    continue
                if abs(gt['viewport']['width'] * dpr - W) > 3 or abs(gt['viewport']['height'] * dpr - H) > 3:
                    raise RuntimeError('viewport %s dpr %s != %s' % (gt['viewport'], dpr, size))
                body = ev('document.body?document.body.innerText.slice(0,600):""') or ''
                wall = blocked(gt.get('title') or '', body)
                if wall:
                    raise ValueError('blocked title/body: ' + str(gt.get('title')))
                if len(gt['boxes']) < 3:
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
                if len(boxes) < 3:
                    raise ValueError('fewer than 3 usable boxes')
                split = 'val' if t['site'] in VAL_SITES else 'train'
                if split == 'val':
                    raise ValueError('validation set is frozen')
                (OUT / split / 'images').mkdir(parents=True, exist_ok=True); (OUT / split / 'labels').mkdir(parents=True, exist_ok=True)
                img.save(OUT / split / 'images' / (tid + '.png'))
                (OUT / split / 'labels' / (tid + '.txt')).write_text(''.join('0 %.6f %.6f %.6f %.6f\n' % ((a + c) / 2 / W, (b + d) / 2 / H, (c - a) / W, (d - b) / H) for a, b, c, d in boxes))
                results.append(dict(t, final_url=final_url, split=split, boxes=len(boxes), title=gt.get('title'), wall=wall, ok=True))
                print(tid, len(boxes), flush=True)
            except Exception as e:
                results.append(dict(t, final_url=final_url, ok=False, error=str(e)[:300]))
                print('FAIL', tid, str(e)[:150], flush=True)
                # Any page failure invalidates the session. The next task gets a fresh
                # browser and compositor rather than retrying a dead CDP endpoint.
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:
                        pass
                ws = None
            finally:
                signal.alarm(0)
                checkpoint = base / 'results.json'
                tmp = checkpoint.with_suffix('.tmp')
                tmp.write_text(json.dumps(results))
                tmp.replace(checkpoint)
    finally:
        signal.alarm(0)
        stop_process(browser)
        stop_process(comp)
        if profile:
            shutil.rmtree(profile, ignore_errors=True)
        os.close(fd); log.close()
    return results


def run(nworkers, limit=None, new_sites=False):
    if not 1 <= nworkers <= 5:
        raise ValueError('workers must be between 1 and 5')
    manifest = ROOT / 'train/web/manifest.json'
    existing = json.loads(manifest.read_text()) if manifest.exists() else []
    tasks = json.loads((OUT / 'plan.json').read_text())
    planned_ids = {task_id(t, i) for i, t in enumerate(tasks)}
    # Recover completed pages if the previous orchestrator stopped before a worker returned.
    for checkpoint in sorted(FAKE.glob('web*/results.json')):
        recovered = json.loads(checkpoint.read_text())
        recovered = [r for r in recovered if r.get('id') in planned_ids and
                     (not r.get('ok') or (OUT / r.get('split', 'train') /
                      'images' / (r['id'] + '.png')).exists())]
        existing = merge_results(existing, recovered)
    tmp = manifest.with_suffix('.tmp')
    tmp.write_text(json.dumps(existing, indent=1))
    tmp.replace(manifest)
    domains = blocked_domains()
    pending = []
    for i, t in enumerate(tasks):
        t = dict(t, id=task_id(t, i))
        if new_sites and t['site'] not in NEW_SITES:
            continue
        if any(r.get('id') == t['id'] and r.get('quality_rejected') for r in existing):
            continue
        if t['site'] in VAL_SITES or excluded(urllib.parse.urlparse(t['url']).hostname or '', domains):
            continue
        if any((OUT / split / 'images' / (t['id'] + '.png')).exists() for split in ('train', 'val')):
            continue
        pending.append(t)
    tasks = pending[:limit] if limit else pending
    if not tasks:
        print('No pending train tasks')
        return
    # Each worker owns one display size. A single requested worker runs sizes serially.
    sizes = sorted({t['size'] for t in tasks})
    if nworkers == 1:
        jobs = [(0, size, [t for t in tasks if t['size'] == size]) for size in sizes]
    else:
        counts = {size: 1 for size in sizes}
        for _ in range(nworkers - len(sizes)):
            size = max(sizes, key=lambda s: sum(t['size'] == s for t in tasks) / counts[s])
            counts[size] += 1
        jobs = []
        for size, count in counts.items():
            ts = [t for t in tasks if t['size'] == size]
            for k in range(count):
                if ts[k::count]:
                    jobs.append((len(jobs), size, ts[k::count]))
    with Pool(min(nworkers, len(jobs))) as pool:
        for chunk in pool.imap_unordered(worker, jobs, chunksize=1):
            existing = merge_results(existing, chunk)
            tmp = manifest.with_suffix('.tmp')
            tmp.write_text(json.dumps(existing, indent=1))
            tmp.replace(manifest)
    print('ok', sum(bool(r.get('ok')) for r in existing), 'manifest entries', len(existing))


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('cmd', choices=['plan', 'run'])
    ap.add_argument('--workers', type=int, default=5)
    ap.add_argument('--limit', type=int)
    ap.add_argument('--new-sites', action='store_true')
    a = ap.parse_args()
    if a.cmd == 'plan':
        plan(sites=NEW_SITES if a.new_sites else None)
    else:
        run(a.workers, a.limit, a.new_sites)
