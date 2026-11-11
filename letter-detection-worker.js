// Single real frame in flight. No queued replay or fabricated observations.
let imageDetector,videoDetector,vision,files,onnx=null,samples=[],parameters,modelVersion=0;
let classifyLetter,isUsableLetterHand,sameObservedHand,validSample,validParameters,tracks=[],lastAnchor=-Infinity,lastFrame=-Infinity,searchIndex=0;
const TASKS='0.10.22-rc.20250304';
let pixelsCanvas=null;
let preserveUsableMotion=false;
let stableMotionGate=false;
const options=mode=>({baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',delegate:'CPU'},runningMode:mode,numHands:1,minHandDetectionConfidence:.5,minHandPresenceConfidence:.5,minTrackingConfidence:.5});
let baseSamples=[],allowed=[];
function personal(rows){samples=baseSamples.concat((rows||[]).filter(r=>validSample(r,allowed)));modelVersion++;tracks=[];}
self.onmessage=async({data})=>{
 try{
  if(data.type==='init'){
   const start=performance.now();
   stableMotionGate=data.recovery==='stable-palm';
   preserveUsableMotion=data.recovery==='continuity'||stableMotionGate;
   ({classifyLetter,isUsableLetterHand,sameObservedHand}=await import('./letter-recognition.js?v=20261111-architecture-2'));
   ({validSample,validParameters}=await import('./gesture-model.js?v=20261109-static-alphabet-v2'));
   vision=await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@'+TASKS+'/+esm');
   files=await vision.FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@'+TASKS+'/wasm');
   imageDetector=await vision.HandLandmarker.createFromOptions(files,options('IMAGE'));
   const m=await(await fetch('./models/asl-knn.json')).json();if(m.version!==2||m.normalization!=='wrist-palm-orientation-v2'||!Array.isArray(m.labels)||!Array.isArray(m.samples)||!m.samples.every(s=>validSample(s,m.labels))||!validParameters(m.parameters))throw Error('Invalid letter reference model');baseSamples=m.samples;parameters=m.parameters;allowed=[...m.labels,'5'];personal(data.personalSamples);
   try{
    const {createOnnxHandDetector}=await import('./onnx-hand-detector.js?v=20261111-architecture-2');
    onnx=await createOnnxHandDetector({modelBase:new URL('./models/hand-landmarks/',self.location.href).href});
   }catch(error){self.postMessage({type:'warning',message:'ONNX recovery unavailable: '+error.message});}
   self.postMessage({type:'ready',delegate:'CPU worker',onnx:Boolean(onnx),modelVersion,initializationMs:performance.now()-start});return;
  }
  if(data.type==='personal'){personal(data.samples);self.postMessage({type:'model',modelVersion});return;}
  if(data.type!=='frame')return;
  const bitmap=data.bitmap,version=modelVersion,started=performance.now(),aspect=bitmap.height/bitmap.width;
  if(!pixelsCanvas||pixelsCanvas.width!==bitmap.width||pixelsCanvas.height!==bitmap.height)pixelsCanvas=new OffscreenCanvas(bitmap.width,bitmap.height);
  const pixelsContext=pixelsCanvas.getContext('2d',{willReadFrequently:true});pixelsContext.drawImage(bitmap,0,0);
  const imageData=pixelsContext.getImageData(0,0,bitmap.width,bitmap.height);
  let lo=255,hi=0;for(let i=0;i<imageData.data.length;i+=256){const v=(imageData.data[i]+imageData.data[i+1]+imageData.data[i+2])/3;lo=Math.min(lo,v);hi=Math.max(hi,v);}
  if(hi-lo<8){tracks=[];lastFrame=data.timestamp;bitmap.close();self.postMessage({type:'frame',id:data.id,modelVersion:version,timestamp:data.timestamp,capturedAt:data.capturedAt,imageAspect:aspect,landmarks:[],staticResult:null,motionHands:[],quality:[],timings:{primaryMs:0,videoMs:0,recoveryMs:0,classifierMs:0},inferencePerformed:false,inferenceMs:performance.now()-started});return;}

  const timings={primaryMs:0,videoMs:0,recoveryMs:0,classifierMs:0};
  const usable=p=>isUsableLetterHand(p,aspect);
  const classify=p=>{const t=performance.now(),r=classifyLetter(p,samples,parameters,aspect);timings.classifierMs+=performance.now()-t;return r;};
  const choose=d=>{const h=(d.landmarks||[]).filter(usable),r=h.map(classify),ids=r.map((v,i)=>v?i:-1).filter(i=>i>=0);return ids.length===1?{points:h[ids[0]],result:r[ids[0]]}:null;};
  let detection={landmarks:[]},staticResult=null,motionHands=[],quality=[],trackedResult=null;
  try{
   if(data.timestamp<=lastFrame||data.timestamp-lastFrame>500)tracks=[];
   lastFrame=data.timestamp;
   if(onnx&&tracks.length){
    const t=performance.now(),next=[];
    for(const p of tracks){const d=await onnx.track(bitmap,p);if(d.landmarks[0]&&usable(d.landmarks[0])){next.push(d.landmarks[0]);quality.push(d.quality[0]);}}
    timings.recoveryMs+=performance.now()-t;tracks=next;
    if(next.length){trackedResult={landmarks:next};motionHands=next;const c=choose(trackedResult);detection={landmarks:c?[c.points]:next};staticResult=c?.result||null;}
   }
   if(!trackedResult||data.timestamp-lastAnchor>=500){
    const t=performance.now(),primary=imageDetector.detect(imageData);timings.primaryMs=performance.now()-t;lastAnchor=data.timestamp;
    const c=choose(primary);
    if(c){detection={...primary,landmarks:[c.points]};staticResult=c.result;tracks=[];motionHands=primary.landmarks;quality=[{source:'tasks-independent',configuredPresenceThreshold:.5,perJointConfidence:null}];}
    else if(!trackedResult){
     detection=primary;motionHands=primary.landmarks||[];
     if(primary.landmarks?.some(usable)){
      if(!videoDetector)videoDetector=await vision.HandLandmarker.createFromOptions(files,options('VIDEO'));
      const t=performance.now(),v=videoDetector.detectForVideo(imageData,data.timestamp);timings.videoMs=performance.now()-t;detection.trackedLandmarks=v.landmarks;
      const anchor=primary.landmarks.find(usable),p=(v.landmarks||[]).find(p=>sameObservedHand(anchor,p,aspect));if(p){staticResult=classify(p);motionHands=[p];}
     }
     // An abstaining classifier is not a failed hand detector. In the
     // continuity experiment keep the measured trajectory and its timestamp.
     if(!staticResult&&onnx&&(!preserveUsableMotion||!motionHands.some(usable))){
      const t=performance.now();let r=await onnx.detect(bitmap);
      if(!r.landmarks.some(usable))r=await onnx.searchRegion(bitmap,searchIndex++);
      timings.recoveryMs+=performance.now()-t;const h=r.landmarks.filter(usable);
      if(h.length){tracks=h;motionHands=h;const c=choose(r);detection={...r,landmarks:c?[c.points]:h};staticResult=c?.result||null;quality=r.quality;}
     }
    }
   }
   self.postMessage({type:'frame',id:data.id,modelVersion:version,timestamp:data.timestamp,capturedAt:data.capturedAt,imageAspect:aspect,...detection,staticResult,motionHands,stableMotionGate,quality,timings,inferencePerformed:true,inferenceMs:performance.now()-started});
  }finally{bitmap.close();}
 }catch(error){self.postMessage({type:'error',message:error.stack||String(error)});}
};
