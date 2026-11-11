"""Development comparison. Publisher rows do not establish signer independence."""
import hashlib,json,pickle,time
from pathlib import Path
import numpy as np
import quickjs
from sklearn.ensemble import RandomForestClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[1]
prior=ROOT/'reports/alphabet-architecture-20261111'
out=ROOT/'reports/alphabet-phase3'
audit=json.loads((prior/'geometry-candidate-evaluation.json').read_text())
source=audit['dataset']; cache=Path(source['cache'])
for name,digest in source['files'].items():
    if hashlib.sha256((cache/name).read_bytes()).hexdigest()!=digest:raise ValueError(name+' hash mismatch')
mu=np.load(cache/'mean.npy'); sd=np.load(cache/'std.npy')
tr=np.load(cache/'X_train.npy')*sd+mu; te=np.load(cache/'X_test.npy')*sd+mu
y=np.load(cache/'y_train.npy'); yt=np.load(cache/'y_test.npy')
fit=audit['fitSourceRows']; val=audit['validationSourceRows']
assert not set(fit)&set(val)
keep=~np.isin(yt,[9,25]);te=te[keep];yt=yt[keep]
def key(row):return np.round(row[:63],6).astype('<f8').tobytes()
assert not {key(r) for r in tr[fit+val]} & {key(r) for r in te}
js=quickjs.Context()
js.eval((ROOT/'alphabet-features.js').read_text().replace('export ',''))
def features(rows):
    return np.array([json.loads(js.eval('JSON.stringify(alphabetFeatures('+json.dumps([dict(zip('xyz',p)) for p in row[:63].reshape(21,3)])+',.75))')) for row in rows])
x=features(tr[fit]); v=features(tr[val]); t=features(te)
probe=json.loads((prior/'tasks-current.json').read_text())['cases']
observed=[]; missing=[]
for case in probe:
    frame=case['rows'][-1]
    if not frame['usable']:
        missing.append(case['letter']);continue
    observed.append((case['letter'],[q[k] for q in frame['points'] for k in 'xyz']))
probe_x=features([np.array(r) for _,r in observed])
probe_y=np.array([ord(label)-65 for label,_ in observed])
report={'scope':'Publisher row split, development only; unknown signer/session IDs and label-map limitations. No camera fixtures trained on. Timing is Python CPU single-row prediction, not browser FPS.', 'source':source['source'],'fit':len(x),'validation':len(v),'test':len(t),'models':{}}
def score(p,truth,classes,g):
    ix=np.argsort(p,axis=1)
    a,b=ix[:,-1],ix[:,-2]; m=p[np.arange(len(p)),a]; n=p[np.arange(len(p)),b]
    pred=np.where((m>=g[0]) & (m-n>=g[1]),classes[a],-1)
    counts=dict(correct=int(sum(pred==truth)),wrong=int(sum((pred!=truth)&(pred!=-1))),abstain=int(sum(pred==-1)))
    matrix={}
    for k,q in zip(truth,pred):
        row=matrix.setdefault(chr(65+k),{}); label='abstain' if q==-1 else chr(65+q); row[label]=row.get(label,0)+1
    return counts,matrix
for name,model,columns in [
 ('coordinate-mlp',make_pipeline(StandardScaler(),MLPClassifier(hidden_layer_sizes=(64,32),max_iter=140,random_state=391)),slice(0,63)),
 ('geometry-mlp',make_pipeline(StandardScaler(),MLPClassifier(hidden_layer_sizes=(64,32),max_iter=140,random_state=391)),slice(None)),
 ('geometry-random-forest',RandomForestClassifier(n_estimators=96,max_depth=16,min_samples_leaf=2,random_state=391,n_jobs=1),slice(None))]:
    a,b,c=(q[:,columns] for q in (x,v,t))
    model.fit(a,y[fit]); vp=model.predict_proba(b)
    def objective(g):
        q,_=score(vp,y[val],model.classes_,g);return 5*q['wrong']+q['abstain']
    gate=min(((p,m) for p in [.5,.65,.8,.9,.95,.98,.995] for m in [.1,.2,.35]),key=objective)
    counts,matrix=score(model.predict_proba(c),yt,model.classes_,gate)
    times=[]
    for row in c[:64]:
        start=time.perf_counter_ns();model.predict_proba(row.reshape(1,-1));times.append((time.perf_counter_ns()-start)/1e6)
    report['models'][name]=dict(gate=gate,validation=score(vp,y[val],model.classes_,gate)[0],test=counts,confusion=matrix,pickleBytes=len(pickle.dumps(model)),medianMs=float(np.median(times)))
    transfer,matrix=score(model.predict_proba(probe_x[:,columns]),probe_y,model.classes_,gate)
    for label in missing:
        row=matrix.setdefault(label,{});row['abstain']=row.get('abstain',0)+1
    transfer['abstain']+=len(missing)
    report['models'][name]['referenceTransfer']=dict(counts=transfer,confusion=matrix,missingLandmarks=missing)
    print(name,counts,transfer,flush=True)
    (out/'comparison.json').write_text(json.dumps(report,indent=2))
