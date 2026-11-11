"""Freeze development-selected models, then evaluate fresh tests exactly once."""
import json,hashlib,time,sys
from pathlib import Path
import numpy as np,torch,quickjs
from temporal import ROOT,Temporal,features,nuisance,outputs,metrics,score
from dtw import matrix,classify,encode,SITE

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def freeze():
 tv=json.loads((ROOT/'temporal-validation.json').read_text());dv=json.loads((ROOT/'dtw-validation.json').read_text())
 choice='temporal' if tv['best']['score']<dv['best']['score'] else 'dtw'
 files=['temporal-candidate.pt','dtw-candidate.json','development-manifest.json','development-features.json','selection.json','protocol.json']
 report={'selected':choice,'selectionRule':'Lower validation objective; ties prefer DTW','validation':{'temporal':tv['best'],'dtw':dv['best'],'baseline':dv['baseline']},'files':{f:digest(ROOT/f) for f in files},'baselineSha256':digest(SITE/'models/asl-words.json'),'codeHashes':{p.name:digest(p) for p in Path(__file__).parent.glob('*.py')}}
 path=ROOT/'frozen-candidates.json'
 if path.exists():assert json.loads(path.read_text())==report,'Frozen candidate changed'
 else:path.write_text(json.dumps(report,indent=2))
 print(json.dumps(report,indent=2),flush=True)
def segment(rows):
 js=quickjs.Context()
 for name in ['motion-model.js','automatic-motion.js']:js.eval((SITE/name).read_text().replace('export ',''))
 js.eval('''function segments(row){const a=createAutomaticMotion(),out=[];const frames=row.rawFrames.concat(Array.from({length:20},()=>[null,null]));const times=row.timestamps.concat(Array.from({length:20},(_,i)=>row.timestamps[row.timestamps.length-1]+(i+1)*100));frames.forEach((f,i)=>{const clip=a.push(f,times[i],row.imageAspect);if(clip){out.push({rawFrames:clip.frames,body:clip.frames.map(x=>row.body[frames.indexOf(x)]||null),timestamps:clip.frames.map(x=>times[frames.indexOf(x)]),imageAspect:row.imageAspect,sequence:encodeMotion(clip.frames,row.imageAspect),end:times[i]});}});return JSON.stringify(out);}''')
 result=[]
 for i,row in enumerate(rows):
  for k,clip in enumerate(json.loads(js.eval('segments('+json.dumps(row)+')'))):result.append({**row,**clip,'parent':i,'sha256':row['sha256']+'-segment-'+str(k)})
 return result
def temporal_predict(rows):
 saved=torch.load(ROOT/'temporal-candidate.pt',map_location='cpu',weights_only=True);c=saved['config'];net=Temporal(c['width']);net.load_state_dict(saved['state']);net.eval()
 with torch.no_grad():p=net(torch.tensor(np.stack([features(r) for r in rows]))).softmax(1).numpy()
 return outputs(p,c['threshold'],c['margin'])
def auto_stats(rows,clips,pred):
 groups=[[] for r in rows]
 for c,p in zip(clips,pred):
  if p:groups[c['parent']].append(p)
 return dict(knownClips=sum(r['kind']=='supported' for r in rows),correctClips=sum(r['kind']=='supported' and r['label'] in ps for r,ps in zip(rows,groups)),missedClips=sum(r['kind']=='supported' and r['label'] not in ps for r,ps in zip(rows,groups)),wrongSuggestions=sum(sum(p!=r['label'] for p in ps) for r,ps in zip(rows,groups) if r['kind']=='supported'),repeatedSuggestions=sum(len(ps)-len(set(ps)) for ps in groups),unsupportedFalse=sum(len(ps) for r,ps in zip(rows,groups) if r['kind']=='unsupported'),syntheticFalse=sum(len(ps) for r,ps in zip(rows,groups) if r['kind'].startswith('synthetic')))
def evaluate():
 frozen=json.loads((ROOT/'frozen-candidates.json').read_text())
 for file,h in frozen['files'].items():assert digest(ROOT/file)==h,file
 assert digest(SITE/'models/asl-words.json')==frozen['baselineSha256']
 for name,h in frozen['codeHashes'].items():assert digest(Path(__file__).parent/name)==h,name
 output=ROOT/'fresh-test-results.json'
 if output.exists():print(output.read_text());return
 rows=json.loads((ROOT/'test-features.json').read_text());dev=json.loads((ROOT/'development-features.json').read_text());old=json.loads(Path('/opt/handspeak-training/popsign/manifest.json').read_text());assert not({r['sha256'] for r in rows}&{r['sha256'] for r in dev+old})
 assert not({r['participant'] for r in rows}&{r['participant'] for r in dev})
 assert len({r['sha256'] for r in rows+dev})==len(rows+dev)
 rows+=nuisance(rows,24,789);encode(rows);clips=segment(rows)
 baseline=json.loads((SITE/'models/asl-words.json').read_text());candidate=json.loads((ROOT/'dtw-candidate.json').read_text());refs=baseline['samples']+candidate['samples'];n=len(baseline['samples']);m=matrix(rows+clips,refs,'fresh-test-distances');predictions={
 'baseline':classify(m[:,:n],baseline['samples'],baseline['parameters']),
 'dtw':classify(m[:,n:],candidate['samples'],candidate['parameters']),
 'temporal':temporal_predict(rows+clips)}
 reports={}
 for name,pred in predictions.items():
  reports[name]={'wholeClip':metrics(rows,pred[:len(rows)]),'automatic':auto_stats(rows,clips,pred[len(rows):]),'perWord':{label:metrics([r for r in rows if r['label']==label],[p for r,p in zip(rows,pred) if r['label']==label]) for label in ['HELLO','THANK YOU','PLEASE','YES','NO','FINISH']}}
 winner=frozen['selected'];a=reports[winner]['wholeClip'];b=reports['baseline']['wholeClip'];gate=a['correct']>b['correct'] and a['wrong']<=b['wrong'] and a['unsupportedFalse']<=b['unsupportedFalse'] and a['syntheticFalse']<=b['syntheticFalse']
 aa=reports[winner]['automatic'];ab=reports['baseline']['automatic'];automatic_gate=aa['correctClips']>=ab['correctClips'] and all(aa[k]<=ab[k] for k in ['wrongSuggestions','repeatedSuggestions','unsupportedFalse','syntheticFalse'])
 result={'protocol':'Fresh recordings selected before tuning. Source signer splits disjoint. Prior evaluations used other recordings of test signers. Source-timestamp segmentation replay is not a real-time webcam test.','selectedBeforeTest':winner,'reports':reports,'wholeClipPromotionGate':gate,'automaticReplayGate':automatic_gate,'promoted':False,'remainingGates':['Real-time browser measurements','Physical webcam ordinary-motion negatives and live accuracy validation'],'predictions':[{k:r[k] for k in ['label','kind','sha256']}|{name:p[i] for name,p in predictions.items()} for i,r in enumerate(rows)]}
 output.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='predictions'},indent=2),flush=True)
if __name__=='__main__':freeze() if '--freeze' in sys.argv else evaluate()
