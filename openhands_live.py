"""OpenHands video adapter; independent allowlist, no legacy-policy changes."""
import hashlib,json,subprocess,sys,tempfile,threading,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
UP=ROOT/'third_party/OpenHands-source/api'
BUSY=threading.Lock()

def metadata():
    return json.loads((ROOT/'models/openhands-passed.json').read_text())

def _reference_video_map():
    path=ROOT/'openhands-reference-videos.json'
    if not path.is_file():return {}
    try:rows=json.loads(path.read_text(encoding='utf-8')).get('rows') or []
    except Exception:return {}
    videos={}
    for row in rows:
        word=str(row.get('word') or '').strip().lower()
        url=str(row.get('video') or '').strip()
        if word and url.startswith('https://') and row.get('video_verified') is True:
            videos[word]=url
    return videos

def status():
    meta=metadata()
    required=[UP/'lstm_model_v7.pth',UP/'model/pose_landmarker_lite.task',UP/'model/hand_landmarker.task',UP/'data/labels/word_labels_100.json']
    available=all(p.exists() for p in required)
    if available:available=hashlib.sha256(required[0].read_bytes()).hexdigest()==meta['checkpointSha256']
    remote=_reference_video_map()
    videos={}
    for label in meta['labels']:
        name=label.lower()
        for candidate in [f'media/signs/{name}.mp4',f'openhands-test/reference-videos/{name}.mp4']:
            if (ROOT/candidate).is_file():videos[name]='/'+candidate;break
        if name not in videos and name in remote:videos[name]=remote[name]
    return dict(available=available,videos=videos,labels=meta['labels'],vocabularySize=len(meta['labels']),modelClasses=100,model=f"OpenHands 100-class BiLSTM / {len(meta['labels'])} virtual-camera-passed output labels",scope=meta['evaluationScope'],videoProcessing='This server processes the recorded video locally; temporary file deleted after inference.',source=meta['source'],liveCameraAccuracyVerified=False)

def filter_result(result,allowed):
    winner=(result.get('predicted') or '').upper()
    confidence=result.get('confidence')
    # Winner must pass the allowlist. Never renormalize or promote runner-up.
    accepted=winner in allowed
    return dict(label=winner if accepted else None,confidence=confidence if accepted else None,
      predictions=[dict(label=p['word'].upper(),score=p['confidence']) for p in result.get('top5',[]) if p['word'].upper() in allowed] if accepted else [],
      state='recognized' if accepted else 'rejected',message='Possible match; review before adding.' if accepted else result.get('error') or 'The full-model winner is not an enabled virtual-camera-passed word.',
      model='OpenHands',seconds=result.get('seconds'),scoreType='uncalibrated full-100-class softmax; no subset renormalization')

def recognize(body):
    if not status()['available']:raise ValueError('OpenHands model files are unavailable or fail checksum validation.')
    if not BUSY.acquire(blocking=False):raise BlockingIOError('OpenHands is busy. Wait for the previous recording to finish.')
    path=None
    try:
        with tempfile.NamedTemporaryFile(suffix='.webm',delete=False) as f:
            path=f.name;f.write(body)
        process=subprocess.run([sys.executable,str(ROOT/'training/openhands_live_infer.py'),path],cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
        if process.returncode:
            raise ValueError('Video could not be processed. Use a short, clear sign recording with your upper body and hands visible.')
        result=json.loads(process.stdout.strip().splitlines()[-1])
        return filter_result(result,set(metadata()['labels']))
    finally:
        if path:os.unlink(path)
        BUSY.release()
