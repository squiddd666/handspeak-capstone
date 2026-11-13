"""One end-to-end integration smoke test, not a 70-word accuracy evaluation."""
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
from no_obs_virtual_camera import prepare
ROOT=Path(__file__).resolve().parents[1]
camera,meta=prepare(dict(word='BEFORE',mode='openhands70',source=str(ROOT/'media/signs/before.mp4')))
responses=[];errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--use-fake-device-for-media-stream=fps=15','--use-file-for-fake-video-capture='+str(camera)])
 context=browser.new_context(permissions=['camera'],viewport={'width':1440,'height':1000})
 page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("window.openhandsQA=[];document.addEventListener('handspeak:word-capture-diagnostics',e=>openhandsQA.push(e.detail));")
 page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded')
 page.wait_for_function("document.documentElement.dataset.handspeakReady==='true'")
 page.select_option('#recognitionMode','words')
 page.wait_for_function("document.querySelector('#openhandsStatus').textContent.includes('ready')")
 page.check('#openhandsConsent');page.click('#cameraButton')
 page.wait_for_function("document.querySelector('#webcam').videoWidth>0")
 cycle=round(meta['sourceDurationSeconds']*15)/15+8
 page.wait_for_function("cycle=>{let t=document.querySelector('#webcam').currentTime%cycle;return t>2.15&&t<2.35}",arg=cycle,timeout=20000,polling=20)
 with page.expect_response(lambda r:'/api/openhands/recognize' in r.url and r.request.method=='POST',timeout=110000) as pending:
  page.click('#openhandsRecord')
 response=pending.value;data=response.json()
 page.wait_for_function("document.querySelector('#openhandsStatus').textContent.includes('Review before adding')",timeout=10000)
 assert response.status==200,data
 assert data['label']=='BEFORE',data
 assert page.locator('#liveLetter').inner_text()=='BEFORE'
 page.click('#openhandsAccept')
 assert 'BEFORE' in page.locator('#messageText').inner_text()
 assert 'BEFORE' in page.locator('#interpreterLog').inner_text()
 assert not errors,errors
 result=dict(expected='BEFORE',response=data,display=page.locator('#liveLetter').inner_text(),draft=page.locator('#messageText').inner_text(),capture=page.evaluate('openhandsQA'),stream=page.locator('#webcam').evaluate("v=>({width:v.videoWidth,height:v.videoHeight,label:v.srcObject.getVideoTracks()[0].label})"),page_errors=errors,scope='One real website MediaRecorder -> local OpenHands endpoint -> reviewed draft smoke test. Not all-70 virtual-camera or physical-webcam validation.')
 (ROOT/'website-word-test/openhands70-browser-smoke.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
 page.screenshot(path=str(ROOT/'website-word-test/openhands70-browser-smoke.png'))
 print('PASS: fake camera -> website video recording -> OpenHands BEFORE -> displayed -> reviewed word log')
 browser.close()
