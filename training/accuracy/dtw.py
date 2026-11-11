"""Fit expanded DTW including explicit unsupported references; validation only."""
import sys,json,itertools,hashlib
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np,quickjs
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fit_words import distance,mirror,predict
from temporal import ROOT,metrics,score,nuisance
SITE=Path(__file__).resolve().parents[2]
def encode(rows):
 js=quickjs.Context();js.eval((SITE/'motion-model.js').read_text().replace('export ',''))
 for r in rows:
  if 'sequence' not in r:r['sequence']=json.loads(js.eval('JSON.stringify(encodeMotion('+json.dumps(r['rawFrames'])+','+str(r['imageAspect'])+'))'))
 return rows
def init(references):
 global refs
 refs=[np.array(r['sequence']) for r in references]
def compare(sequence):
 if sequence is None:return [float('inf')]*len(refs)
 a=np.array(sequence);m=mirror(a);return [min(distance(a,b),distance(m,b)) for b in refs]
def matrix(rows,train,name):
 signature=hashlib.sha256(json.dumps([(r['sha256'],r.get('sequence')) for r in rows]+[(r['label'],r['sequence']) for r in train]).encode()).hexdigest();path=ROOT/(name+'.npz')
 if path.exists():
  d=np.load(path)
  if str(d['signature'])==signature:return d['matrix']
 result=[]
 with ProcessPoolExecutor(max_workers=2,initializer=init,initargs=(train,)) as pool:
  for line in pool.map(compare,[r.get('sequence') for r in rows]):
   result.append(line)
   if len(result)%12==0:print(name,len(result),'/',len(rows),flush=True)
 m=np.array(result);np.savez(path,signature=signature,matrix=m);return m
def classify(mat,refs,p):
 result=[]
 for row in mat:
  if not np.isfinite(row).any():result.append(None);continue
  out=predict(row[None,:],refs,p)[0];result.append(None if out=='UNKNOWN' else out)
 return result
if __name__=='__main__':
 rows=json.loads((ROOT/'development-features.json').read_text());train=[dict(r,label=r['label'] if r['kind']=='supported' else 'UNKNOWN') for r in rows if r['split']=='train' and r['sequence']];val=[r for r in rows if r['split']=='val'];val+=nuisance(val,24,456);encode(val)
 model=json.loads((SITE/'models/asl-words.json').read_text());base=model['samples'];combined=train+base;m=matrix(val,combined,'validation-distances');best=None
 for limit,ratio,votes,strong in itertools.product([.2,.3,.4,.5,.65,.8,1.],[1,1.2,1.5],[1,2],[1.5,2.5,5.]):
  p=dict(maxDistance=limit,minRatio=ratio,minVotes=votes,mirror=True,strongRatio=strong);out=classify(m[:,:len(train)],train,p);stats=metrics(val,out);entry=dict(parameters=p,metrics=stats,score=score(stats))
  if best is None or entry['score']<best['score']:best=entry
 baseline=metrics(val,classify(m[:,len(train):],base,model['parameters']))
 (ROOT/'dtw-candidate.json').write_text(json.dumps(dict(parameters=best['parameters'],samples=[dict(label=r['label'],sequence=r['sequence']) for r in train]),separators=(',',':')))
 (ROOT/'dtw-validation.json').write_text(json.dumps(dict(best=best,baseline=baseline,trainingReferences=len(train)),indent=2));print(json.dumps(dict(best=best,baseline=baseline),indent=2),flush=True)
