"""Reference clips -> fresh landmarks -> live API / actual JS classifiers.
Not browser automation, getUserMedia, webcam accuracy, or independent holdout.
"""
import json,re,hashlib,time,urllib.request,urllib.error,subprocess,csv,html
from pathlib import Path
import cv2,mediapipe as mp
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'website-word-test';OUT.mkdir(exist_ok=True)
CACHE=OUT/'landmarks';CACHE.mkdir(exist_ok=True)
BASE='http://localhost:8000'
def get(path):
 with urllib.request.urlopen(BASE+path,timeout=30) as r:return json.load(r)
def post(path,payload):
 request=urllib.request.Request(BASE+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
 try:
  with urllib.request.urlopen(request,timeout=180) as r:return r.status,json.load(r)
 except urllib.error.HTTPError as e:return e.code,json.load(e)
norm=lambda s:re.sub('[^A-Z0-9]','',s.upper())
inventory={name:get('/api/'+name+'/status') for name in ['capstone-asl','beginner-asl','research-words']}
(OUT/'inventory.json').write_text(json.dumps(inventory,indent=2))
lookup={}
for p in sorted((ROOT/'media/signs').glob('*.mp4')):lookup.setdefault(norm(p.stem),p)
for p in sorted((ROOT/'openhands-test/reference-videos').glob('*.mp4')):lookup.setdefault(norm(p.stem),p)
for p in sorted((ROOT.parent/'handspeak-training/test').glob('*.mp4')):
 lookup.setdefault(norm(p.stem.partition('-')[2]),p)
jobs=[]
def add(model,labels,endpoint=None,vocabulary=None,**extra):
 for label in labels:jobs.append(dict(model=model,expected=label,endpoint=endpoint,vocabulary=vocabulary,**extra))
c=inventory['capstone-asl'];b=inventory['beginner-asl']
add('capstone-full',c['labels'],'/api/capstone-asl','full')
add('capstone-core',c['coreLabels'],'/api/capstone-asl','core')
add('capstone-extended',c['extendedLabels'],'/api/capstone-asl','extended')
add('beginner-ready',b['labels'],'/api/beginner-asl')
for key,vocab in [('essential','essential'),('target20','target20'),('passedTarget20','target20-passed')]:
 if b.get(key,{}).get('available'):add(vocab,b[key]['labels'],'/api/beginner-asl',vocab)
add('research-five',inventory['research-words']['labels'],'/api/research-words')
base=json.loads((ROOT/'models/asl-words.json').read_text());extra=json.loads((ROOT/'models/asl-extra-words.json').read_text())
# BABY and WATER are binary fallback labels in the default recognition pipeline.
add('browser-default',sorted(set(base['labels']+['BABY','WATER'])),mode='default')
add('browser-expanded',sorted(set(base['labels']+extra['labels']+['BABY'])),mode='expanded')
for group in json.loads((ROOT/'models/motion-categories/index.json').read_text())['groups']:
 add('browser-'+group['id'],group['labels'],mode='category',modelPath=group['file'])

def landmarks(path):
 sha=hashlib.sha256(path.read_bytes()).hexdigest();cache=CACHE/(sha+'.json')
 if cache.exists():return json.loads(cache.read_text()),sha
 cap=cv2.VideoCapture(str(path));count=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=cap.get(cv2.CAP_PROP_FPS)
 if count<1 or fps<=0:raise ValueError('Video metadata unavailable')
 # Sample the whole source at <=15 Hz, <=90 real observations, never repeat frames.
 step=max(1,int(round(fps/15)),(count+89)//90);frames=[];raw=[];aspect=1
 with mp.solutions.holistic.Holistic(model_complexity=1,smooth_landmarks=True,min_detection_confidence=.5,min_tracking_confidence=.5) as tracker:
  i=0
  while True:
   ok,image=cap.read()
   if not ok:break
   if i%step==0:
    aspect=image.shape[0]/image.shape[1];result=tracker.process(cv2.cvtColor(image,cv2.COLOR_BGR2RGB))
    points=lambda obj:[[p.x,p.y,p.z] for p in obj.landmark] if obj else None
    left,right=points(result.left_hand_landmarks),points(result.right_hand_landmarks)
    raw.append([[dict(x=p[0],y=p[1],z=p[2]) for p in hand] if hand else None for hand in [left,right]])
    if result.pose_landmarks and (left or right):
     pose=points(result.pose_landmarks)
     frames.append(dict(timestampMs=i/fps*1000,pose=[pose[j] for j in [0,2,5,11,12,13,14]],left=left,right=right))
   i+=1
 cap.release()
 value=dict(frames=frames,rawFrames=raw,aspect=aspect,durationMs=count/fps*1000,sourceFrames=count,sourceFps=fps)
 cache.write_text(json.dumps(value));return value,sha

results=[]
def save():
 summaries=[]
 for model in dict.fromkeys(j['model'] for j in jobs):
  group=[r for r in results if r['model']==model];attempts=[r for r in group if r['outcome']!='untested']
  summaries.append(dict(model=model,planned=sum(j['model']==model for j in jobs),processed=len(group),tested=len(attempts),correct=sum(r['outcome']=='correct' for r in group),wrong=sum(r['outcome']=='wrong' for r in group),rejected=sum(r['outcome']=='rejected' for r in group),failed=sum(r['outcome']=='failed' for r in group),untested=sum(r['outcome']=='untested' for r in group)))
 report=dict(scope='Backend reference-clip test through localhost API plus real on-device JS classifier functions in Node. Python MediaPipe Holistic landmarks: not browser tracking, automatic capture timing, virtual-camera or physical-webcam testing. One reference clip per word/mode; training overlap possible. No thresholds tuned.',complete=len(results)==len(jobs),planned=len(jobs),processed=len(results),summaries=summaries,rows=results)
 temp=OUT/'results.tmp';temp.write_text(json.dumps(report,indent=2));temp.replace(OUT/'results.json')
 table=''.join('<tr>'+''.join(f'<td>{html.escape(str(r[k]))}</td>' for k in ['model','planned','tested','correct','wrong','rejected','failed','untested'])+'</tr>' for r in summaries)
 details=''.join('<tr>'+''.join(f'<td>{html.escape(str(r.get(k,"")))}</td>' for k in ['model','expected','predicted','outcome','error'])+'</tr>' for r in results)
 page=f'<!doctype html><html><meta charset="utf-8"><meta http-equiv="refresh" content="30"><title>HandSpeak word tests</title><style>body{{font:14px system-ui;background:#101912;color:#def3e5;padding:24px}}table{{border-collapse:collapse}}td,th{{padding:8px;border:1px solid #456}}a{{color:#6fda9c}}</style><a href="/#workspace">Back to HandSpeak</a><h1>Current website word-model reference tests</h1><p>{report["processed"]}/{report["planned"]} word/mode cases processed. Complete: {report["complete"]}</p><p>{html.escape(report["scope"])}</p><table><tr><th>Model</th><th>Planned</th><th>Tested</th><th>Correct</th><th>Wrong</th><th>Rejected</th><th>Failed</th><th>Untested</th></tr>{table}</table><h2>Per-word outcomes</h2><table><tr><th>Model</th><th>Expected</th><th>Predicted</th><th>Outcome</th><th>Error</th></tr>{details}</table></html>'
 (ROOT/'website-word-results.html').write_text(page,encoding='utf-8')
 return report
for job in jobs:
 row=dict(job);path=lookup.get(norm(job['expected']));variant=False
 if not path and job['model'].startswith('capstone-'):
  path=lookup.get(norm(re.sub(r'[12]$','',job['expected'])));variant=bool(path)
 if not path:row.update(predicted=None,outcome='untested',error='No matching labeled reference video available')
 else:
  try:
   data,sha=landmarks(path);row.update(file=str(path),sha256=sha,variant_not_verified=variant,extractedFrames=len(data['frames']))
   if job.get('endpoint'):
    if job['endpoint']=='/api/research-words':
     inp=OUT/'node-input.json';op=OUT/'node-output.json';inp.write_text(json.dumps(dict(data,mode='research-encode')))
     subprocess.run(['node',str(ROOT/'training/website_word_runner.mjs'),str(inp),str(op)],check=True,cwd=ROOT,capture_output=True)
     payload=dict(consent=True,**json.loads(op.read_text()))
    else:
     payload=dict(consent=True,frames=data['frames'])
     if job['vocabulary']:payload['vocabulary']=job['vocabulary']
     if job['vocabulary'] in ['target20','target20-passed']:
      payload['capture']=dict(complete=True,interrupted=False,durationMs=data['durationMs'])
    code,response=post(job['endpoint'],payload);row.update(http=code,response=response)
    prediction=response.get('label') if job['endpoint']=='/api/research-words' else next(iter(response.get('predictions',[])),{}).get('label')
    row['predicted']=prediction
    row['outcome']='failed' if code!=200 else 'correct' if prediction==job['expected'] else 'wrong' if prediction else 'rejected'
    if code!=200:row['error']=response.get('error','API failure')
   else:
    inp=OUT/'node-input.json';op=OUT/'node-output.json';inp.write_text(json.dumps(dict(data,**job)))
    run=subprocess.run(['node',str(ROOT/'training/website_word_runner.mjs'),str(inp),str(op)],check=True,cwd=ROOT,capture_output=True)
    response=json.loads(op.read_text());prediction=response['predicted'];row.update(response=response,predicted=prediction,outcome='correct' if prediction==job['expected'] else 'wrong' if prediction else 'rejected')
  except Exception as e:row.update(predicted=None,outcome='failed',error=str(e))
 results.append(row);save();print(f'{len(results)}/{len(jobs)} {row["model"]} {row["expected"]}: {row["outcome"]} {row.get("predicted")}',flush=True)
report=save()
with (OUT/'results.csv').open('w',newline='') as f:
 keys=['model','expected','predicted','outcome','error','file','sha256','variant_not_verified'];writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows({k:r.get(k) for k in keys} for r in results)
print(json.dumps(report['summaries'],indent=2),flush=True)
