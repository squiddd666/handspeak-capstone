import json,time,sys,subprocess
import imageio_ffmpeg
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path('website-word-test/current-auto-virtual');out.mkdir(exist_ok=True)
word=sys.argv[1] if len(sys.argv)>1 else 'before'
source=Path('media/signs')/(word+'.mp4')
if not source.exists():source=Path('openhands-test/reference-videos')/(word+'.mp4')
camera=(out/(word+'.y4m')).resolve()
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',str(source),'-an','-vf','scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2:color=gray,setsar=1,fps=15,tpad=start_duration=4:start_mode=add:stop_duration=4:stop_mode=add:color=gray,format=yuv420p','-f','yuv4mpegpipe',str(camera)],check=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--use-fake-device-for-media-stream=fps=15','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture='+str(camera)])
 page=b.new_page();page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("window.captures=[];document.addEventListener('handspeak:word-capture-diagnostics',e=>captures.push(e.detail))")
 try:
  page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded');page.wait_for_selector('#openhandsEnabled',state='attached')
  page.select_option('#recognitionMode','words');page.check('#openhandsConsent');page.click('#cameraButton')
  with page.expect_response(lambda r:r.url.endswith('/api/openhands/recognize') and r.request.method=='POST',timeout=150000) as res:
   page.wait_for_function("document.querySelector('#webcam').videoWidth>0",timeout=60000)
  response=res.value;page.wait_for_timeout(1000)
  result={'expected':word.upper(),'http':response.status,'response':response.json(),'status':page.locator('#openhandsStatus').inner_text(),'live':page.locator('#liveLetter').inner_text(),'captures':page.evaluate('captures'),'errors':errors}
  if result['response'].get('label'):
   page.locator('#openhandsAccept').click();result['word_log']=page.locator('#interpreterLog').inner_text();result['added_to_log']=result['response']['label'] in result['word_log']
 except Exception as e:result={'error':str(e),'status':page.locator('#openhandsStatus').inner_text(),'feedback':page.locator('#recognitionFeedback').inner_text(),'errors':errors}
 page.screenshot(path=str(out/(word+'.png')),full_page=True)
 (out/(word+'.json')).write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);b.close()
