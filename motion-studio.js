import {isWordEnabled} from './vocabulary-settings.js?v=20261011-features-1';
import {isTemporalWordModel,validTemporalWordModel,recognizeTemporalWord} from './temporal-word-model.js?v=20261020-short-runs-1';
import {recognizeExpandedMotion} from './expanded-motion.js?v=20261109-vm-sync-1';
import {createAutomaticMotion} from './automatic-motion.js?v=20261020-appearance-1';
import {motionFrame,encodeMotion,validMotion,recognizeMotion,validMotionParameters} from './motion-model.js?v=20261109-vm-sync-1';
import {validBinaryTemporalModel,recognizeBinaryTemporal} from './hello-binary.js?v=20261021-binary-2';

export function createMotionStudio({isRunning,onWord,onStatus,speak,onFinish=()=>false,onDiagnostic=()=>{}}){
  const $=s=>document.querySelector(s), key='handspeak-motion-v3';
  let examples=[],baseExamples=[],parameters,baseState='Loading pretrained words…',capture=null,pending=null,lastSample=-Infinity,legacyExamples=false;
  let automatic=createAutomaticMotion();
  let autoWasActive=false,expansion=null,defaultModel=null,categoryModel=null,binaryModels=[];
  const expandedEnabled=()=>!categoryModel && $('#expandedWords').checked && expansion;
  const recognizeRaw=(sequence,frames,aspect)=>{if(isTemporalWordModel(categoryModel))return recognizeTemporalWord(categoryModel,frames,aspect);if(!categoryModel){const existing=recognizeExpandedMotion(sequence,allExamples(),parameters,expandedEnabled(),defaultModel?.cameraCompatibility);if(existing)return existing;for(const model of binaryModels){const match=recognizeBinaryTemporal(model,frames,aspect);if(match)return match;}return null;}const match=recognizeMotion(sequence,allExamples(),parameters);return match&&match.label!=='OTHER MOVEMENT'?match:null;};
  const recognize=(sequence,frames,aspect)=>{const match=recognizeRaw(sequence,frames,aspect);return match&&isWordEnabled(match.label)?match:null;};
  const allExamples=()=>baseExamples.concat(examples);
  function setHelp(message){$('#motionHelp').textContent=message;$('#motionCaptureStatus').textContent=message;}
  const labelOK=label=>typeof label==='string'&&/^[a-zA-Z][a-zA-Z /'-]{0,29}$/.test(label);
  try{
    const saved=JSON.parse(localStorage.getItem(key)||'[]');
    if(Array.isArray(saved))examples=saved.slice(0,96).filter(e=>labelOK(e.label)&&validMotion(e.sequence));
    const legacy=JSON.parse(localStorage.getItem('handspeak-motion-v2')||localStorage.getItem('handspeak-motion-v1')||'[]');
    legacyExamples=Array.isArray(legacy)&&legacy.length>0;
  }catch{}
  async function loadPretrained(){
    try{
      const response=await fetch('./models/asl-words.json?v=20261020-camera-compatibility-2');
      if(!response.ok)throw new Error('Word model download failed');
      const model=await response.json();
      if(model.version!==1||model.encoding!=='two-hand-motion-v3'||!validMotionParameters(model.parameters)
        ||!Array.isArray(model.samples)||model.samples.length<6||model.samples.length>600
        ||!model.samples.every(e=>labelOK(e.label)&&validMotion(e.sequence)))throw new Error('Invalid word model');
      const counts={};model.samples.forEach(e=>counts[e.label]=(counts[e.label]||0)+1);
      if(Object.keys(counts).length<2||Object.values(counts).some(n=>n<3))throw new Error('Insufficient word references');
      defaultModel=model;
      if(!categoryModel){baseExamples=model.samples;parameters=model.parameters;}
      baseState=`${new Set(baseExamples.map(e=>e.label)).size} pretrained words loaded`;
    }catch(error){console.warn(error);baseState='Pretrained words unavailable — reload to retry';}
    render();
  }
  async function loadExpansion(){
    try {
      const response=await fetch('./models/asl-extra-words.json?v=20261023-hungry-cutoff-1');
      if(!response.ok)throw new Error('Extra words unavailable');
      const model=await response.json();
      if(model.version!==1||model.encoding!=='two-hand-motion-v3'||!validMotionParameters(model.parameters)
        ||!Array.isArray(model.labels)||model.labels.length!==7||new Set(model.labels).size!==7||!model.labels.every(l=>['DRINK','WATER','BOOK','FOOD','HUNGRY','LIKE','GO'].includes(l))
        ||!Array.isArray(model.samples)||model.samples.length>200||!model.samples.every(e=>model.labels.includes(e.label)&&validMotion(e.sequence))
        ||!model.labels.every(l=>model.samples.filter(e=>e.label===l).length>=3))throw new Error('Invalid extra word model');
      const prior=model.baselineExtra;
      if(!prior || !validMotionParameters(prior.parameters) || !Array.isArray(prior.labels)
        || prior.labels.length!==3 || new Set(prior.labels).size!==3 || !prior.labels.every(l=>['DRINK','WATER','BOOK'].includes(l))
        || !Array.isArray(prior.samples) || prior.samples.length>200 || !prior.samples.every(e=>prior.labels.includes(e.label)&&validMotion(e.sequence))
        || !prior.labels.every(l=>prior.samples.filter(e=>e.label===l).length>=3)
        || !Array.isArray(model.newLabels) || model.newLabels.length!==4 || new Set(model.newLabels).size!==4
        || !model.newLabels.every(l=>['FOOD','HUNGRY','LIKE','GO'].includes(l)))throw new Error('Invalid preview stages');
      expansion=model;
      $('#expandedWords').disabled=false;
      $('#expandedWordsStatus').textContent='Preview ready: DRINK · WATER · BOOK · FOOD · HUNGRY · LIKE · GO. Limited accuracy; may mistake other movements for words. Review every suggestion.';
    } catch {
      $('#expandedWordsStatus').textContent='Extra words could not load. The original six words still work; reload to retry.';
    }
    render();
  }
  async function loadBinaryModels(){
    const loaded=[];
    for(const [path,word] of [
      ['./models/hello-binary.json?v=20261021-binary-2','HELLO'],
      ['./models/baby-binary.json?v=20261021-baby-1','BABY'],
      ['./models/water-binary.json?v=20261021-water-1','WATER']
    ])try{
      const response=await fetch(path);
      if(!response.ok)throw new Error(`${word} model download failed`);
      const model=await response.json();
      if(!validBinaryTemporalModel(model)||model.word!==word)throw new Error(`Invalid ${word} model`);
      loaded.push(model);
    }catch(error){console.warn(error);}
    binaryModels=loaded;render();
  }
  $('#expandedWords').addEventListener('change',()=>{
    cancel();onStatus('—');render();
    setHelp(expandedEnabled()?'Extra words preview enabled: DRINK, WATER, BOOK, FOOD, HUNGRY, LIKE, GO. Sign once, then pause.':'Using the original six words.');
  });
  function render(){
    const counts={};allExamples().filter(e=>e.label!=='OTHER MOVEMENT').forEach(e=>counts[e.label]=(counts[e.label]||0)+1);
    binaryModels.forEach(model=>counts[model.word]=Math.max(3,counts[model.word]||0));
    $('#expandedWords').disabled=Boolean(categoryModel)||!expansion;
    if(expandedEnabled())expansion.samples.forEach(e=>counts[e.label]=(counts[e.label]||0)+1);
    $('#motionLibrary').textContent=isTemporalWordModel(categoryModel)?categoryModel.labels.join(' · '):Object.keys(counts).map(label=>counts[label]>=3?label:`${label} (needs ${3-counts[label]} more examples)`).join(' · ')||'No word examples loaded yet.';
    $('#motionModelStatus').textContent=`${baseState}${expandedEnabled()?' + 7 preview words':''} · ${examples.length} personal examples${legacyExamples?' · Older personal recordings use a previous format; re-record those words if you want to use them.':''}`;
    $('#motionReady').textContent=isTemporalWordModel(categoryModel)?`Word model loaded: ${categoryModel.labels.join(' · ')}. Review each suggestion.`:(categoryModel||Object.values(counts).filter(n=>n>=3).length>=2)
      ?(baseExamples.length?'Pretrained words ready — no personal training required for these. New personal words need three examples each.':'Personal vocabulary ready')
      :'Waiting for pretrained words (or teach two words, three examples each).';
    $('#motionAccept').disabled=!pending;
    document.dispatchEvent?.(new CustomEvent('handspeak:personal-words'));
  }
  function finish(force=false){
    const active=capture;if(!active)return;
    clearTimeout(active.timer);
    // Give slow streams a bounded chance to reach the existing sample minimum.
    if(!force&&active.frames.length<12&&performance.now()<active.deadline){
      setHelp(`Camera is slow — collecting more frames (${active.frames.length}/12). Keep your hands in view.`);
      active.timer=setTimeout(()=>finish(true),Math.max(0,active.deadline-performance.now()));
      return;
    }
    capture=null;
    $('#motionTeach').disabled=false;$('#motionRecognize').disabled=false;$('#motionLabel').disabled=false;
    $('#motionCancel').disabled=true;$('#wordCaptureButton').disabled=false;
    const tracked=active.frames.filter(frame=>frame.some(Boolean)).length;
    if(active.frames.length<12){onStatus('Not enough frames','The recording was too slow. See the details below the camera.');setHelp(`Not enough camera frames: ${active.frames.length}/12 minimum. Try again with fewer apps open or a faster device.`);return;}
    const sequence=encodeMotion(active.frames,active.imageAspect||1);
    onDiagnostic({capture:'manual',frames:active.frames.length,trackedFrames:tracked,validSequence:Boolean(sequence)});
    if(!sequence){onStatus('Hands not tracked','Keep both hands fully visible. See the details below the camera.');setHelp(`Not enough clear hand tracking: hands visible in ${tracked}/${active.frames.length} frames. Keep your hands fully in view and use front lighting.`);return;}
    if(active.label){
      const updated=examples.concat({label:active.label,sequence});
      try{localStorage.setItem(key,JSON.stringify(updated));examples=updated;
        setHelp(`Saved an example of “${active.label}”. Record it again with a slightly different speed.`);onStatus('—','Personal example saved — record another example or try recognition.');
      }catch{setHelp('Could not save this recording. Browser storage may be full.');}
    }else{
      pending=recognize(sequence,active.frames,active.imageAspect||1);
      onDiagnostic({capture:'manual',frames:active.frames.length,trackedFrames:tracked,validSequence:true,match:pending?.label||null,sequence});
      setHelp(pending?`Possible match: “${pending.label}”. Check it before adding it to your message.`:`Captured ${active.frames.length} frames, but the model found no clear match. This experimental model may not recognize your signing reliably.`);
      onStatus(pending?.label||'No reliable match',pending?'Possible match — verify before adding':'The model did not recognize this recording. Your sign may still be correct.');
      maybeAddToSentence();
    }
    render();
  }
  function start(teach){
    if(!isRunning()){setHelp('Select Words in motion above the camera, then start the camera.');return;}
    if(capture)return;
    const label=$('#motionLabel').value.trim().replace(/\s+/g,' ').toUpperCase();
    if(teach && !labelOK(label)){setHelp('Enter a word or short phrase using letters (up to 30 characters).');return;}
    if(teach && (examples.length>=96 || examples.filter(e=>e.label===label).length>=8)){
      setHelp('Library limit reached (8 recordings per word, 96 total). Remove a word to record more.');return;
    }
    const counts={};allExamples().forEach(e=>counts[e.label]=(counts[e.label]||0)+1);
    // A category preview is a trained classifier with no template samples, so the
    // "two words with three examples" rule does not apply to it. Without this the
    // manual Record button silently did nothing for single-word previews.
    if(!teach && !isTemporalWordModel(categoryModel) && Object.values(counts).filter(n=>n>=3).length<2){setHelp('The word model is not ready. Wait for it to load, or reload the page.');return;}
    automatic.reset();autoWasActive=false;
    pending=null;render();onStatus('—','Get ready — recording starts after the countdown.');lastSample=-Infinity;
    const now=performance.now();
    capture={label:teach?label:null,start:now+1500,end:now+4000,deadline:now+6000,frames:[],timer:setTimeout(()=>finish(),4050)};
    $('#motionTeach').disabled=true;$('#motionRecognize').disabled=true;$('#motionLabel').disabled=true;
    $('#motionCancel').disabled=false;$('#wordCaptureButton').disabled=true;
    setHelp('Get ready… recording starts in 1.5 seconds. Perform the sign once over 2.5 seconds.');
  }
  function cancel(){
    automatic.reset();autoWasActive=false;
    if(capture){clearTimeout(capture.timer);capture=null;setHelp('Recording canceled. Nothing was saved.');}
    pending=null;$('#motionAccept').disabled=true;
    $('#motionTeach').disabled=false;$('#motionRecognize').disabled=false;$('#motionLabel').disabled=false;$('#motionCancel').disabled=true;$('#wordCaptureButton').disabled=false;
  }
  $('#automaticWords').addEventListener('change',()=>{
    cancel();onStatus('—');
    setHelp($('#automaticWords').checked?'Automatic words enabled. Sign once, then pause briefly.':'Automatic words off. Select Record a word to capture a sign.');
  });
  function automaticFrame(detection,now){
    if(!$('#automaticWords').checked||!isRunning()||(!baseExamples.length&&!isTemporalWordModel(categoryModel)))return;
    const clip=automatic.push(motionFrame(detection),now,detection.imageAspect||1);
    const active=automatic.isActive();
    if(active&&!autoWasActive){pending=null;render();onStatus('—','Hand detected · Analyzing movement… pause when finished.');setHelp('Watching your sign… pause briefly when finished.');}
    autoWasActive=active;
    if(!clip)return;
    const sequence=encodeMotion(clip.frames,clip.imageAspect);
    pending=sequence?recognize(sequence,clip.frames,clip.imageAspect):null;
    const tracked=clip.frames.filter(f=>f.some(Boolean)).length;
    onDiagnostic({capture:'automatic',frames:clip.frames.length,trackedFrames:tracked,durationMs:Math.round(now-clip.start),validSequence:Boolean(sequence),match:pending?.label||null,sequence});
    const detail=pending?'Possible match — verify before adding':!sequence?`Capture incomplete: ${tracked}/${clip.frames.length} frames had usable hands. Keep the full hand visible; check Camera diagnostics.`:'Hands captured, but no word passed the matching checks. Check the active vocabulary and Camera diagnostics.';
    onStatus(pending?.label||(clip.frames.length<12?'Not enough frames':!sequence?'Capture incomplete':'No reliable match'),detail);
    setHelp(pending?`Possible match: “${pending.label}”. Pause before your next sign. Review it before adding it.`:detail);
    maybeAddToSentence();render();
  }
  function acceptPending(automaticAdd=false){
    if(!pending)return;
    const word=pending.label;
    if(onWord(word)===false){setHelp('Message is full. Edit or clear it before adding another word.');return;}
    pending=null;
    if(!automaticAdd && $('#motionAutoSpeak').checked)speak(word);
    setHelp(`Added “${word}” to your draft. Review it before speaking.`);render();
  }
  function maybeAddToSentence(){if(pending?.label==='FINISH'&&onFinish()){pending=null;setHelp('FINISH received. Check sentence interpretation below for the result.');return;}if($('#sentenceAutoAdd').checked)acceptPending(true);}
  $('#motionTeach').addEventListener('click',()=>start(true));
  $('#motionRecognize').addEventListener('click',()=>start(false));
  $('#motionCancel').addEventListener('click',cancel);
  $('#motionAccept').addEventListener('click',()=>acceptPending());
  $('#sentenceAutoAdd').addEventListener('change',()=>{if($('#sentenceAutoAdd').checked&&pending&&pending.label!=='FINISH'){acceptPending(true);render();}});
  $('#motionRemove').addEventListener('click',()=>{
    if(capture)return;
    const label=$('#motionLabel').value.trim().replace(/\s+/g,' ').toUpperCase();
    const updated=examples.filter(e=>e.label!==label);
    if(updated.length===examples.length){setHelp('Enter the name of a recorded word to remove it.');return;}
    try{localStorage.setItem(key,JSON.stringify(updated));examples=updated;pending=null;render();setHelp(`Removed “${label}”.`);}
    catch{setHelp('Could not update browser storage.');}
  });
  render();
  void loadPretrained();
  void loadExpansion();
  void loadBinaryModels();
  return {
    usesTemporalModel:()=>isTemporalWordModel(categoryModel),
    hasPersonalWord:label=>!isTemporalWordModel(categoryModel)&&examples.some(example=>example.label===label),
    setVocabulary(model,name=''){
      if(!defaultModel)return false;
      if(isTemporalWordModel(model)&&!validTemporalWordModel(model))return false;
      if(model && !isTemporalWordModel(model) && (model.version!==1||model.encoding!=='two-hand-motion-v3'||!validMotionParameters(model.parameters)
        ||!Array.isArray(model.labels)||!model.labels.length||model.labels.length>30||!model.labels.every(labelOK)
        ||!Array.isArray(model.samples)||model.samples.length>450||!model.samples.every(e=>labelOK(e.label)&&(model.labels.includes(e.label)||e.label==='OTHER MOVEMENT')&&validMotion(e.sequence))
        ||!model.labels.every(l=>model.samples.filter(e=>e.label===l).length>=3)))return false;
      cancel();categoryModel=model;const active=model||defaultModel;baseExamples=active.samples||[];parameters=active.parameters;automatic=createAutomaticMotion({sampleIntervalMs:isTemporalWordModel(model)?30:80});
      baseState=model?`${name} category preview (${model.labels.length} ${model.labels.length===1?'word':'words'})`:`${new Set(baseExamples.map(e=>e.label)).size} pretrained words loaded`;
      pending=null;onStatus('—');render();setHelp(model?'Category preview enabled. Use only its listed words; review every match.':'Default vocabulary restored.');return true;
    },
    cancel,
    isCapturing:()=>Boolean(capture)||automatic.isActive(),
    isRecording:()=>Boolean(capture),
    recognize:()=>start(false),
    frame(detection,now){
      if(!capture){automaticFrame(detection,now);return;}
      if(now<capture.start){setHelp(`Get ready… ${Math.ceil((capture.start-now)/1000)}. Keep your hands in view.`);return;}
      if(now>=capture.deadline){finish(true);return;}
      if(now>=capture.end&&capture.frames.length>=12){finish(true);return;}
      onStatus('—',capture.label?'Hand detected — recording a personal example.':'Analyzing movement… finish your sign and pause.');
      setHelp(now>=capture.end?`Camera is slow — collecting more frames (${capture.frames.length}/12). Keep your hands in view.`:`Recording… ${((capture.end-now)/1000).toFixed(1)} seconds left`);
      if(now-lastSample>=(isTemporalWordModel(categoryModel)?30:80)){
        const aspect=detection.imageAspect||1;
        if(capture.imageAspect&&Math.abs(capture.imageAspect-aspect)>.01){cancel();setHelp('Camera orientation changed. Record the sign again.');return;}
        capture.imageAspect=aspect;capture.frames.push(motionFrame(detection));lastSample=now;
        if(now>=capture.end&&capture.frames.length>=12)finish(true);
      }
    }
  };
}
