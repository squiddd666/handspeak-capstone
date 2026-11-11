import {createLetterCamera} from '../letter-camera.js';
import assert from 'node:assert/strict';
let worker,cb,cancelled;
globalThis.Worker=class{constructor(){worker=this;this.messages=[]}postMessage(m){this.messages.push(m)}terminate(){}};
globalThis.createImageBitmap=async()=>({close(){}});
const video={requestVideoFrameCallback(f){cb=f;return 12},cancelVideoFrameCallback(id){cancelled=id}};
const cam=createLetterCamera({onDetection(){},onError(e){throw Error(e)}});
worker.onmessage({data:{type:'ready',modelVersion:1}});await cam.ready;
cam.push(video);cb(0,{mediaTime:.1});await Promise.resolve();
cb(0,{mediaTime:.1});cb(0,{mediaTime:.2});
assert.equal(cam.diagnostics().submitted,1);assert.equal(cam.diagnostics().duplicates,1);assert.equal(cam.diagnostics().dropped,1);
assert.equal(worker.messages[1].timestamp,100);cam.close();assert.equal(cancelled,12);
console.log('Decoded timestamps, duplicate guard, backpressure and cancellation passed');

