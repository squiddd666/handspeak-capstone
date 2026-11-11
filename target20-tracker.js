// CPU pose tracking avoids the legacy Holistic WebGL bottleneck on machines
// without a GPU. Hand landmarks come from the app's existing hand detector.
const POSE=[0,2,5,11,12,13,14];
const distance=(a,b)=>(a.x-b.x)**2+(a.y-b.y)**2;
export function associateHands(pose,hands){
  if(!pose?.[11]||!pose?.[12]||[11,12].some(i=>(pose[i].visibility??1)<.5))return null;
  const shoulderWidth=Math.sqrt(distance(pose[11],pose[12]));
  if(shoulderWidth<.02)return null;
  const reliable=i=>pose[i]&&(pose[i].visibility??1)>=.5;
  let left=null,right=null;
  if(hands.length>=2&&reliable(15)&&reliable(16)){
    const [a,b]=hands;
    if(distance(a[0],pose[15])+distance(b[0],pose[16])<=distance(b[0],pose[15])+distance(a[0],pose[16])){left=a;right=b;}
    else{left=b;right=a;}
  }else if(hands.length===1){
    const l=reliable(15)?distance(hands[0][0],pose[15]):Infinity;
    const r=reliable(16)?distance(hands[0][0],pose[16]):Infinity;
    if(Math.min(l,r)<shoulderWidth**2*.64){if(l<r)left=hands[0];else right=hands[0];}
  }
  if(left&&distance(left[0],pose[15])>shoulderWidth**2*.64)left=null;
  if(right&&distance(right[0],pose[16])>shoulderWidth**2*.64)right=null;
  const points=hand=>hand?.map(p=>[p.x,p.y,p.z||0])||null;
  return {pose:POSE.map(i=>[pose[i].x,pose[i].y,pose[i].z||0]),left:points(left),right:points(right)};
}
export async function createTarget20Tracker(){
  let diagnostic={poses:0,rawHands:0,associatedHands:0};
  const vision=await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/+esm');
  const files=await vision.FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/wasm');
  const pose=await vision.PoseLandmarker.createFromOptions(files,{
    baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task',delegate:'CPU'},
    runningMode:'VIDEO',numPoses:1,minPoseDetectionConfidence:.5,minPosePresenceConfidence:.5,minTrackingConfidence:.5,
  });
  return {close:()=>pose.close(),diagnostics:()=>diagnostic,detect(video,now,detection){
    const result=pose.detectForVideo(video,now),body=result.landmarks?.[0];
    diagnostic={poses:result.landmarks?.length||0,rawHands:detection.landmarks?.length||0,associatedHands:0};
    if(!body)return null;
    const associated=associateHands(body,detection.landmarks||[]);
    diagnostic.associatedHands=Number(Boolean(associated?.left))+Number(Boolean(associated?.right));
    return associated;
  }};
}
