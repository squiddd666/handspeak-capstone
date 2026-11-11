"""Explore a two-model ensemble using validation rows only, without test input."""
import json,sys
from pathlib import Path
import numpy as np
import torch

sys.path.insert(0,str(Path(__file__).resolve().parent))
from train_target20 import CACHE,LABELS
from train_essential import ROOT,_build_runtime

def main():
    torch.set_num_threads(4)
    rows=[r for r in json.loads((CACHE/'target20-manifest.json').read_text())['samples'] if r['split']=='val']
    rows=[r for r in rows if (CACHE/'landmarks-v1'/(r['sha256']+'.npz')).exists()]
    x=torch.from_numpy(np.stack([np.load(CACHE/'landmarks-v1'/(r['sha256']+'.npz'))['x'] for r in rows]));y=np.array([LABELS.index(r['label']) for r in rows])
    _,candidate,labels,_=_build_runtime(CACHE/'target20-candidate.pt')
    _,base,base_labels,_=_build_runtime(ROOT/'models/beginner-need79-v6.pt')
    def infer(model):
        with torch.no_grad():return torch.cat([model(batch).softmax(1) for batch in x.split(16)]).numpy()
    p=infer(candidate);old=infer(base);mapping=np.array([LABELS.index(name) if name in LABELS else LABELS.index('UNKNOWN') for name in base_labels]);mapped=np.zeros((len(y),len(LABELS)))
    for i,j in enumerate(mapping):mapped[:,j]+=old[:,i]
    known=y!=LABELS.index('UNKNOWN');results=[]
    for alpha in [0,.05,.1,.2,.3,.4,.5,.6,.7,.8,1]:
        score=(1-alpha)*p+alpha*mapped;pred=score.argmax(1)
        results.append(dict(base_weight=alpha,overall=float(np.mean(pred==y)),targets=float(np.mean(pred[known]==y[known])),unknown_correct=int(np.sum((pred==y)&~known)),unknown_total=int((~known).sum())))
    results.sort(key=lambda r:(r['overall'],r['targets']),reverse=True)
    output=dict(scope='Exploratory model selection on validation only; no test data consumed.',results=results)
    (CACHE/'target20-ensemble-comparison.json').write_text(json.dumps(output,indent=2))
    print(json.dumps(output,indent=2),flush=True)
if __name__=='__main__':main()
