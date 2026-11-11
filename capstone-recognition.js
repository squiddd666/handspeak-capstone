const POSE_INDICES=[0,2,5,11,12,13,14];
const friendly=label=>label.replace(/[12]$/,'').replaceAll('-',' ').replaceAll('/',' / ');

export function createCapstoneRecognition({isRunning,startCamera,onWord,onStatus,prepare}){
  const $=selector=>document.querySelector(selector);
  let available=false,pose=null,capture=null,pending='',lastPoseAt=-Infinity,request=null,holisticBusy=false,vocabMode='core';
  const status=$('#capstoneStatus'),record=$('#capstoneRecord'),accept=$('#capstoneAccept');
  const TIERS={core:{name:'core',count:7,acc:'92.4%'},extended:{name:'extended',count:19,acc:'77%'},full:{name:'full',count:100,acc:'74.4%'}};
  function message(value){status.textContent=value;}
  function controls(){record.disabled=!available||Boolean(capture||request);accept.disabled=!pending;}
  async function refresh(){
    try{
      const response=await fetch('/api/capstone-asl/status',{cache:'no-store'}),data=await response.json();
      if(!response.ok||!Array.isArray(data.labels)||data.labels.length!==100)throw Error();
      available=true;
      vocabMode=$('#capstoneVocabMode')?.value||'core';
      if(!TIERS[vocabMode])vocabMode='core';
      showVocabulary(data);
      const tier=TIERS[vocabMode];
      message(`${tier.count}-word ${tier.name} vocabulary ready (${tier.acc} top-1). Record one complete sign for four seconds; review the top prediction.`);
    }catch{message('The 100-word model is unavailable. Reload the page to retry.');}
    controls();
  }
  function showVocabulary(data){
    const names=vocabMode==='core'?(data.coreLabels||data.labels)
      :vocabMode==='extended'?(data.extendedLabels||data.labels):data.labels;
    $('#capstoneVocabulary').textContent=names.map(friendly).join(' · ');
    const summary=$('#capstoneWords details.camera-tip summary');
    if(summary)summary.textContent=vocabMode==='full'?'See all 100 available signs':`See the ${names.length} verified signs`;
  }
  async function loadPose(){
    if(pose)return;
    message('Loading full-body and hand tracking…');
    if(!window.Holistic)await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='https://cdn.jsdelivr.net/npm/@mediapipe/holistic@0.5.1675471629/holistic.js';script.onload=resolve;script.onerror=()=>reject(Error('Holistic tracker download failed'));document.head.append(script);});
    pose=new window.Holistic({locateFile:file=>`https://cdn.jsdelivr.net/npm/@mediapipe/holistic@0.5.1675471629/${file}`});
    // Phone / narrow layouts cannot sustain Holistic complexity 1 during a 4s
    // virtual-camera take (DEMAND repeatedly finished with 2–3 tracked frames).
    // Complexity 0 keeps pose+hand samples above the 5-frame gate without
    // changing the server ST-GCN vocabulary or confidence gates.
    const phone=typeof window!=='undefined'&&window.innerWidth>0&&window.innerWidth<500;
    pose.setOptions({modelComplexity:phone?0:1,smoothLandmarks:true,minDetectionConfidence:phone?0.45:0.5,minTrackingConfidence:phone?0.45:0.5});
    pose.onResults(result=>{
      holisticBusy=false;if(!capture)return;
      const points=value=>value?.length===21?value.map(p=>[p.x,p.y,p.z||0]):null;
      if(!result.poseLandmarks)return;
      if(!result.leftHandLandmarks&&!result.rightHandLandmarks)return;
      capture.frames.push({pose:POSE_INDICES.map(i=>{const p=result.poseLandmarks[i];return[p.x,p.y,p.z||0];}),left:points(result.leftHandLandmarks),right:points(result.rightHandLandmarks)});
    });
  }
  function cancel(text='100-word recording canceled.'){capture=null;pending='';accept.disabled=true;record.disabled=!available;message(text);}
  async function begin(){
    if(!$('#capstoneConsent').checked){message('Enable landmark processing for this model first. Camera video is not uploaded.');return;}
    pending='';controls();
    try{
      prepare();
      if(!isRunning())await startCamera();
      if(!isRunning())return;
      await loadPose();
      message('Get ready… recording starts in 1.5 seconds. Keep your upper body and at least one hand visible.');
      record.disabled=true;
      setTimeout(()=>{if(!isRunning()){cancel('Start the camera and try again.');return;}capture={start:performance.now(),frames:[]};lastPoseAt=-Infinity;message('Recording for four seconds… perform one complete sign.');onStatus('—','Recording with the 100-word model…');},1500);
    }catch(error){cancel(`Could not load upper-body tracking: ${error.message||'reload and try again.'}`);}
  }
  async function finish(){
    const frames=capture?.frames||[];capture=null;
    if(frames.length<5){cancel(`Not enough tracked frames (${frames.length}/5). Keep your upper body and at least one hand visible.`);return;}
    request=new AbortController();controls();message('Analyzing the recorded landmarks on the server…');
    const timeout=setTimeout(()=>request?.abort(),20000);
    try{
      const response=await fetch('/api/capstone-asl',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({consent:true,frames,vocabulary:vocabMode}),signal:request.signal});
      const data=await response.json();if(!response.ok)throw Error(data.error||'Recognition failed');
      pending=data.predictions?.[0]?.label||'';
      const names=(data.predictions||[]).map((item,index)=>`${index+1}. ${friendly(item.label)}`).join(' · ');
      const scope=`${data.vocabularySize||TIERS[vocabMode].count}-word ${data.vocabulary||vocabMode}`;
      if(!pending){
        message(data.lowConfidence
          ?`No confident match in the ${TIERS[vocabMode].count}-word ${vocabMode} vocabulary. Sign again, or widen the vocabulary.`
          :'No prediction returned. Try recording again.');
        onStatus('No reliable match',data.lowConfidence
          ?`${TIERS[vocabMode].count}-word model found no confident match — nothing added.`
          :'100-word model prediction — verify before adding. Scores are not calibrated confidence.');
        return;
      }
      message(`Possible match: ${friendly(pending)}. Top five (${scope}): ${names}. Verify before adding.`);
      onStatus(pending?friendly(pending):'No reliable match','100-word model prediction — verify before adding. Scores are not calibrated confidence.');
    }catch(error){message(error.name==='AbortError'?'Recognition timed out. Try again.':error.message);pending='';}
    finally{clearTimeout(timeout);request=null;controls();}
  }
  function frame(detection,now,video){
    if(!capture||!pose||holisticBusy||now-lastPoseAt<65)return;
    lastPoseAt=now;holisticBusy=true;
    pose.send({image:video}).catch(error=>{holisticBusy=false;cancel(`Tracking stopped: ${error.message}`);});
    if(now-capture.start>=4000)void finish();
  }
  record.addEventListener('click',()=>void begin());
  $('#capstoneCancel').addEventListener('click',()=>cancel());
  $('#capstoneVocabMode')?.addEventListener('change',()=>void refresh());
  accept.addEventListener('click',()=>{if(pending&&onWord(friendly(pending))!==false){message(`Added ${friendly(pending)} to the draft. Review it before speaking.`);pending='';controls();}});
  window.addEventListener('pagehide',()=>{request?.abort();pose?.close?.();});
  void refresh();controls();
  return {frame,cancel,isCapturing:()=>Boolean(capture)};
}
