import {loadVocabularySettings,applyVocabularySettings,isWordEnabled} from './vocabulary-settings.js?v=20261112-count-19-fix';
import {loadAccuracyProfiles,publishedAccuracy,accuracyText} from './motion-accuracy.js?v=20261020-accuracy-1';

// Browse UI removed. This module still prepares camera vocabulary and accuracy text
// for Watch & Learn / motion recognition.
export function createVocabularyLibrary({setVocabulary}) {
  const $=s=>document.querySelector(s);
  let catalog=null,packs=[],active='',loadId=0,libraryId=0,accuracyProfiles={},preparedId='';
  let cameraMatch=null;

  document.addEventListener('handspeak:essential-practice',async event=>{
    const {id,label,personal}=event.detail;
    const item=catalog?.items.find(entry=>entry.id===id);
    if(personal){
      if(!await activate(''))return;
      const preview=$('#researchWordsToggle');
      if(preview?.checked){preview.checked=false;preview.dispatchEvent(new Event('change'));}
      const motionLabel=$('#motionLabel');
      if(motionLabel){motionLabel.value=label;motionLabel.closest('details').open=true;motionLabel.scrollIntoView({block:'center',behavior:'smooth'});}
      cameraMode();
      document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#motionLabel'}}));
      return;
    }
    if(!item)return;
    await preparePractice(item);
    await practice(item);
  });

  function renderCameraAccuracy(){
    const output=$('#liveWordAccuracy');if(!output)return;
    output.hidden=!cameraMatch;if(!cameraMatch)return;
    const {label,daily,personal}=cameraMatch;
    const pack=packs.find(entry=>entry.id===active);
    const profile=accuracyProfiles[daily?'daily':$('#expandedWords')?.checked&&!$('#expandedWords').disabled?'expanded':'default'];
    const metrics=personal?null:!daily&&pack?publishedAccuracy(pack,label):profile?.words?.[label];
    output.textContent=accuracyText(metrics);
    output.title='Accuracy on recorded test clips, not confidence in this camera match. Live-camera accuracy is unverified.';
  }

  function renderMotionAccuracy(){
    const summary=$('#motionAccuracySummary'),body=$('#motionWordAccuracy');if(!summary||!body)return;
    const pack=packs.find(entry=>entry.id===active),daily=$('#researchWordsToggle')?.checked;
    if(pack&&!daily){
      summary.textContent=pack.labels.map(label=>`${label} · ${accuracyText(publishedAccuracy(pack,label))}`).join(' · ');
      body.textContent=`${pack.labels.map(label=>accuracyText(publishedAccuracy(pack,label))).join(' · ')}. Other-sign false matches: ${pack.test?.negativeFalse??'Not measured'} / ${pack.test?.negativeTotal??'Not measured'}. Live-camera accuracy is unverified.`;
      return;
    }
    const profile=accuracyProfiles[daily?'daily':$('#expandedWords')?.checked&&!$('#expandedWords').disabled?'expanded':'default'];
    summary.textContent=`Recorded word accuracy${profile?` · ${profile.model}`:''}`;
    body.textContent=profile?`${Object.entries(profile.words).map(([label,metrics])=>`${label} — ${accuracyText(metrics)}`).join(' · ')}. ${profile.scope}`:'Recorded accuracy: Not measured. Test results could not be loaded.';
  }

  function defaultLabel(){
    const extra=$('#expandedWords');
    const activeVocabulary=$('#activeVocabulary');
    if(activeVocabulary)activeVocabulary.textContent=extra?.checked&&!extra.disabled?'Camera vocabulary: Default + extra-word preview · 13 words':'Camera vocabulary: Default words';
    renderMotionAccuracy();
  }

  function cameraMode(){
    const mode=$('#recognitionMode');
    if(mode){mode.value='words';mode.dispatchEvent(new Event('change',{bubbles:true}));}
    document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#workspace'}}));
    $('#cameraButton')?.focus({preventScroll:true});
  }

  async function activate(id){
    const requested=++loadId;
    if(!id){
      if(!setVocabulary(null))return false;
      active='';
      defaultLabel();
      return true;
    }
    const pack=packs.find(entry=>entry.id===id);if(!pack)return false;
    try{
      const response=await fetch(pack.file+'?v='+(pack.sha256||'20261002-catalog-1'));if(!response.ok)throw Error('download failed');
      const bytes=await response.arrayBuffer();
      if(pack.sha256){
        const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),n=>n.toString(16).padStart(2,'0')).join('');
        if(hash!==pack.sha256)throw Error('model integrity failed');
      }
      const model=JSON.parse(new TextDecoder().decode(bytes));
      if(!Array.isArray(model.labels)||JSON.stringify(model.labels)!==JSON.stringify(pack.labels))throw Error('vocabulary mismatch');
      if(requested!==loadId)return false;
      if(!setVocabulary(model,pack.name))throw Error('model not ready or invalid');
      active=id;
      const activeVocabulary=$('#activeVocabulary');
      if(activeVocabulary)activeVocabulary.textContent=`Camera vocabulary: ${pack.name} preview`;
      cameraMode();
      renderMotionAccuracy();
      return true;
    }catch{
      return false;
    }
  }

  function dailyPreviewUnavailable(){
    const toggle=$('#researchWordsToggle');
    return Boolean(toggle&&toggle.disabled);
  }

  function noModelMessage(label){
    return `${label} · No enabled camera model: the five-word server preview is not installed on this server. Watch the example, then teach this word or practice with the default words.`;
  }

  async function practice(item){
    if(item.recognition==='default-preview'){
      document.dispatchEvent(new CustomEvent('handspeak:default-practice',{detail:{label:item.label}}));
      return;
    }
    if(item.recognition==='daily-preview'){
      if(dailyPreviewUnavailable())$('#signExampleMode')&&($('#signExampleMode').textContent=noModelMessage(item.label));
      document.dispatchEvent(new CustomEvent('handspeak:enable-word-preview'));
      return;
    }
    if(item.cameraGroups?.length){
      if(await activate(item.cameraGroups.includes(active)?active:item.cameraGroups[0])){
        document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#workspace'}}));
        $('#workspace')?.scrollIntoView({block:'start',behavior:'smooth'});
      }
      return;
    }
    if(['existing-preview','daily-preview','default-preview'].includes(item.recognition)){
      if(!await activate(''))return;
      const extra=$('#expandedWords');if(!extra||extra.disabled)return;
      extra.checked=true;extra.dispatchEvent(new Event('change'));cameraMode();
      return;
    }
    const motionLabel=$('#motionLabel');
    if(motionLabel){
      motionLabel.value=item.label;
      motionLabel.closest('details').open=true;
      motionLabel.scrollIntoView({block:'center',behavior:'smooth'});
      motionLabel.focus({preventScroll:true});
    }
    cameraMode();
    document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#motionLabel'}}));
  }

  async function preparePractice(item){
    if(item.recognition==='daily-preview'){
      if(dailyPreviewUnavailable()){$('#signExampleMode')&&($('#signExampleMode').textContent=noModelMessage(item.label));return;}
      const toggle=$('#researchWordsToggle');
      if(toggle&&!toggle.disabled&&!toggle.checked){toggle.checked=true;toggle.dispatchEvent(new Event('change'));}
      if($('#signExampleMode'))$('#signExampleMode').textContent+=` Camera vocabulary prepared: ${item.label} uses the five-word server preview.`;
      return;
    }
    if(item.recognition==='default-preview'||item.recognition==='existing-preview'){
      if(!await activate(''))return;
      const extra=$('#expandedWords');
      const needsExtra=['DRINK','WATER','BOOK','FOOD','HUNGRY','LIKE','GO'].includes(item.label);
      if(needsExtra&&extra&&!extra.disabled&&!extra.checked){extra.checked=true;extra.dispatchEvent(new Event('change'));}
      if($('#signExampleMode'))$('#signExampleMode').textContent+=` Camera vocabulary prepared for ${item.label}.`;
    }
  }

  async function preparePracticeId(id){
    const dailyIds=['name','home','have','want','love'];
    const extraIds=['drink','water','book','food','hungry','like','go'];
    if(dailyIds.includes(id)){
      if(dailyPreviewUnavailable()){$('#signExampleMode')&&($('#signExampleMode').textContent=noModelMessage(id.toUpperCase()));return;}
      const toggle=$('#researchWordsToggle');
      if(toggle&&!toggle.disabled&&!toggle.checked){toggle.checked=true;toggle.dispatchEvent(new Event('change'));}
      return;
    }
    if(extraIds.includes(id)){
      if(!await activate(''))return;
      const extra=$('#expandedWords');
      if(extra&&!extra.disabled&&!extra.checked){extra.checked=true;extra.dispatchEvent(new Event('change'));}
    }
  }

  async function load(){
    const request=++libraryId;
    try{
      const response=await fetch('models/motion-vocabulary.json?v=20261109-vm-sync-1',{cache:'no-store'});
      if(!response.ok)throw Error();
      const data=await response.json();
      if(!Array.isArray(data.items)||!Array.isArray(data.categories))throw Error();
      let index={groups:[]};
      try{
        const categories=await fetch('models/motion-categories/index.json?v=20261010-single-1',{cache:'no-store'});
        if(categories.ok)index=await categories.json();
      }catch{}
      if(request!==libraryId)return;
      ++loadId;
      await loadVocabularySettings();
      data.items=applyVocabularySettings(data.items);
      catalog=data;
      packs=Array.isArray(index.groups)?index.groups.filter(pack=>pack.labels.some(isWordEnabled)):[];
      for(const item of catalog.items)item.cameraGroups=(item.cameraGroups||[]).filter(id=>packs.some(p=>p.id===id&&p.labels.includes(item.label)));
      if(active&&!packs.some(p=>p.id===active)){setVocabulary(null);active='';defaultLabel();}
      renderMotionAccuracy();
      if(preparedId)void preparePracticeId(preparedId);
    }catch{ /* Practice helpers stay available even if the catalog cannot load. */ }
  }

  $('#expandedWords')?.addEventListener('change',()=>{if(!active)defaultLabel();});
  $('#researchWordsToggle')?.addEventListener('change',renderMotionAccuracy);
  document.addEventListener('handspeak:personal-words',()=>{if(!active)defaultLabel();});
  defaultLabel();
  document.addEventListener('handspeak:default-practice',async event=>{
    if(!await activate(''))return;
    const extra=$('#expandedWords');
    if(extra&&!extra.disabled){
      extra.checked=extra.checked||['DRINK','WATER','BOOK','FOOD','HUNGRY','LIKE','GO'].includes(event.detail.label);
      extra.dispatchEvent(new Event('change'));
    }
    cameraMode();
  });
  document.addEventListener('handspeak:practice',event=>{
    const item=catalog?.items.find(entry=>entry.id===event.detail.id);
    if(item)void practice(item);
  });
  document.addEventListener('handspeak:prepare-practice',event=>{
    preparedId=event.detail.id;
    void preparePracticeId(preparedId);
  });
  void load();
  void loadAccuracyProfiles().then(profiles=>{
    accuracyProfiles=profiles;
    renderMotionAccuracy();
    renderCameraAccuracy();
  });

  return {
    showCameraAccuracy(label,{daily=false,personal=false}={}){
      cameraMatch=typeof label==='string'&&/^[A-Z][A-Z '-]{0,29}$/.test(label)?{label,daily,personal}:null;
      renderCameraAccuracy();
    }
  };
}
