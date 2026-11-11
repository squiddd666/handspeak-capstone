"""Vocabulary presentation overrides and consented match feedback; no automatic training."""
import json,re,uuid,tempfile,subprocess,os
from pathlib import Path
from datetime import datetime,timedelta,timezone

SQLITE_SCHEMA='''
CREATE TABLE IF NOT EXISTS vocabulary_settings(word_id TEXT PRIMARY KEY,description TEXT NOT NULL,video_path TEXT NOT NULL,hidden INTEGER NOT NULL DEFAULT 0,updated_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS match_feedback(id TEXT PRIMARY KEY,owner_id TEXT NOT NULL,predicted TEXT NOT NULL,expected TEXT NOT NULL,verdict TEXT NOT NULL,model TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at TEXT NOT NULL);
'''
class ExperienceStore:
 def __init__(self,connect,root,error,now):self.connect=connect;self.root=root;self.error=error;self.now=now
 def catalog(self):
  items=json.loads((self.root/'models/motion-vocabulary.json').read_text(encoding='utf-8'))['items']
  existing={item['id'] for item in items}
  for label in ['HELLO','THANK YOU','PLEASE','YES','NO','FINISH','DRINK','WATER','BOOK','FOOD','HUNGRY','LIKE','GO','NAME','HOME','HAVE','WANT','LOVE']:
   word=label.lower().replace(' ','-')
   if word not in existing:items.append({'id':word,'label':label,'note':''})
  return items
 def settings(self):
  with self.connect() as db:rows=db.execute('SELECT word_id,description,video_path,hidden,updated_at FROM vocabulary_settings').fetchall()
  labels={x['id']:x['label'] for x in self.catalog()}
  return {'items':{r['word_id']:{'description':r['description'],'video':r['video_path'],'hidden':bool(r['hidden']),'label':labels.get(r['word_id'],'')} for r in rows}}
 def save(self,data):
  word=data.get('id');items={x['id']:x for x in self.catalog()}
  if word not in items:raise self.error(422,'Select an existing vocabulary entry.')
  current=self.settings()['items'].get(word,{})
  description=data.get('description',current.get('description',''));video=data.get('video',current.get('video',''));hidden=data.get('hidden',current.get('hidden',False))
  if not isinstance(description,str) or len(description)>800 or type(hidden) is not bool:raise self.error(422,'Description must be at most 800 characters; visibility must be true or false.')
  if not isinstance(video,str) or (video and (not re.fullmatch(r'media/signs/[a-z0-9-]+\.mp4',video) or not (self.root/video).is_file())):raise self.error(422,'Choose an existing local MP4 practice video.')
  with self.connect() as db:
   if db.execute('SELECT word_id FROM vocabulary_settings WHERE word_id=?',(word,)).fetchone():db.execute('UPDATE vocabulary_settings SET description=?,video_path=?,hidden=?,updated_at=? WHERE word_id=?',(description,video,int(hidden),self.now(),word))
   else:db.execute('INSERT INTO vocabulary_settings VALUES(?,?,?,?,?)',(word,description,video,int(hidden),self.now()))
  return {'ok':True}
 def feedback(self,data,owner):
  if data.get('consent') is not True:raise self.error(422,'Consent is required before submitting this word feedback.')
  predicted=data.get('predicted');expected=data.get('expected');verdict=data.get('verdict');model=data.get('model','')
  valid=lambda word:isinstance(word,str) and 0<len(word)<=80 and bool(re.fullmatch(r"[A-Z0-9][A-Z0-9 '-]*",word))
  if not valid(predicted) or not valid(expected) or verdict not in {'correct','wrong','missed'} or not isinstance(model,str) or len(model)>200:raise self.error(422,'Enter valid word labels and feedback type.')
  if verdict=='correct' and predicted!=expected:raise self.error(422,'Correct feedback must retain the detected word.')
  if verdict=='missed' and predicted!='NO RELIABLE MATCH':raise self.error(422,'Missed feedback must describe a rejected capture.')
  cutoff=(datetime.now(timezone.utc)-timedelta(minutes=10)).isoformat()
  with self.connect() as db:
   if db.execute('SELECT COUNT(*) FROM match_feedback WHERE owner_id=? AND created_at>?',(owner,cutoff)).fetchone()[0]>=20:raise self.error(429,'Please wait before submitting more match feedback.')
   db.execute('INSERT INTO match_feedback VALUES(?,?,?,?,?,?,?,?)',(uuid.uuid4().hex,owner,predicted,expected,verdict,model,'pending',self.now()))
  return {'ok':True,'status':'pending'}
 def review(self,data):
  if data.get('status') not in {'reviewed','dismissed'} or not isinstance(data.get('id'),str):raise self.error(422,'Choose reviewed or dismissed.')
  with self.connect() as db:
   if not db.execute('SELECT id FROM match_feedback WHERE id=?',(data['id'],)).fetchone():raise self.error(404,'Feedback not found.')
   db.execute('UPDATE match_feedback SET status=? WHERE id=?',(data['status'],data['id']))
  return {'ok':True}
 def overview(self):
  with self.connect() as db:feedback=[dict(r) for r in db.execute('SELECT id,predicted,expected,verdict,model,status,created_at FROM match_feedback ORDER BY created_at DESC LIMIT 100')]
  return {'vocabulary':self.catalog(),'settings':self.settings()['items'],'feedback':feedback,'videos':[str(p.relative_to(self.root)) for p in sorted((self.root/'media/signs').glob('*.mp4'))]}
 def upload(self,stream,length,word,content_type):
  if word not in {x['id'] for x in self.catalog()}:raise self.error(422,'Select a vocabulary entry first.')
  if content_type!='video/mp4' or not 32<=length<=20*1024*1024:raise self.error(422,'Upload an MP4 up to 20 MiB.')
  # Stage outside the served root; probe only local file protocols.
  fd,path=tempfile.mkstemp(suffix='.mp4');destination=None
  try:
   with os.fdopen(fd,'wb') as output:
    remaining=length
    while remaining:
     chunk=stream.read(min(65536,remaining))
     if not chunk:raise self.error(422,'Upload was interrupted.')
     output.write(chunk);remaining-=len(chunk)
   with open(path,'rb') as file:
    if b'ftyp' not in file.read(32):raise self.error(422,'The upload is not an MP4 video.')
   try:
    result=subprocess.run(['/usr/bin/ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_entries','format=duration:stream=codec_type','-of','json',path],capture_output=True,timeout=10,check=True)
    info=json.loads(result.stdout);duration=float(info['format']['duration'])
    if not 0<duration<=120 or not any(s.get('codec_type')=='video' for s in info.get('streams',[])):raise ValueError()
   except (OSError,ValueError,KeyError,subprocess.SubprocessError):raise self.error(422,'Use a readable MP4 video no longer than two minutes.')
   filename='admin-'+uuid.uuid4().hex+'.mp4';destination=self.root/'media/signs'/filename
   # Temp and release may be on different mounts; copy in bounded chunks.
   import shutil
   shutil.copyfile(path,destination);os.chmod(destination,0o644)
   video='media/signs/'+filename;self.save({'id':word,'video':video})
   destination=None
   return {'ok':True,'video':video}
  finally:
   Path(path).unlink(missing_ok=True)
   if destination is not None:destination.unlink(missing_ok=True)
