"""Bounded native captures; run under dbus-run-session with fake HOME inherited."""
import os,json,re,subprocess as sp,time,signal
from pathlib import Path
R=Path(__file__).resolve().parent
B='$HOME/.local/share/nefer-hints-test/bin/neferwl'
def main():
 home=Path('/tmp/nh-eval/home');content=home/'Fictional';content.mkdir(exist_ok=True)
 for f in ('Documents','Projects','Music','Pictures'):(content/f).mkdir(exist_ok=True)
 (content/'notes.txt').write_text('Fictional project notes\nReview the demo interface.\n')
 (content/'report-2026.odt').write_text('Fictional placeholder')
 env=os.environ.copy()
 for k in ('NEFERWL_STATE','NEFERWL_SLOT','DISPLAY'):env.pop(k,None)
 env.update(GIO_USE_VOLUME_MONITOR='unix', HOME=str(home),XDG_CONFIG_HOME=str(home/'config'),XDG_DATA_HOME=str(home/'data'),XDG_CACHE_HOME=str(home/'cache'),XDG_STATE_HOME=str(home/'state'),WAYLAND_DISPLAY='nh-eval-unused',GDK_BACKEND='wayland',MOZ_ENABLE_WAYLAND='1')
 fifo=home/'input-native'
 if not fifo.exists():os.mkfifo(fifo)
 fd=os.open(fifo,os.O_RDWR);log=open(home/'native.log','w')
 c=sp.Popen([B,'--backend=headless','--no-xwayland','--no-terminal','--config',str(home/'headless.conf'),'--input',str(fifo),'--timeout','240s'],env=env,stdout=log,stderr=log)
 app=None
 try:
  time.sleep(2)
  entries=[json.loads(l) for l in (home/'state/neferwl/runs/headless/latest.log').read_text().splitlines() if 'listening' in l]
  env['WAYLAND_DISPLAY']=re.search(r'wayland-[\w-]+',json.dumps(entries)).group(0)
  def key(s):os.write(fd,('key '+s+'\nsleep 1s\n').encode());time.sleep(1.5)
  def click(x,y):os.write(fd,f'move {x} {y}\nclick left\nsleep 1s\n'.encode());time.sleep(1.5)
  def shot(name):
   sp.run(['grim',str(R/'frames'/f'{name}.png')],env=env,check=True,timeout=8);print(name,flush=True)
  jobs=[('nautilus',['nautilus','--new-window',str(content)]),('thunar',['thunar',str(content)]),('editor',['gnome-text-editor',str(content/'notes.txt')]),('firefox',['firefox','--no-remote','--profile',str(home/'firefox-eval'),'https://example.org'])]
  (home/'firefox-eval').mkdir(exist_ok=True)
  for name,args in jobs:
   app=sp.Popen(args,env=env,stdout=log,stderr=log,start_new_session=True);time.sleep(8)
   if name=='nautilus':key('F9')
   if name=='thunar':key('Ctrl+b')
   shot(name)
   if name=='nautilus':
    key('Ctrl+1');shot('nautilus-list');key('Shift+F10');shot('nautilus-context');key('Escape');click(257,23);shot('nautilus-menu');key('Escape')
   elif name=='thunar':key('Alt+f');shot('thunar-menu');key('Escape')
   elif name=='editor':key('F10');shot('editor-menu');key('Escape')
   else: key('Ctrl+Shift+a');key('Escape');click(1895,60);shot('firefox-menu')
   try:os.killpg(app.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   time.sleep(2);app=None
 finally:
  if app:
   try:os.killpg(app.pid,signal.SIGTERM)
   except ProcessLookupError:pass
  c.terminate()
  try:c.wait(timeout=5)
  except sp.TimeoutExpired:c.kill();c.wait(timeout=5)
  os.close(fd);log.close()
if __name__=='__main__':main()
