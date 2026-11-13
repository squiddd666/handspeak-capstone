import {isWordEnabled} from './vocabulary-settings.js?v=20261112-count-19-fix';
import {createAutomaticMotion} from './automatic-motion.js?v=20261020-appearance-1';
import {motionFrame,encodeMotion} from './motion-model.js?v=20261020-short-runs-1';
export function createResearchWords({onWord,onStatus,onChange}){
 const $=s=>document.querySelector(s),toggle=$('#researchWordsToggle');
 let available=false,recording=null,pending=null,request=null,timer=null,revision=0,last=-Infinity,authRevision=0,standardVocabulary=null;
 const automatic=createAutomaticMotion();let autoWasActive=false,nextAutomaticAt=0;
 const active=()=>available&&toggle.checked;
 function help(text){$('#researchWordsStatus').textContent=text;}
 function controls(){
  $('#researchRecord').disabled=!active()||Boolean(recording||request);
  $('#researchAccept').disabled=!active()||!pending;
  $('#researchCancel').disabled=!recording&&!request&&!automatic.isActive();
  $('#standardWordOptions').hidden=active();
  $('#automaticWords').disabled=false;
  $('#processingLocation').textContent=active()?'SERVER PREVIEW':'ON DEVICE';
  if(active()){
   if(standardVocabulary===null)standardVocabulary=$('#activeVocabulary').textContent;
   $('#activeVocabulary').textContent='Camera vocabulary: NAME · HOME · HAVE · WANT · LOVE (experimental preview)';
   $('#motionCaptureStatus').textContent=$('#automaticWords').checked?'Five-word automatic capture: sign once, then pause. Each captured sequence sends landmarks to the server.':'Five-word manual capture: select Record a preview word.';
  }else if(standardVocabulary!==null){$('#activeVocabulary').textContent=standardVocabulary;standardVocabulary=null;$('#motionCaptureStatus').textContent='Standard recognition restored. Sign once and pause, or record a word.';}
 }
 function cancel(){automatic.reset();autoWasActive=false;revision++;clearTimeout(timer);timer=null;recording=null;pending=null;request?.abort();request=null;controls();}
 function disable(){cancel();toggle.checked=false;controls();}
 toggle.addEventListener('change',()=>{
  cancel();
  if(!available)toggle.checked=false;
  onChange(active());controls();
  help(active()?'Five-word preview enabled. With Automatic words on, sign once and pause. Completed hand-landmark sequences are sent to the server. Review each suggestion.':'Five-word preview off. Standard recognition stays on your device.');
 });
 async function refresh(){
  const authVersion=++authRevision;disable();available=false;toggle.disabled=true;
  try{
   const response=await fetch('/api/research-words/status',{cache:'no-store'});
   const data=await response.json();
   if(authVersion!==authRevision)return;
   if(!response.ok){help('The five-word service is unavailable. Please reload to retry.');return;}
   available=data.available===true;toggle.disabled=!available;
   help(available?'Five-word preview ready — no sign-in or personal training required. Enable server landmark processing, then sign once and pause.':'The five-word model is unavailable. Standard recognition remains available.');
  }catch{help('Five-word service unavailable. Standard recognition remains available.');}
  controls();
 }
 async function finish(force=false){
  if(!recording||!active())return;
  if(!force&&recording.frames.length<12){timer=setTimeout(()=>void finish(true),2000);help('Collecting more frames from the slow camera…');return;}
  const captured=recording;
  document.dispatchEvent(new CustomEvent('handspeak:word-capture-diagnostics',{detail:{capture:'research-manual',startMediaTime:captured.startMediaTime,endMediaTime:captured.endMediaTime,frames:captured.frames.length}}));
  recording=null;clearTimeout(timer);timer=null;
  const sequence=encodeMotion(captured.frames,captured.aspect||1);
  if(!sequence){help('Not enough clear hand tracking. Keep your hands in view and record again.');onStatus('No reliable match','Not enough clear hand tracking.');controls();return;}
  nextAutomaticAt=performance.now()+6000;
  const version=revision;request=new AbortController();const controller=request;const timeout=setTimeout(()=>controller.abort(),10000);controls();
  help('Analyzing on the server… sending hand-landmark coordinates, not video.');onStatus('—','Analyzing word recording on the server…');
  try{
   const response=await fetch('/api/research-words',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({sequence,consent:true}),signal:controller.signal});
   const data=await response.json();if(version!==revision||!active())return;
   if(!response.ok)throw Error(data.error||'Word recognition failed');
   pending=['NAME','HOME','HAVE','WANT','LOVE'].includes(data.label)&&isWordEnabled(data.label)?data.label:null;
   help(pending?`Possible match: ${pending}. Check the word, then choose Add reviewed word.`:'No reliable match. Your sign may still be correct; this model has limited accuracy.');
   onStatus(pending||'No reliable match',pending?'Experimental server match — verify before adding.':'Try another sign after pausing; recognition is not guaranteed.');
   if(pending&&$('#sentenceAutoAdd').checked&&onWord(pending)!==false){help(`Added ${pending} to your draft. Review it before speaking.`);pending=null;}
   automatic.reset();autoWasActive=false;
  }catch(error){if(version===revision){help(error.name==='AbortError'?'Word recognition request timed out. Try again.':error.message);onStatus('No reliable match','Word recognition request failed; no word was added.');}}
  finally{clearTimeout(timeout);if(version===revision){request=null;controls();}}
 }
 function recognize(){
  if(!active()||recording||request)return;
  cancel();const now=performance.now();recording={start:now+1500,end:now+4000,frames:[],aspect:null};last=-Infinity;
  help('Get ready: after the 1.5-second countdown, sign one of the five words once.');onStatus('—','Get ready for word recording…');timer=setTimeout(()=>void finish(),4050);controls();
 }
 function frame(detection,now){
  if(!active()||document.hidden)return;
  if(!recording){
   if(!$('#automaticWords').checked||request||pending||performance.now()<nextAutomaticAt)return;
   const clip=automatic.push(motionFrame(detection),now,detection.imageAspect||1);
   if(automatic.isActive()&&!autoWasActive){help('Watching your sign… pause briefly to send the captured landmarks.');onStatus('—','Analyzing movement…');controls();}
   autoWasActive=automatic.isActive();
   if(clip){recording={frames:clip.frames,aspect:clip.imageAspect};void finish(true);}
   return;
  }
  if(now<recording.start||now-last<80)return;
  const aspect=detection.imageAspect||1;
  if(recording.aspect&&Math.abs(recording.aspect-aspect)>.01){cancel();help('Camera orientation changed. Record again.');return;}
  recording.startMediaTime??=document.querySelector('#webcam').currentTime;recording.endMediaTime=document.querySelector('#webcam').currentTime;
  last=now;recording.aspect=aspect;recording.frames.push(motionFrame(detection));
  help('Recording your movement… finish the sign and pause.');
 }
 $('#researchRecord').addEventListener('click',()=>$('#wordCaptureButton').click());
 $('#researchCancel').addEventListener('click',()=>{cancel();$('#automaticWords').checked=false;controls();help('Capture canceled. Automatic words paused; turn it back on to resume.');onStatus('—','Capture canceled.');});
 $('#automaticWords').addEventListener('change',()=>{cancel();if(active())help($('#automaticWords').checked?'Automatic server capture enabled. Sign once, then pause.':'Automatic capture paused. You can record a word manually.');});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)cancel();});
 $('#researchAccept').addEventListener('click',()=>{if(active()&&pending&&onWord(pending)!==false){pending=null;help('Reviewed word added to your draft. Use Speak message when ready. Pause briefly before signing the next word.');controls();}});
 $('#sentenceAutoAdd').addEventListener('change',()=>{if(active()&&pending&&$('#sentenceAutoAdd').checked&&onWord(pending)!==false){pending=null;help('Matched word added to your draft. Review it before speaking.');controls();}});

 document.addEventListener('handspeak:enable-word-preview',()=>{
  const mode=$('#recognitionMode');mode.value='words';mode.dispatchEvent(new Event('change',{bubbles:true}));
  if(!available){help('The five-word preview is still loading or unavailable. Reload to retry.');}else{toggle.checked=true;toggle.dispatchEvent(new Event('change'));}
  document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#researchWords'}}));$('#researchWords').scrollIntoView({block:'center',behavior:'smooth'});
 });
 window.addEventListener('pagehide',cancel);
 void refresh();
 return {active,cancel,disable,recognize,frame,isCapturing:()=>Boolean(recording)||automatic.isActive()};
}
