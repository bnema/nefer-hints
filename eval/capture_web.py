#!/usr/bin/env python3
"""Run under dbus-run-session. Bounded headless capture with fresh fake HOME."""
import json, os, re, signal, subprocess as sp, time, urllib.request
from pathlib import Path
import websocket
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parent
BIN='$HOME/.local/share/nefer-hints-test/bin/neferwl'
PAGES=[('hn','https://news.ycombinator.com','dense_text'),('lobsters','https://lobste.rs','dense_text'),('wiki','https://en.wikipedia.org/wiki/Wayland_(protocol)','content'),('mdn','https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Elements/button','content'),('arch','https://archlinux.org','content'),('news','https://www.theguardian.com/international','content'),('github','https://github.com/torvalds/linux','modern_web'),('login','https://github.com/login','forms'),('forms','https://www.w3schools.com/html/html_forms.asp','forms'),('youtube','https://www.youtube.com','modern_web'),('go','https://go.dev/doc/','docs_sidebar'),('hn-dark','https://news.ycombinator.com','theme_variant'),('arch-dark','https://archlinux.org','theme_variant')]

def main():
 home=Path('/tmp/nh-eval/home'); home.mkdir(parents=True,exist_ok=True)
 env=os.environ.copy()
 for k in ('NEFERWL_STATE','NEFERWL_SLOT','DISPLAY'):env.pop(k,None)
 env.update(HOME=str(home),XDG_CONFIG_HOME=str(home/'config'),XDG_DATA_HOME=str(home/'data'),XDG_CACHE_HOME=str(home/'cache'),XDG_STATE_HOME=str(home/'state'),WAYLAND_DISPLAY='nh-eval-unused',GDK_BACKEND='wayland',MOZ_ENABLE_WAYLAND='1')
 for k in ('XDG_CONFIG_HOME','XDG_DATA_HOME','XDG_CACHE_HOME','XDG_STATE_HOME'):Path(env[k]).mkdir(exist_ok=True)
 for folder in ('Documents','Projects/demo-app','Music','Pictures'): (home/folder).mkdir(parents=True,exist_ok=True)
 (home/'notes.txt').write_text('Fictional evaluation notes.\n')
 config=home/'headless.conf';config.write_text('terminal.auto-open = off\nborder.width = 0\nfocus.flash = off\n')
 fifo=home/'input-web'
 if not fifo.exists():os.mkfifo(fifo)
 fd=os.open(fifo,os.O_RDWR)
 log=open(home/'capture-web.log','w')
 compositor=sp.Popen([BIN,'--backend=headless','--no-xwayland','--no-terminal','--config',str(config),'--input',str(fifo),'--timeout','600s'],env=env,stdout=log,stderr=log)
 browser=None
 scenes=json.loads((ROOT/'scenes.json').read_text()); errors={}
 for folder in ('frames','gt','results'): (ROOT/folder).mkdir(exist_ok=True)
 try:
  time.sleep(2)
  lp=home/'state/neferwl/runs/headless/latest.log'
  entries=[json.loads(l) for l in lp.read_text().splitlines() if 'listening' in l]
  env['WAYLAND_DISPLAY']=re.search(r'wayland-[\w-]+',json.dumps(entries)).group(0)
  profile=home/f'chromium-{int(time.time())}'
  browser=sp.Popen(['chromium','--ozone-platform=wayland','--no-first-run','--no-default-browser-check','--disable-sync','--disable-session-crashed-bubble','--remote-debugging-port=9223','--remote-allow-origins=http://localhost:9223',f'--user-data-dir={profile}','--start-fullscreen','--app=https://news.ycombinator.com'],env=env,stdout=log,stderr=log,start_new_session=True)
  time.sleep(5)
  os.write(fd,b'key F11\nsleep 1s\n');time.sleep(2)
  targets=json.load(urllib.request.urlopen('http://localhost:9223/json',timeout=5))
  target=next(t for t in targets if t['type']=='page')
  ws=websocket.create_connection(target['webSocketDebuggerUrl'],origin='http://localhost:9223',timeout=30)
  seq=0
  def call(method,params={}):
   nonlocal seq
   seq+=1;ws.send(json.dumps(dict(id=seq,method=method,params=params)))
   for _ in range(2000):
    msg=json.loads(ws.recv())
    if msg.get('id')==seq:
     if 'error' in msg:raise RuntimeError(msg)
     return msg.get('result',{})
   raise RuntimeError('too many CDP events')
  def evaluate(js):
   result=call('Runtime.evaluate',dict(expression=js,returnByValue=True,awaitPromise=True))
   if 'exceptionDetails' in result:
    detail=result['exceptionDetails'];raise RuntimeError(detail.get('exception',{}).get('description',detail.get('text','JavaScript exception')))
   return result.get('result',{}).get('value')
  def wait_for(selector):
   deadline=time.monotonic()+30
   while time.monotonic()<deadline:
    if evaluate('!!document.querySelector('+json.dumps(selector)+')'):return
    time.sleep(.25)
   raise TimeoutError('waiting for '+selector+'; page: '+str(evaluate('document.body.innerText.slice(0,4000)')))
  if any(category=='mattermost' for _,_,category in PAGES):
   from seed_mattermost import request, PASSWORD
   user,token=request('/users/login',dict(login_id='blair',password=PASSWORD))
   cookie=call('Network.setCookie',dict(name='MMAUTHTOKEN',value=token,url='http://127.0.0.1:8065/',path='/',httpOnly=True,sameSite='Lax'))
   if not cookie.get('success'):raise RuntimeError('cookie injection failed')
   call('Network.setCookie',dict(name='MMUSERID',value=user['id'],url='http://127.0.0.1:8065/',path='/'))
   call('Network.setCookie',dict(name='MMCSRF',value='fictional-eval-csrf',url='http://127.0.0.1:8065/',path='/'))
  for name,url,category in PAGES:
   try:
    call('Emulation.setEmulatedMedia',{'features':[{'name':'prefers-color-scheme','value':'dark' if name.endswith('-dark') else 'light'}]})
    call('Emulation.setAutoDarkModeOverride',{'enabled':name.endswith('-dark')})
    call('Page.navigate',{'url':url});time.sleep(10)
    if category=='mattermost':
     evaluate("[...document.querySelectorAll('button,a')].find(e=>e.innerText.trim()==='View in Browser')?.click()")
     wait_for('#postListContent, #post-list, .post-list__table')
     # Dismiss introductory overlays where present, without accessing any real account.
     evaluate("[...document.querySelectorAll('button,a')].filter(e=>/^(Skip|Later|No thanks|Got it|Close)|No thanks, I.ll figure it out myself/.test(e.innerText.trim())).forEach(e=>e.click())")
     for _ in range(2):
      if evaluate("document.body.innerText.includes('Welcome to Mattermost')"):
       os.write(fd,b'move 140 990\nclick left\nsleep 1s\n');time.sleep(2)
     if name=='mattermost-thread':
      evaluate("[...document.querySelectorAll('button,a')].find(e=>/repl/i.test(e.innerText+' '+e.getAttribute('aria-label')))?.click()")
      wait_for('#rhsContainer, .sidebar--right')
     if name=='mattermost-switcher':
      os.write(fd,b'key Ctrl+k\nsleep 1s\n')
      wait_for('[role=dialog], .modal-content')
     time.sleep(2)
    # Freeze layout between DOM extraction and compositor capture.
    evaluate("document.querySelectorAll('video,audio').forEach(e=>e.pause()); document.documentElement.style.scrollBehavior='auto';")
    gt=evaluate((ROOT/'dom.js').read_text())
    if not gt['boxes']:raise RuntimeError('no visible clickable targets; title='+gt['title'])
    if gt['viewport']['width']!=1920 or gt['viewport']['height']!=1080:raise RuntimeError('non-fullscreen viewport '+str(gt['viewport']))
    sp.run(['grim',str(ROOT/'frames'/f'{name}.png')],env=env,check=True,timeout=10)
    image=Image.open(ROOT/'frames'/f'{name}.png').convert('RGB');draw=ImageDraw.Draw(image)
    for box in gt['boxes']:draw.rectangle(box,outline='lime',width=2)
    image.save(ROOT/'gt'/f'{name}_gt.png')
    (ROOT/'gt'/f'{name}.json').write_text(json.dumps(gt,indent=2)+'\n')
    scenes[name]={'category':category,'url':url}
    print(name,len(gt['boxes']),gt['title'],flush=True)
   except Exception as exc:
    errors[name]=str(exc);print('FAILED',name,str(exc),flush=True)
  ws.close()
 finally:
  if browser:
   try:os.killpg(browser.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:browser.wait(timeout=5)
   except sp.TimeoutExpired:os.killpg(browser.pid,signal.SIGKILL);browser.wait(timeout=5)
  compositor.terminate()
  try:compositor.wait(timeout=5)
  except sp.TimeoutExpired:compositor.kill();compositor.wait(timeout=5)
  os.close(fd);log.close()
  (ROOT/'scenes.json').write_text(json.dumps(scenes,indent=2)+'\n')
  error_file=ROOT/'results'/('mattermost-capture-errors.json' if any(c=='mattermost' for _,_,c in PAGES) else 'web-capture-errors.json')
  error_file.write_text(json.dumps(errors,indent=2)+'\n')
if __name__=='__main__':main()
