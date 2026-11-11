"""Extract PopSign hand sequences using exactly the browser's motion encoding.
Run download_words.py first. Cached source videos stay outside the served website.
"""
import json
from pathlib import Path
import cv2
import numpy as np
import mediapipe as mp
import quickjs
ROOT=Path(__file__).resolve().parents[1]
CACHE=Path('/opt/handspeak-training/popsign')
MODEL='/opt/handspeak-training/hand_landmarker.task'

def configure_worker(model_path):
    global MODEL
    MODEL=model_path

def extract(row):
    out=Path(row['file']).with_suffix('.landmarks.json')
    cv2.setNumThreads(1)
    cached=json.loads(out.read_text()) if out.exists() else None
    js=quickjs.Context()
    for name in ['gesture-model.js','motion-model.js']:
        js.eval((ROOT/name).read_text().replace('export ',''))
    if cached and 'rawFrames' in cached:
        if 'imageAspect' not in cached:
            metadata=cv2.VideoCapture(row['file'],cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1])
            cached['imageAspect']=metadata.get(cv2.CAP_PROP_FRAME_HEIGHT)/metadata.get(cv2.CAP_PROP_FRAME_WIDTH)
            metadata.release()
        cached['sequence']=json.loads(js.eval('JSON.stringify(encodeMotion('+json.dumps(cached['rawFrames'])+','+str(cached['imageAspect'])+'))'))
        if cached['sequence'] is not None:cached['sequence']=np.round(cached['sequence'],5).tolist()
        out.write_text(json.dumps(cached,separators=(',',':')))
        return cached
    cap=cv2.VideoCapture(row['file'],cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1]);n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=cap.get(cv2.CAP_PROP_FPS)
    frames=[];aspect=1
    options=mp.tasks.vision.HandLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(model_asset_path=MODEL),running_mode=mp.tasks.vision.RunningMode.VIDEO,
        num_hands=2,min_hand_detection_confidence=.65,min_hand_presence_confidence=.65,min_tracking_confidence=.6)
    with mp.tasks.vision.HandLandmarker.create_from_options(options) as detector:
        selected=set(np.unique(np.linspace(0,max(0,n-1),30).astype(int)))
        for frame_id in range(n):
            if not cap.grab():break
            if frame_id not in selected:continue
            ok,bgr=cap.retrieve()
            if not ok:continue
            h,w=bgr.shape[:2]
            aspect=h/w
            bgr=cv2.resize(bgr,(round(w*min(1,640/max(h,w))),round(h*min(1,640/max(h,w)))))
            result=detector.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,data=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB)),round(frame_id/max(1,fps)*1000))
            detection={'landmarks':[[{'x':p.x,'y':p.y,'z':p.z} for p in points] for points in result.hand_landmarks],
                       'handedness':[[{'categoryName':h.category_name} for h in hand] for hand in result.handedness]}
            # Same clipped/small-hand gate as the camera path.
            js.eval('var d='+json.dumps(detection)+';')
            data=js.eval('JSON.stringify(motionFrame({landmarks:d.landmarks.filter(isUsableHand),handedness:d.handedness.filter((_,i)=>isUsableHand(d.landmarks[i]))}))')
            frames.append(json.loads(data))
    cap.release()
    result=js.eval('JSON.stringify(encodeMotion('+json.dumps(frames)+','+str(aspect)+'))')
    sequence=json.loads(result)
    if sequence is not None:sequence=np.round(sequence,5).tolist()
    record={**row,'sequence':sequence,'rawFrames':frames,'imageAspect':aspect,'frames':len(frames),'trackedFrames':sum(any(h is not None for h in frame) for frame in frames)}
    out.write_text(json.dumps(record,separators=(',',':')))
    return record

if __name__=='__main__':
    from concurrent.futures import ProcessPoolExecutor
    import argparse,urllib.request
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=CACHE)
    parser.add_argument('--hand-model',type=Path,default=Path(MODEL))
    parser.add_argument('--workers',type=int,default=2)
    args=parser.parse_args();CACHE=args.cache.resolve();MODEL=str(args.hand_model.resolve())
    if not Path(MODEL).exists():
        Path(MODEL).parent.mkdir(parents=True,exist_ok=True)
        urllib.request.urlretrieve('https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task',MODEL)
    manifest=json.loads((CACHE/'manifest.json').read_text())
    rows=[]
    with ProcessPoolExecutor(max_workers=args.workers,initializer=configure_worker,initargs=(MODEL,)) as pool:
        for row in pool.map(extract,manifest):
            rows.append(row)
            if len(rows)%12==0:print('Extracted',len(rows),'/',len(manifest),flush=True)
    (CACHE/'extracted.json').write_text(json.dumps(rows,separators=(',',':')))
    from collections import Counter
    print('Usable:',Counter((r['label'],r['split']) for r in rows if r['sequence']),flush=True)
