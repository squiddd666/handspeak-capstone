import fs from 'node:fs';
import {encodeMotion} from '../motion-model.js';
import {recognizeExpandedMotion} from '../expanded-motion.js';
import {recognizeBinaryTemporal} from '../hello-binary.js';
import {recognizeTemporalWord} from '../temporal-word-model.js';
const [inputPath,outputPath]=process.argv.slice(2);
const input=JSON.parse(fs.readFileSync(inputPath,'utf8'));
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const base=read('models/asl-words.json'),extra=read('models/asl-extra-words.json');
const binary=['hello','baby','water'].map(n=>read(`models/${n}-binary.json`));
const sequence=encodeMotion(input.rawFrames,input.aspect);
if(input.mode==='research-encode')fs.writeFileSync(outputPath,JSON.stringify({sequence}));
else{
 let match=null;
 if(sequence){
  if(input.mode==='category')match=recognizeTemporalWord(read(input.modelPath),input.rawFrames,input.aspect);
  else{
   match=recognizeExpandedMotion(sequence,base.samples,base.parameters,input.mode==='expanded'?extra:null,base.cameraCompatibility);
   if(!match)for(const model of binary){match=recognizeBinaryTemporal(model,input.rawFrames,input.aspect);if(match)break;}
  }
 }
 fs.writeFileSync(outputPath,JSON.stringify({predicted:match?.label||null,confidence:match?.confidence??null,validSequence:Boolean(sequence)}));
}
