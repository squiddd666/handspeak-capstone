// Bounded transport: one in-flight frame, no stale queue and no duplicates.
export function createLetterCamera({onDetection,onError,onWarning=()=>{},personalSamples=[]}){
 const worker=new Worker('./letter-detection-worker.js?v=20261111-architecture-2');
 let closed=false,busy=false,lastSource=-Infinity,id=0,version=1,resolveReady,rejectReady;
 let callbackId=null,boundVideo=null;
 const stats={submitted:0,completed:0,dropped:0,duplicates:0,inFlight:0,latencies:[],inference:[],completedAt:[],modelAt:[],quality:null};
 const ready=new Promise((resolve,reject)=>{resolveReady=resolve;rejectReady=reject;});
 function fail(message){if(closed)return;rejectReady?.(Error(message));rejectReady=null;onError(message);}
 worker.onerror=e=>fail(e.message||'Letter detector worker failed');
 worker.onmessage=({data})=>{
  if(closed)return;
  if(data.type==='ready'){version=data.modelVersion;rejectReady=null;stats.backend=data.delegate;stats.onnx=data.onnx;stats.initializationMs=data.initializationMs;resolveReady(data);return;}
  if(data.type==='warning'){onWarning(data.message);return;}
  if(data.type==='model'){version=data.modelVersion;return;}
  if(data.type==='error'){busy=false;stats.inFlight=0;fail(data.message);return;}
  if(data.type==='frame'){
   busy=false;stats.inFlight=0;if(data.modelVersion!==version)return;
   const now=performance.now();stats.completed++;stats.completedAt.push(now);stats.completedAt=stats.completedAt.filter(t=>now-t<=5000);
   stats.latencies.push(now-data.capturedAt);if(data.inferencePerformed){stats.inference.push(data.inferenceMs);stats.modelAt.push(now);}stats.modelAt=stats.modelAt.filter(t=>now-t<=5000);stats.latencies=stats.latencies.slice(-120);stats.inference=stats.inference.slice(-120);
   stats.quality=data.quality;stats.timings=data.timings;onDetection(data,now-data.capturedAt);
  }
 };
 const recovery=new URLSearchParams(globalThis.location?.search||'').get('letterRecovery');
 worker.postMessage({type:'init',personalSamples,recovery});
 async function submit(video,source){
   if(closed)return;
   if(source<=lastSource){stats.duplicates++;return;}lastSource=source;
   if(busy){stats.dropped++;return;}busy=true;stats.inFlight=1;const capturedAt=performance.now();
   let bitmap;
   try{bitmap=await createImageBitmap(video);if(closed){bitmap.close();return;}worker.postMessage({type:'frame',id:++id,timestamp:source,capturedAt,bitmap},[bitmap]);stats.submitted++;}
   catch(error){bitmap?.close();busy=false;stats.inFlight=0;fail(error.message);}
 }
 function onVideoFrame(_,metadata){
   if(closed)return;
   callbackId=boundVideo.requestVideoFrameCallback(onVideoFrame);
   void submit(boundVideo,metadata.mediaTime*1000);
 }
 return {
  ready,
  setPersonalSamples(samples){version++;worker.postMessage({type:'personal',samples});},
  diagnostics(){
   const percentile=(a,p)=>a.length?[...a].sort((a,b)=>a-b)[Math.min(a.length-1,Math.floor(a.length*p))]:0;
   const t=stats.completedAt,span=t.length>1?t[t.length-1]-t[0]:0;
   return {...stats,completedAt:undefined,modelAt:undefined,modelInferenceFps:stats.modelAt.length>1?(stats.modelAt.length-1)*1000/(stats.modelAt[stats.modelAt.length-1]-stats.modelAt[0]):0,latencies:undefined,inference:undefined,processedFps:span?(t.length-1)*1000/span:0,inferenceMedianMs:percentile(stats.inference,.5),inferenceP95Ms:percentile(stats.inference,.95),latencyP95Ms:percentile(stats.latencies,.95),maxQueuedFrames:0};
  },
  push(video){
   if(closed)return;
   if(typeof video.requestVideoFrameCallback==='function'){
     if(!boundVideo){boundVideo=video;callbackId=video.requestVideoFrameCallback(onVideoFrame);}
   }else void submit(video,video.currentTime*1000);
  },
  close(){if(closed)return;closed=true;if(callbackId!==null)boundVideo.cancelVideoFrameCallback(callbackId);worker.terminate();stats.inFlight=0;rejectReady?.(Error('Camera stopped'));rejectReady=null;}
 };
}
