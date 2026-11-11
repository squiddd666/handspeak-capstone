"""Extract landmark observations for reviewed video windows, outside the web root."""
import argparse,hashlib,json,math
from pathlib import Path
import cv2
import mediapipe as mp

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser()
    p.add_argument('video',type=Path);p.add_argument('annotation',type=Path)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    for path in (a.video,a.annotation,a.output):
        if path.resolve().is_relative_to(ROOT):p.error('Private media, annotations and output must stay outside the served workspace')
    annotation=json.loads(a.annotation.read_text(encoding='utf-8'))
    start,end=annotation['start_ms'],annotation['end_ms']
    if not (math.isfinite(start) and math.isfinite(end) and 0<=start<end):p.error('Invalid annotated time window')
    opts=mp.tasks.vision.HandLandmarkerOptions(base_options=mp.tasks.BaseOptions(model_asset_path=str(a.model)),running_mode=mp.tasks.vision.RunningMode.VIDEO,num_hands=2)
    cap=cv2.VideoCapture(str(a.video));rows=[];last=-1;duplicates=0
    try:
        if not cap.isOpened():p.error('Cannot decode recording')
        with mp.tasks.vision.HandLandmarker.create_from_options(opts) as detector:
            while True:
                ok,bgr=cap.read()
                if not ok:break
                ms=cap.get(cv2.CAP_PROP_POS_MSEC)
                if not math.isfinite(ms) or ms<0:raise ValueError('Invalid decoder timestamp')
                if ms>end:break
                if ms<start:continue
                ts=round(ms)
                if ts<=last:duplicates+=1;continue
                last=ts
                image=mp.Image(image_format=mp.ImageFormat.SRGB,data=cv2.cvtColor(bgr,cv2.COLOR_BGR2RGB))
                r=detector.detect_for_video(image,ts)
                hands=[]
                for pts,side in zip(r.hand_landmarks,r.handedness):
                    values=[[q.x,q.y,q.z] for q in pts]
                    hands.append(dict(points=values,handedness=side[0].category_name,handednessScore=side[0].score,
                        inFrame=all(0<=q[0]<=1 and 0<=q[1]<=1 for q in values),jointConfidence=None))
                rows.append(dict(timestampMs=ts,width=bgr.shape[1],height=bgr.shape[0],hands=hands))
    finally:cap.release()
    if not rows:raise ValueError('No timestamped frames in the annotated window')
    if annotation.get('label') in ('J','Z') and sum(bool(r['hands']) for r in rows)<6:
        raise ValueError('Motion window has fewer than six detected observations; review recording')
    result=dict(schema='handspeak-landmark-observations-v1',annotation=annotation,
                parent_media_sha256=hashlib.sha256(a.video.read_bytes()).hexdigest(),
                detector_sha256=hashlib.sha256(a.model.read_bytes()).hexdigest(),
                decoderTimestampDuplicates=duplicates,frames=rows)
    with a.output.open('x',encoding='utf-8') as f:json.dump(result,f)
    print(len(rows),'decoded observations;',duplicates,'non-increasing timestamps skipped')

if __name__=='__main__':main()
