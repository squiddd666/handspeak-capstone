// Opt-in test controls inside HandSpeak itself. Never inject camera data/results.
export function installFakeCameraTest({startCamera,isRunning,setRecognitionMode}){
 const params=new URLSearchParams(location.search);
 if(params.get('fakeCameraTest')!=='1')return;
 const expected=params.get('testWord')||'',mode=params.get('testMode')||'beginner-ready';
 const $=s=>document.querySelector(s);
 const panel=document.createElement('section');panel.className='fake-camera-test';
 panel.style.cssText='grid-column:1/-1;padding:20px;border:2px solid #00e9a5;border-radius:12px;background:#123021;color:#e5fff1';
 panel.innerHTML='<h2 style="margin:0 0 8px">No-OBS camera test</h2><p id="fakeTestExpected"></p><p>This test uses the reference video as the camera. Server models process extracted coordinates on this computer. No expected label is sent to the model.</p><div class="camera-actions"><button type="button" id="fakeTestStart" class="primary-button">1. Start fake camera</button><button type="button" id="fakeTestRecord" class="secondary-button" disabled>2. Record test</button></div><p id="fakeTestStatus" role="status">Ready. Start the fake camera, allow the camera prompt, and verify the reference signer appears.</p><p id="fakeTestResult">No result yet. Capture timing has not been verified.</p>';
 $('#workspace').prepend(panel);
 $('#fakeTestExpected').textContent=`Expected: ${expected} | Vocabulary: ${mode}`;
 setRecognitionMode('words');
 const delay=ms=>new Promise(r=>setTimeout(r,ms));
 async function waitFor(test){for(let i=0;i<100;i++){if(test())return;await delay(100);}throw Error('Word controls are still loading. Reload and retry.');}
 let recordId=null,statusId=null;
 async function configure(){
  if(mode==='beginner-ready'||mode==='capstone-core'||mode==='capstone-extended'||mode==='capstone-full'||mode==='target20'){
   throw Error('This test mode was removed with the experimental server model panels. Use research-five, browser modes, or OpenHands instead.');
  }
  await waitFor(()=>$('#wordRecognitionControls')||$('#openhandsRecord')||$('#researchWordsToggle'));
  if(mode==='openhands'){
   await waitFor(()=>!$('#openhandsRecord')?.disabled);
   recordId='#openhandsRecord';statusId='#openhandsStatus';
  }else if(mode==='research-five'){
   const toggle=$('#researchWordsToggle');await waitFor(()=>!toggle.disabled);toggle.checked=true;toggle.dispatchEvent(new Event('change'));
   recordId='#researchRecord';statusId='#researchWordsStatus';
  }else{
   if(mode.startsWith('browser-single-')){
    throw Error('Category camera-vocabulary browsing was removed. Use browser-expanded, research-five, or OpenHands instead.');
   }else if(mode==='browser-expanded'){
    const toggle=$('#expandedWords');await waitFor(()=>!toggle.disabled);toggle.checked=true;toggle.dispatchEvent(new Event('change'));
   }
   recordId='#wordCaptureButton';statusId='#motionHelp';
  }
  const automatic=$('#automaticWords');automatic.checked=false;automatic.dispatchEvent(new Event('change'));
 }
 $('#fakeTestStart').onclick=async()=>{
  $('#fakeTestStart').disabled=true;
  try{
   $('#fakeTestStatus').textContent='Selecting Words mode and loading the camera. Allow the camera prompt if shown…';
   await configure();await startCamera();
   if(!isRunning())throw Error('Camera did not start. Check the camera prompt and the camera status below.');
   $('#fakeTestStatus').textContent='Camera started. Confirm that the REFERENCE SIGNER appears, then click Record test during the gray lead-in.';
   $('#fakeTestRecord').disabled=false;
  }catch(error){$('#fakeTestStatus').textContent=error.message;}
  finally{$('#fakeTestStart').disabled=false;}
 };
 $('#fakeTestRecord').onclick=()=>{
  if(!isRunning()){$('#fakeTestStatus').textContent='Start the fake camera first.';return;}
  const button=$(recordId);
  if(!button||button.disabled){$('#fakeTestStatus').textContent='The selected model is not ready or is busy. Check its status below.';return;}
  $('#fakeTestResult').textContent='Test requested. No result yet; ensure one complete sign falls within the recording window.';
  button.click();
 };
 let last='';
 setInterval(()=>{const text=statusId&&$(statusId)?.textContent;if(text&&text!==last){last=text;$('#fakeTestStatus').textContent=text;}},250);
 document.addEventListener('handspeak:camera-match',event=>{
  const observed=event.detail.word;
  if(!observed||observed==='—')return;
  $('#fakeTestResult').textContent=`Expected ${expected}; observed ${observed}. ${observed===expected?'Labels match':'Labels do not match'}. Full-sign capture still needs verification; this is not an automatic accuracy pass.`;
 });
}
