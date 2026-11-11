"""Actual Chromium getUserMedia -> HandSpeak UI -> trackers -> Python QA runner.

Y4M files are virtual camera devices, NOT video elements substituted for webcam.
Never inject landmarks, model inputs, predictions, or API responses. Retain every
measured failure. Warm-up replays are recorded but not independent attempts.
All source videos, Y4M streams and detailed logs remain in the private cache.
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import shutil
import time
import urllib.request
from pathlib import Path

import cv2
import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT.parent/'handspeak-training'
CHROME=r'C:\Program Files\Google\Chrome\Application\chrome.exe'
TERMINAL="/Possible match|No confident|No prediction|Not enough|Capture quality insufficient|Could not|timed out|Tracking stopped|Unknown sign|Shoulders|visible-hand|recording window|incomplete|complete, uninterrupted|timestamps|Camera did not start|Recording timed out/.test(document.querySelector('#beginnerStatus').textContent)"


def associated_response(requests, responses):
    matches=[response for response in responses if response.request in requests]
    if len(requests)>1 or len(matches)>1:
        raise RuntimeError('Ambiguous duplicate capture requests')
    return matches[0] if matches else None


def blank_control_verified(samples):
    # Only aggregate contrast and sample count leave the browser.
    return len(samples)>=4 and all(0<=contrast<=3 for contrast in samples)


def assess_outcome(result):
    """Independent capture, encoder, and model outcomes; no rejection credit on failure."""
    data=result.get('backend_response') or {}
    state=data.get('state')
    pred=result.get('predicted')
    capture_ok=bool(result.get('camera_configuration_ok') and not result.get('page_errors') and
                    not result.get('error') and result.get('full_source_window_captured'))
    status=(result.get('status') or '').lower()
    if result['scenario']=='no-hands' and result.get('blank_control_verified') is False:
        capture='capture_failure'
    elif state=='tracking_failure' or 'not enough tracked frames' in status or 'capture quality insufficient' in status:
        capture='insufficient_tracking'
    elif not capture_ok or result.get('http_status')!=200 or state=='incomplete':
        capture='capture_failure'
    else:
        capture='verified'
    encoder=data.get('experimentalEncoder',{}).get('state','not_observed')
    model='not_scored'
    if capture=='verified' and result.get('display_matches_prediction',True) and result.get('confidence_contract_ok',True):
        if state=='recognized' and pred:
            model='correct' if result['scenario']=='normal' and result['label']==pred else 'incorrect'
        elif state in ('unknown','uncertain') and not pred:
            model='abstention'
    return dict(capture_outcome=capture,encoder_outcome=encoder,v3_outcome=model,
                unknown_rejected=result['label']=='UNKNOWN' and result['scenario']=='normal' and model=='abstention')


def camera_file(row,path,scenario,duration_limit=None):
    if scenario=='no-hands':
        command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-f','lavfi','-i','color=c=gray:s=640x480:r=15:d=15']
        filters=[]
    else:
        cap=cv2.VideoCapture(row['file']);fps=cap.get(cv2.CAP_PROP_FPS) or 30;duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/fps;cap.release()
        command=[imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',row['file']]
        filters=[]
        if scenario=='incomplete':filters += [f'trim=end={max(.15,duration*.35):.6f}','setpts=PTS-STARTPTS'];duration=max(.15,duration*.35)
        filters += [f'setpts={3/max(duration,.1):.6f}*PTS','scale=640:480:force_original_aspect_ratio=decrease','pad=640:480:(ow-iw)/2:(oh-ih)/2','setsar=1']
        if scenario=='low-quality':filters += ['scale=80:60','scale=640:480:flags=neighbor','boxblur=8:2','eq=brightness=-0.2:contrast=0.5']
        if scenario=='missing-hands':filters += ['drawbox=x=0:y=190:w=640:h=290:color=gray:t=fill']
        if scenario=='dropped-frames':filters += ['fps=1']
        filters += ['fps=15',f"tpad=start_duration={4.5 if scenario=='delayed' else 2}:stop_duration=9:start_mode=clone:stop_mode=clone"]
    if filters:command += ['-vf',','.join(filters)]
    if duration_limit:command += ['-t',str(duration_limit)]
    command += ['-pix_fmt','yuv420p','-f','yuv4mpegpipe',str(path)]
    subprocess.run(command,check=True)


def playlist_group(group):
    """One camera stream with predeclared source slots; no stream injection/seek.

    The real getUserMedia device reads the Y4M playlist continuously. Media time
    cues recording, while HandSpeak itself extracts and submits all landmarks.
    """
    jobs,group_index=group
    if not jobs:return []
    options=jobs[0][3];work=Path(options['output'])/f'playlist-{group_index}';work.mkdir(parents=True,exist_ok=True)
    temporary=work/'segment.y4m';playlist=work/'camera.y4m';preamble=60;slot=12
    first=jobs[0][0]
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',first['file'],
                    '-vf','trim=end_frame=1,setpts=PTS-STARTPTS,scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=15,tpad=stop_duration=61:stop_mode=clone',
                    '-t',str(preamble),'-pix_fmt','yuv420p','-f','yuv4mpegpipe',str(temporary)],check=True)
    with playlist.open('wb') as target:
        with temporary.open('rb') as source:shutil.copyfileobj(source,target)
        for row,scenario,index,_ in jobs:
            camera_file(row,temporary,scenario,duration_limit=slot)
            with temporary.open('rb') as source:
                header=source.readline();assert b'W640 H480 F15:1' in header
                size=temporary.stat().st_size-len(header)
                assert size==(640*480*3//2+6)*15*slot,('Incorrect virtual slot length',size)
                shutil.copyfileobj(source,target)
    print('PLAYLIST READY',group_index,len(jobs),flush=True)
    results=[]
    with sync_playwright() as p:
        context=p.chromium.launch_persistent_context(str(work/'profile'),executable_path=CHROME,headless=True,
            args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream=fps=15',f'--use-file-for-fake-video-capture={playlist}',
                  '--autoplay-policy=no-user-gesture-required'],viewport={'width':1280,'height':800})
        page=context.new_page();page.set_default_timeout(30000);errors=[];responses=[];sent=[];requests=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:(requests.append(r),sent.append(time.perf_counter())) if r.url.endswith('/api/beginner-asl') and r.method=='POST' else None)
        page.on('response',lambda r:responses.append(r) if r.url.endswith('/api/beginner-asl') and r.request.method=='POST' else None)
        page.add_init_script("window.qaDiagnostics=[];document.addEventListener('handspeak:word-capture-diagnostics',e=>window.qaDiagnostics.push(e.detail));")
        try:
            page.goto(options['url']+'/#workspace',wait_until='domcontentloaded')
            page.wait_for_function("document.documentElement.dataset.handspeakReady==='true'",timeout=60000)
            page.wait_for_function("!document.querySelector('#beginnerVocabMode option[value=target20]').disabled",timeout=60000)
            page.select_option('#recognitionMode','words');page.uncheck('#automaticWords');page.select_option('#beginnerVocabMode','target20');page.check('#beginnerConsent')
            if 'Show more tools' in page.locator('#simpleViewButton').inner_text():page.click('#simpleViewButton')
            page.locator('details.camera-settings > summary').click()
            page.uncheck('#faceTrackingToggle')
            page.locator('details.camera-settings > summary').click()
            warmup_started=time.perf_counter()
            page.click('#beginnerRecord')
            page.wait_for_function("document.querySelector('#beginnerStatus').textContent.startsWith('Get ready') || ("+TERMINAL+")",timeout=120000)
            ready_ms=(time.perf_counter()-warmup_started)*1000 if page.locator("#beginnerStatus").inner_text().startswith("Get ready") else None
            page.wait_for_function(TERMINAL,timeout=120000)
            warmup=dict(start_to_ready_ms=ready_ms,status=page.locator('#beginnerStatus').inner_text(),independent_attempt=False)
            for position,(row,scenario,index,_) in enumerate(jobs):
                result=dict(case_id=index,label=row['label'],scenario=scenario,split=row['split'],source_sha256=row['sha256'],
                            independent_clip=scenario=='normal',camera_type='Chromium Y4M simulated getUserMedia',correct=False,
                            expected_rejection=scenario in ('no-hands','incomplete','low-quality','missing-hands','delayed','dropped-frames'),
                            backend_response=None,warmup=warmup if position==0 else None,playlist_group=group_index,
                            planned_slot_start=preamble+position*slot)
                try:
                    page.wait_for_function("!document.querySelector('#beginnerRecord').disabled",timeout=30000)
                    page.locator('#beginnerRecord').focus()
                    start_time=result['planned_slot_start']
                    page.wait_for_function('(t)=>document.querySelector("#webcam").currentTime>=t',arg=start_time-.5,timeout=max(30000,(preamble+slot)*1000))
                    clock=page.locator('#webcam').evaluate('v=>v.currentTime')
                    result['observed_slot_start']=clock
                    result['browser_user_agent']=page.evaluate('navigator.userAgent')
                    if clock-start_time>.7:raise RuntimeError('Missed reserved clip slot; no partial recording submitted')
                    responses.clear();sent.clear();requests.clear();errors.clear()
                    diag_start=page.evaluate('window.qaDiagnostics.length')
                    if scenario=='no-hands':
                        page.evaluate("""() => {
                          const video=document.querySelector('#webcam');
                          const canvas=document.createElement('canvas');canvas.width=canvas.height=8;
                          const ctx=canvas.getContext('2d',{willReadFrequently:true});
                          window.qaBlankContrast=[];
                          window.qaBlankTimer=setInterval(()=>{
                            if(!document.querySelector('#beginnerStatus').textContent.startsWith('Recording for four') || video.readyState<2)return;
                            ctx.drawImage(video,0,0,8,8);
                            const red=ctx.getImageData(0,0,8,8).data.filter((_,i)=>i%4===0);
                            window.qaBlankContrast.push(Math.max(...red)-Math.min(...red));
                          },250);
                        }""")
                    before=page.locator('#webcam').evaluate('v=>v.getVideoPlaybackQuality().totalVideoFrames')
                    start=time.perf_counter();page.keyboard.press('Enter')
                    if scenario=='interrupted':
                        page.wait_for_function("document.querySelector('#beginnerStatus').textContent.startsWith('Recording for four')",timeout=15000)
                        page.wait_for_timeout(1500);page.click('#beginnerCancel');page.wait_for_timeout(2200)
                        result['status']=page.locator('#beginnerStatus').inner_text();result['correct']=not responses and 'canceled' in result['status']
                    else:
                        page.wait_for_function(TERMINAL,timeout=15000)
                        result['status']=page.locator('#beginnerStatus').inner_text()
                        response=associated_response(requests,responses)
                        if response is not None:
                            data=response.json();result['backend_response']=data;result['http_status']=response.status
                            if options.get('parity'):
                                (work/f'parity-{index}.json').write_text(json.dumps(response.request.post_data_json))
                            prediction=(data.get('predictions') or [{}])[0].get('label');result['predicted']=prediction
                            score=data.get('topScore');gate=data.get('minScore')
                            result['confidence_contract_ok']=bool(not prediction or (score is not None and gate is not None and score+1e-6>=gate))
                            result['correct']=(prediction is None) if row['label']=='UNKNOWN' or result['expected_rejection'] else prediction==row['label']
                            result['api_to_display_ms']=(time.perf_counter()-sent[-1])*1000 if sent else None
                        else:
                            result['predicted']=None;result['capture_failure']=True
                            result['correct']=bool(result['expected_rejection'] and ('Not enough' in result['status'] or 'Capture quality insufficient' in result['status'] or 'timed out' in result['status']))
                    result['capture_to_display_ms']=(time.perf_counter()-start)*1000
                    stream=page.locator('#webcam').evaluate("v=>{const t=v.srcObject?.getVideoTracks()[0];return t?{label:t.label,readyState:t.readyState,settings:t.getSettings(),videoWidth:v.videoWidth,videoHeight:v.videoHeight,decodedFrames:v.getVideoPlaybackQuality().totalVideoFrames,currentTime:v.currentTime}:null}")
                    result['stream']=stream;settings=(stream or {}).get('settings',{})
                    result['delivered_frames_during_attempt']=(stream or {}).get('decodedFrames',before)-before
                    result['camera_configuration_ok']=bool(stream and settings.get('width')==640 and settings.get('height')==480 and settings.get('frameRate',0)>=15)
                    result['capture_diagnostics']=page.evaluate('(n)=>window.qaDiagnostics.slice(n)',diag_start)
                    if scenario=='no-hands':
                        contrasts=page.evaluate('()=>{clearInterval(window.qaBlankTimer);return window.qaBlankContrast}')
                        result['blank_control_samples']=len(contrasts)
                        result['blank_control_verified']=blank_control_verified(contrasts)
                    completed=[d for d in result['capture_diagnostics'] if d.get('startMediaTime') is not None and not d.get('outcome')]
                    result['full_source_window_captured']=bool(completed and completed[-1]['startMediaTime']<=start_time+2.1 and completed[-1]['endMediaTime']>=start_time+4.9)
                    result['display']=page.locator('#liveLetter').inner_text()
                    result['display_matches_prediction']=not result.get('predicted') or result['display']==result['predicted']
                    result['correct']=bool(result['correct'] and not errors and result['display_matches_prediction'] and result['camera_configuration_ok'] and result.get('confidence_contract_ok',True))
                    if scenario=='normal' and not result['full_source_window_captured']:result['correct']=False
                    if position==0:page.locator('#webcam').screenshot(path=str(work/'camera-evidence.png'))
                except Exception as error:
                    result['error']=str(error);result['correct']=False
                    if scenario=='no-hands':
                        page.evaluate('()=>clearInterval(window.qaBlankTimer)')
                result['page_errors']=list(errors);result.update(assess_outcome(result))
                result['correct']=result['v3_outcome']=='correct' or result['unknown_rejected']
                results.append(result)
                with (work/'results.jsonl').open('a',encoding='utf-8') as log:log.write(json.dumps(result)+'\n')
                print(json.dumps({k:result.get(k) for k in ['case_id','label','scenario','predicted','correct','status','error','camera_configuration_ok']}),flush=True)
                # Timeout/cancellation paths must finish before the next reserved slot.
                page.click('#beginnerCancel')
        finally:context.close()
    # Delete only reproducible generated streams in this newly created QA folder.
    for generated in (playlist,temporary):
        if generated.resolve().is_relative_to(Path(options['output']).resolve()) and generated.suffix=='.y4m':generated.unlink(missing_ok=True)
    return results


def worker(job):
    row,scenario,index,options=job
    output=Path(options['output']);work=output/'workers'/str(os.getpid());work.mkdir(parents=True,exist_ok=True)
    y4m=work/'camera.y4m';camera_file(row,y4m,scenario,duration_limit=12)
    result=dict(case_id=index,label=row['label'],scenario=scenario,split=row['split'],source_sha256=row['sha256'],
                independent_clip=scenario=='normal',camera_type='Chromium Y4M simulated getUserMedia',correct=False,
                expected_rejection=scenario in ('no-hands','incomplete','low-quality','missing-hands','delayed','dropped-frames'),
                backend_response=None,warmup=None)
    with sync_playwright() as p:
        browser=p.chromium.launch_persistent_context(str(work/'profile'),executable_path=CHROME,headless=True,
            args=['--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream=fps=15',
                  f'--use-file-for-fake-video-capture={y4m}','--autoplay-policy=no-user-gesture-required'],
            viewport={'width':1280,'height':800})
        page=browser.new_page();page.set_default_timeout(30000);errors=[];responses=[];sent=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:sent.append(time.perf_counter()) if r.url.endswith('/api/beginner-asl') and r.method=='POST' else None)
        page.on('response',lambda r:responses.append(r) if r.url.endswith('/api/beginner-asl') and r.request.method=='POST' else None)
        # Passive event listener only; the application supplies all capture data.
        page.add_init_script("window.qaDiagnostics=[];document.addEventListener('handspeak:word-capture-diagnostics',e=>window.qaDiagnostics.push(e.detail));")
        try:
            page.goto(options['url']+'/#workspace',wait_until='domcontentloaded')
            page.wait_for_function("document.documentElement.dataset.handspeakReady==='true'",timeout=60000)
            page.wait_for_function("!document.querySelector('#beginnerVocabMode option[value=target20]').disabled",timeout=60000)
            page.select_option('#recognitionMode','words');page.uncheck('#automaticWords')
            page.select_option('#beginnerVocabMode','target20')
            page.check('#beginnerConsent')  # Explicit QA consent; not silently enabled by application.
            page.click('#beginnerRecord')
            page.wait_for_function(TERMINAL,timeout=120000)
            result['warmup']=dict(status=page.locator('#beginnerStatus').inner_text(),
                                  api_responses=len(responses),independent_attempt=False)
            page.wait_for_function("!document.querySelector('#beginnerRecord').disabled",timeout=30000)
            if 'Stop camera' in page.locator('#cameraButton').inner_text():page.click('#cameraButton')
            page.click('#beginnerCancel');responses.clear();sent.clear()
            start=time.perf_counter();page.click('#beginnerRecord')
            if scenario=='interrupted':
                page.wait_for_function("document.querySelector('#beginnerStatus').textContent.startsWith('Recording for four')",timeout=30000)
                page.wait_for_timeout(1500);page.click('#beginnerCancel');page.wait_for_timeout(3500)
                result['status']=page.locator('#beginnerStatus').inner_text()
                result['correct']=not responses and 'canceled' in result['status']
            else:
                page.wait_for_function(TERMINAL,timeout=45000)
                result['status']=page.locator('#beginnerStatus').inner_text()
                if responses:
                    response=responses[-1];data=response.json();result['backend_response']=data;result['http_status']=response.status
                    prediction=(data.get('predictions') or [{}])[0].get('label');result['predicted']=prediction
                    result['correct']=(prediction is None) if row['label']=='UNKNOWN' or result['expected_rejection'] else prediction==row['label']
                    result['api_to_display_ms']=(time.perf_counter()-sent[-1])*1000 if sent else None
                else:
                    result['predicted']=None
                    result['capture_failure']=True
                    # Capture-level invalid-input rejection is distinct from a model rejection.
                    result['correct']=bool(result['expected_rejection'] and ('Not enough' in result['status'] or 'Capture quality insufficient' in result['status'] or 'timed out' in result['status']))
            result['capture_to_display_ms']=(time.perf_counter()-start)*1000
            result['stream']=page.locator('#webcam').evaluate("v=>{const t=v.srcObject?.getVideoTracks()[0];return t?{label:t.label,readyState:t.readyState,settings:t.getSettings(),videoWidth:v.videoWidth,videoHeight:v.videoHeight,decodedFrames:v.getVideoPlaybackQuality?.().totalVideoFrames}:null}")
            stream=result['stream'];settings=(stream or {}).get('settings',{})
            result['camera_configuration_ok']=bool(stream and settings.get('width')==640 and settings.get('height')==480 and settings.get('frameRate',0)>=15)
            result['capture_diagnostics']=page.evaluate('window.qaDiagnostics')
            result['display']=page.locator('#liveLetter').inner_text()
            result['display_matches_prediction']=not result.get('predicted') or result['display']==result['predicted']
            result['correct']=bool(result['correct'] and not errors and result['display_matches_prediction'] and result['camera_configuration_ok'])
            if row['label']=='UNKNOWN' or scenario!='normal':result['correct']=False
            if index<2:page.screenshot(path=str(work/f'case-{index}.png'),full_page=True)
        except Exception as error:
            result['error']=str(error)
            try:result['status']=page.locator('#beginnerStatus').inner_text(timeout=2000)
            except Exception:pass
        finally:
            result['page_errors']=errors;browser.close()
    print(json.dumps({k:result.get(k) for k in ['case_id','label','scenario','predicted','correct','status','error','camera_configuration_ok']}),flush=True)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://127.0.0.1:8001');parser.add_argument('--split',choices=['train','val','test'],default='val')
    parser.add_argument('--per-word',type=int,default=1);parser.add_argument('--limit',type=int,default=20)
    parser.add_argument('--workers',type=int,default=2);parser.add_argument('--phase',choices=['known','rejections','confusables'],default='known')
    parser.add_argument('--parity',action='store_true');parser.add_argument('--playlist',action='store_true');parser.add_argument('--offset',type=int,default=0);parser.add_argument('--retry-missed',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    if args.output.resolve().is_relative_to(ROOT.resolve()):parser.error('QA video and landmark output must stay outside the served directory')
    args.output.mkdir(parents=True,exist_ok=True)
    output=args.output/'results.json'
    if output.exists() or (args.output/'protocol.json').exists():raise RuntimeError('Versioned run already exists; use a new output directory')
    m=json.loads((CACHE/'target20-v2-manifest.json').read_text());selected=[]
    if args.phase=='known':
        for label in m['labels'][:20]:
            rows=sorted((r for r in m['samples'] if r['label']==label and r['split']==args.split),key=lambda r:r['sha256'])
            distinct={r['sha256']:r for r in rows};rows=list(distinct.values())
            participants=set();chosen=[];remaining=[]
            for row in rows:
                if row['participant'] not in participants:chosen.append(row);participants.add(row['participant'])
                else:remaining.append(row)
            selected.extend((r,'normal') for r in (chosen+remaining)[:args.per_word])
    elif args.phase=='confusables':
        for gloss,scenario in [('MY','similar-looking'),('OUR','incorrect-target')]:
            row=next(r for r in m['samples'] if r['split']==args.split and r['gloss']==gloss)
            selected.append((row,scenario))
    else:
        for scenario in ('no-hands','incomplete','missing-hands','low-quality','delayed','dropped-frames','interrupted'):
            row=next(r for r in m['samples'] if r['split']==args.split and r['label']=='HELLO')
            selected.append((row,scenario))
        fresh=CACHE/'virtual-v4-unknown-manifest.json'
        unknown=json.loads(fresh.read_text())['samples'] if fresh.exists() and args.split=='test' else [r for r in m['samples'] if r['split']==args.split and r['label']=='UNKNOWN']
        selected.extend((r,'normal') for r in sorted(unknown,key=lambda r:r['sha256'])[:100])
    if args.retry_missed:
        earlier=json.loads(args.retry_missed.read_text())['results']
        missed={r['source_sha256'] for r in earlier if (r.get('error') or '').startswith('Missed reserved clip slot')}
        selected=[(r,scenario) for r,scenario in selected if r['sha256'] in missed]
    if args.parity and args.split=='test':parser.error('Parity capture is development/validation only')
    if args.parity and args.output.resolve().is_relative_to(ROOT):parser.error('Private payloads must stay outside the web root')
    options=dict(url=args.url,output=str(args.output.resolve()),parity=args.parity)
    jobs=[(row,scenario,index,options) for index,(row,scenario) in enumerate(selected[args.offset:args.offset+args.limit])]
    with urllib.request.urlopen(args.url+'/api/beginner-asl/status',timeout=30) as response:backend=json.load(response)['target20']
    expected=json.loads((CACHE/'target20-v3/final-evaluation.json').read_text())
    assert backend.get('checkpointSha256')==expected['checkpoint_sha256'],'QA backend checkpoint differs from the pinned candidate'
    assert abs(backend['gate']-expected['gate'])<1e-9,'QA rejection gate differs from the frozen validation-selected gate'
    config=dict(virtual_camera=True,resolution=[640,480],source_fps=15,playlist_preamble_seconds=60,slot_seconds=12,full_reference_playback_seconds=3,source_lead_seconds=2,split=args.split,phase=args.phase,
                checkpoint_sha256=backend['checkpointSha256'],gate=backend['gate'],model_version=backend['modelVersion'],
                clips_per_word=args.per_word,concurrency=args.workers,results=[])
    (args.output/'protocol.json').write_text(json.dumps({**config,'sources':[dict(sha256=r['sha256'],label=r['label'],scenario=s) for r,s in selected[args.offset:args.offset+args.limit]]},indent=2))
    with cf.ProcessPoolExecutor(max_workers=args.workers) as pool:
        if args.playlist:
            groups=[(jobs[i::args.workers],i) for i in range(args.workers)]
            for batch in pool.map(playlist_group,groups):
                config['results'].extend(batch);output.write_text(json.dumps(config,indent=2))
        else:
            for result in pool.map(worker,jobs):
                config['results'].append(result);output.write_text(json.dumps(config,indent=2))


if __name__=='__main__':main()


