import assert from 'node:assert/strict';
import {createAutomaticWordCapture} from '../automatic-word-capture.js';
function setup(){
 let busy=false,clips=[],discards=[],recorders=[],starts=[];
 const video={currentTime:0,srcObject:{getVideoTracks:()=>[{readyState:'live'}]}};
 const capture=createAutomaticWordCapture({video,clock:()=>video.currentTime*1000,canWatch:()=>!busy,
  onStart:info=>{starts.push(info);return starts.length;},onClip:clip=>{clips.push(clip);busy=true;},onDiscard:text=>discards.push(text),
  createRecorder:()=>{const r={state:'inactive',mimeType:'video/webm',start(){this.state='recording';},stop(){if(this.state==='inactive')return;this.state='inactive';this.ondataavailable?.({data:new Blob(['test-only recorder bytes'])});this.onstop?.();}};recorders.push(r);return r;}});
 const hand=offset=>Array.from({length:21},(_,i)=>({x:.4+(i%5)*.01+offset,y:.4+Math.floor(i/5)*.01,z:0}));
 return {capture,clips,discards,starts,recorders,hand,frame(t,h=[]){video.currentTime=t/1000;capture.frame(h,t);},setBusy:v=>busy=v};
}
{
 const s=setup();for(let t=0;t<=3000;t+=100)s.frame(t);
 assert.equal(s.clips.length,0);assert.ok(s.recorders.filter(r=>r.state==='recording').length<=5);
 for(let t=3100;t<=4500;t+=100)s.frame(t,[s.hand((t/100)%2*.025)]);
 for(let t=4600;t<=5800;t+=100)s.frame(t,[s.hand(.025)]);
 assert.equal(s.clips.length,1);assert.ok(s.clips[0].startMediaTime<3.1);assert.ok(s.clips[0].endMediaTime>=4.5);assert.ok(s.clips[0].endMediaTime-s.clips[0].startMediaTime<=8.25);
 s.setBusy(false);for(let t=5900;t<=9000;t+=100)s.frame(t,[s.hand(.025)]);
 assert.equal(s.clips.length,1,'holding a pose must not duplicate a prediction');
 for(let t=9100;t<=10100;t+=100)s.frame(t,[s.hand((t/100)%2*.025)]);
 for(let t=10200;t<=12600;t+=100)s.frame(t,[s.hand(.025)]);
 assert.equal(s.clips.length,2,'new movement after a quiet interval must rearm without hiding the hands');s.capture.cancel();
 assert.equal(s.recorders.filter(r=>r.state==='recording').length,0);
}
{
 const s=setup();for(let t=0;t<=2000;t+=100)s.frame(t);
 for(let t=2100;t<=3800;t+=100)s.frame(t,[s.hand(0)]);
 assert.equal(s.clips.length,0,'static appearance alone is not a moving word');s.capture.cancel();
}
{
 const s=setup();for(let t=0;t<=2000;t+=100)s.frame(t);
 s.frame(2100,[s.hand(0)]);s.frame(2200,[s.hand(.03)]);s.capture.cancel();
 assert.equal(s.clips.length,0,'cancel must discard video rather than submit');
 assert.equal(s.recorders.filter(r=>r.state==='recording').length,0);
 s.capture.waitForQuiet(2300);
 for(let t=2400;t<=4000;t+=100)s.frame(t,[s.hand((t/100)%2*.025)]);
 assert.equal(s.clips.length,0,'cancel must not immediately recapture the same continuing movement');
 for(let t=4100;t<=5500;t+=100)s.frame(t,[s.hand(.025)]);
 for(let t=5600;t<=6500;t+=100)s.frame(t,[s.hand((t/100)%2*.025)]);
 for(let t=6600;t<=9000;t+=100)s.frame(t,[s.hand(.025)]);
 assert.equal(s.clips.length,1,'a new sign after a quiet interval may resume');s.capture.cancel();
}
{
 const s=setup();for(let t=0;t<=1500;t+=100)s.frame(t,[s.hand((t/100)%2*.025)]);
 assert.equal(s.starts.length,0,'startup mid-gesture cannot submit a tail-only buffer');
 for(let t=1600;t<=4000;t+=100)s.frame(t,[s.hand(.025)]);
 for(let t=4100;t<=5100;t+=100)s.frame(t,[s.hand((t/100)%2*.025)]);
 for(let t=5200;t<=6800;t+=100)s.frame(t,[s.hand(.025)]);
 assert.equal(s.clips.length,1,'complete new gesture after warmup is captured');
 assert.ok(s.clips[0].startMediaTime<=4.1-3,'late onset retains at least three seconds of real pre-roll');
 s.capture.cancel();
}
console.log('PASS: bounded pre-roll, pause detection, blank/static rejection, no duplicate hold, cancellation.');
