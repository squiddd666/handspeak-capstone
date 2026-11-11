"""Private validation-only browser/backend/offline parity evidence."""
import json,sys
from pathlib import Path
import cv2
import mediapipe as mp
import numpy as np
import torch
from train_essential import ROOT, POSE, encode
from beginner_asl import HAND_POINTS,_build_runtime
from target20_candidate import temporal_features
p=ROOT.parent/'handspeak-training'
run=p/'virtual-v5-validation'
manifest={r['sha256']:r for r in json.loads((p/'target20-v2-manifest.json').read_text())['samples'] if r['split']=='val'}
records=json.loads((run/'results.json').read_text())['results'] if (run/'results.json').exists() else [json.loads(line) for f in run.glob('playlist-*/results.jsonl') for line in f.read_text().splitlines()]
_,model,labels,length=_build_runtime(p/'target20-v3/target20-v3-selected.pt')
rows=[]
def raw_offline(path):
    cap=cv2.VideoCapture(path)
    total=cap.get(cv2.CAP_PROP_FRAME_COUNT)
    stride=max(1,round((cap.get(cv2.CAP_PROP_FPS) or 30)/15))
    out=[]
    try:
        with mp.solutions.holistic.Holistic(model_complexity=1,min_detection_confidence=.5,min_tracking_confidence=.5) as tracker:
            i=-1
            while True:
                ok,img=cap.read()
                if not ok:break
                i+=1
                if i%stride:continue
                r=tracker.process(cv2.cvtColor(img,cv2.COLOR_BGR2RGB))
                def xy(obj,idx):
                    return np.array([[obj.landmark[j].x,obj.landmark[j].y] for j in idx]) if obj else None
                out.append((3*i/max(1,total),dict(pose=xy(r.pose_landmarks,POSE),left=xy(r.left_hand_landmarks,range(21)),right=xy(r.right_hand_landmarks,range(21)))))
    finally:cap.release()
    return out

for record in records:
    assert record['source_sha256'] in manifest
    matches=list(run.glob(f"playlist-*/parity-{record['case_id']}.json"))
    if not matches:continue
    frames=json.loads(matches[0].read_text())['frames']
    def hand(f,k):
        return np.asarray(f[k],np.float32)[HAND_POINTS,:2] if f[k] else np.zeros((10,2),np.float32)
    browser=encode([(np.asarray(f['pose'],np.float32)[:,:2],hand(f,'left'),hand(f,'right')) for f in frames],length)
    cached=p/'landmarks-v1'/(record['source_sha256']+'.npz')
    if not cached.exists():continue
    with np.load(cached) as f:offline=f['x']
    a,b=torch.from_numpy(np.stack([browser,offline])).float().split(1)
    with torch.inference_mode():
        bs,os=(model(t).softmax(1)[0] for t in (a,b))
        v=(temporal_features(a)-temporal_features(b)).abs()[:,54:108].mean().item()
    d=record.get('backend_response') or {}
    if d.get('topScore') is not None:
        assert abs(bs.max().item()-d['topScore'])<2e-5
        assert labels[int(bs.argmax())]==d['rawTopLabel']
    rows.append(dict(word=record['label'],browser_frames=len(frames),browser_median_interval_ms=float(np.median(np.diff([f['timestampMs'] for f in frames]))),
                     tensor_shape=list(browser.shape),body_xy_mae=float(np.abs(browser[:2,:,:7]-offline[:2,:,:7]).mean()),
                     left_mask_disagreement=float(np.not_equal(browser[2,:,7],offline[2,:,7]).mean()),
                     right_mask_disagreement=float(np.not_equal(browser[3,:,17],offline[3,:,17]).mean()),
                     velocity_mae=v,score_mae=float((bs-os).abs().mean()),api_score_verified=d.get('topScore') is not None))
    for side,ch,lo,hi in [('left',2,7,17),('right',3,17,27)]:
        mask=(browser[ch,:,lo]==1)&(offline[ch,:,lo]==1)
        rows[-1][side+'_jointly_visible_xy_mae']=float(np.abs(browser[:2,mask,lo:hi]-offline[:2,mask,lo:hi]).mean()) if mask.any() else None
    if len(rows)<=3 and record.get('full_source_window_captured'):
        offline_raw=raw_offline(manifest[record['source_sha256']]['file'])
        pairs=[]
        if offline_raw:
            for f in frames:
                t=f['timestampMs']/1000-record['planned_slot_start']-2
                if not 0<=t<3:continue
                q=min(offline_raw,key=lambda pair:abs(pair[0]-t))[1]
                pairs.append((f,q))
        rows[-1]['raw_approximate_time_pairs']=len(pairs)
        for k in ('pose','left','right'):
            differences=[np.abs(np.asarray(f[k])[:,:2]-q[k]).mean() for f,q in pairs if f[k] is not None and q[k] is not None]
            rows[-1][k+'_raw_xy_mae']=float(np.mean(differences)) if differences else None
            rows[-1][k+'_presence_disagreement']=float(np.mean([(f[k] is None)!=(q[k] is None) for f,q in pairs])) if pairs else None
(run/'parity-aggregate.json').write_text(json.dumps(rows,indent=2))
print('Validation paired captures:',len(rows),'API score checks:',sum(r['api_score_verified'] for r in rows))

