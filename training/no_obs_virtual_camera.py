"""Prepare/launch a Chromium file-backed fake camera, without OBS or automation.
Only source video pixels are supplied. No landmarks/predictions are injected.
"""
import argparse,csv,hashlib,json,re,subprocess,sys,urllib.request
from pathlib import Path
import imageio_ffmpeg
import cv2
from urllib.parse import urlencode

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT.parent/'handspeak-training'/'no-obs-virtual-camera'
KEY=lambda s:re.sub('[^A-Z0-9]','',re.sub('[12]$','',s.upper()))

def candidates():
    results=json.loads((ROOT/'website-word-test/results.json').read_text())['rows']
    policy=json.loads((ROOT/'models/disabled-word-policy.json').read_text())
    blocked={KEY(x) for x in policy['labels']}
    rows={}
    for row in results:
        if row['outcome']=='correct' and KEY(row['expected']) not in blocked:
            rows.setdefault(row['expected'],dict(word=row['expected'],source=row['file'],mode=row['model']))
    return sorted(rows.values(),key=lambda r:r['word'])

def prepare(row):
    OUT.mkdir(parents=True,exist_ok=True)
    source=Path(row['source']);slug=re.sub('[^a-z0-9]+','-',row['word'].lower()).strip('-')
    path=OUT/(slug+'.y4m');meta=OUT/(slug+'.json')
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    if not(path.exists() and meta.exists() and json.loads(meta.read_text()).get('sourceSha256')==sha):
        # Preserve source motion/timing, resize with letterboxing; add real blank
        # intervals, not held/replayed landmark observations. Chromium loops EOF.
        filters='scale=640:480:force_original_aspect_ratio=decrease,pad=640:480:(ow-iw)/2:(oh-ih)/2:color=gray,setsar=1,fps=15,tpad=start_duration=4:start_mode=add:stop_duration=4:stop_mode=add:color=gray,format=yuv420p'
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',str(source),'-an','-vf',filters,'-pix_fmt','yuv420p','-f','yuv4mpegpipe',str(path)],check=True)
        cap=cv2.VideoCapture(str(source));duration=cap.get(cv2.CAP_PROP_FRAME_COUNT)/cap.get(cv2.CAP_PROP_FPS);cap.release()
        metadata=dict(**row,sourceSha256=sha,cameraFile=str(path),sourceStartSeconds=4,sourceDurationSeconds=duration,cycleDurationSeconds=duration+8,changes='640x480 letterbox, 15fps, 4s blank before and after; source speed unchanged',virtualCameraTested=False)
        meta.write_text(json.dumps(metadata,indent=2))
    return path,json.loads(meta.read_text())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--word');parser.add_argument('--list',action='store_true');parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args();rows=candidates()
    if args.list:
        for i,r in enumerate(rows,1):print(f'{i:2}. {r["word"]:16} {r["mode"]}')
        return
    if not args.word:
        for i,r in enumerate(rows,1):print(f'{i:2}. {r["word"]:16} {r["mode"]}')
        choice=input('Choose word number (or Q to quit): ').strip()
        if choice.lower()=='q':return
        try:row=rows[int(choice)-1] if int(choice)>0 else None
        except (ValueError,IndexError):row=None
        if not row:raise SystemExit('Invalid word number')
    else:
        row=next((r for r in rows if KEY(r['word'])==KEY(args.word)),None)
        if not row:raise SystemExit('Word is disabled or has no passing reference clip')
    camera,meta=prepare(row)
    print('\nExpected word:',row['word'],'| Website vocabulary:',row['mode'])
    print('Fake-camera file:',camera)
    print(f'Feed: 4s blank -> {meta["sourceDurationSeconds"]:.2f}s sign -> 4s blank, then loops.')
    if args.prepare_only:
        print('Prepared only. No browser launched; no live result measured.');return
    try:urllib.request.urlopen('http://localhost:8000/',timeout=5).close()
    except Exception:raise SystemExit('Start HandSpeak first: .\\.venv\\Scripts\\python.exe server.py')
    browsers=[Path(r'C:\Program Files\Google\Chrome\Application\chrome.exe'),Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')]
    browser=next((p for p in browsers if p.exists()),None)
    if not browser:raise SystemExit('Chrome or Edge is required')
    profile=OUT/'profiles'/re.sub('[^a-z0-9]+','-',row['word'].lower())
    profile.mkdir(parents=True,exist_ok=True)
    # No remote debugging, permission bypass, OBS, or access to your real profile.
    url='http://localhost:8000/?'+urlencode(dict(fakeCameraTest='1',testWord=row['word'],testMode=row['mode']))+'#workspace'
    command=[str(browser),'--user-data-dir='+str(profile),'--no-first-run','--no-default-browser-check','--use-fake-device-for-media-stream','--use-file-for-fake-video-capture='+str(camera),'--new-window',url]
    subprocess.Popen(command)
    print('Opened isolated test browser. Use the green No-OBS camera test panel: Start fake camera, then Record test.')
    print('Select the vocabulary printed above; use its normal Record control during the gray lead-in.')
    print('Check that the camera shows the reference signer, NOT your real webcam or a generic test pattern.')
    print('Close this test browser before choosing another word; do not reuse an existing test window.')
    print('Record observations in website-word-test/virtual-camera-worksheet.csv. Nothing is marked passed automatically.')

if __name__=='__main__':main()
