import {validMotion} from './motion-model.js?v=20261018-perword-1';

// Server preview and optional personal training are separate choices.
const words=['NAME','HOME','HAVE','WANT','LOVE'];
const $=selector=>document.querySelector(selector);
let needsReload=false;
function counts(){
  const result={};
  try{
    const rows=JSON.parse(localStorage.getItem('handspeak-motion-v3')||'[]');
    if(Array.isArray(rows))for(const row of rows.slice(0,96)){
      if(words.includes(row?.label)&&validMotion(row.sequence))result[row.label]=(result[row.label]||0)+1;
    }
  }catch{}
  return result;
}
function update(){
  const saved=counts();
  for(const card of document.querySelectorAll('[data-daily-word]')){
    const label=card.dataset.dailyWord,n=saved[label]||0;
    card.querySelector('[data-daily-status]').textContent=n>=3?`${n} personal examples · ready to try, accuracy unverified`:`Server preview needs no training · ${n}/3 optional personal examples`;
    card.querySelector('[data-daily-practice]').disabled=needsReload||n<3;
    card.querySelector('[data-daily-teach]').textContent=n?'Add another example':'Teach this word';
  }
}
function wordMode(){
  const mode=$('#recognitionMode');mode.value='words';mode.dispatchEvent(new Event('change',{bubbles:true}));
}
for(const card of document.querySelectorAll('[data-daily-word]')){
  const label=card.dataset.dailyWord;
  card.querySelector('[data-daily-preview]').addEventListener('click',()=>document.dispatchEvent(new CustomEvent('handspeak:enable-word-preview',{detail:{id:label.toLowerCase()}})));
  card.querySelector('[data-daily-teach]').addEventListener('click',()=>{
    wordMode();$('#motionLabel').value=label;$('#motionLabel').closest('details').open=true;
    $('#dailyWordsStatus').textContent=`Teach ${label}: start the camera, then select Record example. Wait for the countdown and sign once. Save at least three examples.`;
    document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#motionLabel'}}));$('#motionLabel').scrollIntoView({block:'center',behavior:'smooth'});$('#motionLabel').focus({preventScroll:true});
  });
  card.querySelector('[data-daily-practice]').addEventListener('click',()=>{
    if(needsReload||(counts()[label]||0)<3){update();return;}
    wordMode();document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#workspace'}}));$('#workspace').scrollIntoView({block:'start',behavior:'smooth'});$('#cameraButton').focus({preventScroll:true});
    $('#dailyWordsStatus').textContent=`Try your personal ${label} gesture at the camera. Sign once, then pause; verify any suggested word.`;
  });
  card.querySelector('[data-daily-video]')?.addEventListener('click',()=>{
    document.dispatchEvent(new CustomEvent('handspeak:example',{detail:{label,id:label.toLowerCase(),src:['HOME','HAVE'].includes(label)?`media/signs/${label.toLowerCase()}.mp4?v=20261020-practice-2`:undefined}}));
    document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#sign-examples'}}));$('#sign-examples').scrollIntoView({block:'start',behavior:'smooth'});
  });
}
document.addEventListener('handspeak:personal-words',update);
window.addEventListener('storage',event=>{if(event.key==='handspeak-motion-v3'||event.key===null){needsReload=true;update();$('#dailyWordsStatus').textContent='Personal examples changed in another tab. Reload this page before practicing them.';}});
update();
