// Geometry schema v1: image-width coordinates, stable palm scale, anatomical
// joint cosines, extension ratios, thumb contact and signed finger separation.
// Orientation is retained: rotating K into P must not make them equivalent.
export function alphabetFeatures(points,aspect=1){
  if(!Array.isArray(points)||points.length!==21||!Number.isFinite(aspect)||aspect<=0
    ||!points.every(p=>[p.x,p.y,p.z].every(Number.isFinite)))return null;
  const p=points.map(p=>[p.x,p.y*aspect,p.z]);
  const sub=(a,b)=>a.map((v,i)=>v-b[i]);
  const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
  const norm=a=>Math.hypot(...a),dist=(a,b)=>norm(sub(p[a],p[b]));
  const scale=Math.max(Math.hypot(p[5][0]-p[17][0],p[5][1]-p[17][1]),.65*Math.hypot(p[9][0]-p[0][0],p[9][1]-p[0][1]));
  if(scale<1e-5)return null;
  const out=p.flatMap(q=>sub(q,p[0]).map(v=>v/scale));
  const chains=[[0,1,2,3,4],[0,5,6,7,8],[0,9,10,11,12],[0,13,14,15,16],[0,17,18,19,20]];
  for(const c of chains){
    for(let j=1;j<=3;j++){
      const a=sub(p[c[j-1]],p[c[j]]),b=sub(p[c[j+1]],p[c[j]]);
      out.push(dot(a,b)/Math.max(1e-8,norm(a)*norm(b)));
    }
  }
  for(const c of chains){let path=0;for(let j=1;j<c.length;j++)path+=dist(c[j-1],c[j]);out.push(dist(c[0],c[4])/Math.max(path,1e-8));}
  const tips=[4,8,12,16,20];
  for(let a=0;a<5;a++)for(let b=a+1;b<5;b++)out.push(dist(tips[a],tips[b])/scale);
  for(const base of [5,9,13,17])out.push(dist(4,base)/scale);
  // Project tip separation onto its own MCP separation axis. Crossing fingers
  // changes sign; a V spreads further along the same axis than a U.
  for(const [a,b]of [[5,9],[9,13],[13,17]]){
    const axis=sub(p[b],p[a]),span=norm(axis);out.push(dot(sub(p[b+3],p[a+3]),axis)/Math.max(span*scale,1e-8));
  }
  return out.length===100&&out.every(Number.isFinite)?out:null;
}

export function predictAlphabetGeometry(points,model,aspect=1){
  if(model?.schema!=='alphabet-joints-v1'||model.featureCount!==100)return null;
  const f=alphabetFeatures(points,aspect);if(!f)return null;
  let a=f.map((v,i)=>(v-model.mean[i])/model.std[i]);
  if(!a.every(Number.isFinite)||a.some(v=>Math.abs(v)>model.parameters.maxZScore))return null;
  for(let layer=0;layer<model.weights.length;layer++){
    const w=model.weights[layer],bias=model.biases[layer];
    a=bias.map((b,j)=>a.reduce((s,v,i)=>s+v*w[i][j],b));
    if(layer<model.weights.length-1)a=a.map(v=>Math.max(0,v));
  }
  const mx=Math.max(...a),exp=a.map(v=>Math.exp(v-mx)),sum=exp.reduce((s,v)=>s+v,0),prob=exp.map(v=>v/sum);
  const ids=prob.map((_,i)=>i).sort((a,b)=>prob[b]-prob[a]);const first=ids[0],second=ids[1];
  if(prob[first]<model.parameters.minProbability||prob[first]-prob[second]<model.parameters.minMargin)return null;
  return {letter:model.labels[first],confidence:prob[first],source:'geometry-mlp',margin:prob[first]-prob[second]};
}
