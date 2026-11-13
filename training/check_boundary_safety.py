import json,hashlib
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT=Path('website-word-test/boundary-consensus-virtual');results=[]
with sync_playwright() as p:
 for mode in ['blank','cancel','gap']:
  args=['--use-fake-device-for-media-stream=fps=15','--use-fake-ui-for-media-stream']
  if mode in ['cancel','gap']:args.append('--use-file-for-fake-video-capture='+str((OUT/'before.y4m').resolve()))
  b=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=args)
  page=b.new_page();posts=[];errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:posts.append(r.url) if r.method=='POST' and r.url.endswith('/api/openhands/recognize') else None)
  try:
   page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded');page.wait_for_selector('#openhandsEnabled',state='attached');page.select_option('#recognitionMode','words');page.click('#cameraButton');page.wait_for_function("document.querySelector('#webcam').videoWidth>0",timeout=60000)
   if mode=='blank':page.wait_for_timeout(12000)
   else:
    page.wait_for_function("document.querySelector('#openhandsStatus').textContent.includes('Watching your sign')",timeout=45000)
    if mode=='cancel':page.click('#openhandsCancel')
    else:page.evaluate('()=>{const end=performance.now()+1000;while(performance.now()<end){};}')
    page.wait_for_timeout(3000)
   result={'case':mode,'posts':len(posts),'errors':errors,'passed':not posts and not errors,'status':page.locator('#openhandsStatus').inner_text(),'automaticEnabled':page.locator('#automaticWords').is_checked(),'codeSHA':hashlib.sha256(Path('automatic-word-capture.js').read_bytes()).hexdigest()}
   if mode=='gap':result['passed']=result['passed'] and 'timing-gap' in result['status']
   page.click('#cameraButton')
  except Exception as e:result={'case':mode,'passed':False,'error':str(e),'posts':len(posts),'errors':errors}
  results.append(result);print(json.dumps(result),flush=True);b.close()
(OUT/'safety-results.json').write_text(json.dumps(results,indent=2))
