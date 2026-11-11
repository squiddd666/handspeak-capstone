"""Development-only detector and classifier diagnostics on exposed photos."""
import cv2,mediapipe as mp,numpy as np,quickjs
import json,os,time,queue
from pathlib import Path
root=Path(__file__).resolve().parents[1]
asset=Path(os.environ['TEMP'])/'handspeak-probe-hand-landmarker.task'
js=quickjs.Context()
for n in ('gesture-model.js','letter-recognition.js'):
 js.eval('\n'.join(l for l in (root/n).read_text(encoding='utf8').splitlines() if not l.startswith('import ')).replace('export ',''))
js.eval('const model='+ (root/'models/asl-knn.json').read_text()+';')
rows=[]
for letter in 'AKORSUVX5':
 src=cv2.imread(str(root/f'media/letters/{letter.lower()}.jpg'));h,w=src.shape[:2]
 for width in (320,640,960):
  height=width*3//4;k=min(width/w,height/h)
  im=cv2.resize(src,(round(w*k),round(h*k)));ih,iw=im.shape[:2]
  canvas=np.full((height,width,3),136,np.uint8);x,y=(width-iw)//2,(height-ih)//2
  canvas[y:y+ih,x:x+iw]=im
  img=mp.Image(image_format=mp.ImageFormat.SRGB,data=cv2.cvtColor(canvas,cv2.COLOR_BGR2RGB))
  for mode in ('IMAGE','VIDEO','LIVE_STREAM'):
   deliveries=queue.Queue()
   opts=mp.tasks.vision.HandLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(asset)),running_mode=getattr(mp.tasks.vision.RunningMode,mode),
      result_callback=(lambda result,image,ts:deliveries.put((result,ts))) if mode=='LIVE_STREAM' else None)
   with mp.tasks.vision.HandLandmarker.create_from_options(opts) as d:
    for i in range(1 if mode=='IMAGE' else 6):
     # Repeated still pixels exercise detector initialization and tracking only.
     # Never pass this fixture to the motion matcher.
     start=time.perf_counter()
     if mode=='LIVE_STREAM':
      d.detect_async(img,i*67)
      r,ts=deliveries.get(timeout=10)
      assert ts==i*67
     else:r=d.detect(img) if mode=='IMAGE' else d.detect_for_video(img,i*67)
     elapsed=(time.perf_counter()-start)*1000
     pts=[dict(x=p.x,y=p.y,z=p.z)for p in r.hand_landmarks[0]]if r.hand_landmarks else []
     result=js.eval('JSON.stringify((()=>{const votes=[];const points='+json.dumps(pts)+''';const usable=isUsableLetterHand(points,.75);
      const result=usable?classifyLetter(points,model.samples,model.parameters,.75,v=>votes.push(v)):null;
      return {usable,result,votes,reason:usable?(votes[votes.length-1]?.reason||'unavailable'):(points.length?'unusable-landmarks':'no-landmarks')};})())''')
     rows.append(dict(letter=letter,sourceSize=[w,h],input=[width,height],mode=mode,frame=i,raw=len(r.hand_landmarks),handedness=r.handedness[0][0].category_name if pts else None,detectorMs=elapsed,**json.loads(result)))
out=root/'reports/alphabet-phase5/detector-modes.json'
out.write_text(json.dumps(dict(scope='Native detector, exposed static photos, fresh task per case; repeated still frames only test detector behavior',rows=rows),indent=2))
print(len(rows))

