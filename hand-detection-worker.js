// Keep detector work off the camera/UI thread for temporal word capture.
let hands,files,HandLandmarker,options,delegate;
self.onmessage=async({data})=>{
 try{
  if(data.type==='init'){
   const {preferredVisionDelegate}=await import('./camera-performance.js?v=20261010-single-1');
   const vision=await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/+esm');
   HandLandmarker=vision.HandLandmarker;files=await vision.FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/wasm');
   delegate=preferredVisionDelegate(()=>new OffscreenCanvas(1,1));
   options={baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',delegate},runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.5,minHandPresenceConfidence:.5,minTrackingConfidence:.5};
   if(delegate==='GPU')options.canvas=new OffscreenCanvas(1,1);
   try{hands=await HandLandmarker.createFromOptions(files,options);}catch(error){if(delegate==='CPU')throw error;delete options.canvas;delegate='CPU';options.baseOptions.delegate=delegate;hands=await HandLandmarker.createFromOptions(files,options);}
   self.postMessage({type:'ready',delegate});return;
  }
  const frame=new ImageData(new Uint8ClampedArray(data.pixels),data.width,data.height);
  let result;
  try{result=hands.detectForVideo(frame,data.timestamp);}
  catch(error){
   if(delegate!=='GPU')throw error;
   try{hands.close();}catch{}
   delete options.canvas;delegate='CPU';options.baseOptions.delegate=delegate;
   hands=await HandLandmarker.createFromOptions(files,options);
   self.postMessage({type:'delegate',delegate});
   result=hands.detectForVideo(frame,data.timestamp);
  }
  self.postMessage({type:'frame',generation:data.generation,timestamp:data.timestamp,imageAspect:data.height/data.width,landmarks:result.landmarks,handedness:result.handedness});
 }catch(error){self.postMessage({type:'error',message:error.message});}
};
