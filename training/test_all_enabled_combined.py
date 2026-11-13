from pathlib import Path
import json,sys,subprocess,time,datetime,hashlib,collections,urllib.request,html,re
import cv2,imageio_ffmpeg
from playwright.sync_api import sync_playwright
from no_obs_virtual_camera import candidates
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'handspeak-training/all-enabled-combined-v1'
OUT.mkdir(exist_ok=True)
PUBLIC=ROOT/'website-word-test/all-enabled-combined-v1'
PUBLIC.mkdir(exist_ok=True)

def combined_case(p,row):
 word=row['word'].lower();automatic=False;tag=word;source=Path(row['source'])
 if not source.exists():source=ROOT/'openhands-test/reference-videos'/f'{word}.mp4'
 camera=OUT/(word+'.y4m')
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',str(source),'-an','-vf','scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2:color=gray,setsar=1,fps=15,tpad=start_duration=4:start_mode=add:stop_duration=4:stop_mode=add:color=gray,format=yuv420p','-f','yuv4mpegpipe',str(camera)],check=True)
 c=cv2.VideoCapture(str(camera));cycle=c.get(cv2.CAP_PROP_FRAME_COUNT)/c.get(cv2.CAP_PROP_FPS);c.release()
 b=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--use-fake-device-for-media-stream=fps=15','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture='+str(camera)])
 page=b.new_page(viewport={'width':1440,'height':1000});page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("window.qa={browser:[],capture:[]};document.addEventListener('handspeak:combined-browser-result',e=>qa.browser.push(e.detail));document.addEventListener('handspeak:word-capture-diagnostics',e=>qa.capture.push(e.detail))")
 def save_request(req):
  if req.url.endswith('/api/openhands/recognize') and req.method=='POST':
   body=req.post_data_buffer
   if body:(OUT/(word+'-capture.webm')).write_bytes(body)
 page.on('request',save_request)
 r={'expected':word.upper(),'scope':'Actual browser + OpenHands inference on same 3-second virtual-camera capture. One reference; not webcam accuracy.','captureMode':'automatic' if automatic else 'manual'}
 try:
  page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded');page.wait_for_selector('#openhandsEnabled',state='attached');page.select_option('#recognitionMode','words')
  if not automatic:page.uncheck('#automaticWords')
  page.click('#cameraButton')
  page.wait_for_function("document.querySelector('#webcam').videoWidth>0",timeout=60000)
  if not automatic:
   page.wait_for_timeout(4000)
   page.locator('#openhandsRecord').scroll_into_view_if_needed()
   page.wait_for_function("cycle=>{const t=document.querySelector('#webcam').currentTime%cycle;return t>=2.25&&t<=2.42}",arg=cycle,timeout=30000,polling=20)
  with page.expect_response(lambda response:response.url.endswith('/api/openhands/recognize') and response.request.method=='POST',timeout=120000) as response:
   if not automatic:page.click('#openhandsRecord')
  res=response.value;r.update(http=res.status,server=res.json())
  page.wait_for_timeout(700)
  r.update(diagnostics=page.evaluate('qa'),choices=page.locator('[data-combined-word]').all_text_contents(),status=page.locator('#openhandsStatus').inner_text(),current=page.locator('#interpreterWord').inner_text(),stream=page.locator('#webcam').evaluate('v=>v.srcObject.getVideoTracks()[0].getSettings()'))
  choice=page.locator('[data-combined-word="'+word.upper()+'"]')
  r['expectedOffered']=choice.count()==1
  if r['expectedOffered']:
   choice.click();page.locator('#interpreterAdd').click();r['log']=page.locator('#interpreterLog').inner_text();r['loggedOnce']=page.locator('#interpreterLog .word-log-complete span').all_text_contents().count(word.upper())==1
 except Exception as e:r['error']=str(e);r['status']=page.locator('#openhandsStatus').inner_text()
 r['errors']=errors;page.screenshot(path=str(OUT/(tag+'.png')),full_page=False);b.close()
 if camera.is_file():camera.unlink()
 return r

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
  if result.get('predicted')==word and page.locator('#beginnerAccept').is_enabled():
   page.click('#beginnerAccept');result['loggedOnce']=page.locator('#interpreterLog .word-log-complete span').all_text_contents().count(word)==1
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

def classify(row,result):
 if row['mode']=='beginner-ready':
  outcome=result.get('outcome','harness_error')
  if outcome=='correct' and not result.get('loggedOnce'):return 'log_failure'
  return outcome
 if result.get('errors'):return 'application_error'
 if result.get('error'):return 'harness_error'
 capture=next((x for x in result.get('diagnostics',{}).get('capture',[]) if x.get('startMediaTime') is not None),None)
 if not capture:return 'capture_failure'
 cap=cv2.VideoCapture(row['source']);duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS);cap.release()
 cycle=(round(duration*15)+120)/15
 start=4+round((capture['startMediaTime']-4)/cycle)*cycle
 result['timing']={'captureStart':capture['startMediaTime'],'captureEnd':capture['endMediaTime'],'sourceStart':start,'sourceEnd':start+duration,'toleranceSeconds':.2}
 full=capture['startMediaTime']<=start+.2 and capture['endMediaTime']>=start+duration-.2
 result['fullSourceCaptured']=full
 if not full:return 'capture_failure'
 if result.get('http',200)!=200 and not result.get('choices'):return 'processing_error'
 if result.get('expectedOffered'):
  if not result.get('loggedOnce'):return 'log_failure'
  return 'conflict_correct_available' if len(result.get('choices',[]))>1 else 'correct'
 return 'wrong' if result.get('choices') else 'rejected'

def report(manifest,rows,protocol):
 summary=dict(collections.Counter(r['outcome'] for r in rows))
 data={'url':'http://localhost:8000/#workspace','planned':len(manifest),'completed':len(rows),'complete':len(rows)==len(manifest),'summary':summary,'protocol':protocol,'rows':rows}
 for folder in [OUT,PUBLIC]:
  tmp=folder/'results.tmp';tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(folder/'results.json')
 table=''.join('<tr>'+''.join('<td>'+html.escape(str(r.get(k,'')))+'</td>' for k in ['word','mode','outcome','predictions'])+'</tr>' for r in rows)
 page='<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="30"><title>All enabled word test</title><style>body{font:16px system-ui;max-width:1200px;margin:40px auto;background:#0b140e;color:#e5f6ee}td,th{padding:10px;border-bottom:1px solid #345;text-align:left}</style><h1>All enabled words: live virtual-camera test</h1><p>'+str(len(rows))+'/'+str(len(manifest))+' completed. '+html.escape(json.dumps(summary))+'</p><p>Manual captures; actual models. Conflicts are not unambiguous passes. One existing reference per word, possible training overlap; not independent accuracy, automatic capture, or physical webcam verification. Separate Beginner mode is NOT part of the combined two-model workflow.</p><table><tr><th>Word</th><th>Mode</th><th>Outcome</th><th>Predictions</th></tr>'+table+'</table>'
 (ROOT/'all-enabled-word-results.html').write_text(page,encoding='utf-8')
 return data

def main():
 status=json.load(urllib.request.urlopen('http://localhost:8000/api/openhands/status'))
 old=candidates();combined={r['word']:dict(word=r['word'],source=r['source'],mode='combined') for r in old if r['mode']=='browser-expanded'}
 for word in status['labels']:
  combined[word]=dict(word=word,source=str(ROOT/status['videos'][word.lower()].lstrip('/')),mode='combined')
 manifest=sorted(list(combined.values())+[r for r in old if r['mode']=='beginner-ready'],key=lambda r:r['word'])
 pinned=['app.js','openhands-recognition.js','combined-word-results.js','motion-studio.js','models/openhands-passed.json','models/disabled-word-policy.json']
 hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in pinned}
 protocol={'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'capture':'Manual aligned 3-second combined capture / 4-second Beginner capture','camera':[640,480,15],'scope':'All enabled motion words, in their supported modes. Existing references, not independent accuracy or physical webcam verification. No prediction mocks, landmark injection, or expected labels sent to inference. Correct conflict choices are manual review, not model accuracy.','combinedCount':len(combined),'separateBeginnerCount':len(manifest)-len(combined),'hashes':hashes}
 existing=PUBLIC/'results.json'
 rows=json.loads(existing.read_text())['rows'] if existing.exists() else []
 done={r['word'] for r in rows}
 (PUBLIC/'manifest.json').write_text(json.dumps(manifest,indent=2))
 report(manifest,rows,protocol)
 with sync_playwright() as p:
  for row in manifest:
   if row['word'] in done:continue
   assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in hashes.items()),'Application changed during audit'
   try:
    result=run_case(p,row) if row['mode']=='beginner-ready' else combined_case(p,row)
    outcome=classify(row,result)
   except Exception as e:result={'error':str(e)};outcome='harness_error'
   predictions=result.get('choices') if row['mode']=='combined' else [result.get('predicted')]
   entry={'word':row['word'],'mode':row['mode'],'outcome':outcome,'predictions':predictions,'details':result}
   rows.append(entry);report(manifest,rows,protocol)
   print(json.dumps({'completed':len(rows),'planned':len(manifest),'word':row['word'],'outcome':outcome,'predictions':predictions}),flush=True)
 print('COMPLETE',json.dumps(report(manifest,rows,protocol)['summary']),flush=True)
if __name__=='__main__':main()
