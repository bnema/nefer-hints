"""Seed disposable localhost preview ONLY. Run after docker startup; never use production."""
import json,urllib.request
BASE='http://127.0.0.1:8065/api/v4'
PASSWORD='Fictional-Eval-Only-2026!'
def request(path,data=None,token=None):
 headers={'Content-Type':'application/json'}
 if token:headers['Authorization']='Bearer '+token
 req=urllib.request.Request(BASE+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
 with urllib.request.urlopen(req,timeout=15) as r:return json.load(r),r.headers.get('Token')
def seed():
 users=[];tokens=[]
 for name in ('alex','blair','casey','drew','ellis'):
  u,_=request('/users',dict(email=f'{name}@fictional.example',username=name,password=PASSWORD))
  _,t=request('/users/login',dict(login_id=name,password=PASSWORD));users.append(u);tokens.append(t)
 team,_=request('/teams',dict(name='fictional-demo',display_name='Fictional Demo Team',type='O'),tokens[0])
 for u in users[1:]:request('/teams/'+team['id']+'/members',dict(team_id=team['id'],user_id=u['id']),tokens[0])
 channels=[]
 for name in ('planning','design','engineering','social'):
  c,_=request('/channels',dict(team_id=team['id'],name=name,display_name=name.title(),type='O'),tokens[0]);channels.append(c)
  for u in users[1:]:request('/channels/'+c['id']+'/members',dict(user_id=u['id']),tokens[0])
 for i in range(32):
  c=channels[0] if i<23 else channels[1+(i%3)]
  text=['Please review the fictional release checklist.','The demo dashboard is ready for feedback.','Design notes: improve keyboard navigation and contrast.','Next milestone: test the onboarding flow.'][i%4]
  p,_=request('/posts',dict(channel_id=c['id'],message=f'{text} Update {i+1}.'),tokens[i%5])
  if i%4==0:
   for j in (1,2):request('/posts',dict(channel_id=c['id'],root_id=p['id'],message=f'Fictional reply {j}: reviewed, thanks!'),tokens[(i+j)%5])
   request('/reactions',dict(user_id=users[1]['id'],post_id=p['id'],emoji_name='thumbsup'),tokens[1])
 return dict(team='fictional-demo',channel='planning')
if __name__=='__main__':print(json.dumps(seed()))
