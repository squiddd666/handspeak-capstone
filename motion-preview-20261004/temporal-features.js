// Evaluation-only implementation. Input features are [153 channels][32 frames].
export function temporalLogits(input,weights){
  function conv(x,w,b){
    const channels=w.length,length=x[0].length,pad=Math.floor(w[0][0].length/2);
    return Array.from({length:channels},(_,o)=>Array.from({length},(_,t)=>{
      let sum=b[o];
      for(let c=0;c<x.length;c++)for(let k=0;k<w[o][c].length;k++){
        const index=t+k-pad;if(index>=0&&index<length)sum+=x[c][index]*w[o][c][k];
      }
      return Math.max(0,sum);
    }));
  }
  const a=conv(input,weights['net.0.weight'],weights['net.0.bias']);
  const b=conv(a,weights['net.3.weight'],weights['net.3.bias']);
  const pooled=b.map(row=>row.reduce((sum,x)=>sum+x,0)/row.length);
  return weights['net.7.weight'].map((row,i)=>row.reduce((sum,w,j)=>sum+w*pooled[j],weights['net.7.bias'][i]));
}

export function temporalFeatures(row){
  const aspect=row.imageAspect,frames=row.rawFrames,body=row.body||frames.map(()=>null);
  const wrists=frames.flatMap(f=>f.filter(Boolean).map(h=>[h[0].x,h[0].y*aspect]));
  const center=wrists.length?[0,1].map(i=>wrists.reduce((s,w)=>s+w[i],0)/wrists.length):[0,0];
  const vectors=frames.map((frame,t)=>{
    const pose=body[t],good=Boolean(pose&&Math.min(pose[1].visibility,pose[2].visibility)>.5);
    const origin=good?[(pose[1].x+pose[2].x)/2,(pose[1].y+pose[2].y)*aspect/2]:center;
    const scale=good?Math.max(.08,Math.hypot(pose[1].x-pose[2].x,(pose[1].y-pose[2].y)*aspect)):.2;
    const vector=[];
    for(const h of frame){
      if(!h){vector.push(...Array(69).fill(0));continue;}
      const palm=Math.max(.035,Math.hypot(h[5].x-h[17].x,(h[5].y-h[17].y)*aspect));
      vector.push(1,...h.flatMap(p=>[(p.x-h[0].x)/palm,(p.y-h[0].y)*aspect/palm,(p.z-h[0].z)/palm]),(h[0].x-origin[0])/scale,(h[0].y*aspect-origin[1])/scale,(h[0].x-center[0])/scale,(h[0].y*aspect-center[1])/scale,Number(good));
    }
    for(let i=0;i<5;i++){
      if(good&&pose[i].visibility>.5)vector.push(1,(pose[i].x-origin[0])/scale,(pose[i].y*aspect-origin[1])/scale);
      else vector.push(0,0,0);
    }
    return vector.map(v=>Number.isFinite(v)?Math.max(-10,Math.min(10,v)):0);
  });
  if(!vectors.length)return Array.from({length:153},()=>Array(32).fill(0));
  return Array.from({length:153},(_,c)=>Array.from({length:32},(_,i)=>{
    const t=i*(vectors.length-1)/31,a=Math.floor(t),b=Math.min(a+1,vectors.length-1);
    return vectors[a][c]+(vectors[b][c]-vectors[a][c])*(t-a);
  }));
}
