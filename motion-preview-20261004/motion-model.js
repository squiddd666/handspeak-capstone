// Sequence matching for pretrained words and optional personal examples.
export const MOTION_FRAMES = 20;

export function motionFrame(detection){
  const slots=[null,null];
  (detection.landmarks||[]).slice(0,2).forEach((points,i)=>{
    if(points.length!==21 || !points.every(p=>[p.x,p.y,p.z].every(Number.isFinite)))return;
    const side=detection.handedness?.[i]?.[0]?.categoryName;
    let slot=side==='Left'?0:side==='Right'?1:(points[0].x<.5?0:1);
    if(slots[slot])slot=1-slot;
    slots[slot]=points;
  });
  return slots;
}

export function encodeMotion(frames,imageAspect=1){
  if(frames.length<12)return null;
  if(!Number.isFinite(imageAspect)||imageAspect<=0)return null;
  // MediaPipe x/z use image width; y uses height. Match in width-based units.
  frames=frames.map(frame=>frame.map(hand=>hand?.map(p=>({...p,y:p.y*imageAspect}))||null));
  const start=frames.findIndex(frame=>frame.some(Boolean));
  if(start<0)return null;
  let end=frames.length-1;while(end>start&&!frames[end].some(Boolean))end--;
  frames=frames.slice(start,end+1).map(frame=>frame.slice());
  // Fill only brief, bounded tracking gaps; never invent leading/trailing hands.
  for(const side of [0,1]){
    for(let i=1;i<frames.length-1;i++){
      if(frames[i][side]||!frames[i-1][side])continue;
      let next=i;while(next<frames.length&&!frames[next][side])next++;
      if(next===frames.length||next-i>2)continue;
      const a=frames[i-1][side],b=frames[next][side];
      for(let j=i;j<next;j++){
        const t=(j-i+1)/(next-i+1);
        frames[j][side]=a.map((p,k)=>({x:p.x+(b[k].x-p.x)*t,y:p.y+(b[k].y-p.y)*t,z:p.z+(b[k].z-p.z)*t}));
      }
      i=next;
    }
  }
  // Ignore isolated entry/exit detections only when one continuous movement
  // contains at least 70% of the usable frames. Never join disconnected runs.
  const runs=[];let runStart=-1,lastVisible=-1,count=0;
  for(let i=0;i<frames.length;i++){
    if(!frames[i].some(Boolean))continue;
    if(runStart>=0&&i-lastVisible>3){runs.push({start:runStart,end:lastVisible,count});runStart=-1;count=0;}
    if(runStart<0)runStart=i;
    lastVisible=i;count++;
  }
  if(runStart>=0)runs.push({start:runStart,end:lastVisible,count});
  const strongest=runs.sort((a,b)=>b.count-a.count)[0];
  const observed=runs.reduce((sum,run)=>sum+run.count,0);
  if(strongest&&strongest.count>=8&&strongest.count>=observed*.7)frames=frames.slice(strongest.start,strongest.end+1);
  const visible=frames.filter(frame=>frame.some(Boolean));
  if(visible.length<8)return null;
  if(visible.length/frames.length<.7)return null;
  // Center the entire movement so a different starting hand position does not
  // translate every frame away from the training references.
  const first=visible.flatMap(frame=>frame.filter(Boolean));
  const anchor={x:first.reduce((s,h)=>s+h[0].x,0)/first.length,y:first.reduce((s,h)=>s+h[0].y,0)/first.length};
  const widths=visible.flatMap(frame=>frame.filter(Boolean).map(p=>Math.hypot(p[5].x-p[17].x,p[5].y-p[17].y)));
  const scale=widths.reduce((a,b)=>a+b,0)/widths.length;
  if(scale<.035)return null;
  return Array.from({length:MOTION_FRAMES},(_,i)=>{
    const frame=frames[Math.round(i*(frames.length-1)/(MOTION_FRAMES-1))];
    return frame.flatMap(hand=>hand?[1,...hand.flatMap(p=>[(p.x-anchor.x)/scale,(p.y-anchor.y)/scale,(p.z-hand[0].z)/scale])]:Array(64).fill(0));
  });
}

export function validMotion(sequence){
  return Array.isArray(sequence)&&sequence.length===MOTION_FRAMES
    && sequence.every(frame=>Array.isArray(frame)&&frame.length===128&&frame.every(v=>Number.isFinite(v)&&Math.abs(v)<50)
      && [0,1].includes(frame[0])&&[0,1].includes(frame[64]));
}

export function motionDistance(a,b){
  // Banded dynamic time warping tolerates modest differences in signing speed.
  let previous=Array(b.length+1).fill(Infinity);previous[0]=0;
  for(let i=1;i<=a.length;i++){
    const current=Array(b.length+1).fill(Infinity);
    for(let j=Math.max(1,i-5);j<=Math.min(b.length,i+5);j++){
      let cost=0;
      for(const offset of [0,64]){
        if(a[i-1][offset]!==b[j-1][offset]){cost+=2;continue;}
        if(!a[i-1][offset])continue;
        let sum=0;
        for(let c=1;c<=63;c++){
          const weight=c%3===0?.5:1;
          sum+=((a[i-1][offset+c]-b[j-1][offset+c])*weight)**2;
        }
        cost+=Math.sqrt(sum/63);
      }
      current[j]=cost+Math.min(previous[j],current[j-1],previous[j-1]);
    }
    previous=current;
  }
  return previous[b.length]/Math.max(a.length,b.length);
}

export function mirrorMotion(sequence){
  return sequence.map(frame=>[64,0].flatMap(offset=>[frame[offset],...frame.slice(offset+1,offset+64).map((v,i)=>i%3===0?-v:v)]));
}

export function validMotionParameters(p){
  return p && Number.isFinite(p.maxDistance)&&p.maxDistance>0&&p.maxDistance<=10
    && Number.isFinite(p.minRatio)&&p.minRatio>=1&&p.minRatio<=5
    && Number.isInteger(p.minVotes)&&p.minVotes>=1&&p.minVotes<=3
    && typeof p.mirror==='boolean'
    && (p.strongRatio===undefined||(Number.isFinite(p.strongRatio)&&p.strongRatio>=1.5&&p.strongRatio>=p.minRatio&&p.strongRatio<=5));
}

export function recognizeMotion(sequence, examples, parameters={maxDistance:.65,minRatio:1.3,minVotes:2,mirror:false}){
  if(!validMotion(sequence))return null;
  const counts={};examples.forEach(e=>counts[e.label]=(counts[e.label]||0)+1);
  if(Object.values(counts).filter(n=>n>=3).length<2)return null;
  const mirrored=parameters.mirror?mirrorMotion(sequence):null;
  const ranked=examples.filter(e=>counts[e.label]>=3).map(e=>({label:e.label,distance:Math.min(motionDistance(sequence,e.sequence),mirrored?motionDistance(mirrored,e.sequence):Infinity)})).sort((a,b)=>a.distance-b.distance);
  const best=ranked[0],other=ranked.find(e=>e.label!==best.label);
  const separation=other?other.distance/(best.distance+1e-6):Infinity;
  const votes=ranked.slice(0,3).filter(e=>e.label===best.label).length;
  if(best.distance>parameters.maxDistance || separation<parameters.minRatio
    || (votes<parameters.minVotes&&separation<(parameters.strongRatio??Infinity)))return null;
  return {label:best.label,distance:best.distance};
}
