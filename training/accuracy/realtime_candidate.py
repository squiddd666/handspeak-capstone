import json,sys
from pathlib import Path
import torch
from playwright.sync_api import sync_playwright
ROOT=Path('/opt/handspeak-training/accuracy-v4')
old=json.loads(Path('/opt/handspeak-training/popsign/manifest.json').read_text());videos={name:Path('/opt/handspeak/asl-examples')/(name+'.mp4') for name in ['hello','thank-you','please','yes','no']};videos['finish']=Path(next(r['file'] for r in old if r['split']=='train' and r['label']=='FINISH'))
saved=torch.load(ROOT/'temporal-candidate.pt',map_location='cpu',weights_only=True);payload=dict(weights={k:v.tolist() for k,v in saved['state'].items()},config=saved['config'])
with sync_playwright() as p:
 browser=p.chromium.launch(args=['--no-sandbox']);page=browser.new_page();page.set_default_timeout(180000)
 def serve(route):
  name=route.request.url.split('/')[-1].removesuffix('.mp4');data=videos[name].read_bytes();header=route.request.headers.get('range')
  if header:
   start,end=header.removeprefix('bytes=').split('-');start=int(start);end=min(int(end) if end else len(data)-1,len(data)-1);route.fulfill(status=206,content_type='video/mp4',headers={'Accept-Ranges':'bytes','Content-Range':f'bytes {start}-{end}/{len(data)}'},body=data[start:end+1])
  else:route.fulfill(content_type='video/mp4',headers={'Accept-Ranges':'bytes'},body=data)
 page.route('**/candidate-audit/*.mp4',serve);page.goto('https://handspeak.cvsu.dev',wait_until='domcontentloaded')
 page.evaluate('''async data=>{
 window.candidateData=data;const v=await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/+esm');const f=await v.FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/wasm');
 window.handAudit=await v.HandLandmarker.createFromOptions(f,{baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',delegate:'CPU'},runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.65,minHandPresenceConfidence:.65,minTrackingConfidence:.6});
 window.poseAudit=await v.PoseLandmarker.createFromOptions(f,{baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task',delegate:'CPU'},runningMode:'IMAGE',numPoses:1,minPoseDetectionConfidence:.5,minPosePresenceConfidence:.5});
 }''',payload)
 reports=[]
 for name in videos:
  report=page.evaluate('''async name=>{
   const {motionFrame,encodeMotion,recognizeMotion}=await import('./motion-model.js?v=20261001-auto-cache-1');const {isUsableHand}=await import('./gesture-model.js?v=20261001-auto-cache-1');const {createAutomaticMotion}=await import('./automatic-motion.js?v=20261001-auto-cache-1');const {temporalFeatures,temporalLogits}=await import('./training/accuracy/temporal-browser.js');
   const baseline=await(await fetch('./models/asl-words.json')).json();const segmenter=createAutomaticMotion();
   const video=document.createElement('video');video.muted=true;video.playsInline=true;video.src='/candidate-audit/'+name+'.mp4';await new Promise((r,j)=>{video.onloadedmetadata=r;video.onerror=j});
   const canvas=document.createElement('canvas');canvas.width=480;canvas.height=640;const ctx=canvas.getContext('2d');const small=document.createElement('canvas');small.width=240;small.height=320;const sc=small.getContext('2d');const images=new Map(),suggestions=[],latencies=[];
   for(let i=0;i<4;i++)handAudit.detectForVideo(new ImageData(480,640),performance.now());
   const start=performance.now();await video.play();let end=null,last=-Infinity,lastVideo=-1,frames=0;
   await new Promise((resolve,reject)=>{
    function tick(){try{
     const now=performance.now();if(video.ended&&end===null)end=now;
     if(end!==null&&now-end>3000){resolve();return;}
     if(now-last>=80&&(video.currentTime!==lastVideo||video.ended)){
      last=now;lastVideo=video.currentTime;ctx.fillStyle='black';ctx.fillRect(0,0,480,640);if(!video.ended)ctx.drawImage(video,0,0,480,640);
      const began=performance.now();const d=handAudit.detectForVideo(ctx.getImageData(0,0,480,640),now);latencies.push(performance.now()-began);frames++;
      const ids=d.landmarks.map((h,i)=>isUsableHand(h)?i:-1).filter(i=>i>=0);const frame=motionFrame({landmarks:ids.map(i=>d.landmarks[i]),handedness:ids.map(i=>d.handedness[i])});
      sc.drawImage(canvas,0,0,240,320);images.set(frame,sc.getImageData(0,0,240,320));while(images.size>64)images.delete(images.keys().next().value);
      const clip=segmenter.push(frame,now,4/3);
      if(clip){
       const begin=performance.now(),middle=images.get(clip.frames[Math.floor(clip.frames.length/2)]);const pose=middle?poseAudit.detect(middle).landmarks[0]:null;const body=pose?[0,11,12,13,14].map(i=>pose[i]):null;
       const logits=temporalLogits(temporalFeatures({rawFrames:clip.frames,body:clip.frames.map(()=>body),imageAspect:4/3}),candidateData.weights);const max=Math.max(...logits),exp=logits.map(x=>Math.exp(x-max)),sum=exp.reduce((a,b)=>a+b,0),probs=exp.map(x=>x/sum),order=probs.map((_,i)=>i).sort((a,b)=>probs[b]-probs[a]),best=order[0];
       const labels=['HELLO','THANK YOU','PLEASE','YES','NO','FINISH','UNKNOWN'];const candidate=best<6&&probs[best]>=candidateData.config.threshold&&probs[best]-probs[order[1]]>=candidateData.config.margin?labels[best]:null;
       const candidateMs=performance.now()-begin;const sequence=encodeMotion(clip.frames,4/3);const base=sequence?recognizeMotion(sequence,baseline.samples,baseline.parameters)?.label||null:null;
       suggestions.push({timeMs:now-start,candidate,baseline:base,candidateIncludingPoseMs:candidateMs,bodyFound:!!body,samples:clip.frames.length});
      }
     }
     requestAnimationFrame(tick);
    }catch(e){reject(e);}}
    requestAnimationFrame(tick);
   });
   latencies.sort((a,b)=>a-b);return {name,durationMs:video.duration*1000,wallPlaybackMs:end-start,frames,handInferenceP95Ms:latencies[Math.floor(latencies.length*.95)],suggestions};
  }''',name)
  reports.append(report);print(json.dumps(report),flush=True)
 (ROOT/'realtime-candidate.json').write_text(json.dumps({'method':'Normal-speed video playback at real wall-clock timing, CPU hand tracker, automatic segmenter, center-frame Pose Landmarker and frozen temporal model. Bounded in-memory image thumbnails only. Also evaluates baseline on identical captured hand segments. Training-video functional benchmark; not a physical-webcam accuracy test. This is an evaluation harness, not a deployed replacement.','results':reports},indent=2));browser.close()
