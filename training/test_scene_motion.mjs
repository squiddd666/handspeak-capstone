import assert from 'node:assert/strict';
import {createSceneMotion} from '../scene-motion.js';
let pixels=new Uint8ClampedArray(64*48*4).fill(100);
globalThis.document={createElement:()=>({getContext:()=>({drawImage(){},getImageData:()=>({data:pixels})})})};
const s=createSceneMotion(),v={readyState:4,currentTime:0};let r;
for(let t=0;t<=1400;t+=100){v.currentTime=t/1000;r=s.sample(v,t);}
assert.ok(r.quietForMs>=1100&&r.observations>=7);
assert.equal(s.sample(v,5000).quietForMs,0,'repeated video frame must not manufacture pause evidence');
v.currentTime=2;pixels=new Uint8ClampedArray(64*48*4).fill(240);r=s.sample(v,2000);assert.equal(r.quietForMs,0,'scene movement resets evidence');
for(let t=2100;t<=3500;t+=100){v.currentTime=t/1000;r=s.sample(v,t,false);}
assert.ok(r.quietForMs>=1100);
// A small moving area must not be averaged away by the rest of the still scene.
for(let i=0;i<8;i++){pixels[i*4]=0;pixels[i*4+1]=0;pixels[i*4+2]=0;}v.currentTime=3.6;r=s.sample(v,3600,false);assert.equal(r.quietForMs,0);
s.reset();console.log('PASS scene motion: fresh-frame evidence, scene changes, local movement, reset.');
