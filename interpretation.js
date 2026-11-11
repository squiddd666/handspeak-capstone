export function createInterpreter({getMessage,setMessage,speak=()=>{}}) {
  const $=s=>document.querySelector(s);
  let result=null, applied=false, revision=0, lastSpoken=null, interacted=false, warmChecks=0;
  const state=(value,text)=>document.dispatchEvent(new CustomEvent('handspeak:sentence-state',{detail:{state:value,text}}));
  const status=$('#interpretStatus'), box=$('#interpretResult'), button=$('#interpretButton');
  async function availability(){
    try {const response=await fetch('/api/interpret/status');if(!response.ok)throw Error();const data=await response.json();if(!interacted){status.textContent=data.warming?'Local sentence assistant is warming up… Please wait a moment.':data.available?'Local sentence assistant ready. Up to 500 characters.':'Local model is unavailable. Your draft and other features still work.';if(data.warming&&warmChecks++<25)setTimeout(()=>void availability(),2000);}}
    catch{if(!interacted)status.textContent='Could not check the local model. You can retry interpretation.';}
  }
  async function interpret(autoSpeak=false){
    interacted=true;
    if(button.disabled){status.textContent='An interpretation is already running. Wait for its result; sign FINISH again afterward to speak it.';return;}
    const requestRevision=revision;
    const original=getMessage();
    if(!original.trim()){status.textContent='Your draft is empty. Add recognized words to your message or use Edit message before interpreting.';return;}
    if(original.length>500){status.textContent='Enter 1–500 characters. Use Edit message to adjust your draft.';return;}
    result=null;applied=false;box.hidden=true;button.disabled=true;state('interpreting','Interpreting your sentence…');
    const started=Date.now(),buttonLabel=button.textContent;
    button.textContent='Interpreting…';button.setAttribute('aria-busy','true');
    const progress=()=>{status.textContent=`Interpreting on this server… ${Math.floor((Date.now()-started)/1000)} seconds elapsed. The local model may take up to 45 seconds. Your draft is unchanged.`;};
    progress();const ticker=setInterval(progress,1000);
    const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),50000);
    try {
      const response=await fetch('/api/interpret',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:original}),signal:controller.signal});
      const data=await response.json();if(!response.ok)throw Error(data.error||'Interpretation failed.');
      result=data;$('#interpretOriginal').textContent=original;$('#interpretSuggestion').textContent=data.sentence||'More context is needed.';$('#interpretNote').textContent=data.note;
      box.hidden=false;$('#interpretUndo').hidden=true;state('review',data.needsClarification?'More context needed · Edit your draft.':'Sentence ready · Review the suggestion.');
      $('#interpretApply').disabled=data.needsClarification||!data.sentence||getMessage()!==original;
      status.textContent=getMessage()!==original?'Your draft changed. Interpret again to use a current suggestion.':'Suggestion only. Compare it with your original words before applying.';
      if(autoSpeak){
        if(!$('#finishInterpretSpeak').checked||revision!==requestRevision||getMessage()!==original){status.textContent='Automatic speech canceled: the draft or FINISH setting changed.';}
        else if(data.needsClarification||!data.sentence){status.textContent='Nothing spoken. The sentence needs clarification; edit the draft and try again.';}
        else{lastSpoken=original;speak(data.sentence);status.textContent='FINISH received — requested speech for the interpreted sentence. Original words remain in your draft. If audio is blocked, use Speak suggestion.';}
      }
    } catch(error){state('error','Interpretation could not finish · Your draft is unchanged.');status.textContent=error.name==='AbortError'?'Interpretation timed out. Your draft is unchanged.':error.message;}
    finally{clearTimeout(timer);clearInterval(ticker);button.disabled=false;button.textContent=buttonLabel;button.removeAttribute('aria-busy');}
  }
  button.addEventListener('click',()=>{void interpret();});
  $('#speakInterpretation').addEventListener('click',()=>{if(result&&!result.needsClarification&&result.sentence)speak(result.sentence);});
  $('#finishInterpretSpeak').addEventListener('change',()=>{
    revision++;
    const autoAdd=$('#sentenceAutoAdd');
    if($('#finishInterpretSpeak').checked&&autoAdd){
      autoAdd.checked=true;autoAdd.dispatchEvent(new Event('change'));
      status.textContent='FINISH speech enabled. Detected words will be added to your draft automatically. Review them, then sign FINISH.';
    }
  });
  $('#interpretApply').addEventListener('click',()=>{
    if(!result||result.needsClarification)return;
    if(getMessage()!==result.original){status.textContent='Your draft changed. Interpret again before applying.';$('#interpretApply').disabled=true;return;}
    setMessage(result.sentence);applied=true;$('#interpretApply').disabled=true;$('#interpretUndo').hidden=false;status.textContent='Suggestion applied. Review before speaking or saving. Original words remain below.';
  });
  $('#interpretUndo').addEventListener('click',()=>{
    if(!applied||!result)return;
    if(getMessage()!==result.sentence){status.textContent='Your draft changed after applying. Use Edit message to avoid overwriting your edits.';return;}
    setMessage(result.original);applied=false;$('#interpretUndo').hidden=true;$('#interpretApply').disabled=false;status.textContent='Original draft restored.';
  });
  new MutationObserver(()=>{revision++;lastSpoken=null;if(result&&!applied&&getMessage()!==result.original)$('#interpretApply').disabled=true;}).observe($('#messageText'),{childList:true,subtree:true,characterData:true});
  if($('#finishInterpretSpeak').checked)$('#finishInterpretSpeak').dispatchEvent(new Event('change'));
  void availability();
  return {finish(){
    if(!$('#finishInterpretSpeak').checked)return false;
    if(!getMessage().trim()){status.textContent='FINISH received, but the draft is empty. Add your words first.';return true;}
    if(lastSpoken===getMessage()){status.textContent='This draft was already spoken. Add or edit words before signing FINISH again.';return true;}
    state('finish','FINISH received · Preparing your sentence.');void interpret(true);return true;
  }};
}
