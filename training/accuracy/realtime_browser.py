"""Play source videos at wall-clock speed through the deployed camera path.
A virtual camera benchmark, not a physical-webcam/user-signing evaluation.
"""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path('/opt/handspeak-training/accuracy-v4')
p=argparse.ArgumentParser();p.add_argument('--cpu',action='store_true');p.add_argument('--only');args=p.parse_args()
old=json.loads(Path('/opt/handspeak-training/popsign/manifest.json').read_text());videos={name:Path('/opt/handspeak/asl-examples')/(name+'.mp4') for name in ['hello','thank-you','please','yes','no']};videos['finish']=Path(next(r['file'] for r in old if r['split']=='train' and r['label']=='FINISH'))
with sync_playwright() as p:
 browser=p.chromium.launch(args=['--no-sandbox']);page=browser.new_page();page.set_default_timeout(120000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 def serve(route):
  name=route.request.url.split('/')[-1].removesuffix('.mp4');data=videos[name].read_bytes();header=route.request.headers.get('range')
  if header:
   start,end=header.removeprefix('bytes=').split('-');start=int(start);end=min(int(end) if end else len(data)-1,len(data)-1);route.fulfill(status=206,content_type='video/mp4',headers={'Accept-Ranges':'bytes','Content-Range':f'bytes {start}-{end}/{len(data)}'},body=data[start:end+1])
  else:route.fulfill(content_type='video/mp4',headers={'Accept-Ranges':'bytes'},body=data)
 page.route('**/realtime-audit/*.mp4',serve)
 page.add_init_script('''window.audit={latencies:[],events:[]};navigator.mediaDevices.getUserMedia=async()=>{
 const canvas=document.createElement('canvas');canvas.width=480;canvas.height=640;const ctx=canvas.getContext('2d');window.auditCanvas=canvas;window.auditVideo=document.createElement('video');auditVideo.muted=true;auditVideo.playsInline=true;
 setInterval(()=>{ctx.fillStyle='black';ctx.fillRect(0,0,480,640);if(auditVideo.readyState>=2&&!auditVideo.ended)ctx.drawImage(auditVideo,0,0,480,640);},33);
 return canvas.captureStream(30);};''')
 page.goto('https://handspeak.cvsu.dev',wait_until='domcontentloaded');page.wait_for_function("document.querySelector('#motionModelStatus').textContent.includes('6 pretrained')")
 page.uncheck('#faceTrackingToggle');page.select_option('#recognitionMode','words')
 page.evaluate('''async cpu=>{const vision=await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/+esm');const original=vision.HandLandmarker.createFromOptions.bind(vision.HandLandmarker);vision.HandLandmarker.createFromOptions=async(files,options)=>{
 if(cpu)options.baseOptions.delegate='CPU';const detector=await original(files,options),detect=detector.detectForVideo.bind(detector);detector.detectForVideo=(video,time)=>{const start=performance.now(),r=detect(video,time);audit.latencies.push(performance.now()-start);return r;};return detector;};
 const el=document.querySelector('#liveLetter');window.auditObserver=new MutationObserver(()=>audit.events.push({text:el.textContent,time:performance.now()}));auditObserver.observe(el,{childList:true,subtree:true,characterData:true});}''',args.cpu)
 page.click('#cameraButton');page.wait_for_function("document.querySelector('#cameraStatus').textContent.includes('Live')")
 results=[]
 for name in ([args.only] if args.only else videos):
  # Reset automatic state, let the tracker see a blank interval, then play once.
  page.evaluate("document.querySelector('#automaticWords').checked=false;document.querySelector('#automaticWords').dispatchEvent(new Event('change'))")
  page.wait_for_timeout(1000)
  result=page.evaluate('''async name=>{
   auditVideo.src='/realtime-audit/'+name+'.mp4';await new Promise((r,j)=>{auditVideo.onloadedmetadata=r;auditVideo.onerror=j});
   audit.latencies=[];audit.events=[];const start=performance.now();document.querySelector('#automaticWords').checked=true;document.querySelector('#automaticWords').dispatchEvent(new Event('change'));
   await auditVideo.play();await new Promise(r=>auditVideo.onended=r);const end=performance.now();await new Promise(r=>setTimeout(r,2500));
   const timings=audit.latencies.slice().sort((a,b)=>a-b);return {name,durationMs:auditVideo.duration*1000,wallPlaybackMs:end-start,processingFrames:audit.latencies.length,inferenceP95Ms:timings[Math.floor(timings.length*.95)],inferenceMedianMs:timings[Math.floor(timings.length*.5)],events:audit.events.map(e=>({...e,time:e.time-start})),status:document.querySelector('#motionCaptureStatus').textContent};
  }''',name)
  expected=name.upper().replace('-',' ');suggestions=[e for e in result['events'] if e['text'] in ['HELLO','THANK YOU','PLEASE','YES','NO','FINISH']];result.update(expected=expected,correct=any(e['text']==expected for e in suggestions),wrong=sum(e['text']!=expected for e in suggestions),repeated=max(0,len(suggestions)-len({e['text'] for e in suggestions})));results.append(result);print(json.dumps(result),flush=True)
 page.evaluate("document.querySelector('#cameraButton').click()")
 report={'method':'Real-time video playback into 480x640 canvas captureStream, deployed camera processing and automatic segmentation, face tracking off. No frame-by-frame seeking. Source examples are training clips, not independent accuracy data. Not a physical webcam.','delegate':'CPU forced for benchmark' if args.cpu else 'Application default GPU/fallback','results':results,'pageErrors':errors}
 (ROOT/('realtime-'+('cpu' if args.cpu else 'default')+('-'+args.only if args.only else '')+'.json')).write_text(json.dumps(report,indent=2));browser.close()
