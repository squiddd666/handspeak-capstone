"""Validation-only V6 tracking comparison; writes aggregate numbers, not landmarks."""
import json, sys, time
from pathlib import Path
import cv2
import mediapipe as mp
import numpy as np
from train_essential import ROOT, POSE
from beginner_asl import HAND_POINTS, _active_span
sys.path.insert(0,str(ROOT))
from target20_encoder_v6 import encode

cache=ROOT.parent/'handspeak-training'
run=cache/(sys.argv[1] if len(sys.argv)>1 else 'virtual-v6-validation')
manifest={r['sha256']:r for r in json.loads((cache/'target20-v2-manifest.json').read_text())['samples'] if r['split']=='val'}
rows=json.loads((run/'results.json').read_text())['results']
previous_run=cache/'virtual-v5-validation'
previous=json.loads((previous_run/'results.json').read_text())['results']
previous_by_word={r['label']:r for r in previous}

keys=('pose','left','right')
pairs={'YES':'YOU','YOU':'YES','GOOD':'EAT','EAT':'GOOD','WHO':'PLEASE','PLEASE':'WHO'}

def offline(path,smooth):
    cap=cv2.VideoCapture(path)
    fps=cap.get(cv2.CAP_PROP_FPS)
    n=cap.get(cv2.CAP_PROP_FRAME_COUNT)
    if fps<=0 or n<=0:raise ValueError('Source timing unavailable')
    start=time.perf_counter()
    out=[]
    try:
        with mp.solutions.holistic.Holistic(model_complexity=1,smooth_landmarks=smooth,
             min_detection_confidence=.5,min_tracking_confidence=.5) as tracker:
            init=(time.perf_counter()-start)*1000
            first=None
            i=-1
            while True:
                ok,img=cap.read()
                if not ok:break
                i+=1
                if i%max(1,round(fps/15)):continue
                start=time.perf_counter()
                r=tracker.process(cv2.cvtColor(img,cv2.COLOR_BGR2RGB))
                if first is None:first=(time.perf_counter()-start)*1000
                points=lambda obj,jj: [[obj.landmark[j].x,obj.landmark[j].y] for j in jj] if obj else None
                out.append(dict(timestampMs=1000*i/fps,pose=points(r.pose_landmarks,POSE),
                         left=points(r.left_hand_landmarks,range(21)),right=points(r.right_hand_landmarks,range(21))))
    finally:cap.release()
    return out,1000*n/fps,init,first

def stats(frames):
    t=np.array([f['timestampMs'] for f in frames])
    side={}
    for k in ('left','right'):
        m=np.array([f[k] is not None for f in frames],bool)
        boundaries=np.flatnonzero(np.diff(np.r_[False,m,False]))
        longest=int(max(boundaries[1::2]-boundaries[::2],default=0))
        side[k]=dict(visible=int(m.sum()),transitions=int(np.count_nonzero(np.diff(m))),longest_run=longest)
    displacement={}
    for k in keys:
        steps=[np.linalg.norm(np.asarray(a[k])[:,:2]-np.asarray(b[k])[:,:2],axis=1).mean()
               for a,b in zip(frames,frames[1:]) if a[k] is not None and b[k] is not None]
        displacement[k]=float(np.median(steps)) if steps else None
    return dict(frames=len(t),span_ms=float(t[-1]-t[0]),median_delta_ms=float(np.median(np.diff(t))),
                max_delta_ms=float(np.diff(t).max()),hands=side,median_step_xy=displacement)

report=[]
encodings={}
for r in rows:
    assert r['source_sha256'] in manifest and r['split']=='val'
    if r['label'] not in pairs:continue
    files=list(run.glob(f"playlist-*/parity-{r['case_id']}.json"))
    payload_run=run.name
    if not files and r['label'] in previous_by_word:
        earlier=previous_by_word[r['label']]
        if earlier['source_sha256']==r['source_sha256'] and earlier['split']=='val':
            files=list(previous_run.glob(f"playlist-*/parity-{earlier['case_id']}.json"))
            if files:r=earlier;payload_run='V5 archival validation'
    if not files:continue
    source=manifest[r['source_sha256']]
    b=json.loads(files[0].read_text())['frames']
    try:
        encodings[r['label']]=encode(b)
    except ValueError:
        pass
    legacy=np.zeros((len(b),27,2),dtype=np.float32)
    masks=np.zeros_like(legacy)
    for i,f in enumerate(b):
        legacy[i,:7]=np.asarray(f['pose'])[:,:2]
        for side,col,first_joint in [('left',0,7),('right',1,17)]:
            if f[side] is not None:
                legacy[i,first_joint:first_joint+10]=np.asarray(f[side])[HAND_POINTS,:2]
                masks[i,first_joint:first_joint+10,col]=1
    delta=np.linalg.norm(np.diff(legacy[:,7:],axis=0),axis=(1,2))
    boundary=np.any(np.diff(masks[:,7:],axis=0)!=0,axis=(1,2))
    off,duration,init,first=offline(source['file'],True)
    no_smooth,_,_,_=offline(source['file'],False)
    aligned=[]
    for f in b:
        rel=(f['timestampMs']/1000-r['planned_slot_start']-2)/3
        if 0<=rel<1:
            t=rel*duration
            q=min(off,key=lambda x:abs(x['timestampMs']-t))
            aligned.append((f,q,abs(q['timestampMs']-t)))
    aligned_stats={}
    for k in keys:
        errs=[float(np.abs(np.array(f[k])[:,:2]-np.array(q[k])[:,:2]).mean())
             for f,q,_ in aligned if f[k] is not None and q[k] is not None]
        aligned_stats[k]=dict(presence_disagreement=float(np.mean([(f[k] is None)!=(q[k] is None) for f,q,_ in aligned])) if aligned else None,
                              jointly_visible_pairs=len(errs),xy_mae=float(np.mean(errs)) if errs else None)
    report.append(dict(word=r['label'],payload_run=payload_run,reference_gloss=source['gloss'],browser=stats(b),offline=stats(off),
                       offline_no_smoothing=stats(no_smooth),offline_init_ms=init,offline_first_frame_ms=first,
                       aligned_pairs=len(aligned),alignment_nearest_median_ms=float(np.median([x[2] for x in aligned])) if aligned else None,
                       aligned=aligned_stats,legacy_crop_frames=len(_active_span(legacy,masks)[0]),legacy_peak_at_visibility_transition=bool(boundary[int(delta.argmax())]),score=(r.get('backend_response') or {}).get('topScore'),
                       raw_top=(r.get('backend_response') or {}).get('rawTopLabel'),prediction=r.get('predicted')))
comparisons={}
for a,b in [('YES','YOU'),('GOOD','EAT'),('WHO','PLEASE')]:
    if a in encodings and b in encodings:
        x,y=encodings[a],encodings[b]
        valid=x.visible[:,7:]&y.visible[:,7:]
        comparisons[a+' / '+b]=dict(joint_hand_mask_agreement=float((x.visible[:,7:]==y.visible[:,7:]).mean()),
                                     jointly_visible_hand_xy_mae=float(np.abs(x.xy[:,7:][valid]-y.xy[:,7:][valid]).mean()) if valid.any() else None)
(run/'v6-confusion-feature-aggregate.json').write_text(json.dumps(comparisons,indent=2))
(run/'v6-tracking-aggregate.json').write_text(json.dumps(report,indent=2))
print('Paired validation classes:',len(report))
