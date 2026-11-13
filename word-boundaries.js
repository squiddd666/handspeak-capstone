// Geometry/time-only boundary consensus. No labels, model scores, or expected words.
export function createWordBoundaries(){
 let previous=[],last=null,active=null,onset=null,armed=true,quietSince=null,cooldown=0,noise=.01;
 function reset(requireQuiet=false,now=0){previous=[];last=null;active=null;onset=null;armed=!requireQuiet;quietSince=null;noise=.01;cooldown=now+(requireQuiet?900:0);}
 function abort(now,reason){active=null;onset=null;armed=false;quietSince=null;cooldown=now+1000;return {type:'reject',reason};}
 const valid=hand=>Array.isArray(hand)&&hand.length===21&&hand.every(p=>p&&Number.isFinite(p.x)&&Number.isFinite(p.y))&&Math.hypot(hand[5].x-hand[17].x,hand[5].y-hand[17].y)>=.018;
 function heldPose(samples,aspect){
  if(samples.length<5||samples.at(-1).time-samples[0].time<850)return null;
  const anchor=samples[Math.floor(samples.length/2)].hands,excursions=[];
  for(const sample of samples){
   if(sample.hands.length!==anchor.length)return null;
   const used=new Set();let worst=0;
   for(const hand of anchor){
    let index=-1,best=Infinity;
    sample.hands.forEach((p,i)=>{if(used.has(i))return;const d=Math.hypot(p[0].x-hand[0].x,(p[0].y-hand[0].y)*aspect);if(d<best){best=d;index=i;}});
    if(index<0)return null;used.add(index);const observed=sample.hands[index];
    const scale=Math.max(.04,Math.hypot(hand[5].x-hand[17].x,(hand[5].y-hand[17].y)*aspect),Math.hypot(hand[9].x-hand[0].x,(hand[9].y-hand[0].y)*aspect));
    const delta=hand.map((point,i)=>Math.hypot(point.x-observed[i].x,(point.y-observed[i].y)*aspect)/scale).sort((a,b)=>b-a);
    worst=Math.max(worst,delta.slice(0,5).reduce((a,b)=>a+b,0)/5);
   }
   excursions.push(worst);
  }
  const ordered=excursions.slice().sort((a,b)=>a-b),score=ordered[Math.floor((ordered.length-1)*.8)];
  return score<=.12&&excursions.slice(-2).every(x=>x<=.14)?{excursion:score,samples:samples.length}:null;
 }
 function observe(input,now,aspect=1,scene={}){
  if(!Number.isFinite(now)||(last!==null&&now<=last))return null;
  const raw=(Array.isArray(input)?input:[]).filter(valid).slice(0,2);
  const hands=raw.filter(h=>h.every(p=>p.x>=-.03&&p.x<=1.03&&p.y>=-.03&&p.y<=1.03)),cropped=raw.length>0&&!hands.length,dt=last===null?100:now-last;
  last=now;
  if(dt>500){previous=hands;onset=null;if(active)return abort(now,'timing-gap');quietSince=null;return null;}
  let energy=0,matched=0,poseStep=0;const used=new Set();
  for(const hand of hands){
   let best=-1,distance=Infinity;
   previous.forEach((prior,i)=>{if(used.has(i))return;const d=Math.hypot(hand[0].x-prior[0].x,(hand[0].y-prior[0].y)*aspect);if(d<distance){distance=d;best=i;}});
   const width=Math.max(.025,Math.hypot(hand[5].x-hand[17].x,(hand[5].y-hand[17].y)*aspect));
   if(best<0||distance>width*3)continue;
   used.add(best);matched++;
   const delta=hand.reduce((sum,p,i)=>sum+Math.hypot(p.x-previous[best][i].x,(p.y-previous[best][i].y)*aspect),0)/21/width;
   energy=Math.max(energy,delta*Math.min(2,100/Math.max(40,dt)));
   const scale=Math.max(.04,width,Math.hypot(hand[9].x-hand[0].x,(hand[9].y-hand[0].y)*aspect));
   const changes=hand.map((p,i)=>Math.hypot(p.x-previous[best][i].x,(p.y-previous[best][i].y)*aspect)/scale).sort((a,b)=>b-a);
   poseStep=Math.max(poseStep,changes.slice(0,5).reduce((a,b)=>a+b,0)/5);
  }
  previous=hands;
  const high=Math.max(.08,4*noise+.02),low=Math.min(high*.8,Math.max(.035,2.2*noise+.01));
  // Local finger articulation can be diluted by the 21-joint average.
  // Require independent pixel motion for this additional onset path.
  const articulated=matched>0&&poseStep>=.10&&scene.available===true&&scene.energy>Math.max(.008,(scene.threshold||.004)*1.5);
  const moving=matched>0&&(energy>=high||articulated),still=hands.length>0&&matched>0&&energy<=low;
  if(!active&&still&&!onset)noise=Math.min(.03,Math.max(.002,noise*.95+energy*.05));
  if(moving)quietSince=null;else if(still||!hands.length)quietSince??=now;else quietSince=null;
  if(!armed){if(now>=cooldown&&quietSince!==null&&now-quietSince>=600)armed=true;else return null;}
  if(!active){
   if(!hands.length){onset=null;return null;}
   if(moving){
    if(!onset||now-onset.start>650)onset={start:now,votes:0};
    onset.votes++;
    const visualOnset=onset.votes>=2&&scene.available===true&&scene.energy>Math.max(.008,(scene.threshold||.004)*1.5);
    if((onset.votes>=3||visualOnset)&&now-onset.start>=100){
     active={start:onset.start,motionVotes:onset.votes,visualOnset,visible:onset.votes,quietStart:null,quietVotes:0,missingSince:null,stableBeforeLoss:false,lastSeen:now,lastPoseMotion:now,holdSamples:[]};onset=null;
     return {type:'start',onsetTime:active.start};
    }
   }else if(onset&&now-onset.start>300)onset=null;
   return null;
  }
  if(cropped){active.croppedSince??=now;if(now-active.croppedSince>=400)return abort(now,'hands-cropped');}else active.croppedSince=null;
  if(hands.length){
   if(active.missingSince!==null){active.quietStart=null;active.quietVotes=0;active.stableBeforeLoss=false;}
   if(poseStep>.14)active.lastPoseMotion=now;
   active.visible++;active.lastSeen=now;active.missingSince=null;
   if(active.holdSamples.length&&active.holdSamples.at(-1).hands.length!==hands.length)active.holdSamples=[];
   active.holdSamples.push({hands,time:now});active.holdSamples=active.holdSamples.filter(sample=>now-sample.time<=1100);
   if(moving){active.motionVotes++;active.quietStart=null;active.quietVotes=0;}
   else if(still){active.quietStart??=now;active.quietVotes++;}
   else{active.quietStart=null;active.quietVotes=0;}
  }else{
   active.holdSamples=[];
   if(active.missingSince===null){active.missingSince=now;active.stableBeforeLoss=now-active.lastPoseMotion>=250&&active.quietVotes>=3&&active.quietStart!==null&&now-active.quietStart>=250;}
   if(!active.stableBeforeLoss&&now-active.missingSince>=1600&&scene.available!==true)return abort(now,'hands-lost-while-scene-not-stable');
  }
  const mature=now-active.start>=2400&&(active.motionVotes>=3||active.visualOnset);
  const poseHold=hands.length?heldPose(active.holdSamples,aspect):null;
  const stableEnd=now-active.lastPoseMotion>=850&&(Boolean(poseHold)||hands.length&&active.quietVotes>=5&&active.quietStart!==null&&now-active.quietStart>=850);
  const exitedAfterHold=!hands.length&&active.stableBeforeLoss&&now-active.missingSince>=700;
  const visualEnd=!hands.length&&scene.quietForMs>=1100&&scene.observations>=7;
  if(mature&&(stableEnd||exitedAfterHold||visualEnd)){
   const quality={onsetEvidence:active.visualOnset?'landmarks-and-scene':'landmark-consensus',motionVotes:active.motionVotes,visibleObservations:active.visible,quietVotes:active.quietVotes,durationMs:now-active.start,poseWindow:poseHold,endpoint:stableEnd?'stable-pause':exitedAfterHold?'exit-after-stable-hold':'scene-motion-corroborated',sceneQuietMs:scene.quietForMs||0};
   active=null;onset=null;armed=false;quietSince=null;cooldown=now+1000;
   return {type:'end',quality};
  }
  if(now-active.start>6000)return abort(now,'no-stable-end');
  return null;
 }
 return {observe,reset,abort,isActive:()=>Boolean(active)};
}
