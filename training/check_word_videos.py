from pathlib import Path
import argparse,hashlib
from playwright.sync_api import sync_playwright
import json
parser=argparse.ArgumentParser(description='Functional browser replay of five labeled example videos; not an accuracy benchmark.')
parser.add_argument('--videos',type=Path,default=Path('/opt/handspeak/asl-examples'))
parser.add_argument('--output',type=Path,default=Path('/opt/handspeak-training/browser-word-v3-audit.json'))
args=parser.parse_args()
with sync_playwright() as p:
 b=p.chromium.launch(args=['--no-sandbox']);page=b.new_page();page.set_default_timeout(120000)
 def serve_video(route):
  data=(args.videos/route.request.url.split('/')[-1]).read_bytes();header=route.request.headers.get('range')
  if header:
   start,end=header.removeprefix('bytes=').split('-');start=int(start);end=min(int(end) if end else len(data)-1,len(data)-1)
   route.fulfill(status=206,content_type='video/mp4',headers={'Accept-Ranges':'bytes','Content-Range':f'bytes {start}-{end}/{len(data)}'},body=data[start:end+1])
  else:route.fulfill(content_type='video/mp4',headers={'Accept-Ranges':'bytes'},body=data)
 page.route('**/word-test/*.mp4',serve_video)
 page.goto('http://localhost:8000',wait_until='domcontentloaded')
 page.evaluate('''async()=>{
 const vision=await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/+esm');
 const files=await vision.FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/wasm');
 window.auditDetector=await vision.HandLandmarker.createFromOptions(files,{baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',delegate:'CPU'},runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.65,minHandPresenceConfidence:.65,minTrackingConfidence:.6});window.auditTime=0;
 }''')
 reports=[]
 for name in ['hello','thank-you','please','yes','no']:
  report=page.evaluate('''async name=>{
   const {motionFrame,encodeMotion,recognizeMotion,motionDistance}=await import('./motion-model.js');
   const {isUsableHand}=await import('./gesture-model.js');const model=await(await fetch('./models/asl-words.json')).json();
   const video=document.createElement('video');video.muted=true;video.src='/word-test/'+name+'.mp4';await new Promise((resolve,reject)=>{video.onloadedmetadata=resolve;video.onerror=reject});
   const blank=new ImageData(480,640);for(let k=0;k<4;k++){window.auditTime+=100;window.auditDetector.detectForVideo(blank,window.auditTime);}
   const canvas=document.createElement('canvas');const ratio=640/Math.max(video.videoWidth,video.videoHeight);canvas.width=Math.round(video.videoWidth*ratio);canvas.height=Math.round(video.videoHeight*ratio);const ctx=canvas.getContext('2d');let frames=[];
   for(let i=0;i<30;i++){
    const target=Math.max(.001,(video.duration-.04)*i/29);await new Promise(resolve=>{video.onseeked=resolve;video.currentTime=target;});if(Math.abs(video.currentTime-target)>.05)throw Error("Video seek did not reach target: "+video.currentTime+" vs "+target);
    ctx.drawImage(video,0,0,canvas.width,canvas.height);window.auditTime+=100;
    const d=window.auditDetector.detectForVideo(ctx.getImageData(0,0,canvas.width,canvas.height),window.auditTime);const ids=d.landmarks.map((p,i)=>isUsableHand(p)?i:-1).filter(i=>i>=0);
    frames.push(motionFrame({landmarks:ids.map(i=>d.landmarks[i]),handedness:ids.map(i=>d.handedness[i])}));
   }
   const sequence=encodeMotion(frames,video.videoHeight/video.videoWidth);return {name,tracked:frames.filter(f=>f.some(Boolean)).length,valid:!!sequence,prediction:sequence?recognizeMotion(sequence,model.samples,model.parameters):null,rawFrames:frames,imageAspect:video.videoHeight/video.videoWidth};
  }''',name)
  report['expected']=name.upper().replace('-',' ');report['sha256']=hashlib.sha256((args.videos/(name+'.mp4')).read_bytes()).hexdigest();reports.append(report);print(json.dumps({k:v for k,v in report.items() if k!='rawFrames'}),flush=True)
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(reports))
 assert all(r['prediction'] and r['prediction']['label']==r['expected'] for r in reports),'One or more example videos did not match; inspect the output report'
 b.close()
