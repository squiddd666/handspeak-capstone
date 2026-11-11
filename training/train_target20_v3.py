"""Targeted validation-only novelty correction after softmax overconfidence.

Three predeclared kernel widths, one ridge penalty, one fixed score scale.
No test arrays opened and no production checkpoint replaced.
"""
import hashlib
import argparse
import json
from pathlib import Path
import numpy as np
import torch
from train_target20_v2 import CACHE, load_selection, augment, probabilities, threshold
from target20_candidate import RBFCandidate
from beginner_asl import _build_runtime


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-name',default='target20-v3');parser.add_argument('--source-run',default='target20-v2')
    args=parser.parse_args()
    if any(Path(n).name!=n for n in [args.run_name,args.source_run]):raise ValueError('Run names must be directory names')
    run=CACHE/args.run_name;run.mkdir(exist_ok=True)
    if (run/'selection.json').exists():raise RuntimeError('Versioned run already exists')
    torch.set_num_threads(3);torch.manual_seed(42);rng=np.random.default_rng(42)
    manifest,groups,failures=load_selection()
    previous=json.loads((CACHE/args.source_run/'selection.json').read_text())
    source=CACHE/args.source_run/'target20-v2-tcn-s42.pt'
    _,encoder,labels,_=_build_runtime(source)
    x=torch.tensor(np.stack([a for r in groups['train'] for a in [r[0],augment(r[0],rng),augment(r[0],rng)]]))
    y=np.array([r[1] for r in groups['train'] for _ in range(3)])
    vx=torch.tensor(np.stack([r[0] for r in groups['val']]))
    vy=np.array([r[1] for r in groups['val']])
    missing=np.array([labels.index(r['label']) for r in failures if r['split']=='val'],dtype=int)
    with torch.no_grad():features=torch.cat([encoder.embedding(c) for c in x.split(32)])
    mean=features.mean(0);scale=features.std(0).clamp(min=.03)
    z=torch.nn.functional.normalize((features-mean)/scale,dim=1)
    distances=torch.cdist(z,z).square()
    targets=torch.nn.functional.one_hot(torch.tensor(y,dtype=torch.long),21).float()
    count=np.bincount(y,minlength=21)
    weights=torch.tensor(len(y)/(21*count[y]),dtype=torch.float32)
    trials=[]
    for gamma in (2.,8.,32.):
        model=RBFCandidate(len(z),gamma=gamma)
        model.encoder.load_state_dict(encoder.state_dict())
        model.mean.copy_(mean);model.scale.copy_(scale);model.support.copy_(z)
        kernel=torch.exp(-gamma*distances)
        coefficients=torch.linalg.solve(kernel+.1*torch.diag(1/weights),targets)
        model.coefficients.copy_(coefficients)
        chosen,attempts=threshold(probabilities(model,vx),vy,missing)
        name=f'target20-v3-rbf-g{int(gamma)}';path=run/(name+'.pt')
        torch.save(dict(architecture='target20-rbf-v3',state_dict=model.state_dict(),labels=labels,T=32,
                        version=name,support_count=len(z),gamma=gamma,temperature=.15,seed=42,gate=chosen['gate']),path)
        trial=dict(name=name,checkpoint=str(path),validation=chosen,threshold_trials=attempts,pretrained=False)
        trials.append(trial);print(name,chosen,flush=True)
    old=next(t for t in previous['trials'] if t['name']==previous['selected'])
    trials.append(old)
    selected=max(trials,key=lambda t:(t['validation']['unknown_far_upper_95']<=.05,t['validation']['macro_f1']))
    result=dict(protocol='Targeted RBF novelty head after v2 validation exposed overconfidence; three fixed widths (2,8,32), ridge .1, temperature .15; no test arrays opened.',
                labels=labels,dataset_sha256=hashlib.sha256((CACHE/'target20-v2-manifest.json').read_bytes()).hexdigest(),
                trials=trials,selected=selected['name'],selected_checkpoint=selected['checkpoint'],selected_threshold=selected['validation']['gate'],
                test_evaluation_performed=False,limitations=previous['limitations'],previous_run=str(CACHE/'target20-v2/selection.json'))
    (run/'selection.json').write_text(json.dumps(result,indent=2))
    print('SELECTION LOCKED',selected['name'],selected['validation'],flush=True)


if __name__=='__main__':main()
