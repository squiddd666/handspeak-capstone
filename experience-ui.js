const $=s=>document.querySelector(s);
const el=(tag,text)=>{const node=document.createElement(tag);node.textContent=text;return node;};
export function createExperienceUI({getMessage,setMessage,stopSpeech}){
 const chips=$('#sentenceChips'),progress=$('#sentenceProgress');let editIndex=-1,lastMatch=null;
 function announce(text){const toast=$('#toast');if(toast)toast.textContent=text;}
 function openCorrection(index,word){editIndex=index;$('#wordCorrection').value=word;$('#wordCorrectionDialog').showModal();$('#wordCorrection').focus();}
 function removeWord(index){
  const words=getMessage().match(/\S+/g)||[];
  if(index<0||index>=words.length)return;
  const [removed]=words.splice(index,1);setMessage(words.join(' '));
  announce(`Removed ${removed}. ${words.length} ${words.length===1?'word':'words'} left.`);
  // Keep the keyboard caret with the list instead of dropping focus to the document.
  queueMicrotask(()=>{const labels=[...chips.querySelectorAll('.word-chip-label')];
   (labels[Math.min(index,labels.length-1)]||labels[labels.length-1])?.focus();});
 }
 function render(){
  const words=getMessage().match(/\S+/g)||[];chips.replaceChildren();
  words.forEach((word,index)=>{
   const wrap=el('span');wrap.className='word-chip';
   const label=el('button',word);label.type='button';label.className='word-chip-label';label.dataset.index=String(index);
   label.setAttribute('aria-label',`Edit word ${index+1}: ${word}`);
   label.onclick=()=>openCorrection(index,word);
   const remove=el('button','\u00d7');remove.type='button';remove.className='word-chip-remove';remove.dataset.index=String(index);
   remove.setAttribute('aria-label',`Remove word ${index+1}: ${word}`);remove.title='Remove word';
   remove.onclick=event=>{event.stopPropagation();removeWord(index);};
   wrap.append(label,remove);chips.append(wrap);
  });
  if(!words.length){const empty=el('span','Your sentence starts with the first added word.');empty.className='chips-empty';chips.append(empty);}
  progress.textContent=words.length?`${words.length} words collected · Review them, then sign FINISH.`:'Collecting words · Sign once, then pause.';
  // Never silently overwrite a correction dialog after the draft changes.
  if($('#wordCorrectionDialog').open){$('#wordCorrectionDialog').close();editIndex=-1;}
 }
 // Arrow keys walk the chips, Home/End jump, Delete or Backspace removes the focused word.
 chips.addEventListener('keydown',event=>{
  const labels=[...chips.querySelectorAll('.word-chip-label')];const current=labels.indexOf(document.activeElement);
  if(current<0)return;
  const key=event.key;
  if(key==='ArrowRight'||key==='ArrowLeft'){event.preventDefault();const step=key==='ArrowRight'?1:-1;labels[(current+step+labels.length)%labels.length].focus();}
  else if(key==='Home'){event.preventDefault();labels[0].focus();}
  else if(key==='End'){event.preventDefault();labels[labels.length-1].focus();}
  else if(key==='Delete'||key==='Backspace'){event.preventDefault();removeWord(current);}
 });
 document.addEventListener('handspeak:draft-changed',render);
 $('#wordCorrectionForm').onsubmit=event=>{
  event.preventDefault();const replacement=$('#wordCorrection').value.trim();const words=getMessage().match(/\S+/g)||[];
  if(editIndex<0||editIndex>=words.length||!replacement)return;
  words[editIndex]=replacement;const next=words.join(' ');if(next.length>1000){$('#wordCorrectionError').textContent='The draft must stay within 1,000 characters.';return;}
  setMessage(next);$('#wordCorrectionDialog').close();
 };
 $('#removeChip').onclick=()=>{const words=getMessage().match(/\S+/g)||[];if(editIndex>=0)words.splice(editIndex,1);setMessage(words.join(' '));$('#wordCorrectionDialog').close();};
 $('#closeWordCorrection').onclick=()=>$('#wordCorrectionDialog').close();
 document.addEventListener('handspeak:sentence-state',event=>{progress.textContent=event.detail.text;$('#stopSpeechButton').disabled=event.detail.state!=='speaking';});
 $('#stopSpeechButton').onclick=stopSpeech;
 // Explicit opt-in feedback for the last captured word/rejection; no recordings.
 document.addEventListener('handspeak:camera-match',event=>{
  const {word,model}=event.detail;const missed=word==='No reliable match';
  if(!missed&&!/^[A-Z][A-Z0-9 '-]{0,79}$/.test(word)){lastMatch=null;$('#matchFeedback').hidden=true;return;}
  lastMatch={predicted:missed?'NO RELIABLE MATCH':word,model,missed};$('#matchFeedback').hidden=false;
  $('#matchCorrect').disabled=missed;$('#matchFeedbackTitle').textContent=missed?'Was a sign missed?':`Was “${word}” correct?`;
  $('#matchFeedbackForm').hidden=true;$('#matchFeedbackStatus').textContent='';
 });
 function feedback(correct){if(!lastMatch)return;$('#matchVerdict').value=correct?'correct':lastMatch.missed?'missed':'wrong';$('#expectedWord').value=correct?lastMatch.predicted:'';$('#expectedWord').readOnly=correct;$('#feedbackConsent').checked=false;$('#matchFeedbackForm').hidden=false;if(!correct)$('#expectedWord').focus();}
 $('#matchCorrect').onclick=()=>feedback(true);$('#matchWrong').onclick=()=>feedback(false);
 $('#matchFeedbackForm').onsubmit=async event=>{
  event.preventDefault();if(!lastMatch)return;const match={...lastMatch};$('#submitMatchFeedback').disabled=true;
  try{const response=await fetch('/api/match-feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...match,expected:$('#expectedWord').value.trim().toUpperCase(),verdict:$('#matchVerdict').value,consent:$('#feedbackConsent').checked})});const data=await response.json();if(!response.ok)throw Error(data.error);$('#matchFeedbackStatus').textContent='Submitted for administrator review. It will not retrain the model automatically.';$('#matchFeedbackForm').hidden=true;}
  catch(error){$('#matchFeedbackStatus').textContent=error.message||'Could not submit feedback.';}finally{$('#submitMatchFeedback').disabled=false;}
 };
 // Nonintrusive first-use walkthrough, always available from the header.
 const steps=[['Welcome to HandSpeak','Supported signs → text draft → your review → speech. Recognition is experimental; it may miss signs or suggest the wrong word.'],['Set up your camera','Use good lighting. Keep your hands, face, and upper body in view. Start camera requests permission only when you choose it.'],['Choose supported words','Use Learn to watch examples and choose a camera vocabulary. A learning entry does not necessarily have a recognition model.'],['Sign, then pause','Choose Words in motion and enable Automatic words. Complete one sign, then pause. Only matched words can be added.'],['Review and correct','Enable automatic adding or choose Add matched word. Click a sentence chip to replace or remove a wrong word.'],['Use FINISH','Enable Collect motion words and speak the sentence on FINISH. Check that your draft has words, then sign FINISH using a vocabulary that supports it. Only the text draft reaches the local LLM.'],['Speech and privacy','Review the sentence. Speak message reads your draft; Interpret draft suggests grammar. FINISH speech is optional. Stop speech cancels playback. Saving stores reviewed text; guest history depends on your browser cookie.']];
 let step=0;
 function showStep(){const [title,text]=steps[step];$('#tutorialTitle').textContent=title;$('#tutorialText').textContent=text;$('#tutorialCounter').textContent=`Step ${step+1} of ${steps.length}`;$('#tutorialPrevious').disabled=step===0;$('#tutorialNext').textContent=step===steps.length-1?'Done':'Next';}
 function remember(){try{localStorage.setItem('handspeak-tutorial-seen','1');}catch{}$('#tutorialDialog').close();}
 $('#openTutorial').onclick=()=>{step=0;showStep();$('#tutorialDialog').showModal();};
 $('#tutorialPrevious').onclick=()=>{step=Math.max(0,step-1);showStep();};$('#tutorialNext').onclick=()=>{if(step===steps.length-1)remember();else{step++;showStep();}};
 $('#tutorialSkip').onclick=remember;$('#tutorialDialog').addEventListener('cancel',remember);
 // The guide is available on request. Do not block direct camera access with a dialog.
 const prefs={};try{Object.assign(prefs,JSON.parse(localStorage.getItem('handspeak-accessibility')||'{}'));}catch{}
 function access(){document.body.classList.toggle('large-text',$('#textSize').value==='large');try{localStorage.setItem('handspeak-accessibility',JSON.stringify({size:$('#textSize').value,rate:$('#speechRate').value}));}catch{}}
 $('#textSize').value=prefs.size==='large'?'large':'normal';$('#speechRate').value=['0.8','1','1.2'].includes(prefs.rate)?prefs.rate:'1';access();$('#textSize').onchange=access;$('#speechRate').onchange=access;
 document.addEventListener('keydown',event=>{if(!event.altKey||!event.shiftKey||event.target.closest('input,textarea,select,[contenteditable]')||document.querySelector('dialog[open]'))return;const action={s:'#speakButton',e:'#editMessageButton',x:'#stopSpeechButton'}[event.key.toLowerCase()];if(action){event.preventDefault();document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#workspace'}}));$(action).click();}});
 async function evaluations(){
  try{
   const [base,expanded,index]=await Promise.all(['models/asl-words-evaluation.json','models/asl-extra-words-evaluation.json','models/motion-categories/index.json'].map(async path=>{const response=await fetch(path,{cache:'no-store'});if(!response.ok)throw Error();return response.json();}));
   const rows=[['Default six words',base.testIncludingTrackingFailures.correct,base.test.wrong,base.testIncludingTrackingFailures.total-base.testIncludingTrackingFailures.correct-base.test.wrong,`${base.unknownWordTest.falseAccepts}/${base.unknownWordTest.total}`],['Expanded · new words',expanded.expanded.new.correct,'Not separated','Not separated',`${expanded.expanded.negative.wrong}/${expanded.expanded.negative.total}`]];
   for(const pack of index.groups||[]){const t=pack.test;if(t)rows.push([pack.name,t.correct,t.wrong??'Not measured',t.missed??'Not measured',`${t.negativeFalse}/${t.negativeTotal}`]);}
   const body=$('#recordedEvaluationRows');body.replaceChildren();for(const row of rows){const tr=document.createElement('tr');row.forEach(value=>tr.append(el('td',String(value))));body.append(tr);}
  }catch{$('#recordedEvaluationNote').textContent='Recorded test reports could not load. Retry by refreshing the page.';}
 }
 void evaluations();render();
}
