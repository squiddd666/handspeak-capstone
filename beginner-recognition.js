const POSE_INDICES=[0,2,5,11,12,13,14];

export function createBeginnerRecognition({isRunning,startCamera,onWord,onStatus,prepare}){
  const $=s=>document.querySelector(s);
  let available=false,pose=null,capture=null,pending='',lastPoseAt=-Infinity,request=null,holisticBusy=false,labels=[];
  let countdown=null,deadline=null,generation=0,starting=false;
  let poseMode='',processingGeneration=null,lastCapturedVideoTime=-1,sourceTimestamp=0;
  const experimentalClock=new URLSearchParams(window.location.search).get('wordCapture')==='v9';
  let videoFrameId=null;
  function stopVideoClock(){
    if(videoFrameId!==null)$('#webcam')?.cancelVideoFrameCallback?.(videoFrameId);
    videoFrameId=null;
  }
  function startVideoClock(video,current){
    if(!experimentalClock||poseMode!=='target20'||!video.requestVideoFrameCallback)return;
    const next=(now,metadata)=>{
      videoFrameId=null;
      if(capture?.generation!==current)return;
      videoFrameId=video.requestVideoFrameCallback(next);
      frame(null,now,video,metadata.mediaTime);
    };
    videoFrameId=video.requestVideoFrameCallback(next);
  }
  const status=$('#beginnerStatus'),record=$('#beginnerRecord'),accept=$('#beginnerAccept');
  if(!status||!record||!accept)return {frame(){},cancel(){},isCapturing:()=>false};
  function message(value){status.textContent=value;}
  function modelName(){const mode=$('#beginnerVocabMode')?.value;return mode==='target20-passed'?'Passed offline checks preview':mode==='target20'?'20-word research preview':mode==='essential'?'Five-word research preview':'Beginner model';}
  function controls(){record.disabled=!available||Boolean(starting||countdown||capture||request);accept.disabled=!pending;}
  async function refresh(){
    try{
      const response=await fetch('/api/beginner-asl/status',{cache:'no-store'}),data=await response.json();
      available=Boolean(data.available&&Array.isArray(data.labels)&&data.labels.length);
      labels=data.labels||[];
      const count=$('#beginnerCount');if(count)count.textContent=available?`${labels.length} signs`:'Not trained';
      $('#beginnerVocabulary').textContent=labels.join(' · ')||'Model not trained yet';
      message(available
        ?`${labels.length} ready Beginner words online (≥70% held-out top-1). Record one complete sign for four seconds; review before adding. Live-camera accuracy is unverified.`
        :'Beginner model checkpoint not found yet. Deploy beginner-phase123-v2.pt to enable this panel.');
    }catch{available=false;message('Beginner model status unavailable.');}
    controls();
  }
  async function loadPose(){
    const wanted=['target20','target20-passed'].includes($('#beginnerVocabMode')?.value)?'target20':'holistic';
    if(pose&&poseMode===wanted)return;
    if(pose){pose.close?.();pose=null;holisticBusy=false;processingGeneration=null;}
    poseMode=wanted;
    message('Loading full-body and hand tracking…');
    // Target-20 uses the same Holistic body+hand profile as offline extraction.
    if(!window.Holistic)await new Promise((resolve,reject)=>{const script=document.createElement('script');script.src='https://cdn.jsdelivr.net/npm/@mediapipe/holistic@0.5.1675471629/holistic.js';script.onload=resolve;script.onerror=()=>reject(Error('Holistic tracker download failed'));document.head.append(script);});
    pose=new window.Holistic({locateFile:file=>`https://cdn.jsdelivr.net/npm/@mediapipe/holistic@0.5.1675471629/${file}`});
    pose.setOptions({modelComplexity:1,smoothLandmarks:true,minDetectionConfidence:.5,minTrackingConfidence:.5});
    pose.onResults(result=>{
      holisticBusy=false;if(!capture||processingGeneration!==capture.generation)return;
      capture.results++;
      const points=value=>value?.length===21?value.map(p=>[p.x,p.y,p.z||0]):null;
      if(!result.poseLandmarks)return;
      if(!result.leftHandLandmarks&&!result.rightHandLandmarks&&poseMode!=='target20')return;
      if(result.leftHandLandmarks||result.rightHandLandmarks)capture.handFrames++;
      capture.frames.push({timestampMs:poseMode==='target20'?sourceTimestamp:performance.now()-capture.start,pose:POSE_INDICES.map(i=>{const p=result.poseLandmarks[i];return[p.x,p.y,p.z||0];}),left:points(result.leftHandLandmarks),right:points(result.rightHandLandmarks)});
    });
    await pose.initialize();
    // Holistic's first send allocates graph resources and can block for seconds.
    // Do this BEFORE the countdown, never inside a supposedly timed recording.
    message('Preparing landmark tracking…');
    await pose.send({image:$('#webcam')});
  }
  function cancel(text='Beginner recording canceled.'){
    if(capture)document.dispatchEvent(new CustomEvent('handspeak:word-capture-diagnostics',{detail:{
      outcome:'cancelled',reason:text,trackedFrames:capture.frames.length,handFrames:capture.handFrames,
      processedFrames:capture.results,elapsedMs:performance.now()-capture.start,
      tracker:pose?.diagnostics?.()||null,vocabulary:$('#beginnerVocabMode')?.value||'ready'}}));
    stopVideoClock();generation++;clearTimeout(countdown);clearTimeout(deadline);countdown=null;deadline=null;
    request?.abort();request=null;starting=false;capture=null;pending='';controls();message(text);
  }
  async function begin(){
    if(starting||countdown||capture||request)return;
    if(!$('#beginnerConsent').checked){message('Enable landmark processing for this model first. Camera video is not uploaded.');return;}
    const current=++generation;starting=true;pending='';controls();
    try{
      prepare();
      if(!isRunning())await startCamera();
      if(!isRunning()){cancel('Camera did not start. Check camera access and try again.');return;}
      await loadPose();
      if(current!==generation)return;
      starting=false;
      message('Get ready… recording starts in 1.5 seconds.');
      record.disabled=true;
      countdown=setTimeout(()=>{
        countdown=null;if(current!==generation)return;
        if(!isRunning()){cancel('Start the camera and try again.');return;}
        capture={start:performance.now(),startMediaTime:$('#webcam').currentTime,frames:[],results:0,handFrames:0,generation:current};lastPoseAt=-Infinity;lastCapturedVideoTime=-1;
        startVideoClock($('#webcam'),current);
        deadline=setTimeout(()=>cancel('Recording timed out before a complete capture. Nothing was submitted.'),8000);
        message('Recording lead-in. Start signing after 1.5 seconds; you have four seconds to complete the sign.');onStatus('','Recording with the selected word model.');
      },poseMode==='target20'?1500:0);
    }catch(error){if(current===generation)cancel(`Could not load tracking: ${error.message||'reload and try again.'}`);}
  }
  async function finish(){
    if(capture)document.dispatchEvent(new CustomEvent('handspeak:word-capture-diagnostics',{detail:{trackedFrames:capture.frames.length,handFrames:capture.handFrames,processedFrames:capture.results,elapsedMs:performance.now()-capture.start,startMediaTime:capture.startMediaTime,endMediaTime:$('#webcam').currentTime,vocabulary:$('#beginnerVocabMode')?.value||'ready'}}));
    const handFrames=capture?.handFrames||0;
    if(!capture)return;
    const durationMs=performance.now()-capture.start;
    const frames=capture.frames;capture=null;stopVideoClock();
    clearTimeout(deadline);deadline=null;
    const minimum=poseMode==='target20'?12:3;
    if(frames.length<minimum||(poseMode==='target20'&&handFrames<3)){cancel(`Not enough tracked frames (${frames.length}/${minimum}, ${handFrames} hand frames). Keep your hands in view and try again.`);return;}
    if(!$('#beginnerConsent').checked){cancel('Consent withdrawn. Nothing was submitted.');return;}
    if(poseMode==='target20'){
      const first=frames.findIndex(f=>f.left||f.right), last=frames.length-1-[...frames].reverse().findIndex(f=>f.left||f.right);
      if(handFrames<8 || handFrames/(last-first+1)<.6 || frames[frames.length-1].timestampMs-frames[0].timestampMs<.7*durationMs ||
        frames.some((f,i)=>i&&(f.timestampMs<=frames[i-1].timestampMs||f.timestampMs-frames[i-1].timestampMs>600))){
        cancel('Capture quality insufficient: hand visibility or frame continuity. Nothing was submitted.');return;
      }
    }
    const current=generation;
    request=new AbortController();controls();message('Analyzing landmarks on the server…');
    const timeout=setTimeout(()=>request?.abort(),20000);
    try{
      const closed=($('#beginnerWords')?.dataset.closedLabels||'').split('|').filter(Boolean);
      const body={consent:true,frames};
      if($('#beginnerVocabMode')?.value==='essential')body.vocabulary='essential';
      if(['target20','target20-passed'].includes($('#beginnerVocabMode')?.value)){body.vocabulary=$('#beginnerVocabMode').value;body.capture={complete:true,interrupted:false,durationMs};}
      if(closed.length)body.closedLabels=closed;
      const response=await fetch('/api/beginner-asl',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),signal:request.signal});
      const data=await response.json();if(!response.ok)throw Error(data.error||'Recognition failed');
      if(current!==generation)return;
      pending=(experimentalClock&&poseMode==='target20'&&data.state!=='recognized'?'':data.predictions?.[0]?.label)||'';
      const names=(data.predictions||[]).map((item,index)=>`${index+1}. ${item.label}`).join(' · ');
      if(!pending){
        message(data.message||(data.state==='unknown'?'Unknown sign — no word added.':data.lowConfidence?'No confident match. Sign again.':'No prediction returned.'));
        onStatus('No reliable match',`${modelName()} — verify before adding.`,modelName());
        return;
      }
      message(`Possible match: ${pending}. Top five: ${names}. Verify before adding.`);
      onStatus(pending,`${modelName()} prediction — verify before adding. Scores are not calibrated confidence.`,modelName());
    }catch(error){if(current===generation){message(error.name==='AbortError'?'Recognition timed out. Try again.':error.message);pending='';}}
    finally{clearTimeout(timeout);if(current===generation){request=null;controls();}}
  }
  function frame(detection,now,video,mediaTime){
    const usingVideoClock=experimentalClock&&poseMode==='target20'&&video.requestVideoFrameCallback;
    if(usingVideoClock&&!Number.isFinite(mediaTime))return;
    const sourceTime=usingVideoClock?mediaTime:video.currentTime;
    if(!capture||!pose||holisticBusy||now-lastPoseAt<65||sourceTime===lastCapturedVideoTime)return;
    lastCapturedVideoTime=sourceTime;
    if(poseMode==='target20-tasks'){
      lastPoseAt=now;capture.results++;
      try{const result=pose.detect(video,now,detection);if(result){capture.frames.push({...result,timestampMs:performance.now()-capture.start});if(result.left||result.right)capture.handFrames++;}}
      catch(error){cancel(`Tracking stopped: ${error.message}`);return;}
      if(capture&&capture.frames.length>=12&&capture.handFrames>=3&&performance.now()-capture.start>=4000)void finish();
      return;
    }
    lastPoseAt=now;holisticBusy=true;processingGeneration=capture.generation;
    const submittedCapture=capture;
    sourceTimestamp=sourceTime*1000;

    pose.send({image:video}).then(()=>{
      if(capture!==submittedCapture)return;
      const elapsed=performance.now()-capture.start;
      if(elapsed>=(poseMode==='target20'?4000:5500)&&capture.frames.length>=(poseMode==='target20'?12:3)&&(poseMode!=='target20'||capture.handFrames>=3))void finish();
    }).catch(error=>{holisticBusy=false;if(capture===submittedCapture)cancel(`Tracking stopped: ${error.message}`);});
  }
  record.addEventListener('click',()=>void begin());
  $('#beginnerCancel')?.addEventListener('click',()=>cancel());
  accept.addEventListener('click',()=>{if(pending&&onWord(pending)!==false){message(`Added ${pending} to the draft.`);pending='';controls();}});
  window.addEventListener('pagehide',()=>{cancel();pose?.close?.();});
  void refresh();controls();
  return {frame,cancel,isCapturing:()=>Boolean(capture),needsHandDetection:()=>Boolean(capture)&&poseMode==='target20-tasks'};
}

