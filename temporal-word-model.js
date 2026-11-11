import {classify} from './temporal-motion/classifier.js?v=20261020-diagnostics-1';
export const TEMPORAL_ENCODING='hands-only-body-tips-residual-v1';
export const isTemporalWordModel=model=>model?.encoding===TEMPORAL_ENCODING;
export function validTemporalWordModel(model){
 if(!model||model.version!==1||!isTemporalWordModel(model)||model.featureMode!=='hands-only'
   ||!Array.isArray(model.labels)||model.labels.length!==1||!Array.isArray(model.outputLabels)
   ||model.outputLabels.length<2||model.outputLabels.length>256||new Set(model.outputLabels).size!==model.outputLabels.length
   ||!model.labels.every(l=>typeof l==='string'&&/^[A-Z][A-Z '-]{0,29}$/.test(l)&&model.outputLabels.includes(l))
   ||!Number.isFinite(model.threshold)||model.threshold<0||model.threshold>1
   ||!Number.isFinite(model.margin)||model.margin<0||model.margin>1
   ||!Array.isArray(model.weights)||model.weights.length!==1)return false;
 if(model.thresholdByLabel&&!model.labels.every(l=>Number.isFinite(model.thresholdByLabel[l])&&model.thresholdByLabel[l]>=model.threshold&&model.thresholdByLabel[l]<=1))return false;
 const shapes={mean:[1,175,1],scale:[1,175,1],'project.weight':[64,350,1],'project.bias':[64],'head.1.weight':[model.outputLabels.length,128],'head.1.bias':[model.outputLabels.length]};
 for(let b=0;b<3;b++)for(const [layer,shape] of [[0,[64,64,3]],[1,[64]],[4,[64,64,3]]]){
  shapes[`blocks.${b}.${layer}.weight`]=shape;shapes[`blocks.${b}.${layer}.bias`]=[64];
 }
 function tensor(value,shape){return shape.length?Array.isArray(value)&&value.length===shape[0]&&value.every(v=>tensor(v,shape.slice(1))):Number.isFinite(value);}
 const weights=model.weights[0];
 return Boolean(weights&&Object.entries(shapes).every(([key,shape])=>tensor(weights[key],shape))&&weights.scale[0].every(row=>row[0]>0));
}
export function recognizeTemporalWord(model,frames,aspect){
 const result=classify(model,frames,aspect);
 return result.label?{label:result.label,confidence:result.confidence}:null;
}
