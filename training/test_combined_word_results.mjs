import assert from 'node:assert/strict';
import {combineWordResults as combine} from '../combined-word-results.js';
const same=combine({label:'food'},{label:'FOOD',confidence:.4});
assert.equal(same.length,1);assert.deepEqual(same[0].sources,['Browser','OpenHands']);
assert.equal(same[0].confidence,.4);
const conflict=combine({label:'FOOD'},{label:'GIVE',confidence:.99});
assert.deepEqual(conflict.map(x=>x.word),['FOOD','GIVE']); // no cross-model score ranking
assert.equal(combine({label:'FOOD'},{error:'Unavailable'})[0].word,'FOOD');
assert.equal(combine(null,{label:'BEFORE',confidence:.8})[0].word,'BEFORE');
assert.equal(combine(null,null).length,0);
console.log('PASS combined results: agreement, deduplication, conflict, fallback, rejection.');
