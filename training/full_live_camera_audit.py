"""Frozen 26-letter + 64-motion-word live website audit; no inference mocks."""
import json,sys,time,math,hashlib,datetime,collections,html,re,os,subprocess,urllib.request,string
from pathlib import Path
import cv2,imageio_ffmpeg
from playwright.sync_api import sync_playwright
from no_obs_virtual_camera import candidates
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'handspeak-training/full-camera-audit-v1';OUT.mkdir(exist_ok=True)
PUBLIC=ROOT/'website-word-test/full-camera-audit-v1';PUBLIC.mkdir(exist_ok=True)
CHROME=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
TOL=.2

def checksum(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def reveal(page,selector):page.locator(selector).evaluate("e=>{for(let p=e.parentElement;p;p=p.parentElement)if(p.tagName==='DETAILS')p.open=true;}")
def camera_file(row):
 work=OUT/row['id'];work.mkdir(exist_ok=True);camera=work/'camera.y4m'
 if row['kind']=='letter-static':
  source=cv2.imread(row['source']);assert source is not None
  h,w=source.shape[:2];small=cv2.resize(source,(round(w*min(640/w,480/h)),round(h*min(640/w,480/h))))
  base=__import__('numpy').full((480,640,3),128,dtype='uint8');y=(480-small.shape[0])//2;x=(640-small.shape[1])//2;base[y:y+small.shape[0],x:x+small.shape[1]]=small
  import numpy as np
  with open(camera,'wb') as f:
   f.write(b'YUV4MPEG2 W640 H480 F15:1 Ip A1:1 C420jpeg\n')
   for index in range(22*15):
    frame=base if 4*15<=index<18*15 else np.full((480,640,3),128,np.uint8)
    f.write(b'FRAME\n');f.write(cv2.cvtColor(frame,cv2.COLOR_BGR2YUV_I420).tobytes())
  return camera,22.,14.
 cap=cv2.VideoCapture(row['source']);fps=cap.get(cv2.CAP_PROP_FPS);duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps;cap.release()
 filters='scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2:color=gray,setsar=1,fps=15,tpad=start_duration=4:start_mode=add:stop_duration=4:stop_mode=add:color=gray,format=yuv420p'
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',row['source'],'-an','-vf',filters,'-f','yuv4mpegpipe',str(camera)],check=True)
 cap=cv2.VideoCapture(str(camera));cycle=cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS);cap.release()
 return camera,cycle,duration

def launch(p,camera,profile=None):
 args=['--use-fake-device-for-media-stream=fps=15','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture='+str(camera)]
 browser=p.chromium.launch(executable_path=CHROME,headless=True,args=args)
 return browser,browser.new_page(viewport={'width':1440,'height':1000})

def letter_case(p,row):
 camera,cycle,duration=camera_file(row);browser,page=launch(p,camera);errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)));page.set_default_timeout(30000)
 page.add_init_script("window.letterQA={commits:[],trace:[]};document.addEventListener('handspeak:letter-committed',e=>letterQA.commits.push({...e.detail,mediaTime:document.querySelector('#webcam')?.currentTime}));setInterval(()=>{const v=document.querySelector('#webcam');if(!v?.srcObject)return;letterQA.trace.push({mediaTime:v.currentTime,hands:document.querySelector('#trackingHands').textContent,letter:document.querySelector('#liveResult').hidden?null:document.querySelector('#liveLetter').textContent,confidence:document.querySelector('#liveConfidence').textContent,feedback:document.querySelector('#recognitionFeedback').textContent});},250);")
 result={'sourceSha256':checksum(row['source']),'kind':row['kind']}
 try:
  page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded');page.wait_for_selector('#openhandsEnabled',state='attached');page.select_option('#recognitionMode','letters');page.click('#cameraButton')
  page.wait_for_function("document.querySelector('#webcam').videoWidth>0&&document.querySelector('#webcam').srcObject?.getVideoTracks()[0]?.readyState==='live'",timeout=60000)
  result['stream']=page.locator('#webcam').evaluate("v=>({label:v.srcObject.getVideoTracks()[0].label,settings:v.srcObject.getVideoTracks()[0].getSettings()})")
  target=22 if row['kind']=='letter-static' else 2*cycle
  page.wait_for_function('target=>document.querySelector("#webcam").currentTime>=target',arg=target,timeout=int((target+15)*1000))
  result.update(page.evaluate('letterQA'));result['draft']=page.locator('#messageText').inner_text();result['visibleResult']=page.locator('#liveLetter').inner_text();result['feedback']=page.locator('#recognitionFeedback').inner_text()
  diagnostic=page.locator('#cameraDiagnostics').inner_text()
  try:result['diagnostics']=json.loads(diagnostic)
  except:result['diagnosticsText']=diagnostic
  committed=[c['letter'] for c in result['commits']];wrong=[c for c in committed if c!=row['label']]
  result['outcome']='application_error' if errors else 'wrong_or_mixed_commit' if wrong else 'correct' if row['label'] in committed else 'unstable_not_committed' if any(x['letter']==row['label'] for x in result['trace']) else 'wrong_prediction_uncommitted' if any(x['letter'] and x['letter']!=row['label'] for x in result['trace']) else 'no_hand_capture' if not any(not x['hands'].startswith('0') for x in result['trace']) else 'rejected'
  page.screenshot(path=str(OUT/row['id']/'result.png'))
 except Exception as e:result.update(outcome='harness_or_camera_error',error=str(e))
 finally:
  result['pageErrors']=errors;browser.close()
  if camera.resolve().parent==(OUT/row['id']).resolve():camera.unlink(missing_ok=True)
 return result

def automatic_case(p,row):
 camera,cycle,duration=camera_file(row);browser,page=launch(p,camera);errors=[];requests=[];responses=[]
 page.set_default_timeout(30000);page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:requests.append({'at':time.monotonic()}) if r.method=='POST' and r.url.endswith('/api/openhands/recognize') else None)
 page.on('response',lambda r:responses.append(r) if r.request.method=='POST' and r.url.endswith('/api/openhands/recognize') else None)
 page.add_init_script("window.wordQA={captures:[],boundaries:[],browser:[]};document.addEventListener('handspeak:word-capture-diagnostics',e=>wordQA.captures.push(e.detail));document.addEventListener('handspeak:word-boundary',e=>wordQA.boundaries.push(e.detail));document.addEventListener('handspeak:combined-browser-result',e=>wordQA.browser.push(e.detail));")
 result={'sourceSha256':checksum(row['source']),'captureMode':'automatic','recordButtonClicked':False}
 try:
  page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded');page.wait_for_selector('#openhandsEnabled',state='attached');page.select_option('#recognitionMode','words');assert page.locator('#automaticWords').is_checked();page.click('#cameraButton')
  page.wait_for_function("document.querySelector('#webcam').videoWidth>0&&document.querySelector('#webcam').srcObject?.getVideoTracks()[0]?.readyState==='live'",timeout=60000)
  result['stream']=page.locator('#webcam').evaluate("v=>({label:v.srcObject.getVideoTracks()[0].label,settings:v.srcObject.getVideoTracks()[0].getSettings()})")
  now=page.locator('#webcam').evaluate('v=>v.currentTime');first=4+math.floor(now/cycle)*cycle
  if first<now+.5:first+=cycle
  media_deadline=first+cycle+duration+4
  wall=time.monotonic()
  while not responses:
   page.wait_for_timeout(200)
   if requests and time.monotonic()-requests[0]['at']>105:break
   if not requests and page.locator('#webcam').evaluate('v=>v.currentTime')>=media_deadline:break
   if time.monotonic()-wall>max(120,media_deadline+10):break
   if not page.locator('#webcam').evaluate('v=>!!v.srcObject'):break
  page.wait_for_timeout(500);result.update(page.evaluate('wordQA'))
  result['requestCount']=len(requests);result['status']=page.locator('#openhandsStatus').inner_text();result['hint']=page.locator('#wordHandStatus').inner_text();result['choices']=page.locator('[data-combined-word]').all_text_contents()
  if responses:result.update(http=responses[0].status,response=responses[0].json())
  capture=next((c for c in result.get('captures',[]) if c.get('capture')=='openhands-video'),None)
  full=False
  if capture:
   start=4+round((capture['startMediaTime']-4)/cycle)*cycle
   full=capture['startMediaTime']<=start+TOL and capture['endMediaTime']>=start+duration-TOL
   result['sourceWindow']={'start':start,'end':start+duration};result['captureFullReference']=full;result['sourceCycleIndex']=round((start-4)/cycle)
  expected=page.locator('[data-combined-word="'+row['label']+'"]');result['expectedOffered']=expected.count()==1
  if result['expectedOffered']:
   expected.click();page.locator('#interpreterAdd').click();result['log']=page.locator('#interpreterLog').inner_text();result['loggedOnce']=page.locator('#interpreterLog .word-log-complete span').all_text_contents().count(row['label'])==1
  if errors:outcome='application_error'
  elif not capture:outcome='no_automatic_capture'
  elif not full:outcome='incomplete_capture'
  elif requests and not responses:outcome='processing_timeout'
  elif not responses:outcome='submission_failure'
  elif result['expectedOffered']:outcome='log_failure' if not result.get('loggedOnce') else 'conflict_correct_available' if len(result['choices'])>1 else 'correct'
  elif result['choices']:outcome='wrong_prediction'
  elif result.get('http',200)!=200:outcome='processing_failure'
  else:outcome='rejected'
  result['outcome']=outcome;page.screenshot(path=str(OUT/row['id']/'result.png'))
 except Exception as e:result.update(outcome='harness_or_camera_error',error=str(e))
 finally:
  result['pageErrors']=errors;browser.close()
  if camera.resolve().parent==(OUT/row['id']).resolve():camera.unlink(missing_ok=True)
 return result

def beginner_case(p,row):
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
  page.select_option('#recognitionMode','words');reveal(page,'#automaticWords');page.uncheck('#automaticWords')
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
   events=[e for e in result['events']['matches'] if e['detail']['word'] not in ['â€”','No reliable match','Not enough frames','Hands not tracked','Capture incomplete']]
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


def save(manifest,rows,protocol):
 counts={kind:dict(collections.Counter(r['outcome'] for r in rows if r['group']==kind)) for kind in ['letters','automatic_words','manual_beginner']}
 data={'planned':len(manifest),'completed':len(rows),'complete':len(rows)==len(manifest),'summary':counts,'protocol':protocol,'rows':rows}
 for folder in [PUBLIC,OUT]:
  tmp=folder/'results.tmp';tmp.write_text(json.dumps(data,indent=2));tmp.replace(folder/'results.json')
 table=''.join('<tr>'+''.join('<td>'+html.escape(str(r.get(k,'')))+'</td>' for k in ['label','group','outcome','prediction'])+'</tr>' for r in rows)
 body='<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="30"><title>Full live camera audit</title><style>body{font:16px/1.6 system-ui;max-width:1200px;margin:35px auto;background:#0b140e;color:#def5e8}td,th{padding:10px;text-align:left;border-bottom:1px solid #345}a{color:#00d9a2}</style><a href="/#workspace">Back to Hand Speak</a><h1>Full live virtual-camera audit</h1><p>'+str(len(rows))+'/'+str(len(manifest))+' completed</p><pre>'+html.escape(json.dumps(counts,indent=2))+'</pre><p>24 held-image letter checks and two natural-speed J/Z motion clips. 47 automatic combined words; 17 separate manual Beginner words. Existing references, not independent signer/webcam accuracy. Conflicts and incomplete captures are not clear passes. No app or model changes during this run.</p><table><tr><th>Label</th><th>Mode</th><th>Outcome</th><th>Prediction</th></tr>'+table+'</table>'
 (ROOT/'full-camera-audit.html').write_text(body,encoding='utf-8');return data

def main():
 status=json.load(urllib.request.urlopen('http://localhost:8000/api/openhands/status'));beginner_status=json.load(urllib.request.urlopen('http://localhost:8000/api/beginner-asl/status'))
 manifest=[]
 for letter in string.ascii_uppercase:
  kind='letter-motion' if letter in 'JZ' else 'letter-static'
  source=Path(os.environ['TEMP'])/'handspeak-letter-references'/f'{letter.lower()}.mp4' if letter in 'JZ' else ROOT/'media/signspeak-alphabet'/f'{letter}.jpg'
  manifest.append(dict(id='letter-'+letter,label=letter,kind=kind,group='letters',source=str(source)))
 old=candidates();word_sources={r['word']:r for r in old}
 combined={r['word']:r['source'] for r in old if r['mode']=='browser-expanded'}
 for word in status['labels']:combined[word]=str(ROOT/status['videos'][word.lower()].lstrip('/'))
 for label,source in sorted(combined.items()):manifest.append(dict(id='word-'+label,label=label,word=label,kind='word',group='automatic_words',mode='combined',source=source))
 for label in beginner_status['labels']:
  source=word_sources.get(label,{}).get('source',str(ROOT/'media/signs'/f'{label.lower()}.mp4'))
  manifest.append(dict(id='beginner-'+label,label=label,word=label,kind='word',group='manual_beginner',mode='beginner-ready',source=source))
 missing=[r['id'] for r in manifest if not Path(r['source']).is_file()];assert not missing,missing
 files=['app.js','index.html','letter-camera.js','letter-detection-worker.js','signspeak-model.js','models/signspeak/asl.onnx','openhands-recognition.js','automatic-word-capture.js','word-boundaries.js','scene-motion.js','temporal-camera.js','hand-detection-worker.js','motion-studio.js','combined-word-results.js','video_capture_validation.py','training/openhands_live_infer.py','openhands-test/runtime.py','beginner-recognition.js','models/openhands-passed.json','models/disabled-word-policy.json','third_party/OpenHands-source/api/lstm_model_v7.pth']
 hashes={name:checksum(ROOT/name) for name in files}
 protocol={'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'camera':[640,480,15],'model':'Actual live SignSpeak alphabet, combined Browser + OpenHands, and separate Beginner recognizer','letterScope':'24 static SignSpeak sample images, 14-second holds; J/Z natural-speed uncropped cached motion videos, no still substitutions. Possible training overlap.','automaticScope':'Up to two upcoming full source cycles plus endpoint grace, actual automatic capture; no Record click. First submitted clip scored even if wrong. Correct conflict choices are explicit human-review simulation, not automatic top-1 accuracy.','manualScope':'Separate Beginner manual 5.5-second recording; warm-up excluded; no expected label sent to endpoint.','hashes':hashes,'sourceHashes':{r['id']:checksum(r['source']) for r in manifest}}
 existing=PUBLIC/'results.json';rows=json.loads(existing.read_text())['rows'] if existing.exists() else [];done={r['id'] for r in rows}
 (PUBLIC/'manifest.json').write_text(json.dumps(manifest,indent=2));save(manifest,rows,protocol)
 # Start with one letter and one Beginner mode as harness smoke checks, then the rest.
 ordered=[r for key in ['letter-A','beginner-BATHROOM'] for r in manifest if r['id']==key]+[r for r in manifest if r['id'] not in ['letter-A','beginner-BATHROOM']]
 with sync_playwright() as p:
  for row in ordered:
   if row['id'] in done:continue
   assert all(checksum(ROOT/name)==value for name,value in hashes.items()),'Application/model changed during audit'
   try:
    if row['group']=='letters':details=letter_case(p,row)
    elif row['group']=='automatic_words':details=automatic_case(p,row)
    else:
     details=beginner_case(p,row);outcome=details.get('outcome','harness_or_camera_error')
     if outcome=='correct' and not details.get('loggedOnce'):outcome='log_failure'
     details['outcome']=outcome
    outcome=details['outcome']
   except Exception as e:details={'error':str(e)};outcome='harness_or_camera_error'
   prediction=details.get('choices',details.get('predicted', [x.get('letter') for x in details.get('commits',[])]))
   entry={k:row[k] for k in ['id','label','kind','group']};entry.update(outcome=outcome,prediction=prediction,details=details);rows.append(entry);save(manifest,rows,protocol)
   print(json.dumps({'completed':len(rows),'planned':len(manifest),'id':row['id'],'outcome':outcome,'prediction':prediction}),flush=True)
 print('COMPLETE',json.dumps(save(manifest,rows,protocol)['summary']),flush=True)
if __name__=='__main__':main()
