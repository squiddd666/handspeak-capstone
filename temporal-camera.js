export function createTemporalCamera({onDetection,onGap,onError}){
 const worker=new Worker('./hand-detection-worker.js?v=20261020-tracking-1'),canvas=document.createElement('canvas'),ctx=canvas.getContext('2d',{willReadFrequently:true});
 let queue=[],busy=false,closed=false,generation=0,last=-Infinity,delegate='',lag=0,resolveReady,rejectReady;
 const ready=new Promise((resolve,reject)=>{resolveReady=resolve;rejectReady=reject;});
 function reset(){generation++;queue=[];last=-Infinity;}
 function gap(){reset();onGap();}
 function drain(){
  if(closed||busy||!queue.length)return;
  if(performance.now()-queue[0].timestamp>2500){gap();return;}
  busy=true;const packet=queue.shift();worker.postMessage(packet,[packet.pixels]);
 }
 function fail(message){if(closed)return;rejectReady?.(Error(message));rejectReady=null;onError(message);}
 worker.onerror=event=>fail(event.message||'Hand detector worker failed');
 worker.onmessage=({data})=>{
  if(closed)return;
  if(data.type==='ready'){delegate=data.delegate;rejectReady=null;resolveReady(delegate);return;}
  if(data.type==='delegate'){delegate=data.delegate;gap();return;}
  if(data.type==='error'){fail(data.message);return;}
  busy=false;
  if(data.generation===generation){lag=performance.now()-data.timestamp;if(lag>2500)gap();else onDetection(data,lag);}
  drain();
 };
 worker.postMessage({type:'init'});
 return {
  ready,reset,getDelegate:()=>delegate,
  push(video,now,active){
   if(closed||!delegate||now-last<(delegate==='GPU'?30:active?60:lag>500?120:80))return;
   last=now;const scale=Math.min(1,640/Math.max(video.videoWidth,video.videoHeight)),width=Math.round(video.videoWidth*scale),height=Math.round(video.videoHeight*scale);
   if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;gap();}
   ctx.drawImage(video,0,0,width,height);
   if(queue.length>=36)gap();
   queue.push({type:'frame',generation,timestamp:now,width,height,pixels:ctx.getImageData(0,0,width,height).data.buffer});drain();
  },
  close(){if(closed)return;closed=true;worker.terminate();queue=[];rejectReady?.(Error('Camera stopped'));rejectReady=null;}
 };
}
