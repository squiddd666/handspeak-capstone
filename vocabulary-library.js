import {loadVocabularySettings,applyVocabularySettings,isWordEnabled} from './vocabulary-settings.js?v=20261011-features-1';
import {loadAccuracyProfiles,referenceAccuracy,publishedAccuracy,accuracyText} from './motion-accuracy.js?v=20261020-accuracy-1';
const text=(tag,value,className)=>{const e=document.createElement(tag);e.textContent=value;if(className)e.className=className;return e;};
export function createVocabularyLibrary({onWord,setVocabulary}) {
  const $=s=>document.querySelector(s),size=12;
  let catalog=null,packs=[],page=0,active='',loadId=0,libraryId=0,accuracyProfiles={},preparedId='';
  let cameraMatch=null;
  document.addEventListener('handspeak:essential-practice',async event=>{
    const {id,label,personal}=event.detail;
    const item=catalog?.items.find(item=>item.id===id);
    if(personal){
      if(!await activate(''))return;
      const preview=$('#researchWordsToggle');
      if(preview.checked){preview.checked=false;preview.dispatchEvent(new Event('change'));}
      $('#motionLabel').value=label;$('#motionLabel').closest('details').open=true;
      cameraMode();document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#motionLabel'}}));
      $('#motionLabel').scrollIntoView({block:'center',behavior:'smooth'});
      $('#vocabularyCameraStatus').textContent=`${label}: not in the ready vocabulary. Record at least three personal examples before trying recognition.`;
      return;
    }
    if(!item){$('#vocabularyCameraStatus').textContent='The vocabulary library is still loading or this word is unavailable. Try again shortly.';return;}
    await preparePractice(item);
    await practice(item);
  });
  function renderCameraAccuracy(){
    const output=$('#liveWordAccuracy');if(!output)return;
    output.hidden=!cameraMatch;if(!cameraMatch)return;
    const {label,daily,personal}=cameraMatch;
    const pack=packs.find(pack=>pack.id===active);
    const profile=accuracyProfiles[daily?'daily':$('#expandedWords').checked&&!$('#expandedWords').disabled?'expanded':'default'];
    const metrics=personal?null:!daily&&pack?publishedAccuracy(pack,label):profile?.words?.[label];
    output.textContent=accuracyText(metrics);
    output.title='Accuracy on recorded test clips, not confidence in this camera match. Live-camera accuracy is unverified.';
  }
  function renderMotionAccuracy(){
    const summary=$('#motionAccuracySummary'),body=$('#motionWordAccuracy');if(!summary||!body)return;
    const pack=packs.find(pack=>pack.id===active),daily=$('#researchWordsToggle').checked;
    if(pack&&!daily){
      summary.textContent=pack.labels.map(label=>`${label} · ${accuracyText(publishedAccuracy(pack,label))}`).join(' · ');
      body.textContent=`${pack.labels.map(label=>accuracyText(publishedAccuracy(pack,label))).join(' · ')}. Other-sign false matches: ${pack.test?.negativeFalse??'Not measured'} / ${pack.test?.negativeTotal??'Not measured'}. Live-camera accuracy is unverified.`;return;
    }
    const profile=accuracyProfiles[daily?'daily':$('#expandedWords').checked&&!$('#expandedWords').disabled?'expanded':'default'];
    summary.textContent=`Recorded word accuracy${profile?` · ${profile.model}`:''}`;
    body.textContent=profile?`${Object.entries(profile.words).map(([label,metrics])=>`${label} — ${accuracyText(metrics)}`).join(' · ')}. ${profile.scope}`:'Recorded accuracy: Not measured. Test results could not be loaded.';
  }
  function defaultLabel(){const extra=$('#expandedWords');$('#activeVocabulary').textContent=extra.checked&&!extra.disabled?'Camera vocabulary: Default + extra-word preview · 13 words':'Camera vocabulary: Default words';renderMotionAccuracy();}
  function filtered(){
    const query=$('#vocabularySearch').value.toLowerCase().trim(),category=$('#vocabularyCategory').value,kind=$('#vocabularyFilter').value;
    return catalog.items.filter(item=>(!query||[item.label,...(item.searchAliases||[])].some(value=>value.toLowerCase().includes(query)))&&(!category||item.categories.includes(category))&&(!kind||(kind==='video'&&(item.video||item.youtubeId))||(kind==='model'&&(item.cameraGroups?.length||['existing-preview','daily-preview','default-preview'].includes(item.recognition)))||(kind==='personal'&&!item.cameraGroups?.length&&!['existing-preview','daily-preview','default-preview'].includes(item.recognition))));
  }
  function cameraMode(){const mode=$('#recognitionMode');mode.value='words';mode.dispatchEvent(new Event('change',{bubbles:true}));document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#workspace'}}));$('#cameraButton').focus({preventScroll:true});}
  async function activate(id){
    const requested=++loadId,select=$('#cameraVocabulary'),status=$('#vocabularyCameraStatus');select.value=id;
    if(!id){if(!setVocabulary(null)){status.textContent='Default model is still loading. Try again shortly.';select.value=active;return false;}active='';defaultLabel();status.textContent='Default vocabulary selected. The extra-word preview is controlled below.';return true;}
    const pack=packs.find(p=>p.id===id);if(!pack)return false;
    status.textContent=`Loading ${pack.name}…`;
    try {
      const response=await fetch(pack.file+'?v='+(pack.sha256||'20261002-catalog-1'));if(!response.ok)throw Error('download failed');
      const bytes=await response.arrayBuffer();
      if(pack.sha256){const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');if(hash!==pack.sha256)throw Error('model integrity failed');}
      const model=JSON.parse(new TextDecoder().decode(bytes));
      if(!Array.isArray(model.labels)||JSON.stringify(model.labels)!==JSON.stringify(pack.labels))throw Error('vocabulary mismatch');
      if(requested!==loadId)return false;
      if(!setVocabulary(model,pack.name))throw Error('model not ready or invalid');active=id;$('#activeVocabulary').textContent=`Camera vocabulary: ${pack.name} preview`;
      status.textContent=`${pack.name} preview: ${pack.labels.join(' · ')}. Use only these words; review every suggestion.${pack.test?` ${pack.labels.map(label=>accuracyText(publishedAccuracy(pack,label))).join(' · ')}; ${pack.test.negativeFalse}/${pack.test.negativeTotal} unsupported clips falsely accepted. This is not live-camera accuracy.`:''}${pack.releaseNotice?` ${pack.releaseNotice}`:''} Category changes reset the current capture.`;cameraMode();renderMotionAccuracy();return true;
    }catch{if(requested===loadId){select.value=active;status.textContent='Category could not load. The previous camera vocabulary remains selected. Try again.';}return false;}
  }
  // The five-word preview is optional server code. When it is not installed the
  // word has no camera model at all, so say so instead of letting the default
  // vocabulary answer for it.
  function dailyPreviewUnavailable(){const toggle=$('#researchWordsToggle');return Boolean(toggle&&toggle.disabled);}
  function noModelMessage(label){return `${label} · No enabled camera model: the five-word server preview is not installed on this server. Watch the example, then teach this word or practice with the default words.`;}
  async function practice(item){
    if(item.recognition==='default-preview'){document.dispatchEvent(new CustomEvent('handspeak:default-practice',{detail:{label:item.label}}));return;}
    if(item.recognition==='daily-preview'){
      if(dailyPreviewUnavailable()){
        $('#signExampleMode').textContent=noModelMessage(item.label);
        $('#vocabularyCameraStatus').textContent=noModelMessage(item.label);
      }
      document.dispatchEvent(new CustomEvent('handspeak:enable-word-preview'));return;
    }
    if(item.cameraGroups?.length){if(await activate(item.cameraGroups.includes(active)?active:item.cameraGroups[0])){document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#workspace'}}));$('#workspace').scrollIntoView({block:'start',behavior:'smooth'});}return;}
    if(['existing-preview','daily-preview','default-preview'].includes(item.recognition)){
      if(!await activate(''))return;
      const extra=$('#expandedWords');if(extra.disabled){$('#vocabularyCameraStatus').textContent='Extra words are still loading. Try again shortly.';return;}
      extra.checked=true;extra.dispatchEvent(new Event('change'));cameraMode();return;
    }
    $('#motionLabel').value=item.label;$('#motionLabel').closest('details').open=true;cameraMode();document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#motionLabel'}}));$('#motionLabel').scrollIntoView({block:'center',behavior:'smooth'});$('#motionLabel').focus({preventScroll:true});
    $('#vocabularyCameraStatus').textContent=`${item.label} has no active pretrained model. Record at least three personal examples; this does not validate recognition accuracy.`;
  }
  async function preparePractice(item){
    if(item.recognition==='daily-preview'){
      if(dailyPreviewUnavailable()){$('#signExampleMode').textContent=noModelMessage(item.label);return;}
      if(!$('#researchWordsToggle').disabled&&!$('#researchWordsToggle').checked){
        $('#researchWordsToggle').checked=true;$('#researchWordsToggle').dispatchEvent(new Event('change'));
      }
      $('#signExampleMode').textContent+=` Camera vocabulary prepared: ${item.label} uses the five-word server preview.`;
      return;
    }
    if(item.recognition==='default-preview'||item.recognition==='existing-preview'){
      if(!await activate(''))return;
      const extra=$('#expandedWords');
      const needsExtra=['DRINK','WATER','BOOK','FOOD','HUNGRY','LIKE','GO'].includes(item.label);
      if(needsExtra&&!extra.disabled&&!extra.checked){extra.checked=true;extra.dispatchEvent(new Event('change'));}
      $('#signExampleMode').textContent+=` Camera vocabulary prepared for ${item.label}.`;
    }
  }
  async function preparePracticeId(id){
    const dailyIds=['name','home','have','want','love'];
    const extraIds=['drink','water','book','food','hungry','like','go'];
    if(dailyIds.includes(id)){
      if(dailyPreviewUnavailable()){$('#signExampleMode').textContent=noModelMessage(id.toUpperCase());return;}
      if(!$('#researchWordsToggle').disabled&&!$('#researchWordsToggle').checked){
        $('#researchWordsToggle').checked=true;$('#researchWordsToggle').dispatchEvent(new Event('change'));
      }
      return;
    }
    if(extraIds.includes(id)){
      if(!await activate(''))return;
      const extra=$('#expandedWords');
      if(!extra.disabled&&!extra.checked){extra.checked=true;extra.dispatchEvent(new Event('change'));}
    }
  }
  function render(){
    if(!catalog)return;const matches=filtered(),pages=Math.max(1,Math.ceil(matches.length/size));page=Math.min(page,pages-1);
    $('#vocabularyStatus').textContent=`${matches.length} of ${catalog.items.length} entries · videos, external lessons, and recognition availability are shown separately.`;
    $('#vocabularyPage').textContent=`Page ${page+1} of ${pages}`;$('#vocabularyPrevious').disabled=page===0;$('#vocabularyNext').disabled=page>=pages-1;
    $('#vocabularyEmergency').hidden=!['health-emergency','safety'].includes($('#vocabularyCategory').value);const cards=$('#vocabularyCards');cards.replaceChildren();
    for(const item of matches.slice(page*size,(page+1)*size)){
      const card=text('article','', 'vocabulary-card');card.append(text('h4',item.label));
      card.append(text('span',item.recognition==='default-preview'?'Default motion preview':item.recognition==='daily-preview'?'Five-word server preview':item.cameraGroups?.length?'Category recognition preview':['existing-preview','daily-preview','default-preview'].includes(item.recognition)?'Existing recognition preview':'No enabled model','vocabulary-badge'));
      if(item.testSummary)card.append(text('p',item.testSummary,'camera-tip'));
      const pack=packs.find(pack=>item.cameraGroups?.includes(pack.id)&&pack.labels?.includes(item.label));
      const metrics=pack?publishedAccuracy(pack,item.label):referenceAccuracy(accuracyProfiles,item.label);
      card.append(text('p',`${accuracyText(metrics)}${metrics?` · ${metrics.model}`:''}`,'camera-tip'));
      if(item.note)card.append(text('p',item.note,'camera-tip'));
      const actions=text('div','','vocabulary-card-actions');
      if(item.video||item.youtubeId){const b=text('button','Watch example','secondary-button');b.type='button';b.onclick=()=>{document.dispatchEvent(new CustomEvent('handspeak:example',{detail:{label:item.label,src:item.video,id:item.id}}));document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#sign-examples'}}));$('#sign-examples').scrollIntoView({block:'start',behavior:'smooth'});};actions.append(b);}
      if(item.learningUrl){const a=text('a',item.learningScope?`Lesson: ${item.learningScope}`:'View source example','primary-link');a.href=item.learningUrl;a.target='_blank';a.rel='noopener noreferrer';actions.append(a);}
      if(!item.video&&!item.learningUrl)card.append(text('p','A verified lesson or recording is still needed for this entry.','camera-tip'));
      const camera=text('button',item.cameraGroups?.length||['existing-preview','daily-preview','default-preview'].includes(item.recognition)?'Practice at camera':'Teach this sign','secondary-button');camera.type='button';camera.onclick=()=>{void practice(item);};actions.append(camera);
      const type=text('button','Add as typed text','text-button');type.type='button';type.onclick=()=>{if(onWord(item.label)!==false)$('#vocabularyStatus').textContent=`Added ${item.label} as typed text, not a camera detection.`;};actions.append(type);card.append(actions);cards.append(card);
    }
    if(!matches.length)cards.append(text('p','No matching entries. Try another word or category.'));
  }
  async function load(){
    const request=++libraryId;$('#vocabularyRetry').disabled=true;
    try {
      const response=await fetch('models/motion-vocabulary.json?v=20261109-vm-sync-1',{cache:'no-store'});if(!response.ok)throw Error();const data=await response.json();
      if(!Array.isArray(data.items)||!Array.isArray(data.categories))throw Error();
      let index={groups:[]};try{const r=await fetch('models/motion-categories/index.json?v=20261010-single-1',{cache:'no-store'});if(r.ok)index=await r.json();}catch{}
      if(request!==libraryId)return;++loadId;await loadVocabularySettings();data.items=applyVocabularySettings(data.items);catalog=data;packs=Array.isArray(index.groups)?index.groups.filter(pack=>pack.labels.some(isWordEnabled)):[];
      for(const item of catalog.items)item.cameraGroups=(item.cameraGroups||[]).filter(id=>packs.some(p=>p.id===id&&p.labels.includes(item.label)));
      if(active&&!packs.some(p=>p.id===active)){setVocabulary(null);active='';defaultLabel();}
      const select=$('#vocabularyCategory'),previous=select.value;select.replaceChildren(new Option('All categories',''));catalog.categories.forEach(c=>select.add(new Option(c.name,c.id)));select.value=previous;
      const camera=$('#cameraVocabulary');camera.replaceChildren(new Option('Default words',''));packs.forEach(p=>camera.add(new Option(p.name+' · preview',p.id)));camera.value=active;camera.closest('label').hidden=packs.length===0;
      if(!packs.length)$('#vocabularyCameraStatus').textContent='New category models did not pass evaluation. Default words and the existing extra-word preview remain available.';
      page=0;render();renderMotionAccuracy();
      if(preparedId)void preparePracticeId(preparedId);
    }catch{if(request===libraryId)$('#vocabularyStatus').textContent='Vocabulary could not load. Use Reload library to retry.';}
    finally{if(request===libraryId)$('#vocabularyRetry').disabled=false;}
  }
  for(const id of ['#vocabularySearch','#vocabularyCategory','#vocabularyFilter'])$(id).addEventListener(id==='#vocabularySearch'?'input':'change',()=>{page=0;render();});
  $('#vocabularyPrevious').onclick=()=>{page--;render();};$('#vocabularyNext').onclick=()=>{page++;render();};$('#vocabularyRetry').onclick=()=>{void load();};$('#cameraVocabulary').onchange=e=>{void activate(e.target.value);};
  $('#expandedWords').addEventListener('change',()=>{if(!active)defaultLabel();});
  $('#researchWordsToggle').addEventListener('change',renderMotionAccuracy);
  document.addEventListener('handspeak:personal-words',()=>{if(!active)defaultLabel();});
  defaultLabel();
  document.addEventListener('handspeak:default-practice',async event=>{if(!await activate(''))return;const extra=$('#expandedWords');if(!extra.disabled){extra.checked=extra.checked||['DRINK','WATER','BOOK','FOOD','HUNGRY','LIKE','GO'].includes(event.detail.label);extra.dispatchEvent(new Event('change'));}cameraMode();});
  document.addEventListener('handspeak:practice',event=>{const item=catalog?.items.find(i=>i.id===event.detail.id);if(item)void practice(item);});
  document.addEventListener('handspeak:prepare-practice',event=>{preparedId=event.detail.id;void preparePracticeId(preparedId);});
  void load();
  void loadAccuracyProfiles().then(profiles=>{accuracyProfiles=profiles;render();renderMotionAccuracy();renderCameraAccuracy();});
  return {showCameraAccuracy(label,{daily=false,personal=false}={}){
    cameraMatch=typeof label==='string'&&/^[A-Z][A-Z '-]{0,29}$/.test(label)?{label,daily,personal}:null;
    renderCameraAccuracy();
  }};
}
