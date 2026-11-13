import assert from 'node:assert/strict';
import {createWordBoundaries} from '../word-boundaries.js';
const hand=()=>Array.from({length:21},(_,i)=>({x:.4+(i%5)*.01,y:.4+Math.floor(i/5)*.01,z:0}));
function trial(pixels){const d=createWordBoundaries(),events=[];for(let t=0;t<=700;t+=100){const h=hand();if(t%200)for(const i of [4,8,12])h[i].x+=.008;const e=d.observe([h],t,1,{available:true,energy:pixels?.02:0,threshold:.004});if(e)events.push(e);}return events;}
assert.ok(trial(true).some(e=>e.type==='start'),'small finger articulation plus pixel movement starts capture');
assert.equal(trial(false).length,0,'same landmark fluctuation without pixel movement does not start');
console.log('PASS: corroborated local articulation, no still-pixel false onset.');
