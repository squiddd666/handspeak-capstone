import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const worker = fs.readFileSync(new URL('../letter-detection-worker.js',import.meta.url),'utf8');
async function run(profile,primaryHasHand){
 const primary=Array.from({length:21},(_,i)=>({x:.3+i/100,y:.5,z:0}));
 const recovery=primary.map(p=>({...p,x:p.x+.2}));
 const posted=[];
 const pixels=new Uint8ClampedArray(512);pixels.fill(255,256);
 const sandbox={profile,primaryHasHand,primary,recovery,recoveryCalls:0,performance,
  self:{postMessage:m=>posted.push(m)},OffscreenCanvas:class{
   constructor(w,h){this.width=w;this.height=h}
   getContext(){return {drawImage(){},getImageData:()=>({data:pixels})}}
  }};
 vm.createContext(sandbox);
 vm.runInContext(worker+`
  preserveUsableMotion=profile;
  imageDetector={detect:()=>({landmarks:primaryHasHand?[primary]:[]})};
  videoDetector={detectForVideo:()=>({landmarks:primaryHasHand?[primary]:[]})};
  isUsableLetterHand=p=>p.length===21;sameObservedHand=()=>true;classifyLetter=()=>null;
  onnx={detect:async()=>{recoveryCalls++;return {landmarks:[recovery],quality:[]}}};
 `,sandbox);
 await sandbox.self.onmessage({data:{type:'frame',id:1,timestamp:250,bitmap:{width:640,height:480,close(){}}}});
 assert.equal(posted[0].type,'frame');
 assert.equal(posted[0].timestamp,250);
 return [sandbox.recoveryCalls,posted[0].motionHands[0],primary,recovery];
}
let [calls,hand,primary]=await run(true,true);assert.equal(calls,0);assert.equal(hand,primary);
let legacy=await run(false,true);assert.equal(legacy[0],1);assert.equal(legacy[1],legacy[3]);
let missing=await run(true,false);assert.equal(missing[0],1);assert.equal(missing[1],missing[3]);
console.log('Continuity profile preserves a valid abstaining hand; genuine misses still reach recovery; legacy behavior unchanged.');
