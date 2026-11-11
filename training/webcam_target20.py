"""Exercise the real browser camera pipeline with Chromium's simulated webcam.

This is NOT an OBS/OS virtual camera or a physical-camera measurement.
No landmarks or predictions are injected. Chrome reads Y4M through getUserMedia;
the application performs its own browser tracking, API inference, and display.
"""
import argparse,json,subprocess,time,os,concurrent.futures as cf
from pathlib import Path
import cv2,imageio_ffmpeg
from playwright.sync_api import sync_playwright
from train_essential import ROOT

CACHE=ROOT.parent/'handspeak-training'
CHROME=r'C:\Program Files\Google\Chrome\Application\chrome.exe'

def make_camera(source,dest,scenario):
    cap=cv2.VideoCapture(source);fps=cap.get(cv2.CAP_PROP_FPS) or 30;duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps;cap.release()
    sign_duration={'slow':5.,'fast':3.}.get(scenario,4.)
    filters=[f'setpts={sign_duration/max(duration,.1):.6f}*PTS','scale=640:480:force_original_aspect_ratio=decrease','pad=640:480:(ow-iw)/2:(oh-ih)/2','setsar=1','fps=15']
    if scenario=='dim':filters+=['eq=brightness=-0.15:contrast=0.85']
    if scenario=='far':filters+=['scale=480:360','pad=640:480:(ow-iw)/2:(oh-ih)/2']
    if scenario=='left':filters+=['scale=512:384','pad=640:480:0:48']
    # A brief idle lead-in aligns with the app's countdown; source sign is not
    # classified directly by this test code.
    filters+=['tpad=start_duration=1.5:stop_duration=3:start_mode=clone:stop_mode=clone']
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',source,'-vf',','.join(filters),'-pix_fmt','yuv420p','-f','yuv4mpegpipe',str(dest)],check=True)

def run_case(p,row,scenario,index,mode):
    y4m=CACHE/f'camera-input-{scenario}-{index}.y4m';make_camera(row['file'],y4m,scenario)
    browser=p.chromium.launch_persistent_context(user_data_dir=str(CACHE/f'camera-browser-cache-{os.getpid()}'),executable_path=CHROME,headless=True,args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream',f'--use-file-for-fake-video-capture={y4m}','--autoplay-policy=no-user-gesture-required'])
    page=browser.new_page();page.set_default_timeout(30000);errors=[];page.on('pageerror',lambda e:errors.append(str(e)));responses=[];sent=[]
    console_errors=[];failed_requests=[]
    page.on('console',lambda m:console_errors.append(m.text) if m.type=='error' else None)
    page.on('requestfailed',lambda r:failed_requests.append(dict(url=r.url,error=r.failure)))
    page.add_init_script("window.cameraDiagnostics=[];document.addEventListener('handspeak:word-capture-diagnostics',e=>window.cameraDiagnostics.push(e.detail));")
    page.on('request',lambda r:sent.append(time.perf_counter()) if r.url.endswith('/api/beginner-asl') and r.method=='POST' else None)
    page.on('response',lambda r:responses.append(r) if r.url.endswith('/api/beginner-asl') and r.request.method=='POST' else None)
    result=dict(label=row['label'],scenario=scenario,source_sha256=row['sha256'],camera_type='Chromium simulated getUserMedia camera',correct=False)
    try:
        print('stage',row['label'],'loading',flush=True)
        page.goto('http://127.0.0.1:8000/#workspace',wait_until='domcontentloaded')
        page.wait_for_function("document.documentElement.dataset.handspeakReady==='true'",timeout=60000)
        page.select_option('#recognitionMode','words');page.uncheck('#automaticWords')
        # This preference is hidden by simple view; change the actual control
        # and dispatch its normal event without altering capture or inference.
        page.evaluate("()=>{const t=document.querySelector('#faceTrackingToggle');t.checked=false;t.dispatchEvent(new Event('change',{bubbles:true}));}")
        page.wait_for_function(f"!document.querySelector('#beginnerVocabMode option[value={mode}]').disabled")
        # Optional modules finish status loading asynchronously. Reassert the
        # user's selected mode after initialization, using the real UI event.
        page.select_option('#recognitionMode','words')
        page.wait_for_selector('#wordRecognitionControls',state='visible')
        page.select_option('#beginnerVocabMode',mode);page.check('#beginnerConsent')
        print('stage',row['label'],'warming tracker',flush=True)
        # First capture initializes browser WASM/graph resources. Its prediction
        # is discarded; the second fresh stream is the measured camera trial.
        page.click('#beginnerRecord')
        page.wait_for_function("/Possible match|No confident|No prediction|Not enough|Could not|timed out|Tracking stopped/.test(document.querySelector('#beginnerStatus').textContent)",timeout=120000)
        if page.locator('#cameraButton').inner_text().find('Stop camera')>=0:page.click('#cameraButton')
        page.click('#beginnerCancel');responses.clear();sent.clear()
        print('stage',row['label'],'measured capture',flush=True)
        start=time.perf_counter();page.click('#beginnerRecord')
        page.wait_for_function("/Possible match|No confident|No prediction|Not enough|Could not|timed out|Tracking stopped/.test(document.querySelector('#beginnerStatus').textContent)",timeout=45000)
        result['capture_to_display_ms']=(time.perf_counter()-start)*1000
        result['status']=page.locator('#beginnerStatus').inner_text();result['display']=page.locator('#liveLetter').inner_text()
        result['camera_stream']=page.evaluate("(()=>{const t=document.querySelector('#webcam').srcObject?.getVideoTracks()[0];return t?{label:t.label,settings:t.getSettings(),readyState:t.readyState}:null})()")
        if responses:
            data=responses[-1].json();prediction=(data.get('predictions') or [{}])[0].get('label');result['predicted']=prediction
            result['frames']=data.get('frames');result['vocabulary']=data.get('vocabulary');result['correct']=(prediction is None and data.get('vocabulary')=='target20') if row['label']=='UNKNOWN' else prediction==row['label']
            result['api_to_display_ms']=(time.perf_counter()-sent[-1])*1000 if sent else None
            result['display_matches_prediction']=result['display']==prediction if prediction else True
            result['correct']=bool(result['correct'] and result['display_matches_prediction'] and not errors and result['camera_stream'] and result['camera_stream']['readyState']=='live')
        else:result['error']='No recognition API response; capture failed'
        result['page_errors']=errors
        result['capture_diagnostics']=page.evaluate('window.cameraDiagnostics')
        if index==0:page.screenshot(path=str(CACHE/f'camera-target20-{scenario}.png'),full_page=True)
    except Exception as error:
        result['error']=str(error)
        result['console_errors']=console_errors[-10:];result['failed_requests']=failed_requests[-10:]
        try:result['status']=page.locator('#beginnerStatus').inner_text(timeout=2000);result['page_errors']=errors
        except Exception:pass
    finally:browser.close()
    print('camera',row['label'],scenario,result.get('predicted'),result.get('error',''),flush=True)
    return result

def worker(args):
    with sync_playwright() as p:return run_case(p,*args)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--mode',default='target20');parser.add_argument('--limit',type=int,default=20);parser.add_argument('--variations',action='store_true');parser.add_argument('--unknown',action='store_true');parser.add_argument('--workers',type=int,default=2);parser.add_argument('--retry-errors',action='store_true');args=parser.parse_args()
    manifest=json.loads((CACHE/'target20-manifest.json').read_text());selected=[]
    for label in manifest['labels'][:-1] if not args.unknown else []:
        rows=[r for r in manifest['samples'] if r['split']=='test' and r['label']==label and (CACHE/'landmarks-v1'/(r['sha256']+'.npz')).exists()]
        if rows:selected.append(rows[0])
    if args.unknown:
        glosses=set()
        for row in manifest['samples']:
            if row['split']=='test' and row['label']=='UNKNOWN' and row['gloss'] not in glosses and (CACHE/'landmarks-v1'/(row['sha256']+'.npz')).exists():selected.append(row);glosses.add(row['gloss'])
    results=[];path=CACHE/('target20-webcam-unknown.json' if args.unknown else 'target20-webcam-variations.json' if args.variations else 'target20-webcam.json')
    jobs=[(row,['slow','fast','dim','far','left'][index%5] if args.variations else 'normal',index,args.mode) for index,row in enumerate(selected[:args.limit])]
    if args.retry_errors:
        original=json.loads(path.read_text())['results']
        failed={result['source_sha256'] for result in original if result.get('error')}
        jobs=[job for job in jobs if job[0]['sha256'] in failed]
        path=path.with_name(path.stem+'-retry.json')
    with cf.ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(worker,jobs):
            results.append(result);path.write_text(json.dumps(dict(physical_camera_available=False,obs_available=False,os_virtual_camera_tested=False,simulated_camera=True,concurrent_trials=args.workers,results=results),indent=2))
if __name__=='__main__':main()
