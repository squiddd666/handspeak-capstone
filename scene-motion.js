// Local, low-resolution scene-motion evidence. Only the previous thumbnail is
// retained in memory; no images are saved, emitted as events, or uploaded here.
export function createSceneMotion(){
 let canvas=null,context=null,previous=null,lastMediaTime=-1,quietSince=null,observations=0,noise=.0008;
 function reset(){previous=null;lastMediaTime=-1;quietSince=null;observations=0;noise=.0008;if(canvas){canvas.width=0;canvas.height=0;}canvas=null;context=null;}
 function sample(video,now,learnNoise=true){
  try{
   if(video.readyState<2||video.currentTime===lastMediaTime)return {available:Boolean(previous),quietForMs:0,observations:0};
   lastMediaTime=video.currentTime;
   canvas??=document.createElement('canvas');canvas.width=64;canvas.height=48;
   context??=canvas.getContext('2d',{willReadFrequently:true});context.drawImage(video,0,0,64,48);
   const rgba=context.getImageData(0,0,64,48).data;
   const gray=new Float32Array(64*48);
   for(let i=0;i<gray.length;i++)gray[i]=(.299*rgba[i*4]+.587*rgba[i*4+1]+.114*rgba[i*4+2])/255;
   if(!previous){previous=gray;return {available:Boolean(previous),quietForMs:0,observations:0};}
   const tiles=[];
   for(let y=0;y<48;y+=16)for(let x=0;x<64;x+=16){let sum=0;for(let dy=0;dy<16;dy++)for(let dx=0;dx<16;dx++){const i=(y+dy)*64+x+dx;sum+=Math.abs(gray[i]-previous[i]);}tiles.push(sum/256);}
   previous=gray;tiles.sort((a,b)=>b-a);const energy=tiles[0];
   const threshold=Math.min(.012,Math.max(.004,noise*3+.002));
   if(energy<=threshold){quietSince??=now;observations++;if(learnNoise&&energy<.006)noise=noise*.98+energy*.02;}
   else{quietSince=null;observations=0;}
   return {available:true,quietForMs:quietSince===null?0:now-quietSince,observations,energy,threshold};
  }catch{return {available:Boolean(previous),quietForMs:0,observations:0};}
 }
 return {sample,reset};
}
