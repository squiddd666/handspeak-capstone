import {createSceneMotion} from './scene-motion.js';
import {createWordBoundaries} from './word-boundaries.js?v=20261112-articulation-v2';
// Bounded, overlapping camera buffers preserve real pre-roll. No pixel replay,
// landmark injection, or expected word is supplied to either recognizer.
export function createAutomaticWordCapture({video,canWatch,onStart,onClip,onDiscard,onState,onDiagnostic,clock=()=>performance.now(),
 createRecorder=stream=>{const mime=['video/webm;codecs=vp8','video/webm','video/mp4'].find(type=>MediaRecorder.isTypeSupported(type));return new MediaRecorder(stream,{...(mime?{mimeType:mime}:{}),videoBitsPerSecond:750000});}}){
 const maxRecordingMs=8000,preRollMs=4200;
 let pool=[],capture=null,last=-Infinity,deadline=null,failed=false,blocked=false;
 const boundaries=createWordBoundaries(),sceneMotion=createSceneMotion();
 const state=text=>onState?.(text);
 function drop(entry){entry.keep=false;entry.chunks=[];if(entry.recorder.state==='recording')entry.recorder.stop();}
 function clearPool(){const entries=pool;pool=[];entries.forEach(drop);}
 function cancel(){clearTimeout(deadline);deadline=null;if(capture){const old=capture;capture=null;drop(old);}clearPool();boundaries.reset();sceneMotion.reset();last=-Infinity;failed=false;blocked=false;}
 function segment(now){
  const stream=video.srcObject;if(!stream?.getVideoTracks().some(t=>t.readyState==='live'))return null;
  const entry={recorder:createRecorder(stream),chunks:[],start:now,startedAt:clock(),startMediaTime:video.currentTime,keep:false,moves:0,firstMotion:0,lastMotion:0};
  entry.recorder.ondataavailable=e=>{if(e.data.size)entry.chunks.push(e.data);};
  entry.recorder.onerror=()=>{if(capture===entry){capture=null;clearTimeout(deadline);onDiscard?.('Automatic recording failed. Try again.');}drop(entry);};
  entry.recorder.onstop=()=>{
   if(!entry.keep){entry.chunks=[];return;}
   entry.keep=false;
   const blob=new Blob(entry.chunks,{type:entry.recorder.mimeType||'video/webm'});entry.chunks=[];
   onClip({blob,startMediaTime:entry.startMediaTime,endMediaTime:entry.endMediaTime??video.currentTime,token:entry.token,reason:entry.reason,boundaryQuality:entry.quality});
  };
  entry.recorder.start();return entry;
 }
 function reject(reason,alreadyReported=false){
  if(!alreadyReported)onDiagnostic?.({type:'reject',reason,mediaTime:video.currentTime,recordedMs:capture?clock()-capture.startedAt:0});
  clearTimeout(deadline);deadline=null;if(capture){const entry=capture;capture=null;drop(entry);}
  boundaries.abort(last,reason);clearPool();const message=reason==='maximum-duration-without-confirmed-end'?'No clear pause was detected before the recording limit. Keep your full hand visible, finish one sign, then hold the final pose.':'Capture incomplete ('+reason+'). Keep your full hand visible and try again.';onDiscard?.(message);
 }
 function stop(quality){
  if(!capture)return;
  const entry=capture;capture=null;clearTimeout(deadline);deadline=null;
  entry.reason='confirmed-end';entry.quality=quality;entry.endMediaTime=video.currentTime;
  if(entry.recorder.state==='recording')entry.recorder.stop();
 }
 function frame(hands,now){
  if(failed||now-last<70)return;last=now;
  if(!canWatch()&&!capture){clearPool();if(!blocked){boundaries.reset(true,now);sceneMotion.reset();}blocked=true;return;}
  blocked=false;
  const aspect=video.videoWidth?video.videoHeight/video.videoWidth:1;
  const event=boundaries.observe(hands,now,aspect,sceneMotion.sample(video,now,!boundaries.isActive()));
  if(event)onDiagnostic?.({...event,mediaTime:video.currentTime,now});
  if(capture){
   if(event?.type==='reject'){reject(event.reason,true);return;}
   if(event?.type==='end'){stop(event.quality);return;}
   if(clock()-capture.startedAt>=maxRecordingMs)reject('maximum-duration-without-confirmed-end');
   return;
  }
  if(!canWatch())return;
  // Overlap recorders, rotating once a second. Keep at most five short buffers.
  // Their bytes stay only in memory until a genuine moving sign is selected.
  if(!pool.length||clock()-pool[pool.length-1].startedAt>=1000){try{const entry=segment(now);if(entry)pool.push(entry);}catch(error){failed=true;clearPool();onDiscard?.('Automatic capture unavailable: '+error.message+'. Use Record a word.');return;}}
  while(pool.length>1&&clock()-pool[0].startedAt>preRollMs)drop(pool.shift());
  if(event?.type!=='start'||!pool.length)return;
  // Tracker initialization may finish in the middle of a gesture. Do not
  // submit a tail-only clip merely because onset was observed at startup.
  if(clock()-pool[0].startedAt<3000){
   boundaries.reset(true,now);
   onDiagnostic?.({type:'warmup-skipped',reason:'insufficient-pre-roll',mediaTime:video.currentTime});
   state('Camera warming up - pause, then start your sign again.');return;
  }
  const entry=pool.shift();clearPool();capture=entry;entry.keep=true;
  entry.firstMotion=event.onsetTime;
  try{entry.token=onStart({startMediaTime:entry.startMediaTime});}
  catch(error){capture=null;drop(entry);onDiscard?.(error.message);return;}
  state('Watching your sign - pause briefly when finished.');
  deadline=setTimeout(()=>reject('maximum-duration-without-confirmed-end'),Math.max(500,maxRecordingMs-(clock()-entry.startedAt)));
 }
 return {frame,cancel,waitForQuiet(now=performance.now()){boundaries.reset(true,now);},isCapturing:()=>Boolean(capture)};
}
