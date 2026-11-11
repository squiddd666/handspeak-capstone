// Browser port of the Apache-2.0 OpenCV Zoo MP-PalmDet/MP-HandPose pipeline.
// Attribution and pinned model hashes: third_party/hand-landmarks/NOTICE.md.
// No label or expected gesture is used anywhere in this detector.
export function palmAnchors(){
  const anchors=[];
  for(const [grid,repeats]of [[24,2],[12,6]])for(let y=0;y<grid;y++)for(let x=0;x<grid;x++)
    for(let i=0;i<repeats;i++)anchors.push([(x+.5)/grid,(y+.5)/grid]);
  return anchors;
}
function canvas(w,h){
  const c=typeof OffscreenCanvas!=='undefined'?new OffscreenCanvas(w,h):Object.assign(document.createElement('canvas'),{width:w,height:h});
  return c;
}
function rgbTensor(c,ort){
  const rgba=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
  const data=new Float32Array(c.width*c.height*3);
  for(let i=0,j=0;i<rgba.length;i+=4){data[j++]=rgba[i]/255;data[j++]=rgba[i+1]/255;data[j++]=rgba[i+2]/255;}
  return new ort.Tensor('float32',data,[1,c.height,c.width,3]);
}
export function boxIoU(a,b){
  const intersect=Math.max(0,Math.min(a[2],b[2])-Math.max(a[0],b[0]))*Math.max(0,Math.min(a[3],b[3])-Math.max(a[1],b[1]));
  const area=q=>Math.max(0,q[2]-q[0])*Math.max(0,q[3]-q[1]);
  return intersect/Math.max(1e-8,area(a)+area(b)-intersect);
}
export function decodePalms(boxes,logits,width,height,pad,threshold=.5,maxHands=2){
  const anchors=palmAnchors(),scale=Math.max(width,height),candidates=[];
  for(let i=0;i<anchors.length;i++){
    const score=1/(1+Math.exp(-Math.max(-80,Math.min(80,logits[i]))));if(score<threshold)continue;
    const j=i*18,cx=(boxes[j]/192+anchors[i][0])*scale-pad[0],cy=(boxes[j+1]/192+anchors[i][1])*scale-pad[1];
    const w=boxes[j+2]/192*scale,h=boxes[j+3]/192*scale;
    const box=[cx-w/2,cy-h/2,cx+w/2,cy+h/2];const points=[];
    for(let k=0;k<7;k++)points.push([(boxes[j+4+2*k]/192+anchors[i][0])*scale-pad[0],(boxes[j+5+2*k]/192+anchors[i][1])*scale-pad[1]]);
    candidates.push({box,points,score});
  }
  candidates.sort((a,b)=>b.score-a.score);const kept=[];
  for(const c of candidates){if(kept.every(k=>boxIoU(c.box,k.box)<.3))kept.push(c);if(kept.length>=maxHands)break;}
  return kept;
}
function cropPad(source,box,preRotation=false){
  const x0=Math.max(0,Math.min(source.width,Math.trunc(box[0]))),y0=Math.max(0,Math.min(source.height,Math.trunc(box[1])));
  const x1=Math.max(0,Math.min(source.width,Math.trunc(box[2]))),y1=Math.max(0,Math.min(source.height,Math.trunc(box[3])));
  const w=x1-x0,h=y1-y0;if(w<2||h<2)return null;
  const side=Math.max(2,Math.trunc(preRotation?Math.hypot(w,h):Math.max(w,h))),left=Math.floor((side-w)/2),top=Math.floor((side-h)/2);
  const out=canvas(side,side),ctx=out.getContext('2d');ctx.fillStyle='black';ctx.fillRect(0,0,side,side);ctx.drawImage(source,x0,y0,w,h,left,top,w,h);
  return {canvas:out,box:[x0,y0,x1,y1],bias:[x0-left,y0-top]};
}
function enlarge(box,factor,dy=0){const w=box[2]-box[0],h=box[3]-box[1],cx=(box[0]+box[2])/2,cy=(box[1]+box[3])/2+dy*h;return [cx-w*factor/2,cy-h*factor/2,cx+w*factor/2,cy+h*factor/2];}
function prepareHand(source,palm){
  const pre=cropPad(source,enlarge(palm.box,4),true);if(!pre)return null;
  const points=palm.points.map(p=>[p[0]-pre.bias[0],p[1]-pre.bias[1]]),a=points[0],b=points[2];
  let rad=Math.PI/2-Math.atan2(-(b[1]-a[1]),b[0]-a[0]);rad-=2*Math.PI*Math.floor((rad+Math.PI)/(2*Math.PI));
  const cos=Math.cos(rad),sin=Math.sin(rad),cx=(pre.box[0]+pre.box[2])/2-pre.bias[0],cy=(pre.box[1]+pre.box[3])/2-pre.bias[1];
  const tx=(1-cos)*cx-sin*cy,ty=sin*cx+(1-cos)*cy;
  const rotate=([x,y])=>[cos*x+sin*y+tx,-sin*x+cos*y+ty];
  const rot=canvas(pre.canvas.width,pre.canvas.height),ctx=rot.getContext('2d');ctx.fillStyle='black';ctx.fillRect(0,0,rot.width,rot.height);
  ctx.setTransform(cos,-sin,sin,cos,tx,ty);ctx.drawImage(pre.canvas,0,0);ctx.resetTransform();
  const p=points.map(rotate),box=[Math.min(...p.map(v=>v[0])),Math.min(...p.map(v=>v[1])),Math.max(...p.map(v=>v[0])),Math.max(...p.map(v=>v[1]))];
  const crop=cropPad(rot,enlarge(box,3,-.4));if(!crop)return null;
  const input=canvas(224,224),inputCtx=input.getContext('2d');inputCtx.imageSmoothingQuality='high';inputCtx.drawImage(crop.canvas,0,0,224,224);
  const rx=(crop.box[0]+crop.box[2])/2,ry=(crop.box[1]+crop.box[3])/2;
  return {input,cos,sin,scale:Math.max(crop.box[2]-crop.box[0],crop.box[3]-crop.box[1])/224,
    center:[cos*(rx-tx)-sin*(ry-ty)+pre.bias[0],sin*(rx-tx)+cos*(ry-ty)+pre.bias[1]]};
}

export async function createOnnxHandDetector({modelBase='./models/hand-landmarks/',maxHands=2,presenceThreshold=.8}={}){
  const ort=await import('https://cdn.jsdelivr.net/npm/onnxruntime-web@1.23.2/dist/ort.min.mjs');
  ort.env.wasm.numThreads=1;ort.env.wasm.wasmPaths='https://cdn.jsdelivr.net/npm/onnxruntime-web@1.23.2/dist/';
  const options={executionProviders:['wasm'],graphOptimizationLevel:'all'};
  const manifest=await(await fetch(modelBase+'manifest.json',{cache:'no-cache'})).json();
  async function load(name){
    const response=await fetch(modelBase+name);if(!response.ok)throw Error('Hand model unavailable: '+name);
    const data=await response.arrayBuffer(),digest=await crypto.subtle.digest('SHA-256',data);
    const hash=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');
    if(hash!==manifest.models?.[name]?.sha256)throw Error('Hand model integrity mismatch: '+name);
    return ort.InferenceSession.create(data,options);
  }
  const palm=await load('palm_detection_mediapipe_2023feb.onnx');
  const hand=await load('handpose_estimation_mediapipe_2023feb.onnx');
  let closed=false;
  const api={
    async detect(source){
      if(closed)throw Error('Hand detector is closed');const start=performance.now();
      const width=source.width,height=source.height,ratio=192/Math.max(width,height),w=Math.trunc(width*ratio),h=Math.trunc(height*ratio);
      const left=Math.floor((192-w)/2),top=Math.floor((192-h)/2),input=canvas(192,192),ctx=input.getContext('2d');
      ctx.fillStyle='black';ctx.fillRect(0,0,192,192);ctx.drawImage(source,0,0,width,height,left,top,w,h);
      const tensor=rgbTensor(input,ort);let out;
      try{out=await palm.run({[palm.inputNames[0]]:tensor});}finally{tensor.dispose();}
      const candidates=decodePalms(out.Identity.data,out.Identity_1.data,width,height,[Math.trunc(left/ratio),Math.trunc(top/ratio)],.5,maxHands);
      Object.values(out).forEach(t=>t.dispose());
      const landmarks=[],worldLandmarks=[],handedness=[],quality=[];
      for(const candidate of candidates){
        const prep=prepareHand(source,candidate);if(!prep)continue;const tensor=rgbTensor(prep.input,ort);let result;
        try{result=await hand.run({[hand.inputNames[0]]:tensor});}finally{tensor.dispose();}
        const presence=result.Identity_1.data[0];
        if(presence>=presenceThreshold){
          const xyz=result.Identity.data,world=result.Identity_3.data,side=result.Identity_2.data[0],points=[],metric=[];
          for(let i=0;i<21;i++){
            const x=(xyz[i*3]-112)*prep.scale,y=(xyz[i*3+1]-112)*prep.scale;
            points.push({x:(x*prep.cos-y*prep.sin+prep.center[0])/width,y:(x*prep.sin+y*prep.cos+prep.center[1])/height,z:xyz[i*3+2]*prep.scale/width});
            metric.push({x:world[i*3]*prep.cos-world[i*3+1]*prep.sin,y:world[i*3]*prep.sin+world[i*3+1]*prep.cos,z:world[i*3+2]});
          }
          landmarks.push(points);worldLandmarks.push(metric);handedness.push([{categoryName:side>.5?'Right':'Left',score:Math.max(side,1-side)}]);
          quality.push({palmScore:candidate.score,presenceScore:presence});
        }
        Object.values(result).forEach(t=>t.dispose());
      }
      return {landmarks,worldLandmarks,handedness,quality,inferenceMs:performance.now()-start,backend:'onnx-wasm'};
    },
    async searchRegion(source,index){
      // Uniform, label-blind multi-scale proposals, not a special crop for any
      // test letter. Only one proposal is processed per recovery frame.
      const size=index%10<5?.7:.85,k=index%5,edge=1-size;
      const offsets=[[0,0],[edge,0],[0,edge],[edge,edge],[edge/2,edge/2]],offset=offsets[k];
      const x=Math.round(offset[0]*source.width),y=Math.round(offset[1]*source.height),w=Math.round(size*source.width),h=Math.round(size*source.height);
      const crop=canvas(w,h);crop.getContext('2d').drawImage(source,x,y,w,h,0,0,w,h);
      const result=await api.detect(crop);
      result.landmarks=result.landmarks.map(points=>points.map(p=>({x:(x+p.x*w)/source.width,y:(y+p.y*h)/source.height,z:p.z*w/source.width})));
      result.quality=result.quality.map(q=>({...q,region:[x,y,w,h],source:'multiscale-detection'}));return result;
    },
    async track(source,previous){
      const start=performance.now(),ids=[0,5,9,13,17,1,2],points=ids.map(i=>[previous[i].x*source.width,previous[i].y*source.height]);
      const box=[Math.min(...points.map(p=>p[0])),Math.min(...points.map(p=>p[1])),Math.max(...points.map(p=>p[0])),Math.max(...points.map(p=>p[1]))];
      const prep=prepareHand(source,{box,points});if(!prep)return {landmarks:[],quality:[],inferenceMs:performance.now()-start};
      const tensor=rgbTensor(prep.input,ort);let r;
      try{r=await hand.run({[hand.inputNames[0]]:tensor});}finally{tensor.dispose();}
      const presence=r.Identity_1.data[0],landmarks=[],quality=[];
      if(presence>=presenceThreshold){const xyz=r.Identity.data,p=[];
        for(let i=0;i<21;i++){const x=(xyz[i*3]-112)*prep.scale,y=(xyz[i*3+1]-112)*prep.scale;p.push({x:(x*prep.cos-y*prep.sin+prep.center[0])/source.width,y:(x*prep.sin+y*prep.cos+prep.center[1])/source.height,z:xyz[i*3+2]*prep.scale/source.width});}
        landmarks.push(p);quality.push({palmScore:null,presenceScore:presence,source:'fresh-landmark-inference-on-tracked-roi'});
      }
      Object.values(r).forEach(t=>t.dispose());return {landmarks,quality,inferenceMs:performance.now()-start,backend:'onnx-wasm'};
    },
    async close(){if(closed)return;closed=true;await palm.release();await hand.release();}
  };
  return api;
}
