"""Auditable candidate only: no original/AISA test imagery enters training.

Publisher row partitions lack signer IDs. Reported held-out row performance is
NOT independent-signer accuracy. The publisher card's 24/26-label inconsistency
is retained in the audit and prevents an independent-signer claim.
"""
from pathlib import Path
import json,hashlib,os
os.environ.setdefault('OPENBLAS_NUM_THREADS','2');os.environ.setdefault('OMP_NUM_THREADS','2')
import numpy as np
import quickjs
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import confusion_matrix

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'reports/alphabet-architecture-20261111'

def main():
    provenance=json.loads((OUT/'landmark-dataset-source.json').read_text());cache=Path(provenance['cache'])
    mean=np.load(cache/'mean.npy',allow_pickle=False);std=np.load(cache/'std.npy',allow_pickle=False)
    train=np.load(cache/'X_train.npy',allow_pickle=False)*std+mean;labels=np.load(cache/'y_train.npy',allow_pickle=False)
    test=np.load(cache/'X_test.npy',allow_pickle=False)*std+mean;test_labels=np.load(cache/'y_test.npy',allow_pickle=False)
    js=quickjs.Context();js.eval((ROOT/'alphabet-features.js').read_text().replace('export ',''))
    def features(raw,mirror=1,angle=0):
        p=raw[:63].reshape(21,3).copy();p[:,0]=(p[:,0]-.5)*mirror+.5
        if angle:
            xy=p[:,:2]*[1,.75];center=xy[0].copy();v=xy-center;c=np.cos(angle);s=np.sin(angle);xy=v@np.array([[c,s],[-s,c]])+center;p[:,:2]=xy/[1,.75]
        points=[dict(zip(['x','y','z'],r))for r in p]
        f=json.loads(js.eval('JSON.stringify(alphabetFeatures('+json.dumps(points)+',.75))'))
        return f
    def digest(r):return hashlib.sha256(np.round(r[:63],6).astype('<f8').tobytes()).hexdigest()
    # Preserve publisher test. Quarantine exact overlaps rather than train on
    # their twins; cluster exact duplicate source observations before splitting.
    heldout_hash={digest(r)for r,l in zip(test,test_labels)if l not in [9,25]}
    seen=set();rows=[];y=[];ids=[];removed={'duplicateTrain':0,'overlapWithPublisherTest':0,'motionSnapshots':0}
    for i,(r,l)in enumerate(zip(train,labels)):
        if l in [9,25]:removed['motionSnapshots']+=1;continue
        h=digest(r)
        if h in heldout_hash:removed['overlapWithPublisherTest']+=1;continue
        if h in seen:removed['duplicateTrain']+=1;continue
        seen.add(h);rows.append(r);y.append(int(l));ids.append(i)
    ix=np.arange(len(rows));fit,val=train_test_split(ix,test_size=.2,random_state=391,stratify=y)
    X=[];Y=[]
    for i in fit:
        for mirror,angle in [(1,0),(-1,0),(1,-.12),(-1,.12)]:
            f=features(rows[i],mirror,angle)
            if f is not None:X.append(f);Y.append(y[i])
    X=np.array(X);Y=np.array(Y);scaler=StandardScaler().fit(X);X=scaler.transform(X)
    clf=MLPClassifier(hidden_layer_sizes=(64,32),alpha=.01,max_iter=500,early_stopping=True,validation_fraction=.12,n_iter_no_change=25,random_state=391)
    clf.fit(X,Y)
    def dataset(seq,ys):
        fs=[];ls=[]
        for r,l in zip(seq,ys):
            if l in [9,25]:continue
            f=features(r)
            if f is not None:fs.append(f);ls.append(int(l))
        return scaler.transform(np.array(fs)),np.array(ls)
    V,vy=dataset([rows[i]for i in val],[y[i]for i in val]);vp=clf.predict_proba(V);order=np.argsort(vp,axis=1);best=None
    for probability in [.90,.95,.98,.995]:
        for margin in [.15,.25,.4]:
            mx=vp[np.arange(len(V)),order[:,-1]];second=vp[np.arange(len(V)),order[:,-2]];pred=clf.classes_[order[:,-1]];accept=(mx>=probability)&(mx-second>=margin)&(np.max(np.abs(V),axis=1)<=8)
            correct=int(np.sum(accept&(pred==vy)));wrong=int(np.sum(accept&(pred!=vy)));rejected=int(np.sum(~accept));objective=5*wrong+rejected
            if best is None or objective<best[0]:best=(objective,probability,margin,correct,wrong,rejected)
    parameters={'minProbability':best[1],'minMargin':best[2],'maxZScore':8}
    model={'schema':'alphabet-joints-v1','featureCount':100,'labels':[chr(65+int(v))for v in clf.classes_],'mean':scaler.mean_.tolist(),'std':scaler.scale_.tolist(),'weights':[w.tolist()for w in clf.coefs_],'biases':[b.tolist()for b in clf.intercepts_],
      'parameters':parameters,'license':'CC-BY-4.0 derived training data; project implementation separate','source':provenance['source'],'sourceRevision':provenance['revision'],
      'limitations':['Publisher label indices interpreted as A=0 through Z=25; card claims 24 static classes but arrays have 26. J/Z snapshots excluded.','No signer IDs; not signer-independent.','Source camera aspect ratio unspecified; 4:3 assumption is explicit.','Candidate; not promoted solely on reference regression.']}
    # Test is evaluated once, only after validation gates are frozen.
    T,ty=dataset(test,test_labels);tp=clf.predict_proba(T);order=np.argsort(tp,axis=1);mx=tp[np.arange(len(T)),order[:,-1]];second=tp[np.arange(len(T)),order[:,-2]];pred=clf.classes_[order[:,-1]]
    accept=(mx>=best[1])&(mx-second>=best[2])&(np.max(np.abs(T),axis=1)<=8)
    stats={'correct':int(np.sum(accept&(pred==ty))),'wrong':int(np.sum(accept&(pred!=ty))),'rejected':int(np.sum(~accept)),'total':len(ty)}
    report={'scope':'Publisher-held-out row test, NOT signer-independent; thresholds chosen using validation only. No original photo or AISA frame enters this training.',
      'removed':removed,'fitSourceRows':[ids[i]for i in fit],'validationSourceRows':[ids[i]for i in val],'trainingAugmentedRows':len(X),'validation':{'correct':best[3],'wrong':best[4],'rejected':best[5],'total':len(vy)},'test':stats,'parameters':parameters,'iterations':clf.n_iter_,'dataset':provenance,'limitations':model['limitations']}
    (OUT/'geometry-candidate.json').write_text(json.dumps(model,separators=(',',':')))
    (OUT/'geometry-candidate-evaluation.json').write_text(json.dumps(report,indent=2))
    # Numerical parity fixture is validation-only, with explicit provenance.
    (OUT/'geometry-parity.json').write_text(json.dumps({'input':rows[val[0]][:63].reshape(21,3).tolist(),'aspect':.75,'probabilities':vp[0].tolist(),'labels':model['labels']}))
    print(json.dumps({k:v for k,v in report.items()if k not in ['fitSourceRows','validationSourceRows','dataset']},indent=2))

if __name__=='__main__':main()
