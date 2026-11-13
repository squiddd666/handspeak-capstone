import json
from pathlib import Path
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--use-fake-device-for-media-stream=fps=15','--use-fake-ui-for-media-stream'])
 page=b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 # Fault injection only: real worker initialization, deliberately no frame delivery.
 page.add_init_script("const NativeWorker=window.Worker;window.Worker=class extends NativeWorker{postMessage(data,transfer){if(data?.type==='frame')return;return super.postMessage(data,transfer);}};")
 page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded');page.wait_for_selector('#openhandsEnabled',state='attached');page.select_option('#recognitionMode','words');page.click('#cameraButton')
 page.wait_for_function("document.querySelector('#webcam').srcObject?.getVideoTracks()[0]?.readyState==='live'",timeout=60000)
 page.wait_for_function("document.querySelector('#cameraButton').textContent.includes('Start camera')&&!document.querySelector('#webcam').srcObject",timeout=15000)
 result={'scope':'Worker-stall fault injection, not model accuracy.','cameraStopped':True,'hint':page.locator('#wordHandStatus').inner_text(),'notification':page.locator('#toast').inner_text(),'errors':errors}
 print(json.dumps(result),flush=True);Path('website-word-test/tracking-visibility/watchdog.json').write_text(json.dumps(result,indent=2));b.close()
