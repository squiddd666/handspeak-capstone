// Adapted from medhu0505/SignSpeak (MIT). See third_party/signspeak/LICENSE.
export function normalizeSignSpeak(points){
  if(!Array.isArray(points)||points.length!==21||!points.every(p=>[p.x,p.y,p.z].every(Number.isFinite)))return null;
  const wrist=points[0],m=points[9];
  const scale=Math.hypot(m.x-wrist.x,m.y-wrist.y,m.z-wrist.z);
  if(scale<1e-6)return null;
  const out=new Float32Array(63);
  points.forEach((p,i)=>{out[i*3]=-(p.x-wrist.x)/scale;out[i*3+1]=(p.y-wrist.y)/scale;out[i*3+2]=(p.z-wrist.z)/scale;});
  return out;
}
export function decodeSignSpeak(logits,threshold=.85){
  if(logits.length!==26||!Array.from(logits).every(Number.isFinite))throw Error('Invalid SignSpeak output: expected 26 finite logits');
  const max=Math.max(...logits),exp=Array.from(logits,v=>Math.exp(v-max)),sum=exp.reduce((a,b)=>a+b,0);
  const index=exp.indexOf(Math.max(...exp)),confidence=exp[index]/sum;
  return confidence>=threshold?{letter:String.fromCharCode(65+index),confidence}:null;
}
export async function createSignSpeakModel(){
  const ort=await import('https://cdn.jsdelivr.net/npm/onnxruntime-web@1.23.2/dist/ort.min.mjs');
  ort.env.wasm.numThreads=1;
  ort.env.wasm.wasmPaths='https://cdn.jsdelivr.net/npm/onnxruntime-web@1.23.2/dist/';
  const session=await ort.InferenceSession.create(new URL('./models/signspeak/asl.onnx',import.meta.url).href,{executionProviders:['wasm']});
  let frames=[],last=-Infinity,anchor=null;
  function reset(){frames=[];last=-Infinity;anchor=null;}
  return {reset,async frame(points,timestamp){
    if(timestamp<=last)return null;
    if(!points||timestamp-last>500||(anchor&&Math.hypot(points[0].x-anchor.x,points[0].y-anchor.y)>.25))reset();
    const normalized=points&&normalizeSignSpeak(points);
    if(!normalized){reset();return null;}
    if(timestamp===last)return null;
    last=timestamp;anchor=points[0];frames.push(normalized);if(frames.length>30)frames.shift();
    if(frames.length<30)return null;
    const sequence=new Float32Array(30*63);frames.forEach((f,i)=>sequence.set(f,i*63));
    const input=new ort.Tensor('float32',sequence,[1,30,63]);
    let outputs;
    try{outputs=await session.run({input});return decodeSignSpeak(outputs.logits.data);}
    finally{input.dispose?.();if(outputs)Object.values(outputs).forEach(v=>v.dispose?.());}
  }};
}
