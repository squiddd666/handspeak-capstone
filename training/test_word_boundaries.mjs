import assert from 'node:assert/strict';
import {createWordBoundaries} from '../word-boundaries.js';
const hand=x=>Array.from({length:21},(_,i)=>({x:.4+(i%5)*.01+x,y:.4+Math.floor(i/5)*.01,z:0}));
function setup(){const d=createWordBoundaries(),events=[];return {d,events,step(t,h){const e=d.observe(h,t);if(e)events.push({...e,time:t});}};}
const move=(s,a,b)=>{for(let t=a;t<=b;t+=100)s.step(t,[hand((t/100)%2*.025)]);};
const hold=(s,a,b)=>{for(let t=a;t<=b;t+=100)s.step(t,[hand(.025)]);};
const missing=(s,a,b)=>{for(let t=a;t<=b;t+=100)s.step(t,[]);};
{
 const s=setup();for(let t=0;t<10000;t+=100)s.step(t,[hand((t/100)%2*.0002)]);assert.equal(s.events.length,0,'small jitter is not a sign');
}
{
 const s=setup();hold(s,0,2000);s.step(2100,[hand(.055)]);s.step(2200,[hand(.025)]);hold(s,2300,6000);assert.equal(s.events.length,0,'isolated tracking spike must not start capture');
}
{
 const s=setup();move(s,0,1000);hold(s,1100,1600);assert.equal(s.events.filter(e=>e.type==='end').length,0,'internal pause is not an endpoint');move(s,1700,2300);hold(s,2400,5000);assert.deepEqual(s.events.map(e=>e.type),['start','end']);assert.ok(s.events[1].time>=3200);assert.equal(s.events[1].quality.endpoint,'stable-pause');
}
{
 const s=setup();move(s,0,1000);missing(s,1100,1400);move(s,1500,2200);hold(s,2300,5000);assert.deepEqual(s.events.map(e=>e.type),['start','end'],'temporary occlusion must not split a sign');
}
{
 const s=setup();move(s,0,1000);missing(s,1100,3500);assert.equal(s.events.filter(e=>e.type==='end').length,0);assert.ok(s.events.some(e=>e.reason==='hands-lost-while-scene-not-stable'));
}
{
 const s=setup();move(s,0,1000);s.step(1900,[hand(.1)]);assert.ok(s.events.some(e=>e.reason==='timing-gap'));assert.equal(s.events.filter(e=>e.type==='end').length,0);
}
{
 const s=setup();move(s,0,8000);assert.ok(s.events.some(e=>e.reason==='no-stable-end'));assert.equal(s.events.filter(e=>e.type==='end').length,0);
}
{
 const s=setup();move(s,0,1300);hold(s,1400,1800);missing(s,1900,3500);assert.equal(s.events.filter(e=>e.type==='end').length,1);assert.equal(s.events.find(e=>e.type==='end').quality.endpoint,'exit-after-stable-hold');
}
{
 const s=setup();s.step(0,[null]);s.step(100,[[{}]]);s.step(100,'bad');s.step(-1,[]);assert.equal(s.events.length,0);
}
{
 const d=createWordBoundaries();let events=[];
 for(let t=0;t<=1100;t+=100){const e=d.observe([hand((t/100)%2*.025)],t);if(e)events.push(e);}
 for(let t=1200;t<=3500;t+=100){const e=d.observe([],t,1,{quietForMs:t-1200,observations:(t-1200)/100});if(e)events.push(e);}
 assert.ok(events.some(e=>e.type==='end'&&e.quality.endpoint==='scene-motion-corroborated'));
}
{
 const d=createWordBoundaries();let events=[];
 for(let t=0;t<=1100;t+=100){const e=d.observe([hand((t/100)%2*.025)],t);if(e)events.push(e);}
 for(let t=1200;t<=3500;t+=100){const e=d.observe([],t,1,{quietForMs:0,observations:0,energy:.1});if(e)events.push(e);}
 assert.equal(events.filter(e=>e.type==='end').length,0,'moving scene cannot confirm an endpoint after lost tracking');
 assert.ok(events.some(e=>e.type==='reject'));
}
for(const step of [70,100,160,200]){
 const d=createWordBoundaries(),events=[];
 for(let t=0;t<=6000;t+=step){const offset=t<=1400?(Math.floor(t/step)%2)*.03:.03;const e=d.observe([hand(offset)],t);if(e)events.push(e);}
 assert.deepEqual(events.map(e=>e.type),['start','end'],'supported frame cadence '+step);
}
{
 const d=createWordBoundaries();d.observe([hand(0)],0);
 assert.equal(d.observe([hand(.025)],100,1,{available:true,energy:.1,threshold:.004}),null);
 assert.equal(d.observe([hand(0)],200,1,{available:true,energy:.1,threshold:.004}).type,'start','short real movement can use corroborating video motion');
}
{
 const d=createWordBoundaries();d.observe([hand(0)],0);d.observe([hand(.025)],100,1,{available:true,energy:0,threshold:.004});
 assert.equal(d.observe([hand(0)],200,1,{available:true,energy:0,threshold:.004}),null,'landmark jitter with still pixels cannot take the fast onset path');
}
{
 const s=setup();move(s,0,1000);
 const cropped=hand(.025).map(p=>({...p,y:p.y-.7}));
 for(let t=1100;t<=1900;t+=100)s.step(t,[cropped]);
 assert.ok(s.events.some(e=>e.reason==='hands-cropped'));
 assert.equal(s.events.filter(e=>e.type==='end').length,0,'cropped hands must not cause a confident endpoint');
}
{
 const s=setup(),cropped=hand(0).map(p=>({...p,y:p.y-.7}));
 for(let t=0;t<=4000;t+=100)s.step(t,[cropped]);
 assert.equal(s.events.length,0,'raising a cropped palm is not a complete word');
}
console.log('PASS 19 boundary cases: jitter, spike, internal pause, occlusion, lost tracking, gaps, no endpoint, held exit, invalid frames.');
