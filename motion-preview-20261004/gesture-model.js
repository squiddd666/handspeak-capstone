// Feature normalization must match training/train_asl.py.
export function normalizeLandmarks(points){
  const wrist=points[0], middleBase=points[9];
  const scale=Math.hypot(points[5].x-points[17].x,points[5].y-points[17].y)||1;
  const angle=Math.atan2(middleBase.y-wrist.y,middleBase.x-wrist.x)-Math.PI/2;
  const cosine=Math.cos(-angle),sine=Math.sin(-angle);
  return points.flatMap(point=>{
    const x=(point.x-wrist.x)/scale,y=(point.y-wrist.y)/scale;
    return [x*cosine-y*sine,x*sine+y*cosine,(point.z-wrist.z)/scale];
  });
}

export function validSample(sample, labels){
  return sample && labels.includes(sample.label) && Array.isArray(sample.features)
    && sample.features.length===63 && sample.features.every(Number.isFinite);
}

export const DEFAULT_PARAMETERS = Object.freeze({zWeight:.5,k:3,minAgreement:.7,maxDistance:.25,minRatio:1.5});

export function validParameters(p){
  return p && Number.isFinite(p.zWeight) && p.zWeight>0 && p.zWeight<=1
    && Number.isInteger(p.k) && p.k>=1 && p.k<=15
    && Number.isFinite(p.minAgreement) && p.minAgreement>=.5 && p.minAgreement<=1
    && Number.isFinite(p.maxDistance) && p.maxDistance>0 && p.maxDistance<=1
    && Number.isFinite(p.minRatio) && p.minRatio>=1 && p.minRatio<=5;
}

export function isUsableHand(points){
  return Array.isArray(points) && points.length===21
    && points.every(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)&&Number.isFinite(p.z)
      && p.x>=0 && p.x<=1 && p.y>=0 && p.y<=1)
    && Math.hypot(points[5].x-points[17].x,points[5].y-points[17].y)>=.035;
}

export function classifyFeatures(features, samples, parameters=DEFAULT_PARAMETERS){
  if(!Array.isArray(features)||features.length!==63||!features.every(Number.isFinite))return null;
  const counts={};samples.forEach(s=>counts[s.label]=(counts[s.label]||0)+1);
  if(Object.values(counts).filter(count=>count>=10).length<2)return null;
  const neighbors=[], nearestByLabel={};
  for(const sample of samples){
    if(counts[sample.label]<10)continue;
    let direct=0, mirrored=0;
    for(let i=0;i<63;i++){
      const weight=i%3===2?parameters.zWeight:1;
      const delta=(features[i]-sample.features[i])*weight;
      const mirrorDelta=((i%3===0?-features[i]:features[i])-sample.features[i])*weight;
      direct+=delta*delta;mirrored+=mirrorDelta*mirrorDelta;
    }
    const distance=Math.sqrt(Math.min(direct,mirrored)/63);
    nearestByLabel[sample.label]=Math.min(nearestByLabel[sample.label]??Infinity,distance);
    // Keep only the k best neighbors rather than sorting the entire dataset each frame.
    const index=neighbors.findIndex(n=>n.distance>distance);
    neighbors.splice(index<0?neighbors.length:index,0,{label:sample.label,distance});
    if(neighbors.length>parameters.k)neighbors.pop();
  }
  if(!neighbors.length)return null;
  const votes={};neighbors.forEach(n=>votes[n.label]=(votes[n.label]||0)+1/(n.distance+.001));
  const ranked=Object.entries(votes).sort((a,b)=>b[1]-a[1]);
  const agreement=ranked[0][1]/ranked.reduce((sum,item)=>sum+item[1],0);
  const label=ranked[0][0], nearest=neighbors[0].distance;
  const other=Math.min(...Object.entries(nearestByLabel).filter(([key])=>key!==label).map(([,distance])=>distance));
  if(agreement<parameters.minAgreement || nearest>parameters.maxDistance
    || other/(nearest+1e-8)<parameters.minRatio)return null;
  return {letter:label,confidence:agreement,source:'ai'};
}
