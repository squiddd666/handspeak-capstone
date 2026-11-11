import {FilesetResolver,HandLandmarker} from 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/+esm';
import {isUsableHand} from './gesture-model.js';
import {motionFrame,encodeMotion} from './motion-model.js';
import {createAutomaticMotion} from './capture.js';
import {alignTemporalWindow} from './temporal-window.js';
import {bodyTipFeatures,residualMotionLogits} from './runtime.js';
const $=id=>document.getElementById(id),video=document.querySelector('video'),canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d');
const capture=createAutomaticMotion({sampleIntervalMs:30});
let hands,model,loading,stream,revision=0,raf=0,lastVideo=-1,delegate='',cameraInput='',times=[],events=[],lastCapture=null,rawHands=0,usableHands=0;
function fps(){return times.length>1?Math.round((times.length-1)*10000/(times.at(-1)-times[0]))/10:0;}
function report(){return {build:'20261004-ordinary-preview-1',scope:'Experimental preview; main recognizer unchanged',checkpoint:model?.checkpointSha256,cameraActive:Boolean(stream),expected:$('expected').value,input:cameraInput,delegate,processedFps:fps(),rawHands,usableHands,lastCapture,events};}
function stop(){revision++;cancelAnimationFrame(raf);stream?.getTracks().forEach(t=>t.stop());stream=null;video.srcObject=null;capture.reset();ctx.clearRect(0,0,canvas.width,canvas.height);$('start').disabled=false;$('stop').disabled=true;$('status').textContent='Camera stopped.';$('metrics').textContent=`Last measured rate: ${fps()} processed frames/sec`;}
async function load(){
 if(loading)return loading;
 loading=(async()=>{
  const [response,integrityResponse]=await Promise.all([fetch('./model.json'),fetch('./integrity.json')]);
  if(!response.ok||!integrityResponse.ok)throw Error('Model download failed.');
  const bytes=await response.arrayBuffer(),integrity=await integrityResponse.json();
  const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
  if(hash!==integrity.modelSha256)throw Error('Model verification failed. Reload the page.');
  model=JSON.parse(new TextDecoder().decode(bytes));
  if(model.featureMode!=='hands-only'||model.checkpointSha256!==integrity.checkpointSha256)throw Error('Model metadata mismatch.');
  const files=await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/wasm');
  const options={baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',delegate:'GPU'},runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.65,minHandPresenceConfidence:.65,minTrackingConfidence:.6};
  try{hands=await HandLandmarker.createFromOptions(files,options);delegate='GPU';}
  catch{options.baseOptions.delegate='CPU';hands=await HandLandmarker.createFromOptions(files,options);delegate='CPU';}
 })().catch(error=>{loading=null;throw error;});return loading;
}
function classify(frames,aspect){
 const sequence=encodeMotion(frames,aspect);
 if(!sequence)return {label:null,validSequence:false};
 const input=bodyTipFeatures(alignTemporalWindow({rawFrames:frames,body:frames.map(()=>null),imageAspect:aspect,sequence}));
 const scores=Array(model.outputLabels.length).fill(0);
 for(const weights of model.weights){const logits=residualMotionLogits(input,weights),max=Math.max(...logits),exp=logits.map(x=>Math.exp(x-max)),sum=exp.reduce((a,b)=>a+b,0);exp.forEach((x,i)=>scores[i]+=x/sum/model.weights.length);}
 const order=scores.map((_,i)=>i).sort((a,b)=>scores[b]-scores[a]),label=model.outputLabels[order[0]];
 const accepted=model.labels.includes(label)&&scores[order[0]]>=model.threshold&&scores[order[0]]-scores[order[1]]>=model.margin;
 return {label:accepted?label:null,validSequence:true};
}
function frame(version){
 if(version!==revision||!stream)return;
 try{
  if(video.readyState>=2&&video.currentTime!==lastVideo){
   lastVideo=video.currentTime;const now=performance.now(),detection=hands.detectForVideo(video,now);
   const indices=detection.landmarks.map((h,i)=>isUsableHand(h)?i:-1).filter(i=>i>=0);
   rawHands=detection.landmarks.length;usableHands=indices.length;
   const aspect=video.videoHeight/video.videoWidth;
   canvas.width=Math.min(640,video.videoWidth);canvas.height=Math.round(canvas.width*aspect);
   ctx.drawImage(video,0,0,canvas.width,canvas.height);ctx.fillStyle='#a2f7d2';
   for(const i of indices)for(const point of detection.landmarks[i]){ctx.beginPath();ctx.arc(point.x*canvas.width,point.y*canvas.height,3,0,Math.PI*2);ctx.fill();}
   times.push(now);times=times.filter(t=>now-t<2000);
   const clip=capture.push(motionFrame({landmarks:indices.map(i=>detection.landmarks[i]),handedness:indices.map(i=>detection.handedness[i])}),now,aspect);
   $('status').textContent=capture.isActive()?'Analyzing movement… finish the sign, then pause.':usableHands?'Hand detected — sign once, then pause.':'No hand detected — keep your hands in view.';
   if(clip){const started=performance.now(),result=classify(clip.frames,clip.imageAspect);
    lastCapture={frames:clip.frames.length,trackedFrames:clip.frames.filter(f=>f.some(Boolean)).length,durationMs:Math.round(now-clip.start),...result,classifierMs:Math.round(performance.now()-started)};
    events.push({...lastCapture,expected:$('expected').value});events=events.slice(-20);
    $('result').textContent=result.label?'Possible match: '+result.label:result.validSequence?'No reliable match':'Not enough clear hand frames';
   }
   $('metrics').textContent=`${fps()} processed frames/sec · ${usableHands} usable hand(s) · ${delegate} delegate`;
  }
  raf=requestAnimationFrame(()=>frame(version));
 }catch(error){stop();$('status').textContent='Recognition stopped: '+error.message;}
}
$('start').addEventListener('click',async()=>{
 const version=++revision;$('start').disabled=true;$('stop').disabled=false;$('status').textContent='Opening camera and loading recognizer…';
 try{
  const incoming=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:640},height:{ideal:480}},audio:false});
  if(version!==revision){incoming.getTracks().forEach(t=>t.stop());return;}
  stream=incoming;video.srcObject=stream;await video.play();cameraInput=video.videoWidth+'x'+video.videoHeight;await load();
  if(version!==revision)return;
  capture.reset();times=[];events=[];lastCapture=null;lastVideo=-1;$('result').textContent='Ready — sign once';frame(version);
 }catch(error){if(version===revision){stop();$('status').textContent=error.name==='NotAllowedError'?'Camera permission was denied. Allow camera access and try again.':'Unable to start: '+error.message;}}
});
$('stop').addEventListener('click',stop);
$('mirror').addEventListener('change',()=>canvas.classList.toggle('mirrored',$('mirror').checked));canvas.classList.add('mirrored');
$('expected').addEventListener('change',()=>{capture.reset();events=[];lastCapture=null;$('result').textContent='Ready — sign once';});
$('copy').addEventListener('click',async()=>{const text=JSON.stringify(report(),null,2);$('report').value=text;$('report').hidden=false;try{await navigator.clipboard.writeText(text);$('copyStatus').textContent='Report copied. Paste it into the project chat.';}catch{$('copyStatus').textContent='Select and copy the report below.';$('report').focus();$('report').select();}});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();});window.addEventListener('pagehide',stop);
$('start').disabled=false;$('status').textContent='Select your camera or OBS Virtual Camera when your browser asks.';
