"""Research-only post-hoc calibration candidate. Never overwrites deployed weights/settings.
Download official ASL Citizen exact-gloss examples by range requests; signer-disjoint
validation fits temperature, untouched official test signers evaluate it.
"""
import sys,csv,io,json,hashlib,time,math,collections
from pathlib import Path
import numpy as np
from remotezip import RemoteZip
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT.parent/'handspeak-training/openhands-citizen-calibration-v1';CACHE.mkdir(exist_ok=True)
URL='https://download.microsoft.com/download/b/8/8/b88c0bae-e6c1-43e1-8726-98cf5af36ca4/ASL_Citizen.zip'
LABELS=json.loads((ROOT/'third_party/OpenHands-source/api/data/labels/word_labels_100.json').read_text())
allowed=json.loads((ROOT/'models/openhands-passed.json').read_text())['labels']

def main():
 samples=[];signers={};missing={}
 for split in ['val','test']:
  rows=list(csv.DictReader(open(ROOT.parent/f'handspeak-training/{split}.csv',encoding='utf-8-sig')))
  chosen=[];missing[split]=[]
  for word in allowed:
   matches=sorted([r for r in rows if r['Gloss']==word],key=lambda r:(r['Participant ID'],r['Video file']))
   participants=set()
   for row in matches:
    if row['Participant ID'] in participants:continue
    participants.add(row['Participant ID']);chosen.append({'split':split,'label':word,'participant':row['Participant ID'],'member':'ASL_Citizen/videos/'+row['Video file']})
    if len(participants)==2:break
   if len(participants)<2:missing[split].append(word)
  signers[split]={r['participant'] for r in chosen};samples+=chosen
 assert not signers['val']&signers['test'],'Signer overlap'
 with RemoteZip(URL,timeout=40) as archive:
  (CACHE/'use.txt').write_bytes(archive.read('ASL_Citizen/use.txt'))
  for i,row in enumerate(samples):
   dest=CACHE/row['split']/Path(row['member']).name;dest.parent.mkdir(exist_ok=True)
   size=archive.getinfo(row['member']).file_size
   if not dest.exists() or dest.stat().st_size!=size:
    data=archive.read(row['member']);assert len(data)==size;dest.write_bytes(data)
   row.update(file=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest());print('DOWNLOAD',i+1,len(samples),row['split'],row['label'],flush=True)
 assert not {r['sha256'] for r in samples if r['split']=='val'} & {r['sha256'] for r in samples if r['split']=='test'},'Video-content leakage'
 (CACHE/'manifest.json').write_text(json.dumps({'source':URL,'license':'Research only; raw data must not be redistributed.','missingExactGloss':missing,'samples':samples},indent=2))
 sys.path.insert(0,str(ROOT/'openhands-test'))
 import runtime as rt
 import torch
 torch.set_num_threads(1)
 results=json.loads((CACHE/'predictions.json').read_text()) if (CACHE/'predictions.json').exists() else []
 done={r['sha256'] for r in results}
 for i,row in enumerate(samples):
  if row['sha256'] in done:continue
  entry=dict(row)
  try:
   tensor=rt.extract_keypoints_from_video(row['file'])
   if tensor is None or not torch.isfinite(tensor).all() or tensor[:,13:,:].abs().sum()==0:raise ValueError('No usable hand keypoints')
   x=rt.prepare_input(tensor)
   with torch.random.fork_rng(),torch.inference_mode():
    torch.manual_seed(42);state=np.random.get_state();np.random.seed(42)
    try:
     prob=torch.softmax(rt.MODEL(x),dim=1)
     for _ in range(8):prob+=torch.softmax(rt.MODEL(rt.tta_augment(x)),dim=1)
     prob=(prob/9).squeeze(0).cpu().numpy()
    finally:np.random.set_state(state)
   entry.update(probabilities=prob.tolist(),target=LABELS.index(row['label'].lower()),predicted=LABELS[int(prob.argmax())].upper())
  except Exception as e:entry['error']=str(e)
  results.append(entry);(CACHE/'predictions.json').write_text(json.dumps(results));print('INFERENCE',i+1,len(samples),row['split'],row['label'],entry.get('predicted',entry.get('error')),flush=True)
 def arrays(split):
  valid=[r for r in results if r['split']==split and 'probabilities' in r]
  return np.array([r['probabilities'] for r in valid]),np.array([r['target'] for r in valid],dtype=int)
 def scaled(p,t):
  z=np.log(np.clip(p,1e-12,1))/t;z-=z.max(axis=1,keepdims=True);v=np.exp(z);return v/v.sum(axis=1,keepdims=True)
 def metrics(p,y):
  confidence=p.max(axis=1);correct=(p.argmax(axis=1)==y).astype(float)
  ece=0.
  for a,b in zip(np.linspace(0,1,16)[:-1],np.linspace(0,1,16)[1:]):
   use=(confidence>=a)&(confidence<b if b<1 else confidence<=b)
   if use.any():ece+=float(use.mean())*abs(float(correct[use].mean()-confidence[use].mean()))
  return {'samples':len(y),'top1':float(correct.mean()),'nll':float(-np.log(np.clip(p[np.arange(len(y)),y],1e-12,1)).mean()),'ece15':ece,'brier':float(((p-np.eye(len(LABELS))[y])**2).sum(axis=1).mean())}
 vp,vy=arrays('val');tp,ty=arrays('test')
 if len(vy)<30 or len(ty)<30:raise ValueError('Insufficient usable signer-disjoint calibration/test examples')
 temps=np.exp(np.linspace(math.log(.2),math.log(5),201));nll=[metrics(scaled(vp,t),vy)['nll'] for t in temps];temperature=float(temps[int(np.argmin(nll))])
 before=metrics(tp,ty);after=metrics(scaled(tp,temperature),ty)
 report={'type':'Post-hoc power/temperature calibration of full-100-class averaged probabilities; not weight training.','deployed':False,'source':URL,'sourceLicense':'Microsoft research-only terms; raw clips outside web root.','coveredLabels':sorted(set(r['label'] for r in samples)),'missingExactGloss':missing,'samples':len(samples),'usable':{'calibration':len(vy),'heldOutTest':len(ty)},'signerDisjoint':True,'temperature':temperature,'fitSplit':'official val only; test not used for fitting','calibrationBefore':metrics(vp,vy),'calibrationAfter':metrics(scaled(vp,temperature),vy),'testBefore':before,'testAfter':after,'errors':sum('error' in r for r in results),'top1Unchanged':before['top1']==after['top1'],'reasonNotDeployed':'Candidate calibration covers exact-gloss subset, not all live labels. Temperature changes confidence, never repairs wrong top-1 labels. No weights, enabled labels, or inference thresholds changed.'}
 report['deploymentDecision']={'accepted':False,'reasons':['Candidate requires full label coverage and non-worsening held-out probability metrics before deployment.','Temperature scaling cannot change top-1 labels.'],'weightsRetrained':False}
 (CACHE/'calibration-report.json').write_text(json.dumps(report,indent=2))
 public=ROOT/'website-word-test/openhands-calibration-candidate.json';public.write_text(json.dumps(report,indent=2));print('CALIBRATION_COMPLETE',json.dumps(report),flush=True)
if __name__=='__main__':main()
