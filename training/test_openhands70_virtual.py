"""Frozen 70-word live website test using real MediaRecorder + file-backed camera.
Expected labels only score results; never supplied to the recognition endpoint.
"""
import argparse,collections,csv,datetime,hashlib,html,json,re,subprocess,time
from pathlib import Path
import cv2,imageio_ffmpeg
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'handspeak-training/openhands70-virtual-v1'
CHROME=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
TOLERANCE=.2

def checksum(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def case(p,row):
 word=row['expected'].upper();source=ROOT/row['file'];work=OUT/word.lower();work.mkdir(exist_ok=True)
 camera=work/'camera.y4m'
 result=dict(word=word,source=str(source),source_sha256=checksum(source),outcome='capture_failure',predicted=None,timing_tolerance_seconds=TOLERANCE)
 cap=cv2.VideoCapture(str(source));duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS);cap.release()
 filters='scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2:color=gray,setsar=1,fps=15,tpad=start_duration=4:start_mode=add:stop_duration=4:stop_mode=add:color=gray,format=yuv420p'
 subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',str(source),'-an','-vf',filters,'-pix_fmt','yuv420p','-f','yuv4mpegpipe',str(camera)],check=True)
 cap=cv2.VideoCapture(str(camera));cycle=cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS);cap.release()
 result.update(source_duration=duration,cycle_duration=cycle)
 context=p.chromium.launch_persistent_context(str(OUT/'browser-profile'),executable_path=CHROME,headless=True,permissions=['camera'],viewport={'width':1440,'height':1000},
    args=['--use-fake-device-for-media-stream=fps=15','--use-file-for-fake-video-capture='+str(camera)])
 page=context.new_page();page.set_default_timeout(30000);errors=[];requests=[];responses=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('request',lambda r:requests.append(r) if r.url.endswith('/api/openhands/recognize') and r.method=='POST' else None)
 page.on('response',lambda r:responses.append(r) if r.url.endswith('/api/openhands/recognize') and r.request.method=='POST' else None)
 page.add_init_script("window.virtualQA=[];document.addEventListener('handspeak:word-capture-diagnostics',e=>{if(e.detail.capture==='openhands-video')virtualQA.push(e.detail);});")
 try:
  page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded')
  page.wait_for_function("document.documentElement.dataset.handspeakReady==='true'",timeout=60000)
  page.select_option('#recognitionMode','words')
  page.wait_for_function("document.querySelector('#openhandsStatus').textContent.includes('ready')",timeout=30000)
  page.check('#openhandsEnabled');page.check('#openhandsConsent');page.click('#cameraButton')
  page.wait_for_function("document.querySelector('#webcam').videoWidth>0&&document.querySelector('#webcam').srcObject?.getVideoTracks()[0]?.readyState==='live'",timeout=30000)
  result['stream']=page.locator('#webcam').evaluate("v=>({width:v.videoWidth,height:v.videoHeight,label:v.srcObject.getVideoTracks()[0].label,settings:v.srcObject.getVideoTracks()[0].getSettings()})")
  result['fake_camera_verified']=bool(result['stream']['width']==640 and result['stream']['height']==480 and result['stream']['label'].endswith('camera.y4m') and result['stream']['settings'].get('frameRate')==15)
  # Bring control into view BEFORE timing alignment, so scrolling cannot shift it.
  page.locator('#openhandsRecord').scroll_into_view_if_needed()
  page.wait_for_function("cycle=>{const t=document.querySelector('#webcam').currentTime%cycle;return t>=2.3&&t<=2.43}",arg=cycle,timeout=int((cycle+3)*1000),polling=20)
  start_clock=page.locator('#webcam').evaluate('v=>v.currentTime');result['record_click_media_time']=start_clock
  start=time.perf_counter()
  with page.expect_response(lambda r:r.url.endswith('/api/openhands/recognize') and r.request.method=='POST',timeout=110000) as pending:
   page.click('#openhandsRecord')
  response=pending.value;data=response.json();result.update(http=response.status,response=data,predicted=data.get('label'),elapsed_seconds=round(time.perf_counter()-start,3))
  page.wait_for_function("!document.querySelector('#openhandsCancel').disabled===false",timeout=10000)
  result['status']=page.locator('#openhandsStatus').inner_text();result['display']=page.locator('#liveLetter').inner_text()
  result['capture_diagnostics']=page.evaluate('virtualQA')
  result['request_count']=len(requests);result['response_count']=len(responses)
  source_start=int(start_clock//cycle)*cycle+4;source_end=source_start+duration
  d=result['capture_diagnostics'][-1] if result['capture_diagnostics'] else {}
  result['source_window']=dict(start=source_start,end=source_end)
  full=bool(d.get('startMediaTime') is not None and d['startMediaTime']<=source_start+TOLERANCE and d.get('endMediaTime',0)>=source_end-TOLERANCE)
  result['full_source_captured']=full
  if errors:result['outcome']='application_error'
  elif not result['fake_camera_verified'] or not full:result['outcome']='capture_failure'
  elif response.status!=200:result['outcome']='model_error'
  elif len(requests)!=1 or len(responses)!=1:result['outcome']='application_error'
  elif data.get('label'):
   result['outcome']='correct' if data['label']==word and result['display']==word else 'wrong'
  else:result['outcome']='rejected'
  if data.get('label') and not page.locator('#openhandsAccept').is_disabled():
   page.click('#openhandsAccept');result['reviewed_word_log']=page.locator('#interpreterLog').inner_text()
   result['reviewed_add_worked']=data['label'] in result['reviewed_word_log']
   if not result['reviewed_add_worked'] and result['outcome']=='correct':result['outcome']='application_error'
  page.locator('#cameraStage').screenshot(path=str(work/'camera.png'))
  page.locator('#openhandsWords').screenshot(path=str(work/'result.png'))
 except Exception as e:
  result['error']=str(e)
  try:
   result['status']=page.locator('#openhandsStatus').inner_text();result['capture_diagnostics']=page.evaluate('virtualQA');page.screenshot(path=str(work/'failure.png'))
  except Exception:pass
 finally:
  result['page_errors']=errors;context.close()
  if camera.resolve().is_relative_to(OUT.resolve()):camera.unlink(missing_ok=True)
 return result

def write_report(rows,protocol):
 summary=dict(collections.Counter(r['outcome'] for r in rows))
 report=dict(scope='Actual website Playwright -> Chromium file-backed getUserMedia -> 3-second MediaRecorder -> local OpenHands endpoint -> UI/reviewed word log. One existing reference per word; not physical-webcam or independent generalization accuracy.',planned=70,completed=len(rows),complete=len(rows)==70,summary=summary,protocol=protocol,rows=rows)
 file=OUT/'results.json';temp=file.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2),encoding='utf-8');temp.replace(file)
 public=dict(scope=report['scope'],planned=70,completed=len(rows),complete=report['complete'],summary=summary,rows=[{k:r.get(k) for k in ['word','outcome','predicted','status','full_source_captured','reviewed_add_worked']} for r in rows])
 (ROOT/'website-word-test/openhands70-virtual-results.json').write_text(json.dumps(public,indent=2),encoding='utf-8')
 body=''.join('<tr>'+''.join(f'<td>{html.escape(str(r.get(k,"")))}</td>' for k in ['word','predicted','outcome'])+'</tr>' for r in rows)
 page=f'<!doctype html><html><meta charset="utf-8"><meta http-equiv="refresh" content="30"><title>OpenHands70 camera results</title><style>body{{background:#0b140e;color:#e4f6eb;font:15px/1.6 system-ui;max-width:1100px;margin:32px auto;padding:0 20px}}a{{color:#00e9a5}}td,th{{padding:10px;text-align:left;border-bottom:1px solid #345}}</style><a href="/#workspace">Back to HandSpeak</a><h1>OpenHands 70-word virtual-camera test</h1><p>{len(rows)}/70 completed. {html.escape(json.dumps(summary))}</p><p>{html.escape(report["scope"])}</p><p>A match counts only if the actual recording timestamps cover the full reference interval within 0.2 seconds and the label appears correctly in the UI. Long clips may not fit the website’s existing 3-second recording window; they count as capture failures, not verified passes. No weights, thresholds, or enabled labels changed.</p><table><tr><th>Expected</th><th>Predicted</th><th>Outcome</th></tr>{body}</table></html>'
 (ROOT/'openhands70-virtual-results.html').write_text(page,encoding='utf-8')
 return report

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--limit',type=int,default=70);args=parser.parse_args();OUT.mkdir(exist_ok=True)
 metadata=json.loads((ROOT/'models/openhands-passed.json').read_text());allowed=set(metadata['labels'])
 source_report=json.loads((ROOT/'openhands-test/all100-results.json').read_text())
 sources=sorted([r for r in source_report['rows'] if r['correct'] and r['expected'].upper() in allowed],key=lambda r:r['expected'])
 assert len(sources)==70
 pinned=['models/openhands-passed.json','openhands_live.py','openhands-recognition.js','openhands-test/runtime.py','training/openhands_live_infer.py','third_party/OpenHands-source/api/lstm_model_v7.pth']
 protocol=dict(started_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),source_count=70,source_speed='unchanged',blank_lead_seconds=4,blank_tail_seconds=4,camera=[640,480,15],recording_seconds=3,source_timing_tolerance_seconds=.2,independent_attempts_per_word=1,source_training_overlap='not established; dictionary references may overlap training',hashes={name:checksum(ROOT/name) for name in pinned})
 output=OUT/'results.json';rows=json.loads(output.read_text())['rows'] if output.exists() else []
 if output.exists():
  protocol=json.loads(output.read_text())['protocol']
  assert protocol['hashes']=={name:checksum(ROOT/name) for name in pinned},'Model or adapter changed during run; use a new versioned output directory.'
 done={r['word'] for r in rows};write_report(rows,protocol)
 with sync_playwright() as p:
  for row in sources[:args.limit]:
   if row['expected'].upper() in done:continue
   try:result=case(p,row)
   except Exception as e:result=dict(word=row['expected'].upper(),predicted=None,outcome='capture_failure',error=str(e))
   rows.append(result);write_report(rows,protocol)
   print(json.dumps({k:result.get(k) for k in ['word','predicted','outcome','status','error']}),flush=True)
 assert protocol['hashes']=={name:checksum(ROOT/name) for name in pinned}
 with (OUT/'results.csv').open('w',newline='',encoding='utf-8') as f:
  keys=['word','predicted','outcome','full_source_captured','reviewed_add_worked','status'];w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows({k:r.get(k) for k in keys} for r in rows)
 print(json.dumps(dict(completed=len(rows),summary=dict(collections.Counter(r['outcome'] for r in rows)))),flush=True)
if __name__=='__main__':main()
