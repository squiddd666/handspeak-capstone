"""Cache hand, upper-body landmarks and source timestamps outside the website."""
import json,sys
from pathlib import Path
import cv2,numpy as np,mediapipe as mp,quickjs
from concurrent.futures import ProcessPoolExecutor
ROOT=Path('/opt/handspeak-training/accuracy-v4');SITE=Path(__file__).resolve().parents[2]
def extract(row):
 cv2.setNumThreads(1);out=ROOT/'features'/row['split']/(Path(row['file']).stem+'.json');out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():
  record=json.loads(out.read_text());record['body']=[record['body'][len(record['body'])//2]]*len(record['body']);record['bodyMode']='center-frame reference';out.write_text(json.dumps(record,separators=(',',':')));return record
 js=quickjs.Context()
 for name in ['gesture-model.js','motion-model.js']:js.eval((SITE/name).read_text().replace('export ',''))
 old=Path(row['file']).with_suffix('.landmarks.json');cached=json.loads(old.read_text()) if old.exists() else None
 cap=cv2.VideoCapture(row['file'],cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1]);n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=cap.get(cv2.CAP_PROP_FPS)
 options=mp.tasks.vision.HandLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path='/opt/handspeak-training/hand_landmarker.task'),running_mode=mp.tasks.vision.RunningMode.VIDEO,num_hands=2,min_hand_detection_confidence=.65,min_hand_presence_confidence=.65,min_tracking_confidence=.6)
 if cached and len(cached.get('rawFrames',[]))==30:
  selected=np.unique(np.linspace(0,max(0,n-1),30).astype(int));cap.set(cv2.CAP_PROP_POS_FRAMES,int(selected[len(selected)//2]));ok,bgr=cap.read();pose_points=None
  if ok:
   h,w=bgr.shape[:2];factor=min(1,640/max(h,w));rgb=cv2.cvtColor(cv2.resize(bgr,(round(w*factor),round(h*factor))),cv2.COLOR_BGR2RGB)
   with mp.solutions.pose.Pose(static_image_mode=True,model_complexity=1,enable_segmentation=False,min_detection_confidence=.5) as pose:
    body=pose.process(rgb).pose_landmarks
    if body:pose_points=[dict(x=p.x,y=p.y,z=p.z,visibility=p.visibility) for j,p in enumerate(body.landmark) if j in [0,11,12,13,14]]
  cap.release();result={**row,'rawFrames':cached['rawFrames'],'body':[pose_points]*30,'bodyMode':'center-frame reference','timestamps':[round(int(i)/max(1,fps)*1000) for i in selected],'durationMs':n/max(1,fps)*1000,'imageAspect':cached['imageAspect'],'sequence':cached['sequence']};out.write_text(json.dumps(result,separators=(',',':')));return result
 hands=[];poses=[];times=[];aspect=1;last_body=None
 with mp.tasks.vision.HandLandmarker.create_from_options(options) as detector,mp.solutions.pose.Pose(static_image_mode=True,model_complexity=1,enable_segmentation=False,min_detection_confidence=.5,min_tracking_confidence=.5) as pose:
  selected=set(np.unique(np.linspace(0,max(0,n-1),30).astype(int)))
  for i in range(n):
   if not cap.grab():break
   if i not in selected:continue
   ok,bgr=cap.retrieve()
   if not ok:continue
   h,w=bgr.shape[:2];aspect=h/w;factor=min(1,640/max(h,w));rgb=cv2.cvtColor(cv2.resize(bgr,(round(w*factor),round(h*factor))),cv2.COLOR_BGR2RGB);timestamp=round(i/max(1,fps)*1000)
   if cached and len(cached['rawFrames'])>len(hands):frame=cached['rawFrames'][len(hands)]
   else:
    result=detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=rgb),timestamp)
    d={'landmarks':[[dict(x=p.x,y=p.y,z=p.z) for p in ps] for ps in result.hand_landmarks],'handedness':[[{'categoryName':h.category_name} for h in hs] for hs in result.handedness]}
    js.eval('var d='+json.dumps(d)+';');frame=json.loads(js.eval('JSON.stringify(motionFrame({landmarks:d.landmarks.filter(isUsableHand),handedness:d.handedness.filter((_,i)=>isUsableHand(d.landmarks[i]))}))'))
   if len(hands)==15:
    body=pose.process(rgb).pose_landmarks
    last_body=[dict(x=p.x,y=p.y,z=p.z,visibility=p.visibility) for j,p in enumerate(body.landmark) if j in [0,11,12,13,14]] if body else None
   poses.append(last_body)
   hands.append(frame);times.append(timestamp)
 cap.release()
 sequence=json.loads(js.eval('JSON.stringify(encodeMotion('+json.dumps(hands)+','+str(aspect)+'))'))
 result={**row,'rawFrames':hands,'body':[last_body]*len(hands),'bodyMode':'center-frame reference','timestamps':times,'bodyStride':3,'durationMs':n/max(1,fps)*1000,'imageAspect':aspect,'sequence':sequence}
 out.write_text(json.dumps(result,separators=(',',':')));return result
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--test',action='store_true');args=p.parse_args()
 if args.test:rows=json.loads((ROOT/'fresh-test-manifest.json').read_text())
 else:
  old=json.loads(Path('/opt/handspeak-training/popsign/manifest.json').read_text());rows=[dict(r,kind='unsupported' if r['label']=='DRINK' else 'supported') for r in old if r['split']!='test']+json.loads((ROOT/'development-manifest.json').read_text())
 for r in rows:r['label']='THANK YOU' if r['label']=='THANKYOU' else r['label']
 result=[]
 with ProcessPoolExecutor(max_workers=2) as pool:
  for row in pool.map(extract,rows):
   result.append(row)
   if len(result)%12==0:print('Extracted',len(result),'/',len(rows),flush=True)
 (ROOT/('test-features.json' if args.test else 'development-features.json')).write_text(json.dumps(result,separators=(',',':')))
 print('Complete',len(result),flush=True)
