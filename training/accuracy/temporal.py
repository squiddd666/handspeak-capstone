"""Compact CPU temporal candidate. Development data only; no test access here."""
import copy,json,hashlib
from pathlib import Path
import numpy as np
import torch
from torch import nn
ROOT=Path('/opt/handspeak-training/accuracy-v4')
LABELS=['HELLO','THANK YOU','PLEASE','YES','NO','FINISH','UNKNOWN']
torch.set_num_threads(2)
def features(row):
 frames=row['rawFrames'];body=row.get('body',[None]*len(frames));aspect=row['imageAspect'];vectors=[]
 wrists=[(h[0]['x'],h[0]['y']*aspect) for f in frames for h in f if h]
 center=np.mean(wrists,axis=0) if wrists else np.zeros(2)
 for frame,pose in zip(frames,body):
  good=bool(pose and min(pose[1]['visibility'],pose[2]['visibility'])>.5)
  origin=np.mean([[pose[i]['x'],pose[i]['y']*aspect] for i in [1,2]],axis=0) if good else center
  scale=max(.08,np.linalg.norm(np.array([pose[1]['x']-pose[2]['x'],(pose[1]['y']-pose[2]['y'])*aspect]))) if good else .2
  vector=[]
  for h in frame:
   if not h:vector.extend([0.]*69);continue
   a=np.array([[p['x'],p['y']*aspect,p['z']] for p in h]);palm=max(.035,np.linalg.norm(a[5,:2]-a[17,:2]));local=(a-a[0])/palm
   vector.extend([1.,*local.flatten(),*((a[0,:2]-origin)/scale),*((a[0,:2]-center)/scale),float(good)])
  for i in range(5):
   if good and pose[i]['visibility']>.5:vector.extend([1.,(pose[i]['x']-origin[0])/scale,(pose[i]['y']*aspect-origin[1])/scale])
   else:vector.extend([0.,0.,0.])
  vectors.append(vector)
 if not vectors:return np.zeros((153,32),np.float32)
 a=np.nan_to_num(np.clip(np.array(vectors),-10,10));t=np.linspace(0,len(a)-1,32)
 return np.stack([np.interp(t,np.arange(len(a)),a[:,i]) for i in range(a.shape[1])]).astype(np.float32)
def mirrored(row):
 out=copy.deepcopy(row)
 out['rawFrames']=[[None if h is None else [dict(p,x=1-p['x']) for p in h] for h in reversed(frame)] for frame in row['rawFrames']]
 out['body']=[None if pose is None else [dict(pose[i],x=1-pose[i]['x']) for i in [0,2,1,4,3]] for pose in row['body']]
 return out
def nuisance(rows,count,seed):
 rng=np.random.default_rng(seed);sources=[r for r in rows if any(any(f) for f in r['rawFrames'])];result=[];order=rng.permutation(len(sources))
 for i in range(count):
  src=sources[int(order[i%len(order)])];valid=[f for f in src['rawFrames'] if any(f)];handframe=copy.deepcopy(valid[len(valid)//2]);frames=[];kind=['still','drift','jitter','no-hands'][i%4]
  for t in range(30):
   f=copy.deepcopy(handframe)
   if kind=='no-hands':f=[None,None]
   else:
    for h in f:
     if h:
      dx=(t/29-.5)*.04 if kind=='drift' else rng.normal(0,.0015) if kind=='jitter' else 0
      for p in h:p['x']+=dx
   frames.append(f)
  result.append(dict(label='UNKNOWN',kind='synthetic-'+kind,split=src['split'],participant=src['participant'],sha256=f'synthetic-{seed}-{i}',rawFrames=frames,body=[None]*30,imageAspect=src['imageAspect'],timestamps=list(range(0,3000,100)),durationMs=3000))
 return result
class Temporal(nn.Module):
 def __init__(self,width=32):
  super().__init__();self.net=nn.Sequential(nn.Conv1d(153,width,5,padding=2),nn.ReLU(),nn.Dropout(.15),nn.Conv1d(width,width,3,padding=1),nn.ReLU(),nn.AdaptiveAvgPool1d(1),nn.Flatten(),nn.Linear(width,7))
 def forward(self,x):return self.net(x)
def outputs(probs,threshold,margin):
 order=np.argsort(probs,axis=1);best=order[:,-1];gap=probs[np.arange(len(probs)),best]-probs[np.arange(len(probs)),order[:,-2]]
 return [LABELS[i] if i<6 and probs[n,i]>=threshold and gap[n]>=margin else None for n,i in enumerate(best)]
def metrics(rows,pred):
 known=[(r,p) for r,p in zip(rows,pred) if r.get('kind')=='supported'];neg=[(r,p) for r,p in zip(rows,pred) if r.get('kind')=='unsupported'];synth=[(r,p) for r,p in zip(rows,pred) if r.get('kind','').startswith('synthetic')]
 return dict(correct=sum(p==r['label'] for r,p in known),wrong=sum(p is not None and p!=r['label'] for r,p in known),missed=sum(p is None for r,p in known),total=len(known),unsupportedFalse=sum(p is not None for r,p in neg),unsupportedTotal=len(neg),syntheticFalse=sum(p is not None for r,p in synth),syntheticTotal=len(synth))
def score(m):return 4*m['wrong']+m['missed']+4*m['unsupportedFalse']+4*m['syntheticFalse']
if __name__=='__main__':
 rows=json.loads((ROOT/'development-features.json').read_text());train=[r for r in rows if r['split']=='train'];val=[r for r in rows if r['split']=='val'];train+=nuisance(train,64,123);val+=nuisance(val,24,456);train=train+[mirrored(r) for r in train]
 x=torch.tensor(np.stack([features(r) for r in train]));vx=torch.tensor(np.stack([features(r) for r in val]));y=torch.tensor([LABELS.index(r['label']) if r['label'] in LABELS else 6 for r in train]);weights=1/torch.bincount(y,minlength=7).float().clamp(min=1);weights=weights/weights.mean();best=None;trials=[]
 for seed,width in [(17,16),(29,32)]:
  torch.manual_seed(seed);net=Temporal(width);opt=torch.optim.AdamW(net.parameters(),lr=.003,weight_decay=.01)
  for epoch in range(1,81):
   net.train();order=torch.randperm(len(x))
   for ids in order.split(32):
    batch=x[ids].clone();batch+=torch.randn_like(batch)*.015;opt.zero_grad();loss=nn.functional.cross_entropy(net(batch),y[ids],weight=weights);loss.backward();opt.step()
   if epoch not in [10,20,40,80]:continue
   net.eval()
   with torch.no_grad():probs=net(vx).softmax(1).numpy()
   for threshold in [.4,.55,.7,.85,.95]:
    for margin in [0,.2,.4]:
     m=metrics(val,outputs(probs,threshold,margin));entry=dict(seed=seed,width=width,epoch=epoch,threshold=threshold,margin=margin,metrics=m,score=score(m));trials.append(entry)
     if best is None or entry['score']<best['score']:
      best=entry;torch.save({'state':net.state_dict(),'config':entry},ROOT/'temporal-candidate.pt')
   print('Temporal',seed,width,epoch,'best',best,flush=True)
 (ROOT/'temporal-validation.json').write_text(json.dumps({'best':best,'trials':trials},indent=2));print('Selected',best,flush=True)
