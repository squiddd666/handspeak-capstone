import {createAutomaticWordCapture} from './automatic-word-capture.js?v=20261112-capture-preroll-v2';
import {combineWordResults} from './combined-word-results.js';
export function createOpenHandsRecognition({startCamera,isRunning,onWord,onStatus,onSelect,browserModel}){
 const $=s=>document.querySelector(s);
 const card=document.createElement('section');card.id='openhandsWords';card.className='trainer-card featured-word-model';
 card.innerHTML='<h3>OpenHands · 70 reference-passed words</h3><label class="speech-option"><input type="checkbox" id="openhandsEnabled" checked> Use OpenHands for Record a word</label><p class="camera-tip">Records one isolated sign for a complete capture. The full 100-class model runs on this computer; only its 45 virtual-camera-passed labels are accepted. This is not verified webcam accuracy.</p><label class="speech-option"><input id="openhandsConsent" type="checkbox" checked> Allow recorded video to be processed by this local server. The temporary video is deleted after processing.</label><div class="camera-actions"><button id="openhandsRecord" class="primary-button" type="button" disabled>Record an OpenHands word</button><button id="openhandsCancel" class="secondary-button" type="button" disabled>Cancel</button><button id="openhandsAccept" class="secondary-button" type="button" disabled>Add reviewed word</button></div><p id="openhandsStatus" role="status">Loading OpenHands…</p><details><summary>See the 45 enabled words</summary><p id="openhandsVocabulary"></p></details>';
 document.querySelector('#workspace .camera-actions').after(card);
 card.hidden=true;
 card.querySelector('h3').textContent='Combined word recognition';
 $('#openhandsEnabled').parentElement.lastChild.textContent=' Use combined browser + OpenHands recognition';
 card.querySelector('.camera-tip').textContent='One complete capture is analyzed by both models, including the countdown lead-in so the start of your sign is not cut off. Matching words appear once; conflicting predictions require your choice. Scores are not compared across models.';
 $('#openhandsRecord').textContent='Record a word';
 const choices=document.createElement('div');choices.id='combinedWordChoices';choices.setAttribute('role','group');choices.setAttribute('aria-label','Review model predictions');
 $('#openhandsStatus').after(choices);
 const consentLabel=$('#openhandsConsent').closest('label');
 consentLabel.hidden=true;
 const processingNotice=document.createElement('p');processingNotice.className='camera-tip';
 processingNotice.textContent='Word recognition processes short recordings on this computer and deletes temporary video afterward. No external upload.';
 consentLabel.after(processingNotice);
 const automaticOption=$('#automaticWords').closest('label');
 card.querySelector('.camera-tip').after(automaticOption);
 automaticOption.lastChild.textContent=' Automatic words - raise hands to capture; lower hands between signs';
 // Keep dependencies off-screen; expose only essential main-workspace controls.
 card.classList.add('internal-word-controls');
 const compact=document.createElement('div');compact.id='compactWordControls';compact.hidden=true;
 const cancelButton=$('#openhandsCancel');cancelButton.textContent='Cancel capture / discard';
 automaticOption.lastChild.textContent=' Automatic words';
 compact.append(automaticOption,cancelButton,processingNotice);
 const handStatus=document.createElement('p');handStatus.id='wordHandStatus';handStatus.className='camera-tip';handStatus.setAttribute('role','status');handStatus.textContent='Camera off.';compact.append(handStatus);
 document.querySelector('#workspace .camera-actions').after(compact);
 document.querySelector('#interpreterWord').parentElement.append(choices);

 const progress=new MutationObserver(()=>{if(active())document.dispatchEvent(new CustomEvent('handspeak:openhands-progress',{detail:{text:$('#openhandsStatus').textContent}}));});
 progress.observe($('#openhandsStatus'),{childList:true,characterData:true,subtree:true});
 let labels=[],available=false,recorder=null,timer=null,request=null,pending='',revision=0,recording=false;
 let candidates=[],selectedSource='',autoCapture=null,browserReady=false;
 browserModel.ready.then(()=>{browserReady=true;});
 function choose(entry){pending=entry.word;selectedSource=entry.sources.includes('OpenHands')?'OpenHands':'Browser';controls();onStatus(pending,entry.sources.join(' + ')+(entry.confidence===null?'':` - ${(entry.confidence*100).toFixed(1)}% OpenHands confidence`));}
 function showResults(browser,server){
  candidates=combineWordResults(browser,server);pending='';selectedSource='';choices.replaceChildren();
  for(const entry of candidates){const button=document.createElement('button');button.type='button';button.className='secondary-button';button.dataset.combinedWord=entry.word;button.textContent=entry.word+' - '+entry.sources.join(' + ')+(entry.confidence===null?'':` (${(entry.confidence*100).toFixed(1)}% OpenHands)`);button.onclick=()=>{choose(entry);$('#openhandsStatus').textContent='Selected '+entry.word+'. Use + Add to accept, or Cancel capture / discard.';};choices.append(button);}
  if(candidates.length===1){choose(candidates[0]);$('#openhandsStatus').textContent='Review '+pending+' ('+candidates[0].sources.join(' + ')+'). Use + Add to accept, or Cancel capture / discard.';}
  else if(candidates.length>1){onStatus('No reliable match','Models disagree. Choose a prediction below the camera; neither is accepted automatically.');$('#openhandsStatus').textContent='Models disagree. Choose a word below; confidence scores are not comparable across models.';}
  else{const reason=[browser?.error,server?.error||server?.message].filter(Boolean).join(' / ');onStatus('No reliable match',reason||'Neither model matched.');$('#openhandsStatus').textContent='No match. '+reason;}
  controls();
 }
 function frame(hands,now){autoCapture?.frame(hands,now);}
 const active=()=>$('#openhandsEnabled').checked;
 const isAllowed=label=>labels.includes(String(label).toUpperCase());
 const controls=()=>{$('#openhandsRecord').disabled=!available||recording||Boolean(request);$('#openhandsCancel').disabled=!recording&&!request&&!candidates.length;$('#openhandsAccept').disabled=!pending;document.dispatchEvent(new CustomEvent('handspeak:word-review',{detail:{word:pending,conflict:candidates.length>1&&!pending}}));};
 function cancel(){autoCapture?.cancel();browserModel.cancelCombined();browserModel.clearCombinedHistory();candidates=[];choices.replaceChildren();revision++;clearTimeout(timer);timer=null;recorder?.state==='recording'&&recorder.stop();recorder=null;recording=false;request?.abort();request=null;pending='';controls();}
 function setEnabled(value){if(active()===value)return;cancel();$('#openhandsEnabled').checked=value;}
 $('#openhandsEnabled').onchange=()=>{cancel();onSelect?.(active());};
 async function submitCapture({blob,startMediaTime,endMediaTime,token,reason,boundaryQuality}){
  if(token!==revision)return;
  const browserResult=browserModel.finishCombined();recording=false;recorder=null;clearTimeout(timer);
  document.dispatchEvent(new CustomEvent('handspeak:combined-browser-result',{detail:browserResult}));
  document.dispatchEvent(new CustomEvent('handspeak:word-capture-diagnostics',{detail:{capture:'openhands-video',startMediaTime,endMediaTime,reason,boundaryQuality}}));
  if(!blob.size){controls();$('#openhandsStatus').textContent='No video was captured. Try again.';return;}
  request=new AbortController();const controller=request;controls();
  $('#openhandsStatus').textContent='Analyzing your sign with both models...';
  const timeout=setTimeout(()=>controller.abort(),100000);
  try{
   const response=await fetch('/api/openhands/recognize',{method:'POST',headers:{'X-OpenHands-Consent':'true','Content-Type':blob.type},body:blob,signal:controller.signal});
   const data=await response.json();if(token!==revision)return;
   if(!response.ok)throw Error(data.error||'OpenHands failed');
   showResults(browserResult,{...data,label:data.label&&isAllowed(data.label)?data.label:null});
  }catch(error){if(token===revision)showResults(browserResult,{error:error.name==='AbortError'?'Processing timed out or was canceled.':error.message});}
  finally{clearTimeout(timeout);if(request===controller)request=null;controls();}
 }
 autoCapture=createAutomaticWordCapture({
  video:$('#webcam'),
  canWatch:()=>browserReady&&available&&active()&&isRunning()&&$('#automaticWords').checked&&$('#openhandsConsent').checked&&!recording&&!request&&!candidates.length&&!document.hidden,
  onStart:info=>{
   browserModel.setVocabulary(null);$('#expandedWords').checked=true;
   const token=++revision;pending='';recording=true;browserModel.beginCombined(info);controls();return token;
  },
  onClip:clip=>void submitCapture(clip),
  onDiagnostic:detail=>document.dispatchEvent(new CustomEvent('handspeak:word-boundary',{detail})),
  onDiscard:message=>{browserModel.cancelCombined();recording=false;controls();$('#openhandsStatus').textContent=message;},
  onState:message=>{$('#openhandsStatus').textContent=message;}
 });
 async function record(){
  if(recording||request)return;
  if(!globalThis.MediaRecorder){$('#openhandsStatus').textContent='Video recording is not supported in this browser.';return;}
  setEnabled(true);onSelect?.(true);
  if(!isRunning())await startCamera();if(!isRunning())return;
  const preparation=revision;await browserModel.ready;
  if(preparation!==revision||!isRunning())return;
  autoCapture.cancel();browserModel.setVocabulary(null);$('#expandedWords').checked=true;
  const token=++revision;pending='';recording=true;controls();
  try{
   const stream=$('#webcam').srcObject;
   const mime=['video/webm;codecs=vp8','video/webm','video/mp4'].find(t=>MediaRecorder.isTypeSupported(t));
   recorder=new MediaRecorder(stream,{...(mime?{mimeType:mime}:{}),videoBitsPerSecond:750000});
   const chunks=[],startMediaTime=$('#webcam').currentTime;let endMediaTime=startMediaTime;
   recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
   recorder.onerror=()=>{if(token===revision){cancel();$('#openhandsStatus').textContent='Recording failed. Try again.';}};
   recorder.onstop=()=>{if(token===revision)void submitCapture({blob:new Blob(chunks,{type:mime||'video/webm'}),startMediaTime,endMediaTime,token,reason:'manual'});};
   browserModel.beginCombined();recorder.start();
   $('#openhandsStatus').textContent='Recording lead-in. Start signing after 1.5 seconds.';
   setTimeout(()=>{if(token===revision&&recording)$('#openhandsStatus').textContent='Sign now, then pause.';},1500);
   timer=setTimeout(()=>{if(token===revision&&recorder?.state==='recording'){endMediaTime=$('#webcam').currentTime;recorder.stop();}},5500);
  }catch(error){cancel();$('#openhandsStatus').textContent=error.message;}
 }
 $('#automaticWords').addEventListener('change',()=>{cancel();$('#openhandsStatus').textContent=$('#automaticWords').checked?'Automatic words ready. Sign naturally, then pause.':'Automatic words off. Use Record a word.';});
 document.addEventListener('visibilitychange',()=>{if(document.hidden){autoCapture.cancel();if(recording)cancel();}});
 $('#openhandsConsent').addEventListener('change',()=>{if(!$('#openhandsConsent').checked){cancel();return;}$('#openhandsStatus').textContent='Ready. Sign naturally, then pause briefly. Review each result before adding.';});
 $('#openhandsRecord').onclick=()=>void record();$('#openhandsCancel').onclick=()=>{cancel();autoCapture.waitForQuiet();$('#openhandsStatus').textContent='Capture discarded. Pause briefly, then sign again.';};
 $('#openhandsAccept').onclick=()=>{if(pending&&onWord(pending,selectedSource)!==false){pending='';candidates=[];choices.replaceChildren();controls();$('#openhandsStatus').textContent='Reviewed word added. Pause, then sign your next word.';}};
 fetch('/api/openhands/status',{cache:'no-store'}).then(r=>r.json()).then(data=>{
  available=data.available===true&&Array.isArray(data.labels)&&data.labels.length>0&&data.labels.length<=100&&new Set(data.labels).size===data.labels.length;labels=data.labels||[];
  $('#openhandsVocabulary').textContent=labels.join(' · ');$('#openhandsStatus').textContent=available?'Both word models ready — start camera, sign naturally, then pause.':'OpenHands model files are unavailable.';controls();
  // OpenHands shares the existing Watch & practice picker and player.
  const picker=document.querySelector('#sign-examples .example-words');
  const video=$('#signExampleVideo');
  let selected=null;
  const avatarPanel=document.querySelector('.example-avatar-panel');
  const compare=$('#signExampleCompare');
  const oldColumns=compare.style.gridTemplateColumns;
  labels.forEach(label=>{
   const button=document.createElement('button');
   button.type='button';button.className='secondary-button';
   button.dataset.openhandsExample=label;button.textContent=label;
   button.setAttribute('aria-pressed','false');
   button.onclick=()=>{
    selected=label;
    picker.querySelectorAll('button').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
    const src=data.videos?.[label.toLowerCase()]||'';
    const panel=document.querySelector('.example-video-panel');
    video.pause();
    video.hidden=false;panel.hidden=false;
    compare.hidden=false;avatarPanel.hidden=true;compare.style.gridTemplateColumns='1fr';
    $('#signExampleEmbed').hidden=true;$('#signExampleLesson').hidden=true;
    if(src){
     panel.removeAttribute('data-missing');
     video.onerror=()=>{
      video.onerror=null;video.onloadeddata=null;
      panel.setAttribute('data-missing','');
      video.removeAttribute('src');video.load();
      $('#signExampleReferenceNote').hidden=false;
      $('#signExampleReferenceNote').textContent=`Reference clip for ${label} could not load. Practice at the camera and review the match.`;
      $('#signExampleStatus').textContent=label+' · Reference video unavailable';
     };
     video.onloadeddata=()=>{
      video.onloadeddata=null;
      video.dataset.orientation=video.videoWidth>video.videoHeight?'landscape':'portrait';
      video.loop=Boolean($('#signExampleLoop')?.checked);
      video.currentTime=0;
      const playPromise=video.play();
      if(playPromise?.catch)playPromise.catch(()=>{});
     };
     video.src=src;
     video.setAttribute('aria-label',label+' OpenHands reference example');
     video.playbackRate=Number($('#signExampleSpeed').value);video.load();
     $('#signExampleReferenceNote').hidden=true;
     $('#signExampleStatus').textContent=label+' · OpenHands reference video';
     $('#signExampleMode').textContent='OpenHands · Practice at camera, then record one complete sign and review the match.';
    }else{
     panel.setAttribute('data-missing','');
     video.removeAttribute('src');video.load();
     $('#signExampleReferenceNote').hidden=false;
     $('#signExampleReferenceNote').textContent=`No bundled reference clip for ${label}. Practice at the camera and review the match.`;
     $('#signExampleStatus').textContent=label+' · No local reference video';
     $('#signExampleMode').textContent='OpenHands · No reference clip for this word. Practice at camera, then review the match.';
    }
    $('#signExampleAccuracy').textContent='Passed the virtual-camera reference test; physical-webcam accuracy is not verified.';
   };
   picker.append(button);
  });
  picker.addEventListener('click',event=>{
   if(event.target.closest('button')&&!event.target.closest('[data-openhands-example]')){
    selected=null;avatarPanel.hidden=false;compare.style.gridTemplateColumns=oldColumns;
    picker.querySelectorAll('[data-openhands-example]').forEach(b=>b.setAttribute('aria-pressed','false'));
   }
  },true);
  $('#signExamplePractice').addEventListener('click',event=>{
   if(!selected)return;
   event.preventDefault();event.stopImmediatePropagation();
   setEnabled(true);onSelect?.(true);
   document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#workspace'}}));
   $('#openhandsStatus').textContent=`Practice ${selected}. The reference does not force a prediction.`;
  },true);

 }).catch(()=>{$('#openhandsStatus').textContent='OpenHands could not load. Restart the Python server and refresh.';});
 window.addEventListener('pagehide',cancel);
 return {active,isAllowed,record,frame,cancel,setEnabled,isBusy:()=>recording||Boolean(request)};
}
