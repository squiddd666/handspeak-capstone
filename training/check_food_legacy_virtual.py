"""User-requested Playwright QA: real getUserMedia with a Y4M file camera.
Never inject landmarks, model outputs, backend responses, or expected labels.
"""
import argparse,datetime,hashlib,json,subprocess,time,sys,re
from pathlib import Path
import imageio_ffmpeg,cv2
from playwright.sync_api import sync_playwright
from no_obs_virtual_camera import candidates
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'handspeak-training/food-current-virtual'
OUT.mkdir(parents=True,exist_ok=True)

def reveal(page,selector):
 page.locator(selector).evaluate("e=>{for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;}")

def run_case(p,row):
 word=row['word'];mode=row['mode'];slug=re.sub('[^a-z0-9]+','-',word.lower()).strip('-');work=OUT/slug;work.mkdir(exist_ok=True)
 camera=work/'camera.y4m';source=Path(row['source'])
 cap=cv2.VideoCapture(str(source));duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS);cap.release()
 filters='scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2:color=gray,setsar=1,fps=15,tpad=start_duration=4:start_mode=add:stop_duration=4:stop_mode=add:color=gray,format=yuv420p'
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',str(source),'-an','-vf',filters,'-f','yuv4mpegpipe',str(camera)],check=True)
 cycle=(round(duration*15)+120)/15
 result=dict(word=word,mode=mode,source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),sourceDuration=duration,camera_cycle=cycle,warmup=None,outcome='capture_failure',predicted=None)
 responses=[];errors=[]
 context=p.chromium.launch_persistent_context(str(OUT/'profile'),executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,
   args=['--use-fake-device-for-media-stream=fps=15','--use-file-for-fake-video-capture='+str(camera),'--autoplay-policy=no-user-gesture-required'],viewport={'width':1440,'height':1000},permissions=['camera'])
 page=context.new_page();page.set_default_timeout(30000)
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('response',lambda r:responses.append(r) if r.request.method=='POST' and '/api/' in r.url else None)
 page.add_init_script("window.cameraQA={matches:[],diagnostics:[]};document.addEventListener('handspeak:camera-match',e=>cameraQA.matches.push({detail:e.detail,mediaTime:document.querySelector('#webcam')?.currentTime}));document.addEventListener('handspeak:word-capture-diagnostics',e=>cameraQA.diagnostics.push(e.detail));")
 try:
  page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded')
  page.wait_for_function("document.documentElement.dataset.handspeakReady==='true'",timeout=60000)
  
  if page.locator('#simpleViewButton').get_attribute('aria-pressed')=='true':page.click('#simpleViewButton')
  page.select_option('#recognitionMode','words');page.uncheck('#openhandsEnabled');reveal(page,'#automaticWords');page.uncheck('#automaticWords')
  if mode=='beginner-ready':
   page.wait_for_selector('#beginnerVocabMode',state='attached');reveal(page,'#beginnerVocabMode');page.select_option('#beginnerVocabMode','ready')
   reveal(page,'#beginnerConsent');page.check('#beginnerConsent');record='#beginnerRecord';cancel='#beginnerCancel';status='#beginnerStatus';endpoint='/api/beginner-asl'
  elif mode=='research-five':
   reveal(page,'#researchWordsToggle');page.wait_for_function("!document.querySelector('#researchWordsToggle').disabled",timeout=30000);page.check('#researchWordsToggle')
   record='#researchRecord';cancel='#researchCancel';status='#researchWordsStatus';endpoint='/api/research-words'
  else:
   endpoint=None;record='#wordCaptureButton';cancel='#motionCancel';status='#motionHelp'
   if mode.startswith('browser-single-'):
    page.locator("a[href='#learn']").first.click();reveal(page,'#cameraVocabulary');page.wait_for_function("id=>[...document.querySelector('#cameraVocabulary').options].some(o=>o.value===id)",arg=mode.replace('browser-',''),timeout=30000)
    page.select_option('#cameraVocabulary',mode.replace('browser-',''))
    page.wait_for_function("document.querySelector('#activeVocabulary').textContent.includes('preview')",timeout=30000)
    page.locator("a.brand[href='#workspace']").click()
   else:
    reveal(page,'#expandedWords');page.wait_for_function("!document.querySelector('#expandedWords').disabled",timeout=30000);page.check('#expandedWords')
  page.click('#cameraButton');page.wait_for_function("document.querySelector('#webcam').srcObject?.getVideoTracks()[0]?.readyState==='live'",timeout=60000)
  page.wait_for_function("document.querySelector('#webcam').videoWidth>0",timeout=30000)
  result['stream']=page.locator('#webcam').evaluate("v=>({label:v.srcObject.getVideoTracks()[0].label,settings:v.srcObject.getVideoTracks()[0].getSettings(),width:v.videoWidth,height:v.videoHeight})")
  # Warm-up initializes Holistic/ONNX/CDN runtimes; excluded from accuracy.
  reveal(page,record);page.wait_for_function("s=>!document.querySelector(s).disabled",arg=record,timeout=60000);page.click(record)
  page.wait_for_timeout(18000)
  result['warmup']=dict(status=page.locator(status).inner_text(),independentAttempt=False)
  if page.locator(cancel).is_enabled():page.click(cancel)
  page.wait_for_function("s=>!document.querySelector(s).disabled",arg=record,timeout=30000)
  # Observe source clock, then start normal UI countdown before the next sign.
  page.wait_for_function("cycle=>{const t=document.querySelector('#webcam').currentTime%cycle;return t>=2.15&&t<=2.35;}",arg=cycle,timeout=int((cycle+4)*1000),polling=30)
  before=page.evaluate("()=>({time:document.querySelector('#webcam').currentTime,matches:cameraQA.matches.length,diags:cameraQA.diagnostics.length,frames:document.querySelector('#webcam').getVideoPlaybackQuality().totalVideoFrames})")
  responses.clear();page.click(record);page.wait_for_timeout(13000)
  result['status']=page.locator(status).inner_text()
  result['events']=page.evaluate("n=>({matches:cameraQA.matches.slice(n.matches),diagnostics:cameraQA.diagnostics.slice(n.diags),end:document.querySelector('#webcam').currentTime,frames:document.querySelector('#webcam').getVideoPlaybackQuality().totalVideoFrames})",before)
  result['record_button_media_time']=before['time']
  api=[r for r in responses if endpoint and r.url.endswith(endpoint)]
  if api:
   response=api[-1];data=response.json();result['http']=response.status;result['backend_response']=data
   result['predicted']=data.get('label') if mode=='research-five' else next(iter(data.get('predictions',[])),{}).get('label')
  else:
   events=[e for e in result['events']['matches'] if e['detail']['word'] not in ['—','No reliable match','Not enough frames','Hands not tracked','Capture incomplete']]
   if events:result['predicted']=events[-1]['detail']['word']
  diags=[d for d in result['events']['diagnostics'] if d.get('startMediaTime') is not None and not d.get('outcome')]
  sign_start=(int(before['time']//cycle))*cycle+4;sign_end=sign_start+duration
  if mode=='beginner-ready' and diags:
   start=diags[-1]['startMediaTime'];end=diags[-1]['endMediaTime']
  elif mode!='beginner-ready':start=before['time']+1.5;end=before['time']+4
  else:start=end=None
  result['full_source_captured']=bool(start is not None and start<=sign_start+.2 and end>=sign_end-.2)
  result['capture_window']=dict(start=start,end=end,sourceStart=sign_start,sourceEnd=sign_end)
  result['display']=page.locator('#liveLetter').inner_text()
  if errors:result['outcome']='application_error'
  elif mode!='beginner-ready':result['outcome']='timing_unverified'
  elif not result['full_source_captured']:result['outcome']='capture_failure'
  elif endpoint and not api:result['outcome']='capture_failure'
  elif result.get('http',200)!=200:result['outcome']='model_error'
  elif result['predicted']:result['outcome']='correct' if result['predicted']==word else 'wrong'
  else:result['outcome']='rejected'
  page.screenshot(path=str(work/'website.png'),full_page=False)
 except Exception as e:
  result['error']=str(e)
  try:page.screenshot(path=str(work/'failure.png'))
  except Exception:pass
 finally:
  result['page_errors']=errors;context.close()
  # Only remove this runner's generated temporary camera stream, not sources.
  if camera.resolve().is_relative_to(OUT.resolve()):camera.unlink(missing_ok=True)
 return result

with sync_playwright() as p:
 row=next(r for r in candidates() if r['word']=='FOOD')
 result=run_case(p,row)
 output=ROOT/'website-word-test/current-auto-virtual/food-legacy.json'
 output.write_text(json.dumps(result,indent=2))
 print(json.dumps(result),flush=True)
