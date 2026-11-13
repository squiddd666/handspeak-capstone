import assert from 'node:assert/strict';
import {createAutomaticWordCapture} from '../automatic-word-capture.js';
let wall=0,delay=null,start=null,startWall=null;
const nativeSet=setTimeout,nativeClear=clearTimeout;
globalThis.setTimeout=(fn,ms)=>{delay=ms;return 1;};globalThis.clearTimeout=()=>{};
const video={currentTime:0,srcObject:{getVideoTracks:()=>[{readyState:'live'}]}};
const hand=x=>Array.from({length:21},(_,i)=>({x:.4+(i%5)*.01+x,y:.4+Math.floor(i/5)*.01,z:0}));
const capture=createAutomaticWordCapture({video,clock:()=>wall,canWatch:()=>true,onStart:info=>{start=info.startMediaTime;startWall=wall;return 1;},onClip:()=>{},onDiscard:()=>{},createRecorder:()=>({state:'inactive',start(){this.state='recording';},stop(){this.state='inactive';this.onstop?.();}})});
try{
 for(wall=0;wall<=5000;wall+=100){video.currentTime=wall/1000;const sourceTime=wall-(wall<1500?600:100);capture.frame(wall<3000?[]:[hand((wall/100)%2*.03)],sourceTime);if(start!==null)break;}
 assert.notEqual(start,null);
 assert.equal(delay,8000-(startWall-start*1000),'worker lag must not reduce the actual video recording budget');
 capture.cancel();
}finally{globalThis.setTimeout=nativeSet;globalThis.clearTimeout=nativeClear;}
console.log('PASS: recording budget uses real capture time, independent of changing worker timestamp lag.');
