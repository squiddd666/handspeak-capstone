// Segment one moving sign at a time. No video is stored or uploaded.
export function createAutomaticMotion({sampleIntervalMs=80}={}){
  if(![30,80].includes(sampleIntervalMs))throw new Error('Unsupported capture interval');
  let previous=null,buffer=[],active=null,last=-Infinity,cooldown=0,armed=true,quietSince=null,aspect=null,motionAt=-Infinity,lastMoving=false;
  function reset(){previous=null;buffer=[];active=null;last=-Infinity;cooldown=0;armed=true;quietSince=null;aspect=null;motionAt=-Infinity;lastMoving=false;}
  function push(frame,now,imageAspect=1){
    if(now-last<sampleIntervalMs)return null;
    if(now-last>1000||(aspect!==null&&Math.abs(aspect-imageAspect)>.01))reset();
    last=now;aspect=imageAspect;
    const visible=frame.some(Boolean);
    // Keep the established movement assessment cadence while optionally retaining
    // more frames. Short signs can otherwise lose most of their visible samples.
    let moving=lastMoving;
    if(now-motionAt>=80){
      moving=false;
      if(previous){
      for(let side=0;side<2;side++){
        const a=previous[side],b=frame[side];
        if(!a||!b){if(b)moving=true;continue;}
        const width=Math.max(.035,Math.hypot(b[5].x-b[17].x,(b[5].y-b[17].y)*imageAspect));
        const delta=b.reduce((sum,p,i)=>sum+Math.hypot(p.x-a[i].x,(p.y-a[i].y)*imageAspect),0)/21/width;
        if(delta>.08)moving=true;
      }
      }else if(visible)moving=true;
      previous=frame;motionAt=now;lastMoving=moving;
    }
    if(!moving){if(quietSince===null)quietSince=now;}else quietSince=null;
    if(!armed){
      if(now>=cooldown&&quietSince!==null&&now-quietSince>=350)armed=true;
      else return null;
    }
    buffer.push({frame,now});buffer=buffer.filter(x=>now-x.now<=350);
    if(!active&&visible&&moving){active={frames:buffer.map(x=>x.frame),start:buffer[0].now,moved:now,imageAspect};return null;}
    if(!active)return null;
    active.frames.push(frame);if(moving)active.moved=now;
    if((now-active.moved>=600&&active.frames.length>=12&&now-active.start>=800)||now-active.start>=4500){
      const result=active;active=null;buffer=[];armed=false;cooldown=now+800;
      return result;
    }
    return null;
  }
  return {push,reset,isActive:()=>Boolean(active)};
}
