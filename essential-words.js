import {loadVocabularySettings,isWordEnabled} from './vocabulary-settings.js?v=20261112-count-19-fix';
await loadVocabularySettings();
// Quick access to existing recognition routes; this list does not train models.
const words = [
  ['Hello','Greeting','default'],['Thank you','Polite expression','default'],
  ['Please','Polite expression','default'],['Sorry','Polite expression','beginner'],
  ['Yes','Response','default'],['No','Response','default'],
  ['Help','Essential','essential'],['Love','Emotion','daily'],
  ['I / Me','Pronoun','essential'],['You','Pronoun','essential'],
  ['Want','Verb','daily'],['Need','Verb','essential'],['Like','Verb','extra'],
  ['Good','Description','beginner'],['Bad','Description','beginner'],
  ['What','Question','beginner'],['Where','Question','essential'],
  ['Who','Question','beginner'],['Eat','Daily activity','core'],
  ['Water','Daily needs','extra'],
];
const routes = {
  default:'Default motion preview', daily:'Optional five-word server preview',
  beginner:'Beginner ready server model', core:'Core seven-word server model',
  extra:'Optional extra-word preview', personal:'Not in ready vocabulary · personal training needed',
  essential:'New five-word server preview · experimental',
};
const section = document.createElement('section');
section.className='trainer-card';
section.setAttribute('aria-labelledby','essentialWordsTitle');
const heading=document.createElement('h3');heading.id='essentialWordsTitle';heading.textContent='20 words in motion';
const help=document.createElement('p');
help.textContent='Practice any of these 20 words, or choose Teach motion to record your own examples. Listing a word does not install a recognition model. Server models require landmark-processing consent. HELP, I / ME, YOU, NEED, and WHERE use the new five-word research preview. Review every suggestion; live-camera accuracy is unverified.';
const list=document.createElement('div');list.className='vocabulary-cards';
const status=document.createElement('p');status.className='camera-tip';status.setAttribute('role','status');
section.append(heading,help,list,status);
document.querySelector('#wordRecognitionControls .word-review-bar').after(section);
const modeLabel=document.createElement('label');modeLabel.textContent='Beginner vocabulary ';
const mode=document.createElement('select');mode.id='beginnerVocabMode';
mode.add(new Option('Existing ready vocabulary','ready'));
const preview=new Option('Five-word preview · HELP, I / ME, YOU, NEED, WHERE','essential');preview.disabled=true;mode.add(preview);
const target20=new Option('All 20 target words · research preview','target20');target20.disabled=true;mode.add(target20);
let originalLabels=[],passedWords=[];
const passedOption=new Option('Passed offline checks ? Hello, Please, Help, Water','target20-passed');passedOption.disabled=true;mode.add(passedOption);
const descriptionElement=document.querySelector('#beginnerDescription');
const originalDescription=descriptionElement?.innerHTML||'';
modeLabel.append(mode);document.querySelector('#beginnerConsent').closest('label').before(modeLabel);
mode.addEventListener('change',()=>{
  document.querySelector('#beginnerCancel').click();
  document.querySelector('#beginnerWords').dataset.closedLabels='';
  const labels=(mode.value==='target20-passed'?passedWords:mode.value==='target20'?words.map(word=>word[0].toUpperCase()):mode.value==='essential'?['HELP','I / ME','YOU','NEED','WHERE']:originalLabels).filter(isWordEnabled);
  document.querySelector('#beginnerTitle').textContent=mode.value==='target20-passed'?'Passed offline checks ? experimental':mode.value==='target20'?'20-word research preview':mode.value==='essential'?'Five-word research preview':'Beginner ready vocabulary';
  if(descriptionElement){if(mode.value==='ready')descriptionElement.innerHTML=originalDescription;else descriptionElement.textContent=mode.value==='target20-passed'?'Hello, Please, Help and Water met the preliminary recorded-test thresholds. This uses the full 20-word model without renormalizing its scores. Other signs are rejected; live-camera accuracy is unverified.':mode.value==='target20'?'Experimental model for the 20 listed words. Record one complete sign for four seconds and review the result. Recognition and unknown-sign rejection are not deployment-ready; live-camera accuracy is unverified.':'Experimental five-word preview. Record one complete sign for four seconds and review the result; live-camera accuracy is unverified.';}
  document.querySelector('#beginnerRecord').textContent=mode.value==='target20-passed'?'Record a passed-word sign':mode.value==='target20'?'Record a 20-word sign':mode.value==='essential'?'Record a five-word sign':'Record a Beginner sign';
  document.querySelector('#beginnerCount').textContent=`${labels.length} signs`;
  document.querySelector('#beginnerVocabulary').textContent=labels.join(' · ');
  document.querySelector('#beginnerStatus').textContent=mode.value==='target20-passed'
    ?'Offline-qualified preview selected. Enable landmark-processing consent, record one complete sign, then review before adding.'
    :mode.value==='target20'
    ?'20-word research preview selected. Record one complete sign and review the result. Deployment readiness is not verified.'
    :mode.value==='essential'
    ?'Five-word preview selected. Enable server landmark processing, record one complete sign, and review the result. Other signs may still be misidentified.'
    :'Existing ready vocabulary selected.';
});
fetch('/api/beginner-asl/status',{cache:'no-store'}).then(r=>r.json()).then(data=>{
  originalLabels=data.labels||[];
  passedWords=data.passedTarget20?.labels||[];
  passedOption.disabled=!data.passedTarget20?.available;
  renderPassedWords(data.passedTarget20);
  preview.disabled=!data.essential?.available;
  target20.disabled=!data.target20?.available;
  if(!target20.disabled){
    help.textContent='All 20 words can be practiced with the new research candidate. It has not met deployment-readiness requirements. Enable landmark-processing consent and review every result; original recognition modes remain available below.';
    list.querySelectorAll('article p').forEach((description,index)=>{description.textContent=`${words[index][1]} · All-20 research preview · not deployment ready`;});
  }
  if(preview.disabled || target20.disabled)status.textContent=[preview.disabled ? (data.essential?.reason || 'Five-word preview unavailable: install its checkpoint/report and PyTorch.') : '', target20.disabled ? (data.target20?.reason || 'All-20 preview unavailable: install its checkpoint/report and PyTorch.') : ''].filter(Boolean).join(' ');
}).catch(()=>{status.textContent='Server model status unavailable. Start the Python server and reload.';});
for(const [label,category,route] of words){
  if(!isWordEnabled(label.toUpperCase()))continue;
  const id=label.toLowerCase().replaceAll(' / ','-').replaceAll(' ','-');
  const card=document.createElement('article');card.className='vocabulary-card';
  const title=document.createElement('h4');title.textContent=label;
  const description=document.createElement('p');description.textContent=`${category} · ${routes[route]}`;
  const button=document.createElement('button');button.type='button';button.className='secondary-button';
  button.textContent=route==='personal'?'Teach this word':'Practice '+label;
  button.addEventListener('click',()=>{
    if(!target20.disabled){
      mode.value='target20';mode.dispatchEvent(new Event('change'));
      document.querySelector('#beginnerWords').scrollIntoView({block:'center',behavior:'smooth'});
      status.textContent=`${label}: all-20 research preview selected. Enable landmark processing, record, and review.`;return;
    }
    if(route==='essential'&&preview.disabled){
      document.dispatchEvent(new CustomEvent('handspeak:essential-practice',{detail:{id,label:label.toUpperCase(),personal:true}}));
      status.textContent=`${label}: server preview unavailable. Record personal examples instead.`;return;
    }
    if(route==='beginner'||route==='core'||route==='essential'){
      const panel=document.querySelector(route==='core'?'#capstoneWords':'#beginnerWords');
      if(route==='core'){
        const select=document.querySelector('#capstoneVocabMode');select.value='core';select.dispatchEvent(new Event('change'));
      }else {panel.dataset.closedLabels='';mode.value=route==='essential'?'essential':'ready';mode.dispatchEvent(new Event('change'));}
      panel.scrollIntoView({block:'center',behavior:'smooth'});
      status.textContent=`${label}: enable landmark processing in the ${route==='core'?'core':route==='essential'?'five-word preview':'Beginner'} panel, then record one complete sign and review the result.`;
      return;
    }
    document.dispatchEvent(new CustomEvent('handspeak:essential-practice',{detail:{id,label:label.toUpperCase(),personal:route==='personal'}}));
    status.textContent=`${label} · ${routes[route]}.`;
  });
  const teach=document.createElement('button');teach.type='button';teach.className='secondary-button';
  teach.textContent='Teach motion';teach.setAttribute('aria-label',`Teach ${label} motion`);
  teach.addEventListener('click',()=>{
    document.dispatchEvent(new CustomEvent('handspeak:essential-practice',{detail:{id,label:label.toUpperCase(),personal:true}}));
    status.textContent=`${label}: record at least three complete motion examples, then return to Words in motion to try recognition. Personal examples are stored only in this browser; accuracy is unverified.`;
  });
  card.append(title,description,button,teach);list.append(card);
}

function renderPassedWords(info){
  if(!info?.available||!passedWords.length)return;
  const panel=document.createElement('section');panel.className='trainer-card';panel.id='passedMotionWords';
  const title=document.createElement('h3');title.textContent='Passed offline checks';
  const note=document.createElement('p');note.textContent='These four words met ?80% recall and ?85% precision on recorded test clips. Experimental preview?not verified live-camera accuracy.';
  const cards=document.createElement('div');cards.className='vocabulary-cards';
  for(const label of passedWords){
    const metrics=info.metrics[label],card=document.createElement('article');card.className='vocabulary-card';
    const name=document.createElement('h4');name.textContent=label;
    const detail=document.createElement('p');detail.textContent=`Recorded test: ${metrics.correct}/${metrics.samples} correct ? ${(metrics.recall*100).toFixed(1)}% recall ? ${(metrics.precision*100).toFixed(1)}% precision`;
    const button=document.createElement('button');button.type='button';button.className='secondary-button';button.textContent=`Practice ${label}`;
    button.addEventListener('click',()=>{
      const recognition=document.querySelector('#recognitionMode');recognition.value='words';recognition.dispatchEvent(new Event('change'));
      document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#workspace'}}));
      mode.value='target20-passed';mode.dispatchEvent(new Event('change'));
      document.querySelector('#beginnerWords').scrollIntoView({block:'center',behavior:'smooth'});
      document.querySelector('#beginnerStatus').textContent=`Practice ${label}: enable server landmark processing, then record one complete sign. Review the suggestion before adding.`;
      document.querySelector('#beginnerConsent').focus({preventScroll:true});
    });
    card.append(name,detail,button);cards.append(card);
  }
  panel.append(title,note,cards);section.before(panel);
}
