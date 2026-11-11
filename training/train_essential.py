"""Extract official clips and fine-tune a research candidate; never auto-promote.

Usage: .venv/Scripts/python.exe training/train_essential.py --cache ../handspeak-training
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beginner_asl import HAND_POINTS, encode_landmark_tensor, _build_runtime

POSE = [0, 2, 5, 11, 12, 13, 14]

def encode(frames, length):
    coords, masks = [], []
    for pose, left, right in frames:
        xy = np.concatenate([pose, left, right]).astype(np.float32)
        mask = np.zeros((27, 2), np.float32)
        if left.any(): mask[7:17, 0] = 1
        if right.any(): mask[17:27, 1] = 1
        coords.append(xy); masks.append(mask)
    return encode_landmark_tensor(np.stack(coords), np.stack(masks), length, require_scale=True)


def extract(row, cache, length):
    dest = cache / 'landmarks-v1' / (row['sha256']+'.npz')
    if dest.exists():
        with np.load(dest) as saved: return saved['x']
    dest.parent.mkdir(exist_ok=True)
    frames = []
    cap = cv2.VideoCapture(row['file'])
    try:
        with mp.solutions.holistic.Holistic(model_complexity=1, min_detection_confidence=.5, min_tracking_confidence=.5) as tracker:
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            stride = max(1, round(fps/15)); index=0
            while True:
                ok, image = cap.read()
                if not ok: break
                index+=1
                if (index-1)%stride: continue
                result=tracker.process(cv2.cvtColor(image,cv2.COLOR_BGR2RGB))
                if not result.pose_landmarks: continue
                pose=np.array([[result.pose_landmarks.landmark[i].x,result.pose_landmarks.landmark[i].y] for i in POSE],np.float32)
                hands=[]
                for hand in (result.left_hand_landmarks,result.right_hand_landmarks):
                    hands.append(np.array([[hand.landmark[i].x,hand.landmark[i].y] for i in HAND_POINTS],np.float32) if hand else np.zeros((10,2),np.float32))
                frames.append((pose,*hands))
    finally: cap.release()
    if len(frames)<3 or sum(bool(l.any() or r.any()) for _,l,r in frames)<3:
        raise ValueError('Insufficient tracked frames')
    x=encode(frames,length);np.savez_compressed(dest,x=x)
    return x

def run(cache, epochs):
    torch.set_num_threads(2);torch.manual_seed(42);np.random.seed(42)
    source=ROOT/'models/beginner-need79-v6.pt'
    _,model,labels,length=_build_runtime(source)
    manifest=json.loads((cache/'essential-manifest.json').read_text())
    groups={s:[] for s in ('train','val','test')};failures=[]
    for i,row in enumerate(manifest['samples']):
        try: groups[row['split']].append((extract(row,cache,length),labels.index(row['label']),row))
        except ValueError as error: failures.append(dict(file=row['file'],split=row['split'],error=str(error)))
        print(f'extract {i+1}/{len(manifest["samples"])} failures={len(failures)}',flush=True)
    for split,rows in groups.items():
        if not rows: raise RuntimeError(f'No usable {split} clips')
    def tensors(split):
        rows=groups[split]
        return torch.tensor(np.stack([r[0] for r in rows])),torch.tensor([r[1] for r in rows])
    def evaluate(network,split):
        network.eval();x,y=tensors(split)
        with torch.no_grad():
            probs=network(x).softmax(1);pred=probs.argmax(1)
        return dict(correct=int((pred==y).sum()),total=len(y),per_word={label:dict(correct=int(((pred==y)&(y==labels.index(label))).sum()),total=int((y==labels.index(label)).sum())) for label in manifest['labels']})
    baseline={s:evaluate(model,s) for s in ('val','test')}
    # Freeze the pretrained encoder; only a small head is fitted on 70 train clips.
    # Keep other class rows fixed, since this subset cannot validate their retraining.
    for p in model.parameters(): p.requires_grad=False
    head=model.decoder.classifier
    head.weight.requires_grad=True;head.bias.requires_grad=True
    original_w=head.weight.detach().clone();original_b=head.bias.detach().clone()
    target=[labels.index(label) for label in manifest['labels']]
    other=[i for i in range(len(labels)) if i not in target]
    x,y=tensors('train');model.eval()
    with torch.no_grad(): features=model.encoder(x).detach()
    optimizer=torch.optim.Adam([head.weight,head.bias],lr=.001)
    best=-1;best_state=None;history=[]
    for epoch in range(epochs):
        head.train();optimizer.zero_grad();loss=torch.nn.functional.cross_entropy(head(features),y)
        loss=loss+.1*((head.weight-original_w)**2).mean()
        loss.backward();optimizer.step()
        with torch.no_grad():
            head.weight[other]=original_w[other];head.bias[other]=original_b[other]
        score=evaluate(model,'val');history.append(dict(epoch=epoch+1,loss=float(loss.detach()),validation=score['correct']))
        if score['correct']>best:
            best=score['correct'];best_state={k:v.detach().clone() for k,v in model.state_dict().items()}
        if (epoch+1)%10==0: print('epoch',epoch+1,'val',score['correct'],'/',score['total'],flush=True)
    model.load_state_dict(best_state)
    candidate={s:evaluate(model,s) for s in ('val','test')}
    out=cache/'essential-candidate.pt'
    torch.save(dict(state_dict=best_state,labels=labels,T=length,version='essential-candidate-v1',seed=42),out)
    report=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),candidate=str(out),baseline=baseline,candidate_metrics=candidate,failures=failures,history=history,auto_promoted=False,limitations=['Only five target words evaluated; other-word regression and unsupported-sign rejection not evaluated.','Existing checkpoint training provenance may overlap this source dataset; this is a regression evaluation, not a fresh independent benchmark.','Recorded videos do not establish live-camera accuracy.'])
    (cache/'essential-training-report.json').write_text(json.dumps(report,indent=2))
    print(json.dumps({k:v for k,v in report.items() if k!='history'},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--epochs',type=int,default=60)
    args=parser.parse_args();run(args.cache.resolve(),args.epochs)
