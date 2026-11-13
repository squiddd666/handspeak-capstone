import {wordLogState} from './interpreter-words.js';
// Layout adapted from SignSpeak's MIT-licensed interpreter; attribution in third_party/signspeak.
const workspace=document.querySelector('#workspace');
workspace.classList.add('interpreter-workspace');
const camera=workspace.querySelector('.camera-card');
const heading=document.createElement('header');
heading.className='interpreter-heading';
heading.innerHTML='<div class="interpreter-symbol" aria-hidden="true">✋</div><h1>Hand Speak</h1><p>Spell letters and build words in real time using American Sign Language (ASL)</p>';
workspace.prepend(heading);
const side=document.createElement('aside');
side.className='interpreter-sidebar';side.setAttribute('aria-label','Live interpretation');
side.innerHTML=`<section class="interpreter-stat interpreter-letter"><h2>Current Letter / Sign</h2><div id="interpreterEmpty">—</div></section>
<section class="interpreter-stat"><h2>Current Word</h2><p id="interpreterWord">Spelling…</p></section>
<section class="interpreter-stat"><h2>Word Log</h2><div id="interpreterLog"><p class="interpreter-empty">No words logged yet</p></div></section>
<div class="interpreter-buttons"><button type="button" id="interpreterAdd" disabled>＋ Add</button><button type="button" id="interpreterDelete">⌫ Delete</button><button type="button" id="interpreterCommit">↵ Commit</button></div>
<p class="interpreter-notice">Review every match. Recognition is experimental.</p>`;
camera.after(side);
const live=document.querySelector('#liveResult');
side.querySelector('.interpreter-letter').append(live);
const feedback=document.querySelector('#recognitionFeedback');side.append(feedback);
const controls=document.createElement('section');controls.className='interpreter-controls';
controls.innerHTML='<div><h2>Controls</h2><p>Build words with signs and the tap buttons.</p></div><dl><div><dt>Hold a sign steady</dt><dd>Automatically adds a letter</dd></div><div><dt>＋ Add</dt><dd>Add the current letter</dd></div><div><dt>⌫ Delete</dt><dd>Remove the last character</dd></div><div><dt>↵ Commit</dt><dd>Complete a word in your draft</dd></div><div><dt>Rest your hand (2.5s)</dt><dd>Automatically log current word</dd></div><div><dt>Review your draft below</dt><dd>Correct, save, or speak</dd></div></dl>';
side.after(controls);
const title=camera.querySelector('h2');title.textContent='Live Camera Feed';
const extra=document.createElement('details');extra.className='interpreter-options';
extra.innerHTML='<summary>Camera settings &amp; advanced tools</summary>';
const keep=new Set(['card-heading','mode-picker','camera-stage','camera-actions']);
for(const child of [...camera.children]){
 if([...keep].some(c=>child.classList.contains(c))||child.querySelector('#letterModelSelect'))continue;
 extra.append(child);
}
extra.hidden=true;camera.append(extra);
document.querySelector('#interpreterDelete').onclick=()=>document.querySelector('#backspaceButton').click();
document.querySelector('#interpreterCommit').onclick=()=>document.querySelector('#spaceButton').click();
let pendingWord='',reviewConflict=false;
document.addEventListener('handspeak:word-review',event=>{pendingWord=event.detail.word||'';reviewConflict=Boolean(event.detail.conflict);update();});
function update(){
 const text=document.querySelector('#messageText').textContent;
 const draft=document.querySelector('#messageText span')?'':text;
 const {current:unfinished,completed:words}=wordLogState(draft);
 document.querySelector('#interpreterWord').textContent=reviewConflict?'Choose a word - models disagree':pendingWord?pendingWord+' - awaiting review':unfinished||(document.querySelector('#recognitionMode').value==='words'?'Waiting for a word...':'Spelling...');
 const log=document.querySelector('#interpreterLog');log.replaceChildren();
 const rows=[...(unfinished?[{word:unfinished,status:'In progress'}]:[]),...words.slice().reverse().map(word=>({word,status:'Logged'}))];
 if(!rows.length){const p=document.createElement('p');p.className='interpreter-empty';p.textContent='No words detected yet';log.append(p);}
 for(const entry of rows){
  const row=document.createElement('div');row.className=entry.status==='In progress'?'word-log-pending':'word-log-complete';
  const label=document.createElement('span');label.textContent=entry.word;
  const status=document.createElement('small');status.textContent=entry.status;
  row.append(label,status);log.append(row);
 }
 document.querySelector('#interpreterEmpty').hidden=!live.hidden;
 document.querySelector('#interpreterAdd').disabled=!pendingWord&&(live.hidden||!/^\s*[A-Z]\s*$/.test(document.querySelector('#liveLetter').textContent));
 document.querySelector('#interpreterDelete').disabled=!draft;
 document.querySelector('#interpreterCommit').disabled=!unfinished;
}
new MutationObserver(update).observe(live,{attributes:true,childList:true,subtree:true,characterData:true});
document.addEventListener('handspeak:draft-changed',update);
document.querySelector('#recognitionMode').addEventListener('change',update);
update();
