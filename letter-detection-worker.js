// SignSpeak is the sole alphabet classifier. MediaPipe only extracts landmarks.
let detector,model,version=1;
self.onmessage=async({data})=>{
 try{
  if(data.type==='init'){
   const started=performance.now();
   const {createSignSpeakModel}=await import('./signspeak-model.js');
   model=await createSignSpeakModel();
   const base='https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304';
   const vision=await import(base+'/+esm');
   const files=await vision.FilesetResolver.forVisionTasks(base+'/wasm');
   detector=await vision.HandLandmarker.createFromOptions(files,{
    baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',delegate:'CPU'},
    runningMode:'VIDEO',numHands:2,minHandDetectionConfidence:.5,minHandPresenceConfidence:.5,minTrackingConfidence:.5
   });
   self.postMessage({type:'ready',delegate:'CPU worker / SignSpeak LSTM',onnx:true,modelVersion:version,initializationMs:performance.now()-started});return;
  }
  if(data.type==='personal'){version++;model.reset();self.postMessage({type:'model',modelVersion:version});return;}
  if(data.type!=='frame')return;
  const bitmap=data.bitmap,started=performance.now();
  try{
   const detection=detector.detectForVideo(bitmap,data.timestamp);
   const hands=detection.landmarks||[];
   const staticResult=await model.frame(hands.length===1?hands[0]:null,data.timestamp);
   self.postMessage({type:'frame',id:data.id,modelVersion:version,timestamp:data.timestamp,capturedAt:data.capturedAt,imageAspect:bitmap.height/bitmap.width,landmarks:hands,staticResult,motionHands:[],quality:[{source:'signspeak-lstm'}],timings:{},inferencePerformed:true,inferenceMs:performance.now()-started});
  }finally{bitmap.close();}
 }catch(error){self.postMessage({type:'error',message:error.stack||String(error)});}
};
