import json
from pathlib import Path
from playwright.sync_api import sync_playwright
OUT=Path('website-word-test/tracking-visibility');OUT.mkdir(exist_ok=True)
source=Path('website-word-test/boundary-consensus-virtual/before.y4m').resolve()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--use-fake-device-for-media-stream=fps=15','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture='+str(source)])
 page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 r={}
 try:
  page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded');page.wait_for_selector('#openhandsEnabled',state='attached');page.select_option('#recognitionMode','words');page.click('#cameraButton')
  with page.expect_response(lambda response:response.url.endswith('/api/openhands/recognize') and response.request.method=='POST',timeout=100000) as response:
   page.wait_for_function("()=>{const text=document.querySelector('#wordHandStatus')?.textContent||'';if(!text.includes('tracked')&&!text.includes('Hand detected'))return false;const c=document.querySelector('#overlay');if(!c.width)return false;const pixels=c.getContext('2d').getImageData(0,0,c.width,c.height).data;for(let i=3;i<pixels.length;i+=64)if(pixels[i]>0)return true;return false;}",timeout=60000)
   r['trackingHint']=page.locator('#wordHandStatus').inner_text();r['visibleOverlay']=True
   page.screenshot(path=str(OUT/'tracking-overlay.png'))
  res=response.value;r.update(http=res.status,response=res.json());page.wait_for_timeout(700)
  r['choices']=page.locator('[data-combined-word]').all_text_contents()
  if page.locator('[data-combined-word="BEFORE"]').count():
   page.locator('[data-combined-word="BEFORE"]').click();page.locator('#interpreterAdd').click();r['log']=page.locator('#interpreterLog').inner_text()
  page.click('#cameraButton');r['stoppedHint']=page.locator('#wordHandStatus').inner_text()
 except Exception as e:r['error']=str(e)
 r['errors']=errors;(OUT/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True);b.close()
