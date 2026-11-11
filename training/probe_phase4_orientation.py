"""Paired native MediaPipe framing probe, not independent validation."""
import cv2, mediapipe as mp, quickjs, numpy as np
from pathlib import Path
import hashlib,json,os,time
root=Path(__file__).resolve().parents[1]
task=Path(os.environ['TEMP'])/'handspeak-probe-hand-landmarker.task'
j=quickjs.Context()
for n in ('gesture-model.js','letter-recognition.js'):
 j.eval('\n'.join(l for l in (root/n).read_text(encoding='utf8').splitlines() if not l.startswith('import ')).replace('export ',''))
j.eval('const model='+ (root/'models/asl-knn.json').read_text()+';')
rows=[]
with mp.tasks.vision.HandLandmarker.create_from_options(mp.tasks.vision.HandLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(task)),num_hands=1)) as d:
 for letter in 'AKORSUVX5':
  src=cv2.imread(str(root/f'media/letters/{letter.lower()}.jpg'));h,w=src.shape[:2]
  k=min(640/w,480/h);im=cv2.resize(src,(round(w*k),round(h*k)));ih,iw=im.shape[:2]
  canvas=np.full((480,640,3),136,np.uint8);x,y=(640-iw)//2,(480-ih)//2
  canvas[y:y+ih,x:x+iw]=im
  for angle in (-25,-15,0,15,25):
   for mirror in (False,True):
    name=f'{angle}:{mirror}';region=(0,0,640,480)
    M=cv2.getRotationMatrix2D((320,240),angle,1)
    frame=cv2.warpAffine(canvas,M,(640,480),borderValue=(136,136,136))
    if mirror:frame=cv2.flip(frame,1)
    frame=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)
    inverse=cv2.invertAffineTransform(M)
    def restore(q):
     x,y=inverse @ [639-q.x*640 if mirror else q.x*640,q.y*480,1]
     return dict(x=x/640,y=y/480,z=q.z)
    s=time.perf_counter();r=d.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=frame));ms=(time.perf_counter()-s)*1000
    p=[restore(q) for q in r.hand_landmarks[0]] if r.hand_landmarks else []
    payload=json.dumps(p)
    usable=bool(p) and j.eval('isUsableLetterHand('+payload+',.75)')
    s=time.perf_counter();pred=j.eval('classifyLetter('+payload+',model.samples,model.parameters,.75)?.letter||null') if usable else None
    span=[max(q[k] for q in p)-min(q[k] for q in p) for k in 'xy'] if p else None
    rows.append(dict(letter=letter,region=name,roi=region,sourceSize=[w,h],detected=bool(p),usable=usable,span=span,side=r.handedness[0][0].category_name if p else None,points=p,prediction=pred,detectorMs=ms,classifierMs=(time.perf_counter()-s)*1000 if usable else None))
out=root/'reports/alphabet-phase4/orientation.json'
out.write_text(json.dumps(dict(scope='Native IMAGE probe on exposed regression media; rotation can clip hands and are not acceptance inputs',modelSha256=hashlib.sha256(task.read_bytes()).hexdigest(),rows=rows),indent=2))
for l in 'KORSUVX5':print(l,[(r['region'],r['usable'],r['prediction']) for r in rows if r['letter']==l])
