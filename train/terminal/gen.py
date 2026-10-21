#!/usr/bin/env python3
"""Seeded fake terminal screen generator (stdlib only, all text synthetic).

generate(spec, cols, rows) -> dict(A, B, links, pieces): two escape-sequence strings
with IDENTICAL text/layout. A = normal colours; B = every link cell printed with
truecolor fg=bg magenta (#FF00FF on even rows, #F700F7 on odd rows so that links on
adjacent rows, e.g. a wrapped link, stay separable by colour). Files are written
by the orchestrator and printed with `cat` inside the terminal.
"""
import json, os, random, sys, time

LINK_MAGENTA = ['\x1b[38;2;255;0;255m\x1b[48;2;255;0;255m', '\x1b[38;2;247;0;247m\x1b[48;2;247;0;247m']
TLDS = ['com', 'org', 'net', 'io', 'dev', 'fr', 'de', 'app']
SYL = ['ka', 'ne', 'fer', 'ra', 'to', 'li', 'mo', 'sun', 'del', 'ta', 'vor', 'qui', 'zen', 'bar', 'lum', 'ori', 'pex', 'dra', 'wil', 'har']
WORDS = ['build', 'server', 'cache', 'index', 'config', 'parser', 'render', 'router', 'worker', 'queue', 'token', 'buffer', 'stream', 'schema', 'module', 'plugin', 'client', 'driver', 'kernel', 'socket']
USERS = ['alice', 'bob', 'dev', 'sam', 'mira', 'kenji', 'noor', 'luca']
HOSTS = ['devbox', 'lab-3', 'nuc', 'arch-box', 'build01', 'atlas', 'pyramid']
PROJ = ['nile', 'aton', 'kiln', 'ra-core', 'sphinx', 'delta', 'oasis']
EXTS = ['go', 'rs', 'py', 'c', 'h', 'ts', 'md', 'toml', 'json', 'txt']
PATHS = ['/usr/lib/x', '/etc/hosts.d/local', '/var/log/app.log', '/opt/tools/bin/run', '~/src/lab/notes', './build/out/app', '../shared/lib', 'src/main.go:12', 'pkg/util/io.rs:88:3', 'cmd/serve/main.c:140', 'tests/test_core.py:57']
CMDS = ['echo done', 'killall worker', 'make -j8', 'git status', 'ls -la', 'cargo build', 'go test ./...', 'nvim main.go', 'cat notes.txt', 'systemctl --user status app', 'docker ps', 'pytest -q', 'grep -rn TODO src', 'cd ..', 'rm -rf build', 'killall -9 daemon', 'curl -s localhost:8080']


def fname(r):
    return r.choice(WORDS) + r.choice(['_', '-', '']) + r.choice(WORDS[:8]) + '.' + r.choice(EXTS)


def domain(r):
    k = r.random()
    if k < 0.2:
        return r.choice(['example.com', 'example.org', 'example.net'])
    if k < 0.4:
        return r.choice(['www.', 'docs.', 'api.', '']) + r.choice(WORDS) + '.' + r.choice(['test', 'invalid', 'example'])
    name = ''.join(r.choice(SYL) for _ in range(r.randint(2, 3)))
    return r.choice(['', '', 'www.', 'docs.', 'git.', 'cdn.']) + name + '.' + r.choice(TLDS)


def url_path(r):
    n = r.randint(0, 4)
    p = '/'.join(r.choice(WORDS + ['v2', 'docs', 'releases', 'issues', str(r.randint(1, 999))]) for _ in range(n))
    if r.random() < 0.2 and p:
        p += '?id=%d&q=%s' % (r.randint(1, 99), r.choice(WORDS))
    if r.random() < 0.1 and p:
        p += '#' + r.choice(WORDS)
    return ('/' + p) if p else ''


def make_link(r):
    k = r.random()
    d = domain(r)
    if k < 0.30:
        return 'https://' + d + url_path(r)
    if k < 0.40:
        return 'http://' + d + url_path(r)
    if k < 0.50:
        return 'file:///' + '/'.join(r.choice(['home', 'usr', 'srv', 'tmp', 'share']) if i == 0 else fname(r) if i == 2 else r.choice(WORDS) for i in range(r.randint(1, 3)))
    if k < 0.65:
        return 'www.' + d.replace('www.', '') + (url_path(r) or '/' + r.choice(WORDS))
    if k < 0.85:
        return d.replace('www.', '') + '/' + r.choice(WORDS) + url_path(r)
    return r.choice(USERS) + r.choice(['', '.', '_']) + r.choice(WORDS) + '@' + d.replace('www.', '')


# --- segments: (text, sgr) ; slot segment: ('{L}', sgr) -------------------
class B:
    """Block builder bound to a palette."""
    def __init__(self, r, theme):
        self.r, self.t = r, theme

    def c(self, i, bold=False):
        return ('\x1b[1m' if bold else '') + ('\x1b[3%dm' % i if i < 8 else '\x1b[9%dm' % (i - 8))

    def prompt(self):
        r = self.r
        cmd = r.choice(CMDS)
        if r.random() < 0.5:
            return [[(r.choice(PROJ) + ' ', self.c(4)), (r.choice(['main', 'dev', 'feat/x']) + ' ', self.c(5 if False else 3)), ('❯ ', self.c(2, True)), (cmd, '')]]
        u, h = r.choice(USERS), r.choice(HOSTS)
        return [[('%s@%s' % (u, h), self.c(2, True)), (':', ''), ('~/' + r.choice(PROJ), self.c(4, True)), ('$ ', ''), (cmd, '')]]

    def git_log(self):
        r = self.r
        out = []
        for _ in range(r.randint(3, 7)):
            h = ''.join(r.choice('0123456789abcdef') for _ in range(7))
            msg = r.choice(['fix: handle empty %s', 'feat: add %s support', 'refactor %s loop', 'docs: update %s guide', 'chore: bump %s'] ) % r.choice(WORDS)
            segs = [('* ', self.c(1)), (h + ' ', self.c(3)), ('(HEAD -> main) ' if not out else '', self.c(6, True)), (msg, '')]
            if r.random() < 0.3:
                segs += [(' see ', ''), ('{L}', '')]
            out.append(segs)
        return out

    def git_status(self):
        r = self.r
        out = [[('On branch main', '')], [('Changes not staged for commit:', '')]]
        for _ in range(r.randint(2, 5)):
            out.append([('\tmodified:   ' + 'src/' + fname(r), self.c(1))])
        out.append([('Untracked files:', '')])
        for _ in range(r.randint(1, 3)):
            out.append([('\t' + fname(r), self.c(1))])
        return out

    def git_diff(self):
        r = self.r
        f = 'src/' + fname(r)
        out = [[('diff --git a/%s b/%s' % (f, f), '\x1b[1m')], [('@@ -%d,6 +%d,7 @@ func %s()' % (r.randint(1, 90), r.randint(1, 90), r.choice(WORDS)), self.c(6))]]
        for _ in range(r.randint(4, 9)):
            k = r.random()
            text = '    ' + r.choice(['return ', 'x := ', 'if err != nil {', 'let ', 'for i in ', 'self.']) + r.choice(WORDS) + r.choice(['()', ';', ' {', '']) 
            if k < 0.3:
                out.append([('-' + text, self.c(1))])
            elif k < 0.6:
                out.append([('+' + text, self.c(2))])
            else:
                out.append([(' ' + text, '')])
        return out

    def compiler(self):
        r = self.r
        f = 'src/' + fname(r)
        if r.random() < 0.5:
            return [[(f + ':%d:%d: ' % (r.randint(1, 300), r.randint(1, 60)), '\x1b[1m'), ('error: ', self.c(1, True)), ('undefined: ' + r.choice(WORDS), '')],
                    [('    ' + r.choice(WORDS) + '(' + r.choice(WORDS) + ')', '')]]
        n = r.randint(10, 300)
        return [[('error[E0%d]: ' % r.randint(100, 599), self.c(1, True)), ('cannot find value `%s` in this scope' % r.choice(WORDS), '\x1b[1m')],
                [('  --> ', self.c(4, True)), (f + ':%d:%d' % (n, r.randint(1, 40)), '')],
                [('   | ', self.c(4, True))],
                [('%d | ' % n, self.c(4, True)), ('    let y = ' + r.choice(WORDS) + ';', '')],
                [('   | ', self.c(4, True)), ('          ^^^^ not found', self.c(1, True))]]

    def tests(self):
        r = self.r
        out = []
        for i in range(r.randint(4, 8)):
            ok = r.random() < 0.8
            out.append([('PASS ' if ok else 'FAIL ', self.c(2 if ok else 1, True)), ('tests/test_%s.py::test_%s ' % (r.choice(WORDS), r.choice(WORDS)), ''), ('[%3d%%]' % min(100, (i + 1) * 12), self.c(8 + 0 if False else 4))])
        out.append([('===== %d passed, %d failed in %.2fs =====' % (r.randint(5, 80), r.randint(0, 3), r.random() * 9), self.c(3, True))])
        return out

    def table(self):
        r = self.r
        cols = r.choice([['NAME', 'STATUS', 'AGE', 'RESTARTS'], ['ID', 'SIZE', 'OWNER', 'MODIFIED'], ['PACKAGE', 'VERSION', 'ARCH']])
        widths = [r.randint(10, 22) for _ in cols]
        out = [[(''.join(c.ljust(w) for c, w in zip(cols, widths)), '\x1b[1m')]]
        for _ in range(r.randint(3, 8)):
            vals = [r.choice(WORDS) + '-' + str(r.randint(1, 99)), r.choice(['Running', 'Pending', 'Ready', 'x86_64', '12K', '3.4M']), '%dd' % r.randint(1, 99), str(r.randint(0, 5))][:len(cols)]
            out.append([(vals[0].ljust(widths[0]), ''), (''.join(v.ljust(w) for v, w in zip(vals[1:], widths[1:])), self.c(r.choice([2, 3, 6])))])
        return out

    def json_(self):
        r = self.r
        out = [[('{', '')]]
        for i in range(r.randint(3, 7)):
            key = r.choice(WORDS)
            k = r.random()
            if k < 0.25:
                val = [('"https://', self.c(2)), ('{L}', ''), ('"', self.c(2))]
                val = [('"', self.c(2)), ('{L}', ''), ('"', self.c(2))]
            elif k < 0.6:
                val = [('"' + r.choice(WORDS) + '"', self.c(2))]
            else:
                val = [(str(r.randint(0, 9999)), self.c(3))]
            out.append([('  "' + key + '"', self.c(4)), (': ', '')] + val + [(',', '')])
        out.append([('}', '')])
        return out

    def code(self):
        r = self.r
        lang = r.choice(['py', 'go', 'c'])
        out = []
        for _ in range(r.randint(4, 9)):
            ind = '    ' * r.randint(0, 2)
            if lang == 'py':
                kw, rest = r.choice([('def ', r.choice(WORDS) + '(self, x):'), ('return ', r.choice(WORDS) + '.get(x)'), ('if ', 'x is None:'), ('for ', 'i in range(%d):' % r.randint(2, 99)), ('import ', 'os.path')])
            elif lang == 'go':
                kw, rest = r.choice([('func ', r.choice(WORDS) + '(ctx context.Context) error {'), ('return ', 'nil'), ('if ', 'err != nil {'), ('for ', '_, v := range items {'), ('var ', r.choice(WORDS) + ' int')])
            else:
                kw, rest = r.choice([('static ', 'int %s(void) {' % r.choice(WORDS)), ('return ', '0;'), ('if ', '(!p) {'), ('for ', '(int i = 0; i < n; i++) {'), ('#include ', '<stdio.h>')])
            segs = [(ind, ''), (kw, self.c(5 if r.random() < 0.5 else 4, True)), (rest, '')]
            if r.random() < 0.15:
                segs += [('  # ', self.c(8)), ('docs: ', self.c(8)), ('{L}', self.c(8))]
            out.append(segs)
        return out

    def panel(self):
        r = self.r
        w = r.randint(24, 50)
        title = ' ' + r.choice(WORDS) + ' '
        st = self.c(r.choice([4, 6, 3]))
        out = [[('┌─' + title + '─' * (w - len(title) - 3) + '┐', st)]]
        for _ in range(r.randint(2, 5)):
            txt = ' ' + r.choice(WORDS) + ': ' + str(r.randint(0, 999))
            out.append([('│', st), (txt.ljust(w - 2), ''), ('│', st)])
        out.append([('└' + '─' * (w - 2) + '┘', st)])
        return out

    def progress(self):
        r = self.r
        out = []
        for _ in range(r.randint(1, 3)):
            p = r.randint(0, 100)
            n = 30
            f = n * p // 100
            if r.random() < 0.5:
                out.append([(r.choice(WORDS).ljust(14), ''), ('[' + '#' * f + ' ' * (n - f) + ']', self.c(2)), (' %3d%%' % p, '')])
            else:
                out.append([(r.choice(WORDS).ljust(14), ''), ('█' * f, self.c(6)), ('░' * (n - f), self.c(8)), (' %3d%%' % p, '')])
        return out

    def listing(self):
        r = self.r
        out = []
        for _ in range(r.randint(3, 8)):
            isd = r.random() < 0.3
            out.append([(('drwxr-xr-x' if isd else '-rw-r--r--') + ' %s %6d Oct %2d 17:%02d ' % (r.choice(USERS), r.randint(100, 99999), r.randint(1, 28), r.randint(0, 59)), ''),
                        ((r.choice(WORDS) + ('/' if isd else '.' + r.choice(EXTS))), self.c(4, True) if isd else '')])
        return out

    def log(self):
        r = self.r
        out = []
        for _ in range(r.randint(3, 8)):
            lv = r.choice(['INFO', 'INFO', 'WARN', 'ERROR', 'DEBUG'])
            segs = [('2026-10-21 17:%02d:%02d ' % (r.randint(0, 59), r.randint(0, 59)), self.c(8)), (lv.ljust(6), self.c({'INFO': 2, 'WARN': 3, 'ERROR': 1, 'DEBUG': 4}[lv], True))]
            k = r.random()
            if k < 0.4:
                segs.append((r.choice(['GET ', 'fetching ', 'docs at ', 'see ', 'redirect to ']), ''))
                segs.append(('{L}', ''))
            elif k < 0.6:
                segs.append(('opened ' + r.choice(PATHS), ''))
            else:
                segs.append((r.choice(['listening on :%d' % r.randint(1000, 9999), 'worker %d ready' % r.randint(1, 16), 'cache hit ratio %d%%' % r.randint(1, 99), 'v%d.%d.%d loaded' % (r.randint(0, 3), r.randint(0, 20), r.randint(0, 9))]), ''))
            out.append(segs)
        return out

    def prose(self):
        r = self.r
        pre = r.choice(['Docs: ', 'See ', 'Download: ', 'Contact ', 'Report bugs at ', '# homepage: ', 'Source: ', 'Mirror ', 'Open '])
        return [[(pre, self.c(r.choice([3, 6, 7])) if r.random() < 0.5 else ''), ('{L}', '')]]

    def negatives(self):
        r = self.r
        out = []
        for _ in range(r.randint(2, 4)):
            k = r.random()
            if k < 0.4:
                out.append([('error: cannot open ', ''), (r.choice(PATHS), self.c(3))])
            elif k < 0.7:
                out.append([(r.choice(CMDS), self.c(2)), ('  # ' + r.choice(['version v1.%d.%d' % (r.randint(0, 30), r.randint(0, 9)), 'os.path.join', 'main.go', 'foo.bar']), self.c(8))])
            else:
                out.append([(r.choice(PATHS), self.c(4))])
        return out


BLOCKS = ['prompt', 'git_log', 'git_status', 'git_diff', 'compiler', 'tests', 'table', 'json_', 'code', 'panel', 'progress', 'listing', 'log', 'prose', 'negatives']
STATUS_TEXT = ['DP-2 [x] C {c}% M {m}% 17:25', '[0] 1:fish* 2:nvim-', '[{n}] 1:bash* 2:make 3:ssh-', '"{h}" 17:25 21-Oct-26', 'CPU {c}% | MEM {m}% | {h}', 'session-{n}  1:zsh*  2:logs  3:git', 'DP-1 [x] C {c}% M {m}% 09:41']
STATUS_BGS = ['\x1b[41m\x1b[30m', '\x1b[42m\x1b[30m', '\x1b[43m\x1b[30m', '\x1b[44m\x1b[30m', '\x1b[46m\x1b[30m',
              '\x1b[48;2;0;120;60m\x1b[38;2;255;255;255m', '\x1b[48;2;200;120;0m\x1b[38;2;255;255;255m',
              '\x1b[48;2;40;80;180m\x1b[38;2;255;255;255m', '\x1b[48;2;150;30;30m\x1b[38;2;255;255;255m',
              '\x1b[48;2;30;140;140m\x1b[38;2;255;255;255m']
STATUS_FILLS = ['\x1b[100m\x1b[37m', '\x1b[42m\x1b[30m', '\x1b[40m\x1b[37m', '\x1b[44m\x1b[37m', '\x1b[7m']


def build(spec, cols, rows):
    r = random.Random(spec['seed'])
    b = B(r, None)
    want = spec['links']
    usable = rows - (1 if spec['status'] else 0)
    logical = []
    while len(logical) < usable + 2:
        name = r.choice(BLOCKS)
        if name == 'prose' and not want:
            name = 'negatives'
        lines = getattr(b, name)()
        if name != 'prompt' and r.random() < 0.6:
            lines = b.prompt() + lines
        logical += lines
        if r.random() < 0.2:
            logical.append([('', '')])
    slots = lambda: [i for i, ln in enumerate(logical[:max(1, usable - 2)]) if any(s[0] == '{L}' for s in ln)]
    guard = 0
    while len(slots()) < want and guard < 200:
        guard += 1
        j = r.randrange(0, max(1, usable - 2))
        if not any(s[0] == '{L}' for s in logical[j]):
            logical[j] = b.prose()[0]
    avail = slots()
    chosen = set(r.sample(avail, min(want, len(avail)))) if want else set()
    norm, pieces, nlinks = [], [], 0
    for i, ln in enumerate(logical):
        if len(norm) >= usable:
            break
        cells, did = [], False
        for text, sgr in ln:
            if text != '{L}':
                cells += [(ch, sgr, False) for ch in text]
            elif i in chosen and not did:
                link = make_link(r)
                nat = r.choice(['', '', '\x1b[4m', '\x1b[34m', '\x1b[4;36m', '\x1b[94m'])
                if r.random() < 0.15 and len(link) >= 6 and len(norm) + 2 <= usable:
                    s = cols - len(link) // 2
                    if s >= len(cells) and s < cols - 1:
                        cells += [(' ', '', False)] * (s - len(cells))
                cells += [(ch, nat, True) for ch in link]
                did = True
            else:
                cells += [(ch, sgr, False) for ch in r.choice(PATHS)]
        n_rows = 2 if did and len(norm) + 2 <= usable else 1
        for k in range(n_rows):
            norm.append(cells[k * cols:(k + 1) * cols])
        if did:
            first = len(norm) - n_rows
            found = False
            for k in range(n_rows):
                row = norm[first + k]
                c = 0
                while c < len(row):
                    if row[c][2]:
                        e = c
                        while e < len(row) and row[e][2]:
                            e += 1
                        pieces.append((first + k, c, e)); found = True
                        c = e
                    else:
                        c += 1
            nlinks += 1 if found else 0
    while len(norm) < usable:
        norm.append([])
    return norm, nlinks, pieces


def status_row(cols, r):
    parts = r.sample(STATUS_TEXT, r.randint(1, 3))
    cells = []
    fill = r.choice(STATUS_FILLS)
    for t in parts:
        t = t.format(c=r.randint(1, 99), m=r.randint(1, 99), n=r.randint(0, 9), h=r.choice(HOSTS))
        bg = r.choice(STATUS_BGS)
        cells += [(ch, bg, False) for ch in ' ' + t + ' ']
        if r.random() < 0.5:
            cells.append((' ', fill, False))
    cells = cells[:cols]
    pad = [(' ', fill, False)] * (cols - len(cells))
    return cells + pad if r.random() < 0.5 else pad + cells


def render(rows_cells, magenta):
    out = ['\x1b[0m\x1b[?7l\x1b[?25l\x1b[2J']
    for y, cells in enumerate(rows_cells):
        s = ['\x1b[%d;1H\x1b[0m' % (y + 1)]
        cur = None
        for ch, sgr, link in cells:
            st = LINK_MAGENTA[y % 2] if (link and magenta) else sgr
            if st != cur:
                s.append('\x1b[0m' + st)
                cur = st
            s.append(ch)
        s.append('\x1b[0m\x1b[K')
        out.append(''.join(s))
    return ''.join(out)


def generate(spec, cols, rows):
    norm, nlinks, pieces = build(spec, cols, rows)
    allrows = list(norm)
    if spec['status']:
        allrows.append(status_row(cols, random.Random(spec['seed'] + 7)))
    return dict(A=render(allrows, False), B=render(allrows, True), links=nlinks, pieces=pieces, cols=cols, rows=rows)
