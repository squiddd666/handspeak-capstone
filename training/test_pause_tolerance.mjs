import assert from 'node:assert/strict';
import {createWordBoundaries} from '../word-boundaries.js';
const hand=x=>Array.from({length:21},(_,i)=>({x:.4+(i%5)*.01+x,y:.4+Math.floor(i/5)*.01,z:0}));
{
 const d=createWordBoundaries(),events=[];
 for(let t=0;t<=1500;t+=100){const e=d.observe([hand((t/100)%2*.03)],t,1,{available:true,energy:.1,quietForMs:0});if(e)events.push(e);}
 for(let t=1600;t<=5800;t+=100){const e=d.observe([hand(.03+((t/100)%2?-.0015:.0015))],t,1,{available:true,energy:.1,quietForMs:0});if(e)events.push(e);}
 assert.ok(events.some(e=>e.type==='end'),'a held pose with bounded tracking jitter must finish even with moving background');
}
{
 const d=createWordBoundaries(),events=[];
 for(let t=0;t<=1500;t+=100){const e=d.observe([hand((t/100)%2*.03)],t);if(e)events.push(e);}
 for(let t=1600;t<=6500;t+=100){const e=d.observe([hand(.03+(t-1600)/100*.002)],t);if(e)events.push(e);}
 assert.equal(events.filter(e=>e.type==='end').length,0,'slow continuing movement must not be called a stable hold');
}
console.log('PASS: bounded hand jitter with moving background ends; slow continuing movement does not.');
