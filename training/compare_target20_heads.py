"""Compare alternative classifiers on validation only; do not read the test split.

The input encoder has already been selected using this validation set, so these
results are exploratory and cannot serve as an independent final benchmark.
"""
import json,sys
from pathlib import Path
import numpy as np
import torch
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import confusion_matrix

sys.path.insert(0,str(Path(__file__).resolve().parent))
from train_target20 import CACHE, LABELS, augment
from train_essential import _build_runtime

def main():
    torch.set_num_threads(4);torch.manual_seed(71);rng=np.random.default_rng(71)
    # Explicitly use only train and validation arrays; the test data is never
    # consumed during model selection or threshold selection here.
    groups={'train':[],'val':[]}
    manifest=json.loads((CACHE/'target20-manifest.json').read_text())
    for row in manifest['samples']:
        if row['split'] not in groups: continue
        path=CACHE/'landmarks-v1'/(row['sha256']+'.npz')
        if path.exists():
            with np.load(path) as data:groups[row['split']].append((data['x'],LABELS.index(row['label']),row))
    train=groups['train'];val=groups['val']
    _,model,labels,length=_build_runtime(CACHE/'target20-candidate.pt');model.eval()
    x=np.stack([sample for row in train for sample in [row[0],augment(row[0],rng),augment(row[0],rng)]])
    y=np.array([row[1] for row in train for _ in range(3)])
    vx=np.stack([row[0] for row in val]);vy=np.array([row[1] for row in val])
    def features(data):
        parts=[]
        with torch.no_grad():
            for batch in torch.from_numpy(data).split(16):parts.append(model.encoder(batch).numpy())
        return np.concatenate(parts)
    tx=features(x);vf=features(vx);known=vy!=LABELS.index('UNKNOWN')
    with torch.no_grad():baseline=model(torch.from_numpy(vx)).argmax(1).numpy()
    results=[dict(name='existing neural head',overall=float(np.mean(baseline==vy)),targets=float(np.mean(baseline[known]==vy[known])))]
    models=[]
    for c in [.001,.01,.1,1,10,100]:
        models.append((f'logistic C={c}',make_pipeline(StandardScaler(),LogisticRegression(C=c,class_weight='balanced',max_iter=2500))))
    for c in [.01,.1,1,10,100]:
        for gamma in ['scale',.0001,.001,.01]:
            models.append((f'rbf C={c} gamma={gamma}',make_pipeline(StandardScaler(),SVC(C=c,gamma=gamma,class_weight='balanced'))))
    for name,candidate in models:
        candidate.fit(tx,y);pred=candidate.predict(vf)
        result=dict(name=name,overall=float(np.mean(pred==vy)),targets=float(np.mean(pred[known]==vy[known])),unknown_correct=int(np.sum((pred==vy)&~known)),unknown_total=int((~known).sum()))
        results.append(result);print(json.dumps(result),flush=True)
    results.sort(key=lambda x:(x['overall'],x['targets']),reverse=True)
    output=dict(scope='Exploratory validation only; no test rows or test labels used.',training_clips=len(train),training_augmented_examples=len(x),validation_clips=len(val),ranked_results=results)
    (CACHE/'target20-head-comparison.json').write_text(json.dumps(output,indent=2))
    print('BEST',json.dumps(results[0]),flush=True)

if __name__=='__main__':main()
