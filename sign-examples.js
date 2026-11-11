import {loadVocabularySettings,wordSettings,applyVocabularySettings} from './vocabulary-settings.js?v=20261011-features-1';
import {loadAccuracyProfiles,referenceAccuracy,publishedAccuracy,accuracyText,validAccuracy} from './motion-accuracy.js?v=20261021-baby-1';
import {createSignAvatar} from './sign-avatar.js?v=20261109-kai-match-1';
import {hasSignAnimation} from './sign-animations.js?v=20261105-reference-3';

const canvas = document.querySelector('#signAvatarCanvas');
const status = document.querySelector('#signExampleStatus');
const speed = document.querySelector('#signExampleSpeed');
const video = document.querySelector('#signExampleVideo');
const videoPanel = document.querySelector('.example-video-panel');
const buttons = [...document.querySelectorAll('[data-sign-example]')];
for(const button of buttons)button.dataset.signLabel=button.textContent;
const lesson=document.querySelector('#signExampleLesson');
const playback=document.querySelector('.example-playback');
const daily=new Set(['name','home','have','want','love']);
const extra=new Set(['drink','water','book','food','hungry','like','go']);
const VIDEO_BASE = './media/signs/';
const lifeprintLessons={
  name:'https://www.lifeprint.com/asl101/pages-signs/n/name.htm',
  want:'https://www.lifeprint.com/asl101/pages-signs/w/want.htm',
  love:'https://www.lifeprint.com/asl101/pages-signs/l/love.htm',
  baby:'https://www.lifeprint.com/asl101/pages-signs/b/baby.htm',
  hello:'https://www.lifeprint.com/asl101/pages-signs/h/hello.htm',
  please:'https://www.lifeprint.com/asl101/pages-signs/p/please.htm',
  yes:'https://www.lifeprint.com/asl101/pages-signs/y/yes.htm',
  no:'https://www.lifeprint.com/asl101/pages-signs/n/no.htm',
};
// The 7 words verified for the 100-word model's core vocabulary.
const coreWords=new Map([['belt','BELT'],['eat','EAT'],['empty','EMPTY'],['peg','PEG'],['soccer','SOCCER'],['squeeze','SQUEEZE'],['vlog','VLOG']]);
const extendedWords=new Map([['lock','LOCK'],['duck','DUCK'],['baseballcap','BASEBALLCAP'],['other','OTHER'],['whatfor','WHATFOR'],['drag','DRAG'],['microscope','MICROSCOPE'],['party','PARTY'],['demand','DEMAND'],['edit','EDIT'],['mechanic','MECHANIC'],['deaf','DEAF']]);
const cameraWords=new Map([...coreWords,...extendedWords]);
const coreLessons={belt:'https://www.signingsavvy.com/search/belt',eat:'https://www.signingsavvy.com/search/eat',empty:'https://www.signingsavvy.com/search/empty',peg:'https://www.signingsavvy.com/search/peg',soccer:'https://www.signingsavvy.com/search/soccer',squeeze:'https://www.signingsavvy.com/search/squeeze',vlog:'https://www.signingsavvy.com/search/vlog',
  lock:'https://www.signingsavvy.com/search/lock',duck:'https://www.signingsavvy.com/search/duck',baseballcap:'https://www.signingsavvy.com/search/baseballcap',other:'https://www.signingsavvy.com/search/other',whatfor:'https://www.signingsavvy.com/search/whatfor',drag:'https://www.signingsavvy.com/search/drag',microscope:'https://www.signingsavvy.com/search/microscope',party:'https://www.signingsavvy.com/search/party',demand:'https://www.signingsavvy.com/search/demand',edit:'https://www.signingsavvy.com/search/edit',mechanic:'https://www.signingsavvy.com/search/mechanic',deaf:'https://www.signingsavvy.com/search/deaf'};
const coreAccuracy={BELT:[13,14],EAT:[10,11],EMPTY:[7,8],PEG:[7,8],SOCCER:[8,8],SQUEEZE:[7,8],VLOG:[9,9],
  LOCK:[9,10],DUCK:[8,9],BASEBALLCAP:[8,9],OTHER:[7,8],WHATFOR:[12,14],DRAG:[11,13],MICROSCOPE:[11,13],PARTY:[9,11],DEMAND:[9,11],EDIT:[9,11],MECHANIC:[12,15],DEAF:[8,10]};
const CORE_SENTINEL='capstone-core';

const BEGINNER_SENTINEL='beginner-ready';
const BEGINNER_VIDEO_VERSION='20261105-beginner-ready-5';
const beginnerWords=new Map();
const beginnerAccuracy={};
let beginnerId=null;
function beginnerLessonQuery(name){
  return encodeURIComponent(String(name).toLowerCase().replaceAll(' / ',' ').replaceAll('/',' '));
}
function chooseBeginnerPractice(id,button=null){
  const name=beginnerWords.get(id);
  if(!name)return;
  beginnerId=id;
  chooseSign(id,button,name);
  libraryId=BEGINNER_SENTINEL;
  document.querySelector('#signExampleMode').textContent=`${name} · Beginner ready camera model (≥70% held-out). Watch the 3D demo / reference, then record one complete sign for four seconds and review the top five before adding the word.`;
}
async function loadBeginnerReadyExamples(){
  try{
    const response=await fetch(`models/beginner-ready-labels.json?v=${BEGINNER_VIDEO_VERSION}`,{cache:'no-store'});
    if(!response.ok)return;
    const data=await response.json();
    const ids=data.ids&&typeof data.ids==='object'?data.ids:{};
    const accuracy=data.accuracy&&typeof data.accuracy==='object'?data.accuracy:{};
    const container=document.querySelector('.example-words');
    const practice=document.querySelector('#practiceWord');
    for(const name of data.labels||[]){
      const id=ids[name]||String(name).toLowerCase().replaceAll(' / ','-').replaceAll('/','-').replaceAll(' ','-');
      beginnerWords.set(id,name);
      const metrics=accuracy[name];
      if(metrics&&Number(metrics.total)>0)beginnerAccuracy[name]=[Number(metrics.correct)||0,Number(metrics.total)||0];
      if(buttons.some(button=>button.dataset.signExample===id))continue;
      const button=document.createElement('button');button.type='button';button.className='secondary-button';
      button.dataset.signExample=id;button.dataset.signLabel=name;button.setAttribute('aria-pressed','false');button.textContent=name;
      button.addEventListener('click',()=>chooseBeginnerPractice(id,button));
      buttons.push(button);container.append(button);
      if(practice&&![...practice.options].some(option=>option.value===id))practice.add(new Option(name,id));
    }
    updateAccuracy();
  }catch{ /* Beginner ready examples remain optional when the metadata file is missing. */ }
}

let coreId=null;
const publishedExamples=new Map();
let accuracyProfiles={},publishedPacks=[];
let label = 'HELLO';
let selection = 0;
let libraryId=null;
let avatar=null;
let avatarFailed=false;

function exampleAccuracy(name){
  const pack=publishedPacks.find(pack=>pack.labels?.includes(name));
  return pack?publishedAccuracy(pack,name):referenceAccuracy(accuracyProfiles,name);
}
function updateAccuracy(){
  const beginner=beginnerAccuracy[label];
  const core=coreAccuracy[label];
  const tier=coreWords.has(coreId)||[...coreWords.values()].includes(label)?'Core 7-word':(core?'Extended 19-word':null);
  const metrics=core?null:exampleAccuracy(label),target=document.querySelector('#signExampleAccuracy');
  target.textContent=beginner
    ?`Beginner ready ST-GCN · ${beginner[0]}/${beginner[1]} correct on the held-out test split (${(100*beginner[0]/beginner[1]).toFixed(1).replace(/\.0$/,'')}%). Live-camera accuracy is unverified.`
    :core
    ?`${tier} ST-GCN · ${core[0]}/${core[1]} correct on the held-out test split (${(100*core[0]/core[1]).toFixed(1).replace(/\.0$/,'')}%). Live-camera accuracy is unverified.`
    :`${accuracyText(metrics)}${metrics?` · ${metrics.model}. ${metrics.scope}`:'. No measured test result is available for this word.'}`;
  for(const button of buttons){
    const name=button.dataset.signLabel||button.textContent;
    const core=coreAccuracy[name];
    const isCore=coreWords.has(button.dataset.signExample);
    let badge=button.querySelector('[data-word-accuracy]');
    if(!badge){badge=document.createElement('small');badge.dataset.wordAccuracy='';badge.style.display='block';button.append(badge);}
    if(core){
      badge.textContent=`${(100*core[0]/core[1]).toFixed(1).replace(/\.0$/,'')}% test · ${core[0]}/${core[1]}`;
      button.title=`${isCore?'Core 7-word':'Extended 19-word'} ST-GCN, held-out test split: ${core[0]}/${core[1]} correct. Live-camera accuracy is unverified.`;
      continue;
    }
    const m=exampleAccuracy(name);
    badge.textContent=validAccuracy(m)?`${(100*m.correct/m.total).toFixed(1).replace(/\.0$/,'')}% test · ${m.correct}/${m.total}`:'Not measured';
    button.title=m?`${accuracyText(m)} · ${m.model}. ${m.scope}`:'Recorded accuracy not measured';
  }
}
function preparePractice(id){
  document.dispatchEvent(new CustomEvent('handspeak:prepare-practice',{detail:{id}}));
}
function pauseAll(){
  avatar?.pause();
  if(video){video.pause();}
}
function speedLabel(){
  const rate=Number(speed.value);
  return rate===1?'Normal speed':`${rate}× speed`;
}
function videoSrcFor(id){
  // Keep PopSign/ASL Citizen reference videos (portrait, known-good).
  // Studio Galt mocap drives the 3D signer only — its CC previews are landscape and look blank here.
  // Use the same relative path shape stored in media/avatar/reference/index.json.
  return `${VIDEO_BASE}${id}.mp4`;
}
function referenceSrcFor(id){
  return videoSrcFor(id);
}
function motionStatusText(){
  const hasVideo=Boolean(video?.getAttribute('src'))&&!videoPanel?.hasAttribute('data-missing');
  if(avatar?.referenceMatched)return `${label} · ${speedLabel()} · 3D matched to this reference video`;
  if(avatar?.mocap)return `${label} · ${speedLabel()} · Studio Galt mocap (different performance from the video)`;
  if(avatar?.approximate)return `${label} · ${speedLabel()} · Kai approximation (not the video’s exact hands)`;
  if(hasVideo&&avatar?.usingSkeletal)return `${label} · ${speedLabel()} · 3D skeletal animation`;
  if(hasVideo&&avatar?.usingBaked)return `${label} · ${speedLabel()} · 3D matched to reference video`;
  if(hasVideo&&(avatar?.videoSynced||avatar?.playing))return `${label} · ${speedLabel()} · 3D synced to reference video`;
  return `${label} · ${speedLabel()} · ${hasVideo?'video + 3D':'stylized 3D'}`;
}
function syncVideoRate(){
  if(!video)return;
  video.playbackRate=Number(speed.value)||1;
  video.loop=Boolean(document.querySelector('#signExampleLoop')?.checked);
}
function refreshMirrorStatus(){
  if(!status||!avatar?.playing)return;
  status.textContent=motionStatusText();
}
async function playReferenceVideo(id){
  if(!video)return;
  const src=await videoSrcFor(id);
  syncVideoRate();
  avatar?.setSyncVideo(video);
  const start = () => {
    video.currentTime=0;
    const playPromise=video.play();
    if(playPromise?.catch)playPromise.catch(()=>{ /* autoplay may be blocked until user gesture */ });
    setTimeout(refreshMirrorStatus, 400);
    setTimeout(refreshMirrorStatus, 1200);
  };
  if(video.getAttribute('src')===src && video.readyState>=2){
    videoPanel?.removeAttribute('data-missing');
    start();
    return;
  }
  videoPanel?.removeAttribute('data-missing');
  video.onloadeddata=()=>{
    video.onloadeddata=null;
    const landscape=video.videoWidth>video.videoHeight;
    video.dataset.orientation=landscape?'landscape':'portrait';
    start();
  };
  video.onerror=()=>{
    video.onerror=null;
    videoPanel?.setAttribute('data-missing','');
    avatar?.setSyncVideo(null);
    video.removeAttribute('src');
    video.load();
  };
  video.src=src;
  video.load();
}
function showLesson(id,name){
  if(cameraWords.has(id)){
    lesson.hidden=false;
    lesson.href=coreLessons[id];
    lesson.textContent=`${name} lesson · Signing Savvy (opens in a new tab)`;
    return;
  }
  if(lifeprintLessons[id]){
    lesson.hidden=false;
    lesson.href=lifeprintLessons[id];
    lesson.textContent=`${name} lesson · ASL University / Bill Vicars (opens in a new tab)`;
    return;
  }
  if(id==='thank-you'){
    lesson.hidden=false;
    lesson.href='https://www.lifeprint.com/asl101/pages-signs/t/thankyou.htm';
    lesson.textContent='THANK YOU lesson · ASL University / Bill Vicars (opens in a new tab)';
    return;
  }
  if(id==='finish'){
    lesson.hidden=false;
    lesson.href='https://www.lifeprint.com/asl101/pages-signs/f/finish.htm';
    lesson.textContent='FINISH lesson · ASL University / Bill Vicars (opens in a new tab)';
    return;
  }
  lesson.hidden=true;
}
function instructions(id){
  const standard=buttons.some(b=>b.dataset.signExample===id),published=publishedExamples.get(id);
  document.querySelector('#signExampleMode').textContent=published
    ?`${published.label} · Experimental word preview. Select Practice at camera to load its vocabulary, then start the camera, sign once and pause. Review every match; live-camera accuracy is unverified.`
    :daily.has(id)?`${id.toUpperCase()} · Five-word server preview prepared automatically. Start the camera, sign once, then pause. Review the match before signing again.`
    :extra.has(id)?`${id.toUpperCase()} · Extra-word preview prepared automatically. Start the camera, sign once, then pause. Review every match; live-camera accuracy is unverified.`
    :standard?`${id.toUpperCase()} · Automatic capture: start the camera, sign once, then pause. Review the match. You can also use Record a word.`
    :'Learning example · No enabled model for this word. Personal training is needed before camera practice.';
  const description=wordSettings(id).description;
  if(description)document.querySelector('#signExampleMode').textContent+=` ${description}`;
}
function ensureAvatar(){
  if(avatar||avatarFailed)return avatar;
  try{
    avatar=createSignAvatar(canvas);
    avatar.setSpeed(Number(speed.value));
    avatar.setLoop(document.querySelector('#signExampleLoop').checked);
    if(video)avatar.setSyncVideo(video);
    avatar.setStatusHandler(kind=>{
      if(kind==='playing'||kind==='ready')status.textContent=motionStatusText();
      else if(kind==='loading')status.textContent=`${label} · Loading cartoon signer matched to the reference…`;
      else if(kind==='ended')status.textContent=`${label} · Play again or try it at the camera.`;
      else if(kind==='paused')status.textContent=`${label} · Paused.`;
      else if(kind==='missing')status.textContent=`${label} · 3D signer could not load. Check your connection and reload.`;
    });
  }catch(error){
    console.warn(error);
    avatarFailed=true;
    status.textContent=`${label} · 3D signer could not start. Check your connection and reload.`;
  }
  return avatar;
}
function playSign(id){
  const player=ensureAvatar();
  if(!player)return false;
  playback.hidden=false;
  const reference=referenceSrcFor(id);
  playReferenceVideo(id);
  player.setSpeed(Number(speed.value));
  // Pass the exact displayed reference so Kai loads the video-matched
  // reconstruction instead of an unrelated Studio Galt / authored demo.
  return player.play(id,{reference});
}
function chooseSign(id,button=null,displayName=null){
  const name=displayName||button?.dataset.signLabel||id.replace(/-/g,' ').toUpperCase();
  selection+=1;
  pauseAll();
  label=name;
  libraryId=cameraWords.has(id)?CORE_SENTINEL:id;
  coreId=cameraWords.has(id)?id:null;
  for(const other of buttons)other.setAttribute('aria-pressed',String(other===button));
  showLesson(id,name);
  if(cameraWords.has(id)){
    const tier=coreWords.has(id)?'Core 7-word':'Extended 19-word';
    document.querySelector('#signExampleMode').textContent=`${name} · ${tier} camera model ready. Watch the 3D demo, then record one complete sign for four seconds and review the top five before adding the word.`;
  }else{
    instructions(id);
    preparePractice(id);
  }
  updateAccuracy();
  playSign(id);
}
function chooseCorePractice(id,button=null){
  chooseSign(id,button,cameraWords.get(id));
}
function chooseExample(name,_src,button=null,id=null){
  const selectedId=id||String(name||'').toLowerCase().replace(/\s+/g,'-');
  chooseSign(selectedId,button,name);
}

try{
  ensureAvatar();
}catch{
  avatarFailed=true;
}

for(const button of buttons)button.addEventListener('click',()=>{
  const id=button.dataset.signExample;
  if(cameraWords.has(id)){chooseCorePractice(id,button);return;}
  chooseSign(id,button,button.dataset.signLabel);
});
document.addEventListener('handspeak:example',event=>{
  const data=event.detail;
  const id=data.id||String(data.label||'').toLowerCase().replace(/\s+/g,'-');
  const button=buttons.find(b=>b.dataset.signExample===id)||null;
  chooseSign(id,button,data.label||button?.dataset.signLabel||id);
});
speed.addEventListener('change',()=>{
  avatar?.setSpeed(Number(speed.value));
  syncVideoRate();
  if(avatar?.playing)status.textContent=`${label} · ${speedLabel()} · video + 3D · match the reference video`;
});
document.querySelector('#signExampleLoop').addEventListener('change',event=>{
  avatar?.setLoop(event.target.checked);
  syncVideoRate();
});
document.querySelector('#signExampleReplay').addEventListener('click',()=>{
  if(!avatar)ensureAvatar();
  if(!avatar)return;
  const id=avatar.currentId||'hello';
  // Re-resolve against the reference so a stale mismatched clip cannot stick.
  playSign(id);
});
document.querySelector('#signExamplePractice').addEventListener('click',()=>{
  pauseAll();
  if(libraryId===CORE_SENTINEL&&coreId){document.dispatchEvent(new CustomEvent('handspeak:capstone-practice',{detail:{id:coreId,label:cameraWords.get(coreId)}}));return;}
  if(libraryId===BEGINNER_SENTINEL&&beginnerId){document.dispatchEvent(new CustomEvent('handspeak:beginner-practice',{detail:{id:beginnerId,label:beginnerWords.get(beginnerId)}}));return;}
  if(libraryId){document.dispatchEvent(new CustomEvent('handspeak:practice',{detail:{id:libraryId}}));return;}
  document.dispatchEvent(new CustomEvent('handspeak:default-practice',{detail:{label}}));
});
new IntersectionObserver(entries=>{if(!entries[0].isIntersecting)pauseAll();}).observe(document.querySelector('.example-player'));
document.addEventListener('visibilitychange',()=>{if(document.hidden)pauseAll();});
document.addEventListener('handspeak:view',pauseAll);

async function loadPublishedExamples(){
  try{
    const responses=await Promise.all([
      fetch('models/motion-vocabulary.json',{cache:'no-store'}),
      fetch('models/motion-categories/index.json',{cache:'no-store'})
    ]);
    if(responses.some(response=>!response.ok))return;
    const [catalog,index]=await Promise.all(responses.map(response=>response.json()));
    if(!Array.isArray(catalog.items)||!Array.isArray(index.groups))return;
    publishedPacks=index.groups;
    const container=document.querySelector('.example-words');
    await loadVocabularySettings();
    for(const item of applyVocabularySettings(catalog.items)){
      if(typeof item.id!=='string'||typeof item.label!=='string')continue;
      const enabled=index.groups.some(pack=>Array.isArray(pack.labels)&&pack.labels.includes(item.label)&&item.cameraGroups?.includes(pack.id));
      if(!enabled)continue;
      publishedExamples.set(item.id,item);
      if(buttons.some(button=>button.dataset.signExample===item.id))continue;
      const button=document.createElement('button');button.type='button';button.className='secondary-button';
      button.dataset.signExample=item.id;button.setAttribute('aria-pressed','false');button.textContent=item.label;
      button.dataset.signLabel=item.label;
      button.addEventListener('click',()=>chooseSign(item.id,button,item.label));
      buttons.push(button);container.append(button);
    }
    if(libraryId&&publishedExamples.has(libraryId))instructions(libraryId);
    updateAccuracy();
  }catch{ /* Existing practice examples remain available when the library cannot load. */ }
}
void loadBeginnerReadyExamples();
void loadPublishedExamples();
void loadAccuracyProfiles().then(profiles=>{accuracyProfiles=profiles;updateAccuracy();});

void loadVocabularySettings().then(()=>{
  for(const button of buttons){button.hidden=Boolean(wordSettings(button.dataset.signExample).hidden);}
  for(const option of document.querySelectorAll('#practiceWord option'))option.hidden=Boolean(wordSettings(option.value).hidden);
  for(const card of document.querySelectorAll('[data-daily-word]'))card.hidden=Boolean(wordSettings(card.dataset.dailyWord.toLowerCase()).hidden);
  const active=buttons.find(b=>b.getAttribute('aria-pressed')==='true');
  const first=active&&!active.hidden?active:buttons.find(b=>!b.hidden);
  if(first)chooseSign(first.dataset.signExample,first,first.dataset.signLabel);
});
