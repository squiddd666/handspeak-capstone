"""CC0 online static-image probe; not a webcam or signer-independent benchmark."""
import hashlib,json,os,string,zipfile
from pathlib import Path
import cv2,mediapipe as mp,numpy as np,quickjs,urllib.request
root=Path.cwd()
out=root/'reports/alphabet-architecture-20261111'
cache=Path(os.environ['TEMP']); archive=cache/'handspeak-rasband-test.zip'
model=cache/'handspeak-probe-hand-landmarker.task'
if not model.exists():urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',model)
js=quickjs.Context()
for name in ['gesture-model.js','letter-recognition.js']:
 js.eval('\n'.join(line for line in (root/name).read_text(encoding='utf8').splitlines() if not line.startswith('import ')).replace('export ',''))
js.eval('const m='+ (root/'models/asl-knn.json').read_text(encoding='utf8')+';')
opts=mp.tasks.vision.HandLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(model)),num_hands=1)
rows=[]
with zipfile.ZipFile(archive) as z,mp.tasks.vision.HandLandmarker.create_from_options(opts) as detector:
 for label in [c for c in string.ascii_uppercase if c not in 'JZ']+['nothing']:
  names=sorted(n for n in z.namelist() if n.startswith(label+'/') and n.lower().endswith('.jpg'))
  for n in [names[i] for i in [0,len(names)//2,len(names)-1]] if names else []:
   raw=z.read(n);a=cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR);h,w=a.shape[:2]
   k=min(640/w,480/h);a=cv2.resize(a,(round(w*k),round(h*k)));h,w=a.shape[:2]
   c=np.full((480,640,3),136,np.uint8);x=(640-w)//2;y=(480-h)//2;c[y:y+h,x:x+w]=cv2.cvtColor(a,cv2.COLOR_BGR2RGB)
   result=detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=c))
   pts=[dict(x=q.x,y=q.y,z=q.z)for q in result.hand_landmarks[0]] if result.hand_landmarks else None
   prediction=js.eval('classifyLetter('+json.dumps(pts)+',m.samples,m.parameters,.75)?.letter||null') if pts else None
   rows.append(dict(label=label,prediction=prediction,hand=bool(pts),file=n,sha256=hashlib.sha256(raw).hexdigest()))
report=dict(source='https://www.kaggle.com/danrasband/asl-alphabet-test',license='CC0',selection='First/middle/last filenames per class; no tuning; J/Z excluded because still images',scope='Python Tasks static image probe with actual JS classifier; not webcam or signer-independent',rows=rows)
(out/'online-static-probe.json').write_text(json.dumps(report,indent=2),encoding='utf8')
print(len(rows),sum(r['label']==r['prediction'] for r in rows),sum(bool(r['prediction']) and r['label']!=r['prediction'] for r in rows))
