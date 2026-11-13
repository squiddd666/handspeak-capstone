import json,sys,subprocess,time,hashlib
from pathlib import Path
import cv2,imageio_ffmpeg
from playwright.sync_api import sync_playwright
ROOT=Path.cwd();OUT=ROOT/'website-word-test/boundary-consensus-virtual';OUT.mkdir(exist_ok=True)
word=sys.argv[1].lower();automatic='--automatic' in sys.argv;tag=word+('-automatic' if automatic else '');source=ROOT/'media/signs'/f'{word}.mp4'
if not source.exists():source=ROOT/'openhands-test/reference-videos'/f'{word}.mp4'
camera=OUT/(word+'.y4m')
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',str(source),'-an','-vf','scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2:color=gray,setsar=1,fps=15,tpad=start_duration=4:start_mode=add:stop_duration=4:stop_mode=add:color=gray,format=yuv420p','-f','yuv4mpegpipe',str(camera)],check=True)
c=cv2.VideoCapture(str(camera));cycle=c.get(cv2.CAP_PROP_FRAME_COUNT)/c.get(cv2.CAP_PROP_FPS);c.release()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--use-fake-device-for-media-stream=fps=15','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture='+str(camera)])
 page=b.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(30000);errors=[];posts=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("window.qa={browser:[],capture:[],boundaries:[]};document.addEventListener('handspeak:word-boundary',e=>qa.boundaries.push(e.detail));document.addEventListener('handspeak:combined-browser-result',e=>qa.browser.push(e.detail));document.addEventListener('handspeak:word-capture-diagnostics',e=>qa.capture.push(e.detail))")
 def save_request(req):
  if req.url.endswith('/api/openhands/recognize') and req.method=='POST':
   posts.append(req.url)
   body=req.post_data_buffer
   if body:(OUT/(word+'-capture.webm')).write_bytes(body)
 page.on('request',save_request)
 r={'sceneSHA':hashlib.sha256(Path('scene-motion.js').read_bytes()).hexdigest(),'codeSHA':hashlib.sha256(Path('automatic-word-capture.js').read_bytes()).hexdigest(),'boundarySHA':hashlib.sha256(Path('word-boundaries.js').read_bytes()).hexdigest(),'expected':word.upper(),'scope':'Actual browser + OpenHands inference on same shared virtual-camera capture. One reference; not webcam accuracy.','captureMode':'automatic' if automatic else 'manual'}
 try:
  page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded');page.wait_for_selector('#openhandsEnabled',state='attached');page.select_option('#recognitionMode','words')
  if not automatic:page.uncheck('#automaticWords')
  page.click('#cameraButton')
  page.wait_for_function("document.querySelector('#webcam').videoWidth>0",timeout=60000)
  if not automatic:
   page.wait_for_timeout(4000)
   page.locator('#wordCaptureButton').scroll_into_view_if_needed()
   page.wait_for_function("cycle=>{const t=document.querySelector('#webcam').currentTime%cycle;return t>=2.25&&t<=2.42}",arg=cycle,timeout=30000,polling=20)
  with page.expect_response(lambda response:response.url.endswith('/api/openhands/recognize') and response.request.method=='POST',timeout=65000) as response:
   if not automatic:page.click('#wordCaptureButton')
  res=response.value;r.update(http=res.status,server=res.json())
  page.wait_for_timeout(700)
  r.update(diagnostics=page.evaluate('qa'),choices=page.locator('[data-combined-word]').all_text_contents(),status=page.locator('#openhandsStatus').inner_text(),current=page.locator('#interpreterWord').inner_text(),stream=page.locator('#webcam').evaluate('v=>v.srcObject.getVideoTracks()[0].getSettings()'))
  capture=next((d for d in r['diagnostics']['capture'] if d.get('capture')=='openhands-video'),None)
  if capture:
   cap=cv2.VideoCapture(str(source));duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS);cap.release()
   start=4+round((capture['startMediaTime']-4)/cycle)*cycle
   r['sourceWindow']={'start':start,'end':start+duration};r['fullSourceCapturedWithinTolerance']=capture['startMediaTime']<=start+.2 and capture['endMediaTime']>=start+duration-.2
  choice=page.locator('[data-combined-word="'+word.upper()+'"]')
  r['expectedOffered']=choice.count()==1
  if r['expectedOffered']:
   if '--repeat' in sys.argv:
    page.wait_for_timeout(int((cycle+2)*1000));r['noDuplicateWhileReview']=len(posts)==1
   choice.click();page.locator('#interpreterAdd').click();r['log']=page.locator('#interpreterLog').inner_text();r['loggedOnce']=page.locator('#interpreterLog .word-log-complete span').all_text_contents().count(word.upper())==1
  if '--repeat' in sys.argv and r.get('loggedOnce'):
   with page.expect_response(lambda response:response.url.endswith('/api/openhands/recognize') and response.request.method=='POST',timeout=90000) as second:
    page.wait_for_timeout(100)
   r['secondResponse']=second.value.json();page.wait_for_timeout(700)
   r['secondChoices']=page.locator('[data-combined-word]').all_text_contents()
   r['noUnreviewedAutoAdd']=page.locator('#interpreterLog .word-log-complete span').all_text_contents().count(word.upper())==1
   secondChoice=page.locator('[data-combined-word="'+word.upper()+'"]')
   if secondChoice.count():
    secondChoice.click();page.locator('#interpreterAdd').click()
    r['secondReviewedLogCount']=page.locator('#interpreterLog .word-log-complete span').all_text_contents().count(word.upper())
   r['requestCount']=len(posts)
 except Exception as e:
  r['error']=str(e);r['status']=page.locator('#openhandsStatus').inner_text() if page.locator('#openhandsStatus').count() else 'App did not initialize'
 r['errors']=errors;page.screenshot(path=str(OUT/(tag+'.png')),full_page=True);(OUT/(tag+'.json')).write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True);b.close()
