import {createOpenHandsRecognition} from './openhands-recognition.js?v=20261112-openhands-video-play';
import {installFakeCameraTest} from './fake-camera-test.js?v=20261112-panel-1';
import {commitCurrentWord} from './interpreter-words.js';
import './interpreter-layout.js?v=20261112-capture-preroll-v2';
import {createLetterCamera} from './letter-camera.js?v=20261112-signspeak-only-1';
import {classifyLetter,letterFeatures,isUsableLetterHand,sameObservedHand,createLetterConsensus} from './letter-recognition.js?v=20261111-letter-repair-1';
import {createMultiHandMotionLetters} from './motion-letters.js?v=20261111-motion-geometry-1';
import {createExperienceUI} from './experience-ui.js?v=20261020-simple-view-1';
import {loadVocabularySettings,isWordEnabled} from './vocabulary-settings.js?v=20261112-count-19-fix';
import {createTemporalCamera} from './temporal-camera.js?v=20261112-tracker-watchdog';
import {preferredVisionDelegate} from './camera-performance.js?v=20261010-single-1';
import {createResearchWords} from './research-words.js?v=20261109-vm-sync-1';
import {createVocabularyLibrary} from './vocabulary-library.js?v=20261112-remove-browse-library';
import {createInterpreter} from './interpretation.js?v=20261011-features-1';
import {appendWord,finishSentence,removeLastWord} from './sentence-builder.js?v=20261002-sentences-1';
import { createFaceTracker } from './face-tracker.js?v=20261111-architecture-2';
import { createMotionStudio } from './motion-studio.js?v=auto-preroll-v1-combined-1-20261111-motion20-1';
import { normalizeLandmarks, classifyFeatures, validSample, DEFAULT_PARAMETERS, validParameters, isUsableHand } from './gesture-model.js?v=20261109-static-alphabet-v2';

const signSpeakSelected=true;
const $ = (selector) => document.querySelector(selector);
const video = $('#webcam');
const canvas = $('#overlay');
const ctx = canvas.getContext('2d');
const cameraButton = $('#cameraButton');
const cameraStatus = $('#cameraStatus');
const placeholder = $('#cameraPlaceholder');
const liveResult = $('#liveResult');
const liveLetter = $('#liveLetter');
const liveConfidence = $('#liveConfidence');
const validTrackedHand=p=>Array.isArray(p)&&p.length===21&&p.every(q=>q&&Number.isFinite(q.x)&&Number.isFinite(q.y));
const fullHandInFrame=p=>validTrackedHand(p)&&p.every(q=>q.x>=0&&q.x<=1&&q.y>=0&&q.y<=1);
function reportWordHands(data,lag){
 const raw=(data.landmarks||[]).filter(validTrackedHand),full=raw.filter(fullHandInFrame);
 const hint=$('#wordHandStatus');if(!hint)return;
 const text=!raw.length?'No hand detected - bring your full hand into view.':!full.length?'Hand detected, but partly outside the camera. Move back until all fingers fit.':lag>500?'Hand tracked, but tracking is delayed. Keep the sign slow and clear.':`${full.length} hand${full.length===1?'':'s'} tracked - keep fingers inside the camera.`;
 if(hint.textContent!==text)hint.textContent=text;
}
let vocabularyLibrary;
let openHandsRecognition;
function setWordCameraResult(word,detail,daily=false,model=null){
  if(model!=='OpenHands'&&!isWordEnabled(word)){liveResult.hidden=true;return;}
  liveResult.hidden=word==='—';liveLetter.textContent=word;
  liveConfidence.textContent=detail||'Possible match — verify before adding';
  vocabularyLibrary?.showCameraAccuracy(model?null:word,{daily,personal:!daily&&motionStudio.hasPersonalWord(word)});
  document.dispatchEvent(new CustomEvent('handspeak:camera-match',{detail:{word,model:model||$('#activeVocabulary').textContent}}));
}
const messageText = $('#messageText');
const toast = $('#toast');

const SIGNS = [
  {
    "letter": "A",
    "name": "A",
    "hint": "Closed fist, thumb beside the fingers",
    "motion": false
  },
  {
    "letter": "B",
    "name": "B",
    "hint": "Four fingers up together, thumb across palm",
    "motion": false
  },
  {
    "letter": "C",
    "name": "C",
    "hint": "Curve the fingers and thumb into a C",
    "motion": false
  },
  {
    "letter": "D",
    "name": "D",
    "hint": "Index up; thumb touches the other fingertips",
    "motion": false
  },
  {
    "letter": "E",
    "name": "E",
    "hint": "Curl fingertips down toward the thumb",
    "motion": false
  },
  {
    "letter": "F",
    "name": "F",
    "hint": "Index and thumb touch; other three fingers raised",
    "motion": false
  },
  {
    "letter": "G",
    "name": "G",
    "hint": "Index and thumb point sideways, held apart",
    "motion": false
  },
  {
    "letter": "H",
    "name": "H",
    "hint": "Index and middle fingers together, pointing sideways",
    "motion": false
  },
  {
    "letter": "I",
    "name": "I",
    "hint": "Pinky raised, other fingers closed",
    "motion": false
  },
  {
    "letter": "J",
    "name": "J",
    "hint": "Start with the pinky raised, then trace the J path; requires motion recognition",
    "motion": true
  },
  {
    "letter": "K",
    "name": "K",
    "hint": "Index and middle raised; thumb between them",
    "motion": false
  },
  {
    "letter": "L",
    "name": "L",
    "hint": "Index and thumb form an L",
    "motion": false
  },
  {
    "letter": "M",
    "name": "M",
    "hint": "Thumb tucked under three fingers",
    "motion": false
  },
  {
    "letter": "N",
    "name": "N",
    "hint": "Thumb tucked under two fingers",
    "motion": false
  },
  {
    "letter": "O",
    "name": "O",
    "hint": "Curve all fingertips to meet the thumb",
    "motion": false
  },
  {
    "letter": "P",
    "name": "P",
    "hint": "K handshape pointing down",
    "motion": false
  },
  {
    "letter": "Q",
    "name": "Q",
    "hint": "G handshape pointing down",
    "motion": false
  },
  {
    "letter": "R",
    "name": "R",
    "hint": "Cross the index and middle fingers",
    "motion": false
  },
  {
    "letter": "S",
    "name": "S",
    "hint": "Fist with thumb across the front",
    "motion": false
  },
  {
    "letter": "T",
    "name": "T",
    "hint": "Thumb tucked between index and middle fingers",
    "motion": false
  },
  {
    "letter": "U",
    "name": "U",
    "hint": "Index and middle fingers up together",
    "motion": false
  },
  {
    "letter": "V",
    "name": "V",
    "hint": "Index and middle fingers spread",
    "motion": false
  },
  {
    "letter": "W",
    "name": "W",
    "hint": "Index, middle, and ring fingers raised",
    "motion": false
  },
  {
    "letter": "X",
    "name": "X",
    "hint": "Index bent into a hook",
    "motion": false
  },
  {
    "letter": "Y",
    "name": "Y",
    "hint": "Thumb and pinky extended",
    "motion": false
  },
  {
    "letter": "Z",
    "name": "Z",
    "hint": "Start with the index extended, then trace the Z path; requires motion recognition",
    "motion": true
  },
  {
    "letter": "5",
    "name": "Five",
    "hint": "All five fingers extended and spread",
    "motion": false
  }
];
const STATIC_SIGNS=SIGNS.filter(sign=>!sign.motion);
const MOTION_REFERENCE_VIDEOS={
  J:'https://framerusercontent.com/assets/kdD6YIKtTwsgQjzC89OtLRO3Q.mp4',
  Z:'https://framerusercontent.com/assets/is7w4CKj3wZrASC9kxh6CFHJ7Zo.mp4'
};
function renderSignLibrary(){
  $('#signGrid').innerHTML = SIGNS.filter(sign=>sign.letter!=='5').map(sign => {
    const video=MOTION_REFERENCE_VIDEOS[sign.letter];
    const media=video
      ?`<video class="sign-motion-video" src="${video}" controls playsinline muted loop preload="metadata" aria-label="${sign.name} motion reference video. ${sign.hint}"></video>`
      :`<img src="./media/signspeak-alphabet/${sign.letter}.jpg?v=20261112-signspeak-samples-1" alt="${sign.name} ASL handshape reference. ${sign.hint}" width="200" height="200" loading="lazy" decoding="async">`;
    const badge=video?'Motion reference video':'Handshape reference';
    return `<article class="sign-card"><div class="sign-visual sign-photo${video?' sign-motion':''}">${media}</div><h3>${sign.name}</h3><small>${badge}</small><p>${sign.hint}</p></article>`;
  }).join('');
}
$('#trainingLabel').innerHTML = STATIC_SIGNS.map(sign=>`<option value="${sign.letter}">${sign.name} — ${sign.hint}</option>`).join('');

const faceTracker=createFaceTracker((state,detail)=>{
  $('#faceTrackingStatus').textContent=state;
  $('#trackingFace').textContent=state.toUpperCase();
  $('#faceRetry').hidden=state!=='Unavailable';
  $('#faceTrackingHelp').textContent=detail||(state==='No face'?'Face the camera with your whole face visible and light in front of you.':'Visible facial movements · not a measure of emotion');
},expression=>{
  $('#faceExpression').textContent=expression;
},{preferredDelegate:preferredVisionDelegate()});
$('#faceTrackingToggle').addEventListener('change',event=>faceTracker.setEnabled(event.target.checked));
$('#faceRetry').addEventListener('click',()=>{void prepareFaceTracker();});

let recognitionMode = 'letters';
const cameraDiagnostic={lastCapture:null,times:[],lastRender:0,rawHands:0,usableHands:0};
let letterImageLandmarker=null,letterCamera=null,letterHands=[],letterFrameAt=-Infinity,motionCommittedId=null;
const useLetterWorker=()=>typeof Worker!=='undefined'&&typeof OffscreenCanvas!=='undefined'&&typeof createImageBitmap==='function';
function renderCameraDiagnostic(){
 const times=cameraDiagnostic.times,span=times.length>1?times[times.length-1]-times[0]:0;
 $('#cameraDiagnostics').textContent=JSON.stringify({build:'20261111-architecture-2',recoveryWarning:cameraDiagnostic.recoveryWarning||null,letterWorker:letterCamera?.diagnostics()||null,staticCandidate:cameraDiagnostic.staticCandidate||null,letterMoving:cameraDiagnostic.letterMoving||false,trackerState:cameraDiagnostic.trackerState||'idle',trackerError:cameraDiagnostic.trackerError||null,delegate:handDelegate,processingLagMs:Math.round(temporalLagMs),input:video.videoWidth+'x'+video.videoHeight,processedFps:span?Math.round((times.length-1)*10000/span)/10:0,rawHands:cameraDiagnostic.rawHands,usableHands:cameraDiagnostic.usableHands,mode:recognitionMode,vocabulary:$('#activeVocabulary').textContent,model:$('#motionModelStatus').textContent,extraWords:$('#expandedWords').checked,serverPreview:$('#researchWordsToggle').checked,automaticWords:$('#automaticWords').checked,faceTracking:$('#faceTrackingToggle').checked,lastCapture:cameraDiagnostic.lastCapture},null,2);
}
$('#copyCameraDiagnostics').addEventListener('click',async()=>{renderCameraDiagnostic();try{await navigator.clipboard.writeText($('#cameraDiagnostics').textContent);notify('Diagnostics copied. Paste them into this chat.');}catch{notify('Select and copy the text in Camera diagnostics.');}});
let handVision,handFiles,handRecovery=null;
let handLandmarker,handMaxHands=1,handDelegate='',temporalCamera=null,temporalHands=[],temporalFrameAt=-Infinity,temporalLagMs=0;
let combinedTracking=false;
let stream;
let running = false;
let cameraStarting = false;
let cameraAttempt = 0;
let animationId;
let message = '';
let candidate = '';
let candidateSince = 0;
let committed = '';
let missingFrames = 0;
let missingSince=null;
let demoTimer;
let sessionStarted = Date.now();
let detectionLog = [];
let serverAvailable = false;
let systemLoadVersion = 0;
let trainingActive = false;
let trainingCaptured = 0;
let lastTrainingCapture = 0;
let trainingLabel = '';
let pendingSamples = [];
let lastVideoTime = -1;
let modelParameters = DEFAULT_PARAMETERS;
let aiSamples = [];
let baseSamples = [];
let baseModelState = 'Loading pretrained letters…';
const HOLD_MS = 850;
const letterConsensus=createLetterConsensus({holdMs:signSpeakSelected?2000:HOLD_MS,letterHoldMs:{I:2000,D:2000}});
const motionLetters=createMultiHandMotionLetters();
let motionLetterReady=false;
let motionLetterHoldUntil=0;

let speechRevision=0;
function sentenceState(state,text){document.dispatchEvent(new CustomEvent('handspeak:sentence-state',{detail:{state,text}}));}
function stopSpeech(){speechRevision++;window.speechSynthesis?.cancel();$('#pipelineVoice').classList.remove('active');sentenceState('stopped','Speech stopped · Your draft is unchanged.');}
function speakText(text){
  if(!('speechSynthesis' in window)){notify('Speech is unavailable in this browser');return;}
  const currentSpeech=++speechRevision;window.speechSynthesis.cancel();
  const utterance=new SpeechSynthesisUtterance(text);
  utterance.rate=Number($('#speechRate')?.value||1);
  $('#pipelineVoice').classList.add('active');sentenceState('speaking','Speaking… Use Stop speech to cancel.');
  utterance.onend=()=>{if(currentSpeech!==speechRevision)return;$('#pipelineVoice').classList.remove('active');sentenceState('complete','Speech complete · Ready for your next sentence.');};
  utterance.onerror=()=>{if(currentSpeech!==speechRevision)return;$('#pipelineVoice').classList.remove('active');sentenceState('error','Speech could not play. Try Speak message or check browser audio.');};
  window.speechSynthesis.speak(utterance);
}

const interpreter=createInterpreter({speak:speakText,getMessage:()=>message,setMessage:text=>{message=text;renderMessage();}});

const researchWords=createResearchWords({onWord:addWord,
 onStatus:(word,detail)=>{setWordCameraResult(word,detail,true);setRecognitionFeedback(detail||word);},
 onChange:enabled=>{motionStudio.cancel();liveResult.hidden=true;if(enabled){openHandsRecognition?.setEnabled(false);setRecognitionMode('words',true);}}
});
const motionStudio=createMotionStudio({
  isRunning:()=>running && recognitionMode==='words',
  onWord:addWord,
  onStatus:(word,detail)=>{setWordCameraResult(word,detail);setRecognitionFeedback(word==='—'?(detail||'Ready — sign once, then pause.'):`${word} — ${detail||'Possible match; verify before adding.'}`);},
  speak:speakText,
  onDiagnostic:data=>{
    const {sequence,...summary}=data;
    document.dispatchEvent(new CustomEvent('handspeak:word-capture-diagnostics',{detail:summary}));
    if(new URLSearchParams(location.search).has('motionAudit'))globalThis.__lastMotionSequence=sequence||null;
    cameraDiagnostic.lastCapture=summary;renderCameraDiagnostic();
  },
  onFinish:()=>interpreter.finish()
});
vocabularyLibrary=createVocabularyLibrary({onWord:addWord,setVocabulary:(model,name)=>{if(model)openHandsRecognition?.setEnabled(false);researchWords.disable();const prior=motionStudio.usesTemporalModel(),accepted=motionStudio.setVocabulary(model,name);if(accepted){temporalCamera?.reset();if((running||cameraStarting)&&prior!==motionStudio.usesTemporalModel())stopCamera();}return accepted;}});
$('#motionTeach').addEventListener('click',()=>researchWords.disable(),true);

openHandsRecognition=createOpenHandsRecognition({startCamera,isRunning:()=>running&&recognitionMode==='words',
 browserModel:motionStudio,
 onWord:(word,source)=>addWord(word,source==='OpenHands'?'openhands':null),
 onStatus:(word,detail)=>{if(word==='No reliable match'){liveResult.hidden=true;setRecognitionFeedback(detail||word);}else{setWordCameraResult(word,detail,false,'OpenHands');setRecognitionFeedback(word+' - review before adding.');}},
 onSelect:enabled=>{if(enabled){if(temporalCamera&&!combinedTracking)stopCamera();researchWords.disable();motionStudio.cancel();setRecognitionMode('words');}else if(running){stopCamera();}}
});
document.addEventListener('handspeak:openhands-progress',event=>{if(recognitionMode==='words'&&openHandsRecognition?.active())setRecognitionFeedback(event.detail.text);});
function setRecognitionMode(mode,keepResearch=false){
  openHandsRecognition?.cancel();
  researchWords.cancel();if(!keepResearch)researchWords.disable();
  if(temporalCamera&&mode!=='words')stopCamera();
  if(letterCamera&&mode!=='letters')stopCamera();
  recognitionMode=mode;missingSince=null;motionCommittedId=null;letterConsensus.reset();motionLetters.reset();motionLetterHoldUntil=0;
  if((handLandmarker||cameraStarting)&&handMaxHands!==(mode==='letters'?1:2)){
    stopCamera();handLandmarker?.close?.();handLandmarker=null;
  }
  $('#wordRecognitionControls').hidden=mode!=='words';
  $('#openhandsWords').hidden=true;
  $('#compactWordControls').hidden=mode!=='words';
  $('#recognitionMode').value=mode;
  $('#captureMode').textContent=recognitionMode==='words'?'WORDS IN MOTION':'LETTERS A–Z';
  $('#pipelineMatch').classList.toggle('active',recognitionMode==='words');
  candidate='';candidateSince=0;committed='';
  if(trainingActive)endTraining();
  motionStudio.cancel();liveResult.hidden=true;
  setRecognitionFeedback(running?'Ready — bring your hand into view.':'Camera off — select Start Signing to begin.');
  $('#captureSamplesButton').disabled=recognitionMode==='words';
  $('#demoButton').disabled=recognitionMode==='words';
  clearInterval(demoTimer);
  $('#cameraHelp').textContent=recognitionMode==='words'?'With Automatic words enabled, sign once and pause briefly. Manual recording is also available.':'Hold static letters steady. Trace J with your pinky or Z with your index, then pause.';
}
$('#recognitionMode').addEventListener('change',event=>setRecognitionMode(event.target.value));
$('#wordCaptureButton').addEventListener('click',async()=>{
  $('#wordCaptureButton').disabled=true;
  try{
    if(!running)await startCamera();
    if(!running)return;
    if(recognitionMode!=='words')setRecognitionMode('words');
    if(openHandsRecognition.active())await openHandsRecognition.record();else if(researchWords.active())researchWords.recognize();else motionStudio.recognize();
  }finally{$('#wordCaptureButton').disabled=motionStudio.isRecording();}
});

function loadAISamples(){
  try{
    const saved=JSON.parse(localStorage.getItem('handspeak-ai-samples-pixel-v3')||'[]');
    return Array.isArray(saved)?saved.filter(item=>validSample(item,STATIC_SIGNS.map(sign=>sign.letter))):[];
  }catch{return []}
}

function classifyAI(){return null;}

async function loadPretrainedModel(){
 baseSamples=[];baseModelState='SignSpeak ONNX LSTM - A-Z (loads when camera starts)';
 renderAIStatus();
 $('#captureSamplesButton').disabled=true;
 $('#trainingHelp').textContent='SignSpeak is pretrained. Personal alphabet training is disabled.';
}

function endTraining(){
  trainingActive=false;pendingSamples=[];
  $('#trainingLabel').disabled=false;
  $('#captureSamplesButton').disabled=false;
  $('#captureSamplesButton').textContent='Capture 30 samples';
}

function captureTrainingSample(points,now){
  if(!trainingActive||now-lastTrainingCapture<150||!isUsableLetterHand(points,video.videoHeight/video.videoWidth))return;
  lastTrainingCapture=now;
  pendingSamples.push({label:trainingLabel,features:letterFeatures(points,video.videoHeight/video.videoWidth)});
  trainingCaptured=pendingSamples.length;
  $('#trainingProgress').style.width=`${trainingCaptured/30*100}%`;
  $('#trainingHelp').textContent=`Captured ${trainingCaptured} of 30 samples. Slowly vary the hand angle.`;
  if(trainingCaptured>=30){
    const updated=aiSamples.concat(pendingSamples);
    try{
      localStorage.setItem('handspeak-ai-samples-pixel-v3',JSON.stringify(updated));
      aiSamples=updated;letterCamera?.setPersonalSamples(aiSamples);
      $('#trainingHelp').textContent='Examples saved. Try the sign with a slightly different hand position.';
      notify(`${trainingLabel} training complete`);
    }catch{
      $('#trainingHelp').textContent='Could not save examples. Free browser storage and try again.';
    }
    endTraining();renderAIStatus();
  }
}

function renderAIStatus(){
  renderSignLibrary();
  const counts=Object.fromEntries(SIGNS.map(sign=>[sign.letter,baseSamples.concat(aiSamples).filter(sample=>sample.label===sign.letter).length]));
  $('#aiModelStatus').textContent=`${baseModelState} · ${aiSamples.length} personal samples${motionLetterReady?' · J/Z motion loaded':''}`;
  $('#sampleCounts').textContent='A-Z recognition uses the pretrained SignSpeak neural network, not personal reference samples.';
}

function notify(text){
  toast.textContent = text;
  toast.classList.add('show');
  clearTimeout(notify.timer);
  notify.timer = setTimeout(() => toast.classList.remove('show'), 2200);
}

function renderMessage(){
  messageText.innerHTML = message ? '' : '<span>Recognized words will appear here…</span>';
  if(message) messageText.textContent = message;
  $('#captureTranscript').textContent=message||'Your words will appear here.';
  $('#pipelineReview').classList.toggle('active',Boolean(message));
  document.dispatchEvent(new CustomEvent('handspeak:draft-changed'));
}

function updateSentence(next){
  if(next===null){notify('Message limit reached (1000 characters)');return false;}
  message=next;renderMessage();return true;
}
function addWord(word,model=null){if(!isWordEnabled(word)&&!(model==='openhands'&&openHandsRecognition?.isAllowed(word))){notify('This word is disabled after testing');return false;}const next=appendWord(message,word);return updateSentence(next===null?null:(next.length<1000?next+' ':next));}
document.querySelectorAll('[data-typed-word]').forEach(button=>button.addEventListener('click',()=>{addWord(button.dataset.typedWord);}));
document.querySelectorAll('[data-punctuation]').forEach(button=>button.addEventListener('click',()=>{updateSentence(finishSentence(message,button.dataset.punctuation));}));
$('#removeWordButton').addEventListener('click',()=>{updateSentence(removeLastWord(message));});

function appendCharacter(char){
  if(message.length>=1000){notify('Message limit reached (1000 characters)');return;}
  message += char;
  renderMessage();
}

function setRecognitionFeedback(text){
  const node=$('#recognitionFeedback');
  if(node && node.textContent!==text)node.textContent=text;
}
function setLive(letter,confidence=null){
  vocabularyLibrary?.showCameraAccuracy(null);
  liveResult.hidden = false;
  liveLetter.textContent = letter || 'No reliable match';
  const hasConfidence=Boolean(letter)&&Number.isFinite(confidence)&&confidence>=0&&confidence<=1;
  liveConfidence.textContent=hasConfidence?`${(confidence*100).toFixed(1)}% model confidence`:letter?'Confidence unavailable':'No reliable match';
  liveConfidence.title='Model confidence is not independently measured recognition accuracy.';
  setRecognitionFeedback(letter&&committed===letter?`${letter} — recognized. Verify the draft before speaking.`:letter?`Hand detected · ${letter} — possible match. Hold steady.`:'Hand detected · No reliable match. Try a supported sign.');
}

async function prepareFaceTracker(){
  try{
    const vision=await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/+esm');
    const files=await vision.FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/wasm');
    await faceTracker.load(vision,files);
  }catch{ $('#faceTrackingStatus').textContent='Unavailable';$('#faceRetry').hidden=false; }
}
function createHandRecognizer(delegate,runningMode='VIDEO'){
  const confidence=.5;
  return handVision.HandLandmarker.createFromOptions(handFiles,{
    baseOptions:{modelAssetPath:'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',delegate},
    runningMode,numHands:recognitionMode==='letters'?1:2,minHandDetectionConfidence:confidence,minHandPresenceConfidence:confidence,minTrackingConfidence:confidence
  });
}
function handTrackerFailed(error){
  console.warn('Hand tracking stopped',error);
  try{handLandmarker?.close?.();}catch{}
  handLandmarker=null;letterImageLandmarker?.close?.();letterImageLandmarker=null;motionStudio.cancel();researchWords.cancel();
  cameraDiagnostic.trackerError=String(error?.message||error).slice(0,500);
  const failed=()=>{cameraDiagnostic.trackerState='failed';$('#cameraHelp').textContent='Hand tracking stopped. Stop and restart the camera to retry. Open Camera diagnostics for the error.';renderCameraDiagnostic();};
  if(handDelegate!=='GPU'||!handVision||handRecovery){failed();return;}
  const attempt=cameraAttempt;
  cameraDiagnostic.trackerState='recovering';
  $('#cameraHelp').textContent='Hand tracking is switching to CPU compatibility mode…';renderCameraDiagnostic();
  const recovery=createHandRecognizer('CPU').then(async model=>{
    if(attempt!==cameraAttempt||!running){model.close?.();return;}
    let independent=null;
    try{if(recognitionMode==='letters')independent=await createHandRecognizer('CPU','IMAGE');}catch(error){model.close?.();throw error;}
    if(attempt!==cameraAttempt||!running){model.close?.();independent?.close?.();return;}
    handLandmarker=model;letterImageLandmarker=independent;handDelegate='CPU';cameraDiagnostic.trackerState='ready';lastVideoTime=-1;
    $('#cameraHelp').textContent='Hand tracking restored in CPU compatibility mode. Bring your full hand into view, sign once, then pause.';renderCameraDiagnostic();
  }).catch(fallbackError=>{if(attempt===cameraAttempt&&running){cameraDiagnostic.trackerError=String(fallbackError?.message||fallbackError).slice(0,500);failed();}}).finally(()=>{if(handRecovery===recovery)handRecovery=null;});
  handRecovery=recovery;
}
async function loadRecognizer(){
  const targetHands=recognitionMode==='letters'?1:2;
  if(handLandmarker&&handMaxHands===targetHands){if(recognitionMode==='letters'&&!letterImageLandmarker)letterImageLandmarker=await createHandRecognizer(handDelegate,'IMAGE');void faceTracker.load();return;}
  if(handLandmarker){handLandmarker.close?.();handLandmarker=null;}
  letterImageLandmarker?.close?.();letterImageLandmarker=null;
  handMaxHands=targetHands;
  cameraButton.disabled=true;cameraButton.textContent='Loading recognizer…';cameraDiagnostic.trackerState='loading';cameraDiagnostic.trackerError=null;
  try{
    handVision=await import('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/+esm');
    handFiles=await handVision.FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.22-rc.20250304/wasm');
    handDelegate=preferredVisionDelegate();
    try{handLandmarker=await createHandRecognizer(handDelegate);}
    catch(error){if(handDelegate==='CPU')throw error;handDelegate='CPU';handLandmarker=await createHandRecognizer(handDelegate);}
    if(recognitionMode==='letters'){letterImageLandmarker?.close?.();letterImageLandmarker=await createHandRecognizer(handDelegate,'IMAGE');}
    handMaxHands=targetHands;cameraDiagnostic.trackerState='ready';void faceTracker.load(handVision,handFiles);
  }catch(error){
    console.error(error);cameraDiagnostic.trackerState='failed';cameraDiagnostic.trackerError=String(error?.message||error).slice(0,500);
    throw new Error('The recognition model could not be loaded. Check your internet connection.');
  }finally{
    cameraButton.disabled=cameraStarting;cameraButton.innerHTML=cameraStarting?'Waiting for camera…':'<span aria-hidden="true">◉</span> Start camera';
  }
}

async function startCamera(){
  if(cameraStarting||running)return;
  setRecognitionFeedback('Starting camera… allow camera access when prompted.');
  cameraStarting=true;cameraButton.disabled=true;const attempt=++cameraAttempt;
  clearInterval(demoTimer);
  try{
    if(recognitionMode==='words')await loadVocabularySettings();if(attempt!==cameraAttempt)return;
    if(!navigator.mediaDevices?.getUserMedia) throw new Error('Camera access is not supported by this browser.');
    if(recognitionMode==='letters'&&signSpeakSelected&&!useLetterWorker())throw Error('SignSpeak requires camera worker support in this browser.');
    if(recognitionMode==='words'&&openHandsRecognition.active()){
      setRecognitionFeedback('Preparing word models and hand tracking...');
      if($('#wordHandStatus'))$('#wordHandStatus').textContent='Preparing hand tracking...';
      await motionStudio.ready;
      handLandmarker?.close?.();handLandmarker=null;
      combinedTracking=true;let readyFrames=0,settling=true;
      temporalCamera=createTemporalCamera({latestOnly:true,
        onDetection:(data,lag)=>{if(!running)return;handDelegate=temporalCamera?.getDelegate?.()||handDelegate;temporalLagMs=lag;temporalHands=(data.landmarks||[]).filter(validTrackedHand);temporalFrameAt=performance.now();reportWordHands(data,lag);readyFrames=lag<500&&(data.landmarks||[]).some(fullHandInFrame)?readyFrames+1:0;if(settling&&readyFrames>=3){settling=false;if(!openHandsRecognition.isBusy())setRecognitionFeedback('Automatic words ready. Sign once, then hold the final pose still briefly.');}consumeDetection(data,data.timestamp,data.imageAspect);},
        onGap:()=>{readyFrames=0;settling=true;openHandsRecognition.cancel();temporalHands=[];setRecognitionFeedback('Hold your hands in view briefly while tracking gets ready. Then sign once and hold the final pose.');},
        onError:message=>{cameraDiagnostic.trackerState='failed';cameraDiagnostic.trackerError=message;if(running){stopCamera();notify(message);}}
      });
      handDelegate=await temporalCamera.ready;cameraDiagnostic.trackerState='ready';
    }else if(recognitionMode==='letters'&&useLetterWorker()){
      letterCamera=createLetterCamera({personalSamples:aiSamples,
        onDetection:(data,lag)=>{if(!running)return;temporalLagMs=lag;letterHands=(data.landmarks||[]).filter(p=>isUsableLetterHand(p,data.imageAspect));letterFrameAt=performance.now();consumeDetection(data,data.timestamp,data.imageAspect);},
        onWarning:message=>{cameraDiagnostic.recoveryWarning=message;},
        onError:async message=>{
          if(!running||!letterCamera)return;const attempt=cameraAttempt;letterCamera.close();letterCamera=null;letterHands=[];
          cameraDiagnostic.recoveryWarning=message;
          if(signSpeakSelected){stopCamera();notify('SignSpeak failed: '+message);return;}
          try{await loadRecognizer();if(attempt===cameraAttempt&&running)setRecognitionFeedback('Compatibility detector restored — bring your hand into view.');}
          catch(error){if(attempt===cameraAttempt&&running){stopCamera();notify(error.message);}}
        }
      });
      try{const status=await letterCamera.ready;handDelegate=status.delegate;cameraDiagnostic.trackerState='ready';void prepareFaceTracker();}
      catch(error){letterCamera?.close();letterCamera=null;cameraDiagnostic.recoveryWarning=error.message;if(signSpeakSelected)throw error;await loadRecognizer();}
    }else if(recognitionMode==='words'&&motionStudio.usesTemporalModel()){ 
      temporalCamera=createTemporalCamera({
        onDetection:(data,lag)=>{if(!running)return;handDelegate=temporalCamera?.getDelegate?.()||handDelegate;temporalLagMs=lag;temporalHands=(data.landmarks||[]).filter(isUsableHand);temporalFrameAt=data.timestamp;consumeDetection(data,data.timestamp,data.imageAspect);},
        onGap:()=>{motionStudio.cancel();motionLetters.reset();motionLetterHoldUntil=0;temporalHands=[];setRecognitionFeedback('Camera timing changed or processing fell behind. Pause, then sign again.');},
        onError:message=>{cameraDiagnostic.trackerState='failed';cameraDiagnostic.trackerError=String(message).slice(0,500);if(running){stopCamera();$('#cameraHelp').textContent=message;renderCameraDiagnostic();notify(message);}}
      });
      handDelegate=await temporalCamera.ready;cameraDiagnostic.trackerState='ready';cameraDiagnostic.trackerError=null;void prepareFaceTracker();
    }else await loadRecognizer();
    if(attempt!==cameraAttempt)return;
    const devices=await navigator.mediaDevices.enumerateDevices();
    if(!devices.some(device=>device.kind==='videoinput'))throw new Error('No camera is available. Connect a webcam and retry.');
    const pendingStream=navigator.mediaDevices.getUserMedia({video:{facingMode:'user',width:{ideal:960},height:{ideal:720}},audio:false});
    let cameraTimer;
    let cameraTimedOut=false;
    // A permission/device request can remain pending indefinitely. Late streams
    // are stopped, never attached to a cancelled/newer camera attempt.
    pendingStream.then(late=>{if(cameraTimedOut||attempt!==cameraAttempt)late.getTracks().forEach(t=>t.stop());},()=>{});
    let acquired;
    try{acquired=await Promise.race([pendingStream,new Promise((_,reject)=>{cameraTimer=setTimeout(()=>{cameraTimedOut=true;reject(new Error('Camera startup timed out. Check the browser permission prompt and camera connection.'));},20000);})]);}
    finally{clearTimeout(cameraTimer);}
    if(attempt!==cameraAttempt){acquired.getTracks().forEach(t=>t.stop());return;}
    stream=acquired;
    video.muted=true;video.playsInline=true;video.srcObject = stream;
    await video.play();
    if(attempt!==cameraAttempt){acquired.getTracks().forEach(t=>t.stop());return;}
    running = true;
    $('#trackingState').textContent='LIVE';$('#captureFeed').textContent='LIVE';
    $('#pipelineTrack').classList.add('active');
    placeholder.hidden = true;
    cameraStatus.classList.add('live');
    cameraStatus.innerHTML = '<i></i> Live';
    cameraButton.innerHTML = '<span aria-hidden="true">■</span> Stop camera';
    $('#cameraHelp').textContent = recognitionMode==='words'?'With Automatic words enabled, sign once and pause briefly. Manual recording is also available.':'Hold a supported sign steady until it is added.';
    setRecognitionFeedback(recognitionMode==='words'&&openHandsRecognition.active()?'Hold your hands still in view until tracking is ready. Then sign once and hold the final pose briefly. Review the prediction before adding it.':'Camera ready - bring your hand into view.');
    detect();
  }catch(error){
    if(attempt!==cameraAttempt)return;
    stopCamera();
    setRecognitionFeedback('Camera unavailable — check permission and try again.');
    notify(error.message || 'Camera permission was not granted.');
    cameraDiagnostic.trackerError=String(error.name||'CameraError')+': '+String(error.message||'Camera failed');
    cameraDiagnostic.trackerState='failed';renderCameraDiagnostic();
    $('#cameraHelp').textContent = 'Camera unavailable. Check camera permission and close other camera apps, or use the demonstration videos.';
  }finally{if(attempt===cameraAttempt){cameraStarting=false;cameraButton.disabled=false;}}
}

function stopCamera(){
  openHandsRecognition?.cancel();
  letterCamera?.close();letterCamera=null;letterHands=[];missingSince=null;motionCommittedId=null;
  letterConsensus.reset();
  motionLetters.reset();motionLetterHoldUntil=0;
  temporalCamera?.close();temporalCamera=null;combinedTracking=false;temporalHands=[];temporalLagMs=0;
  researchWords.cancel();
  setRecognitionFeedback('Camera off — select Start Signing to begin.');
  cameraAttempt++;
  cameraStarting=false;
  cameraButton.disabled=false;
  running = false;
  interpreterHandAbsentSince=null;
  faceTracker.reset();
  $('#trackingState').textContent='STANDBY';$('#trackingHands').textContent='0 / 2';if($('#wordHandStatus'))$('#wordHandStatus').textContent='Camera off.';$('#captureFeed').textContent='OFFLINE';
  $('#pipelineTrack').classList.remove('active');
  motionStudio.cancel();
  candidate='';candidateSince=0;committed='';lastVideoTime=-1;
  if(trainingActive){endTraining();$('#trainingHelp').textContent='Capture stopped. Start the camera to try again.';}
  cancelAnimationFrame(animationId);
  stream?.getTracks().forEach(track => track.stop());
  stream = null;
  video.srcObject = null;
  ctx.clearRect(0,0,canvas.width,canvas.height);
  placeholder.hidden = false;
  liveResult.hidden = true;
  cameraStatus.classList.remove('live');
  cameraStatus.innerHTML = '<i></i> Camera off';
  cameraButton.innerHTML = '<span aria-hidden="true">◉</span> Start camera';
}

function drawHand(points){
  const links=[[0,1],[1,2],[2,3],[3,4],[0,5],[5,6],[6,7],[7,8],[5,9],[9,10],[10,11],[11,12],[9,13],[13,14],[14,15],[15,16],[13,17],[17,18],[18,19],[19,20],[0,17]];
  ctx.strokeStyle='#7fe0ca';ctx.lineWidth=3;ctx.lineCap='round';
  links.forEach(([a,b])=>{ctx.beginPath();ctx.moveTo(points[a].x*canvas.width,points[a].y*canvas.height);ctx.lineTo(points[b].x*canvas.width,points[b].y*canvas.height);ctx.stroke()});
  ctx.fillStyle='#fff';points.forEach(p=>{ctx.beginPath();ctx.arc(p.x*canvas.width,p.y*canvas.height,4,0,Math.PI*2);ctx.fill()});
}

function stabilize(result, now){
  const stable=letterConsensus.push(result,now);
  if(stable&&committed!==stable.letter){
    appendCharacter(stable.letter);
    detectionLog.push({symbol:stable.letter,confidence:stable.confidence,latencyMs:Math.round(stable.latencyMs)});
    document.dispatchEvent(new CustomEvent('handspeak:letter-committed',{detail:{letter:stable.letter,kind:'static',timestamp:now,latencyMs:stable.latencyMs,observations:stable.evidenceFrames}}));
    committed=stable.letter;notify(`${stable.letter} added`);
  }
}

function detect(){
  if(!running) return;
  if(video.readyState>=2 && video.currentTime!==lastVideoTime){
    lastVideoTime=video.currentTime;
    canvas.width=video.videoWidth;canvas.height=video.videoHeight;
    const now=performance.now();
    let detection={landmarks:[]};
    const auditStages=!letterCamera&&recognitionMode==='letters'&&typeof URLSearchParams!=='undefined'
      &&new URLSearchParams(location.search).has('letterAudit')?{}:null;
    if(handLandmarker&&!temporalCamera&&!letterCamera){
      try{
        detection=handLandmarker.detectForVideo(video,now);
        if(auditStages)auditStages.videoMs=performance.now()-now;
        if(recognitionMode==='letters'&&letterImageLandmarker){
          const tracked=detection;
          const imageStarted=auditStages?performance.now():0;
          detection=letterImageLandmarker.detect(video);
          if(auditStages)auditStages.primaryMs=performance.now()-imageStarted;
          detection.trackedLandmarks=tracked.landmarks;
        }
      }
      catch(error){
        handTrackerFailed(error);
      }
    }
    ctx.clearRect(0,0,canvas.width,canvas.height);
    faceTracker.draw(video,now,ctx,canvas.width,canvas.height,motionStudio.isCapturing()||researchWords.isCapturing()||Boolean(recognitionMode==='words'&&openHandsRecognition?.active()),letterCamera?250:100);
    if(letterCamera){letterCamera.push(video);if(now-letterFrameAt<400)letterHands.forEach(drawHand);}
    else if(temporalCamera){
      temporalCamera.push(video,now,motionStudio.isCapturing()||Boolean(combinedTracking&&openHandsRecognition?.isBusy()));
      if(now-temporalFrameAt<(combinedTracking?600:200))temporalHands.forEach(drawHand);
    }else if(handLandmarker){
      if(auditStages){detection.auditStages=auditStages;detection.timings=auditStages;}
      consumeDetection(detection,now,video.videoHeight/video.videoWidth);
      if(auditStages)auditStages.frameToUiMs=performance.now()-now;
    }
    else setRecognitionFeedback(cameraDiagnostic.trackerState==='recovering'?'Restoring hand tracking in CPU compatibility mode…':'Hand tracking unavailable — stop and restart the camera.');
  }
  animationId=requestAnimationFrame(detect);
}

function consumeDetection(detection,now,imageAspect){
    const hands=(detection.landmarks||[]).filter(p=>recognitionMode==='letters'?isUsableLetterHand(p,imageAspect):isUsableHand(p));
    if(recognitionMode==='letters'){if(hands.length)interpreterHandAbsentSince=null;else if(interpreterHandAbsentSince===null)interpreterHandAbsentSince=performance.now();}
    const processedAt=performance.now();cameraDiagnostic.times.push(processedAt);cameraDiagnostic.times=cameraDiagnostic.times.filter(t=>processedAt-t<=2000);cameraDiagnostic.rawHands=(detection.landmarks||[]).length;cameraDiagnostic.usableHands=hands.length;
    if(processedAt-cameraDiagnostic.lastRender>=1000){cameraDiagnostic.lastRender=processedAt;renderCameraDiagnostic();}
    if(!temporalCamera&&!letterCamera)hands.forEach(drawHand);
    $('#trackingHands').textContent=`${hands.length} / 2`;
    // OpenHands uses server video inference; browser landmarks feed the shared combined capture.
    // Do not feed them into an unrelated legacy word recognizer.
    if(recognitionMode==='words'&&openHandsRecognition.active()){const indices=(detection.landmarks||[]).map((p,i)=>isUsableHand(p)?i:-1).filter(i=>i>=0);
      motionStudio.frameCombined({landmarks:indices.map(i=>detection.landmarks[i]),handedness:indices.map(i=>detection.handedness?.[i]),imageAspect},now);
      openHandsRecognition.frame(detection.landmarks||[],now);return;}
    const motionHands=(detection.motionHands||detection.trackedLandmarks||detection.landmarks||[]).filter(p=>isUsableLetterHand(p,imageAspect));
    const auditStages=detection.auditStages;
    const motionStarted=auditStages?performance.now():0;
    const temporal=recognitionMode==='letters'&&!trainingActive&&!signSpeakSelected?motionLetters.frame(motionHands,now,1/(imageAspect||1),Boolean(letterCamera&&detection.stableMotionGate)):{moving:false,result:null,presentIds:[]};
    if(auditStages)auditStages.motionMs=performance.now()-motionStarted;
    cameraDiagnostic.staticCandidate=detection.staticResult?.letter||null;cameraDiagnostic.letterMoving=Boolean(temporal.moving);
    if(recognitionMode==='letters'&&typeof URLSearchParams!=='undefined'&&new URLSearchParams(location.search).has('letterAudit'))document.dispatchEvent(new CustomEvent('handspeak:letter-frame',{detail:{detection,temporal,timestamp:now}}));
    if(temporal.result){
      const result=temporal.result;letterConsensus.reset();candidate='';candidateSince=0;committed=result.letter;motionCommittedId=result.handId;
      appendCharacter(result.letter);detectionLog.push({symbol:result.letter,confidence:result.confidence,latencyMs:result.latencyMs});
      document.dispatchEvent(new CustomEvent('handspeak:letter-committed',{detail:{letter:result.letter,kind:'motion',timestamp:now,latencyMs:result.latencyMs,observations:result.observationCount,handId:result.handId}}));
      motionLetterHoldUntil=Infinity;setLive(result.letter);
      setRecognitionFeedback(`${result.letter} — motion recognized. Lower your hand before the next letter; verify the draft before speaking.`);notify(`${result.letter} added`);return;
    }
    if(recognitionMode==='letters'&&!trainingActive&&now<motionLetterHoldUntil&&motionHands.length){
      if(!temporal.presentIds.includes(motionCommittedId)){liveResult.hidden=true;liveLetter.textContent='—';setRecognitionFeedback('Motion letter saved — lower your hands before the next letter.');}
      return;
    }
    if(recognitionMode==='words'){
      if(liveResult.hidden&&!motionStudio.isCapturing()&&!researchWords.active())setRecognitionFeedback(hands.length?($('#automaticWords').checked?'Hand detected — sign once, then pause.':'Hand detected — select Record a word to analyze.'):'No hand detected — bring your hands into view.');
      // Keep original handedness indices when rejecting clipped/small hands.
      const indices=(detection.landmarks||[]).map((p,i)=>isUsableHand(p)?i:-1).filter(i=>i>=0);
      const filtered={landmarks:indices.map(i=>detection.landmarks[i]),handedness:indices.map(i=>detection.handedness?.[i]),imageAspect:imageAspect};
      (researchWords.active()?researchWords:motionStudio).frame(filtered,now);
    }else if(hands.length===1){
      missingFrames=0;missingSince=null;
      const points=hands[0];
      const wasTraining=trainingActive;
      captureTrainingSample(points,now);
      const tracked=(detection.trackedLandmarks||[]).find(p=>sameObservedHand(points,p,imageAspect));
      if(wasTraining)motionLetters.reset();
      const classifierStarted=auditStages?performance.now():0;
      const result=temporal.moving?{letter:'',confidence:0}:(Object.prototype.hasOwnProperty.call(detection,'staticResult')?detection.staticResult:(classifyAI(points,imageAspect)||(tracked?classifyAI(tracked,imageAspect):null)))||{letter:'',confidence:0};
      if(auditStages)auditStages.classifierMs=performance.now()-classifierStarted;
      const uiStarted=auditStages?performance.now():0;
      setLive(result.letter,result.confidence);
      if(!wasTraining)stabilize(result,now);
      else {letterConsensus.reset();candidate='';candidateSince=0;}
      if(wasTraining)setRecognitionFeedback('Hand detected — collecting personal training examples.');
      else if(committed===result.letter && result.letter)setRecognitionFeedback(`${result.letter} — recognized. Verify the draft before speaking.`);
      if(auditStages)auditStages.staticUiMs=performance.now()-uiStarted;
    }else{
      if(!motionHands.length){motionLetters.reset();motionLetterHoldUntil=0;motionCommittedId=null;}letterConsensus.reset();
      liveResult.hidden=true;liveLetter.textContent='—';liveConfidence.textContent='';
      setRecognitionFeedback(hands.length?'Use one hand for letters.':'No hand detected — bring your hand into view.');
      candidate='';candidateSince=0;
      missingFrames++;if(missingSince===null)missingSince=now;if(now-missingSince>=500)committed='';
      if(hands.length>1)$('#cameraHelp').textContent='Use one hand for letters, or switch to Words in motion.';
    }
}

$('#pipelineVoice').addEventListener('click',()=>{if(message)speakText(message);else notify('Add a message first');});

$('#startSigning').addEventListener('click',()=>{$('#workspace').scrollIntoView({behavior:'smooth'});void startCamera();});
cameraButton.addEventListener('click',()=>running?stopCamera():startCamera());
$('#clearButton').addEventListener('click',()=>{clearInterval(demoTimer);message='';detectionLog=[];sessionStarted=Date.now();renderMessage();notify('Message cleared')});
function commitInterpreterWord(){
 const next=commitCurrentWord(message);
 if(next===message)return;
 if(updateSentence(next)){letterConsensus.reset();candidate='';candidateSince=0;notify('Word added to log');}
}
$('#spaceButton').addEventListener('click',commitInterpreterWord);
let interpreterHandAbsentSince=null;
setInterval(()=>{
 if(!running||recognitionMode!=='letters'||trainingActive||interpreterHandAbsentSince===null)return;
 if(performance.now()-interpreterHandAbsentSince>=2500)commitInterpreterWord();
},250);

$('#interpreterAdd').addEventListener('click',()=>{
 if(recognitionMode==='words'&&openHandsRecognition.active()&&!$('#openhandsAccept').disabled){$('#openhandsAccept').click();return;}
 const letter=liveLetter.textContent.trim();
 if(!running||recognitionMode!=='letters'||liveResult.hidden||!/^[A-Z]$/.test(letter))return;
 appendCharacter(letter);committed=letter;letterConsensus.reset();candidate='';candidateSince=0;
 notify(letter+' added manually ? review your draft');
});
$('#backspaceButton').addEventListener('click',()=>{message=message.slice(0,-1);renderMessage()});
$('#copyButton').addEventListener('click',async()=>{if(!message)return notify('There is no message to copy');try{await navigator.clipboard.writeText(message);notify('Message copied')}catch{notify('Copy is unavailable in this browser')}});
$('#speakButton').addEventListener('click',()=>{if(!message)return notify('Add a message first');speakText(message)});
$('#contrastButton').addEventListener('click',()=>{const enabled=document.body.classList.toggle('high-contrast');$('#contrastButton').setAttribute('aria-pressed',String(enabled));try{localStorage.setItem('handspeak-contrast',enabled)}catch{}});
try{if(localStorage.getItem('handspeak-contrast')==='true'){document.body.classList.add('high-contrast');$('#contrastButton').setAttribute('aria-pressed','true');}}catch{}

$('#demoButton').addEventListener('click',()=>{
  if(running) stopCamera();
  clearInterval(demoTimer);
  const demo=['I','L','Y'];let index=0;
  placeholder.hidden=true;liveResult.hidden=false;cameraStatus.classList.add('live');cameraStatus.innerHTML='<i></i> Demo';
  $('#captureFeed').textContent='DEMO';$('#trackingState').textContent='DEMO';
  const tick=()=>{if(index>=demo.length){clearInterval(demoTimer);notify('Demo complete');return}const letter=demo[index++];setLive(letter);liveConfidence.textContent='Simulated example · not camera recognition';setRecognitionFeedback('Demo — simulated letters, not camera recognition.');appendCharacter(letter)};
  tick();demoTimer=setInterval(tick,700);
});

window.addEventListener('beforeunload',stopCamera);

async function api(path, options){
  const response = await fetch(path, options);
  const data = await response.json();
  if(!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}

async function saveSession(){
  if(!message.trim()) return notify('There is no message to save');
  $('#saveButton').disabled=true;
  try{
    await api('/api/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,detections:detectionLog,durationMs:Date.now()-sessionStarted})});
    notify('Translation saved');
    detectionLog=[];sessionStarted=Date.now();
    await loadSystemData();
  }catch(error){notify(error.message||'Saving is temporarily unavailable. Your message is still here.')}finally{$('#saveButton').disabled=false;}
}

function renderHistory(sessions){
  const list=$('#historyList');list.innerHTML='';
  if(!sessions.length){list.innerHTML='<p class="empty-state">No saved sessions yet.</p>';return}
  sessions.forEach(session=>{
    const item=document.createElement('article');item.className='history-item';
    const text=document.createElement('strong');text.textContent=session.message;
    const date=document.createElement('time');date.dateTime=session.created_at;date.textContent=new Date(session.created_at).toLocaleString();
    const meta=document.createElement('small');meta.textContent=`${session.character_count} characters · ${(session.duration_ms/1000).toFixed(1)} seconds`;
    const actions=document.createElement('div');actions.className='history-buttons';
    const restore=document.createElement('button');restore.type='button';restore.className='text-button';restore.textContent='Use message';restore.onclick=()=>{message=session.message;detectionLog=[];sessionStarted=Date.now();renderMessage();document.dispatchEvent(new CustomEvent('handspeak:navigate',{detail:{target:'#messageBox'}}));$('#messageBox').scrollIntoView({block:'center'});notify('Message loaded for review');};
    const remove=document.createElement('button');remove.type='button';remove.className='text-button';remove.textContent='Delete';remove.setAttribute('aria-label','Delete saved message');remove.onclick=async()=>{remove.disabled=true;try{await api('/api/sessions/'+session.id,{method:'DELETE'});await loadSystemData();notify('Saved message deleted');}catch(e){remove.disabled=false;notify(e.message);}};
    actions.append(restore,remove);item.append(text,date,meta,actions);list.append(item);
  });
}

function renderMetrics(metrics){
  $('#metricSessions').textContent=metrics.sessions;
  $('#metricDetections').textContent=metrics.detections;
  $('#metricConfidence').textContent=`${Math.round(metrics.averageConfidence*100)}%`;
  $('#metricLatency').textContent=`${metrics.averageLatencyMs} ms`;
  $('#evaluationCount').textContent=metrics.evaluations;
  const hasRatings=metrics.evaluations>0;
  $('#ratingAccuracy').textContent=hasRatings?`${metrics.ratings.accuracy}/5`:'—';
  $('#ratingUsability').textContent=hasRatings?`${metrics.ratings.usability}/5`:'—';
  $('#ratingPerformance').textContent=hasRatings?`${metrics.ratings.performance}/5`:'—';
}

async function loadSystemData(){
  const version=++systemLoadVersion;
  try{
    const health=await api('/api/health');
    const [sessions,metrics,gestures]=await Promise.all([api('/api/sessions?limit=20'),api('/api/metrics'),api('/api/gestures')]);
    if(version!==systemLoadVersion)return;
    serverAvailable=health.status==='ok';renderHistory(sessions.sessions);renderMetrics(metrics);$('#systemStatus').textContent='Connected · Showing your latest 20 saved messages';
    if(gestures.gestures.length!==SIGNS.length) console.warn('Gesture database and client classifier differ.');
  }catch{if(version!==systemLoadVersion)return;serverAvailable=false;$('#systemStatus').textContent='Saved messages are unavailable. Your current message is still on this page. Try Refresh.';}
}

$('#saveButton').addEventListener('click',saveSession);
$('#refreshHistory').addEventListener('click',async()=>{await loadSystemData();notify(serverAvailable?'History refreshed':'Server is unavailable')});
['accuracy','usability','performance'].forEach(name=>{$(`#${name}`).addEventListener('input',event=>$(`#${name}Value`).textContent=event.target.value)});
$('#evaluationForm').addEventListener('submit',async event=>{
  event.preventDefault();
  const formElement=event.currentTarget;const submit=formElement.querySelector('button[type=submit]');submit.disabled=true;
  const form=new FormData(formElement);
  const payload=Object.fromEntries(form.entries());
  try{
    await api('/api/evaluations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    formElement.reset();['accuracy','usability','performance'].forEach(name=>$(`#${name}Value`).textContent='5');
    notify('Thank you—evaluation submitted');await loadSystemData();
  }catch(error){notify(error.message||'Feedback could not be submitted. Please try again.')}finally{submit.disabled=false;}
});

window.addEventListener('handspeak-auth-changed',()=>{renderHistory([]);$('#systemStatus').textContent='Loading your saved messages…';void loadSystemData();});
$('#editMessageButton').addEventListener('click',()=>{$('#messageEditForm').hidden=false;$('#messageEditor').value=message;$('#messageEditor').focus();});
$('#cancelMessageEdit').addEventListener('click',()=>{$('#messageEditForm').hidden=true;$('#editMessageButton').focus();});
$('#messageEditForm').addEventListener('submit',event=>{event.preventDefault();message=$('#messageEditor').value.slice(0,1000);renderMessage();$('#messageEditForm').hidden=true;$('#editMessageButton').focus();notify('Message updated');});
loadSystemData();
renderAIStatus();
loadPretrainedModel();

$('#captureSamplesButton').addEventListener('click',()=>{
  return notify('Personal alphabet training is disabled for SignSpeak');

  if(!running)return notify('Start the camera before training');
  if(recognitionMode!=='letters')return notify('Switch to Static letters to capture letter samples');
  trainingActive=true;trainingCaptured=0;lastTrainingCapture=0;
  trainingLabel=$('#trainingLabel').value;pendingSamples=[];
  $('#trainingLabel').disabled=true;
  candidate='';candidateSince=0;
  $('#trainingProgress').style.width='0';
  $('#captureSamplesButton').disabled=true;$('#captureSamplesButton').textContent='Capturing…';
  $('#trainingHelp').textContent='Hold the selected gesture steady and slowly vary its angle.';
});

$('#resetModelButton').addEventListener('click',()=>{
  aiSamples=[];letterCamera?.setPersonalSamples(aiSamples);endTraining();localStorage.removeItem('handspeak-ai-samples-pixel-v3');
  $('#trainingProgress').style.width='0';$('#captureSamplesButton').disabled=true;$('#captureSamplesButton').textContent='Personal training disabled';
  $('#trainingHelp').textContent='Personal examples cleared. Pretrained letters remain available.';
  renderAIStatus();notify('Personalized AI model reset');
});

$('#mirrorPreview').addEventListener('change',()=>{const transform=$('#mirrorPreview').checked?'scaleX(-1)':'none';video.style.transform=transform;canvas.style.transform=transform;notify('Preview orientation changed. Recognition uses the original camera input.');});

createExperienceUI({getMessage:()=>message,setMessage:text=>{message=text;renderMessage();},stopSpeech});

document.documentElement.dataset.handspeakReady='true';

installFakeCameraTest({startCamera,isRunning:()=>running,setRecognitionMode});
