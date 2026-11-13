export function createAdaptiveGate({getThreshold,onStart,onEnd,onStuck=()=>{}}){
 const PRE_MS=650,DROP_MS=250,IDLE_MS=850,MAX_MS=5000,MIN_HOT=2;
 let pre=[],active=false,burst=[],first=0,lastMotion=0,goneSince=0,hot=0,stuck=false;
 const visible=v=>v&&v.length===96&&v.slice(0,84).some(x=>x!==0);
 function end(){
  if(!active)return;active=false;
  let last=burst.length-1;while(last>=0&&!visible(burst[last].v))last--;
  const clipped=burst.slice(0,last+1);const result=hot>=MIN_HOT&&clipped.length>=4?clipped.map(x=>x.v):null;
  burst=[];hot=0;goneSince=0;lastMotion=0;stuck=false;onEnd(result);
 }
 return (vec,ts,motion)=>{
  const has=visible(vec),moving=has&&motion>getThreshold();
  if(active){burst.push({v:vec,t:ts});if(moving){lastMotion=ts;hot++}if(!has){if(!goneSince)goneSince=ts;if(ts-goneSince>=DROP_MS){end();return}}else goneSince=0;
   if(ts-first>=MAX_MS){end();return}
   if(has&&ts-lastMotion>=IDLE_MS&&ts-first>=500){end();return}
   if(!stuck&&ts-first>2500){stuck=true;onStuck()}
  }else if(moving){active=true;first=ts;lastMotion=ts;goneSince=0;hot=1;burst=pre.filter(x=>x.t>=ts-PRE_MS&&visible(x.v));burst.push({v:vec,t:ts});onStart()}
  pre.push({v:vec,t:ts});while(pre.length&&pre[0].t<ts-PRE_MS-100)pre.shift();
 };
}
