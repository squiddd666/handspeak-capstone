import {temporalFeatures} from './temporal-motion/temporal-features.js';

function conv(input,weight,bias,dilation=1){
 const outputs=weight.length,length=input[0].length,pad=dilation*Math.floor(weight[0][0].length/2);
 return Array.from({length:outputs},(_,out)=>Array.from({length},(_,time)=>{
  let sum=bias[out];
  for(let channel=0;channel<input.length;channel++)for(let kernel=0;kernel<weight[out][channel].length;kernel++){
   const index=time+kernel*dilation-pad;
   if(index>=0&&index<length)sum+=input[channel][index]*weight[out][channel][kernel];
  }
  return sum;
 }));
}

export function binaryTemporalScore(model,row){
 let value=conv(temporalFeatures(row),model.weights['input.weight'],model.weights['input.bias']).map(channel=>channel.map(x=>Math.max(0,x)));
 [1,2,4].forEach((dilation,index)=>{
  const residual=conv(value,model.weights[`blocks.${index}.weight`],model.weights[`blocks.${index}.bias`],dilation);
  value=value.map((channel,c)=>channel.map((x,t)=>Math.max(0,x+residual[c][t])));
 });
 const pooled=[...value.map(channel=>channel.reduce((sum,x)=>sum+x,0)/channel.length),...value.map(channel=>Math.max(...channel))];
 const logit=model.weights['output.weight'][0].reduce((sum,weight,index)=>sum+weight*pooled[index],model.weights['output.bias'][0]);
 return 1/(1+Math.exp(-Math.max(-50,Math.min(50,logit))));
}

export function validBinaryTemporalModel(model){
 return Boolean(model&&model.version===1&&typeof model.word==='string'&&model.word
  &&model.encoding==='temporal-binary-v1'
  &&Number.isFinite(model.threshold)&&model.threshold>0&&model.threshold<=1&&model.weights);
}

export function recognizeBinaryTemporal(model,frames,aspect){
 if(!validBinaryTemporalModel(model)||!Array.isArray(frames)||frames.length<12)return null;
 const score=binaryTemporalScore(model,{rawFrames:frames,body:frames.map(()=>null),imageAspect:aspect});
 return score>=model.threshold?{label:model.word,confidence:score}:null;
}

export const helloBinaryScore=binaryTemporalScore;
export const validHelloBinaryModel=model=>validBinaryTemporalModel(model)&&model.word==='HELLO';
export const recognizeHelloBinary=(model,frames,aspect)=>validHelloBinaryModel(model)
 ?recognizeBinaryTemporal(model,frames,aspect):null;
