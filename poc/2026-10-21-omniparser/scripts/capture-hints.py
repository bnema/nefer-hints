import os, subprocess as sp, time, pathlib, json, signal
R=pathlib.Path('/tmp/omniparser-eval')
app=os.environ['EVAL_APP']; base=R/('hint-'+app); base.mkdir(exist_ok=True)
fifo=base/'input'; os.mkfifo(fifo) if not fifo.exists() else None
fd=os.open(fifo,os.O_RDWR)
env=os.environ.copy()
for k in ['NEFERWL_STATE','NEFERWL_SLOT','DISPLAY']: env.pop(k,None)
env.update(WAYLAND_DISPLAY='omniparser-unused',XDG_STATE_HOME=str(R/'state'),NEFERWL_HINT_DEBUG='1',MOZ_ENABLE_WAYLAND='1',GDK_BACKEND='wayland')
log=open(base/'process.log','w')
c=sp.Popen([str(R/'neferwl'),'--backend=headless','--no-xwayland','--no-terminal','--config',str(R/'config/hints'),'--size','1920x1080','--input',str(fifo),'--timeout','150s'],env=env,stdout=log,stderr=log)
a=None
try:
    lp=R/'state/neferwl/runs/headless/latest.log'
    time.sleep(3)
    if not lp.exists(): raise RuntimeError('no log')
    entries=[json.loads(l) for l in lp.read_text().splitlines() if 'listening' in l]
    if not entries: raise RuntimeError('no listening entry')
    import re
    txt=json.dumps(entries)
    display=re.search(r'wayland-[\w-]+',txt).group(0)
    env['WAYLAND_DISPLAY']=display
    if app=='firefox': args=['firefox','--no-remote','--profile',str(R/'ffprofile'),'https://news.ycombinator.com']
    elif app=='dumber': args=['$HOME/.local/bin/dumber','browse','--ephemeral','https://news.ycombinator.com']
    elif app=='nautilus': args=['nautilus','--new-window',str(pathlib.Path.home())]
    else: args=['thunar',str(pathlib.Path.home())]
    a=sp.Popen(args,env=env,stdout=log,stderr=log,start_new_session=True)
    def key(s): os.write(fd,('key '+s+'\nsleep 1s\n').encode()); time.sleep(1.5)
    def shot(name):
        dumps=R/'state/neferwl/hints'
        before=set(dumps.glob('*.json')) if dumps.exists() else set()
        key('Super+g'); time.sleep(5)
        after=set(dumps.glob('*.json')) if dumps.exists() else set()
        import shutil
        dest=R/'frames'; dest.mkdir(exist_ok=True)
        for meta in after-before:
            stem=meta.with_suffix('')
            for suffix in ['.json','.png','.annotated.png']:
                shutil.copyfile(str(stem)+suffix,dest/(app+'-'+name+suffix))
        print(app,name,'dumps',len(after-before),flush=True)
        key('Escape')
    time.sleep(13)
    if app=='dumber':
        os.write(fd,b'move 1860 1040\nclick left\n'); time.sleep(4)
        key('Ctrl+l'); os.write(fd,b'type https://news.ycombinator.com\nkey Return\n'); time.sleep(10)
    shot('home' if app in ['nautilus','thunar'] else 'hn')
    if app in ['firefox','dumber']:
        key('Ctrl+l'); os.write(fd,b'type https://archlinux.org\nkey Return\n'); time.sleep(10); shot('arch')
        if app=='dumber':
            key('Ctrl+l'); os.write(fd,b'type https://en.wikipedia.org/wiki/Wayland_(protocol)\nkey Return\n'); time.sleep(10); shot('wiki')
            # no extra scene
        else:
            os.write(fd,b'move 1898 60\nclick left\n'); time.sleep(2); shot('menu')
    else:
        key('Shift+F10'); shot('menu')
finally:
    if a:
        try: os.killpg(a.pid,signal.SIGTERM)
        except ProcessLookupError: pass
    c.terminate()
    try: c.wait(timeout=8)
    except sp.TimeoutExpired: c.kill(); c.wait()
    os.close(fd); log.close()
