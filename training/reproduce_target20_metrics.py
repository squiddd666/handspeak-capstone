"""Re-infer the LOCKED candidate solely to verify reproducibility, never tune."""
import hashlib
import json
import sys
from pathlib import Path
from collections import Counter

import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from beginner_asl import _build_runtime


def main():
    cache=ROOT.parent/'handspeak-training';run=cache/'target20-v3'
    final=json.loads((run/'final-evaluation.json').read_text())
    checkpoint=Path(final['candidate'])
    assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==final['checkpoint_sha256']
    torch.set_num_threads(3);_,model,labels,_=_build_runtime(checkpoint)
    manifest=json.loads((cache/'target20-v2-manifest.json').read_text())
    records=[];checks=[]
    for split in ('val','test'):
        correct=Counter();raw_correct=Counter();unknown_total=0;unknown_false=0
        for row in manifest['samples']:
            if row['split']!=split:continue
            path=cache/'landmarks-v1'/(row['sha256']+'.npz')
            if not path.exists():continue
            with np.load(path) as data:x=torch.tensor(data['x'][None])
            with torch.no_grad():p=model(x).softmax(1)[0].numpy()
            best=int(p.argmax());prediction=labels[best] if best!=20 and p[best]>=final['gate'] else None
            correct[row['label']]+=prediction==row['label'];raw_correct[row['label']]+=labels[best]==row['label']
            if row['label']=='UNKNOWN':unknown_total+=1;unknown_false+=prediction is not None
            records.append(dict(split=split,sha256=row['sha256'],participant=row['participant'],label=row['label'],prediction=prediction))
        expected=final['splits'][split]
        assert unknown_total==expected['unknown_tracked'] and unknown_false==expected['unknown_false_accept']
        for label in labels[:20]:
            assert correct[label]==expected['per_word'][label]['correct']
            assert raw_correct[label]==expected['per_word'][label]['raw_correct']
        checks.append(dict(split=split,per_word_counts_match=True,unknown_counts_match=True))
    # Keep per-clip derived evidence private, never serve participant-linked rows.
    (run/'reproduction-predictions.json').write_text(json.dumps(records,indent=2))
    report=dict(passed=True,checkpoint_sha256=final['checkpoint_sha256'],checks=checks,
                purpose='Exact locked-model reproduction only; no selection or threshold changes')
    (run/'reproduction-check.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))


if __name__=='__main__':main()
