"""One locked final evaluation. Selection must exist; no tuning happens here."""
import csv
import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import torch
from scipy.stats import beta
from sklearn.metrics import confusion_matrix, f1_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from beginner_asl import _build_runtime

CACHE = ROOT.parent/'handspeak-training'
RUN = CACHE/os.environ.get('HANDSPEAK_TARGET20_RUN','target20-v2')


def main():
    global RUN
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-name',default=RUN.name)
    args=parser.parse_args()
    if Path(args.run_name).name!=args.run_name:raise ValueError('Run name must be a directory name')
    RUN=CACHE/args.run_name
    final = RUN/'final-evaluation.json'
    if final.exists():
        raise RuntimeError('Final evaluation is locked. Do not reuse test feedback to optimize this run.')
    selection = json.loads((RUN/'selection.json').read_text())
    manifest = json.loads((CACHE/'target20-v2-manifest.json').read_text())
    assert hashlib.sha256((CACHE/'target20-v2-manifest.json').read_bytes()).hexdigest()==selection['dataset_sha256']
    torch.set_num_threads(3)
    selected = Path(selection['selected_checkpoint'])
    blob = torch.load(selected, map_location='cpu', weights_only=True)
    blob['version'] = RUN.name+'-selected'; blob['gate'] = selection['selected_threshold']
    candidate = RUN/(RUN.name+'-selected.pt')
    if candidate.exists(): raise RuntimeError('Versioned candidate already exists')
    torch.save(blob,candidate)
    _, model, labels, length = _build_runtime(candidate)
    assert labels == manifest['labels'] and length == 32
    gate = selection['selected_threshold']; splits={}
    for split in ('val','test'):
        gold=[]; raw=[]; predicted=[]; times=[]; fresh=[]; failed=Counter()
        for row in manifest['samples']:
            if row['split']!=split: continue
            y=labels.index(row['label']); path=CACHE/'landmarks-v1'/(row['sha256']+'.npz')
            gold.append(y); fresh.append(bool(row.get('fresh_unknown')))
            if not path.exists():
                raw.append(22);predicted.append(22);times.append(None);failed[row['label']]+=1;continue
            with np.load(path) as data: x=torch.tensor(data['x'][None])
            start=time.perf_counter()
            with torch.no_grad(): probs=model(x).softmax(1)[0].numpy()
            times.append((time.perf_counter()-start)*1000)
            best=int(probs.argmax());raw.append(best)
            predicted.append(best if best!=20 and float(probs[best])>=gate else 21)
        gold=np.array(gold);raw=np.array(raw);predicted=np.array(predicted);fresh=np.array(fresh)
        counts=Counter(r['label'] for r in manifest['samples'] if r['split']==split)
        perword={}
        for i,label in enumerate(labels[:20]):
            mask=gold==i;tracked=mask&(raw!=22);tp=int(((predicted==i)&mask).sum());fp=int(((predicted==i)&~mask).sum())
            total=int(mask.sum());neg=int((~mask).sum());precision=tp/(tp+fp) if tp+fp else 0;recall=tp/total if total else 0
            latency=[t for t,k in zip(times,mask) if k and t is not None]
            confusion=Counter(labels[r] for r in raw[tracked] if r!=i and r<len(labels))
            perword[label]=dict(samples=total,tracked=int(tracked.sum()),correct=tp,
                               incorrect=int((mask&(predicted!=i)&(predicted<20)).sum()),
                               raw_correct=int((mask&(raw==i)).sum()),
                               raw_top1=float((raw[tracked]==i).mean()) if tracked.any() else 0.,
                               raw_end_to_end=float((raw[mask]==i).mean()) if mask.any() else 0.,
                               rejected=int((mask&(predicted==21)).sum()),
                               rejection_rate=float((mask&(predicted==21)).sum()/total) if total else 0.,
                               false_accepts=fp,false_acceptance_rate=fp/neg if neg else 0.,
                               tracking_failures=failed[label],precision=precision,recall=recall,
                               f1=2*precision*recall/(precision+recall) if precision+recall else 0.,
                               confused_with=dict(confusion.most_common(3)),
                               latency_median_ms=float(np.median(latency)) if latency else None,
                               latency_p95_ms=float(np.percentile(latency,95)) if latency else None)
        unknown=gold==20;known=~unknown;unknown_tracked=unknown&(raw!=22)
        new=unknown_tracked&fresh;false=int((unknown_tracked&(predicted<20)).sum());n=int(unknown_tracked.sum())
        new_false=int((new&(predicted<20)).sum());new_n=int(new.sum())
        upper=lambda k,n: float(beta.ppf(.95,k+1,n-k)) if n and k<n else 1.
        matrix=confusion_matrix(gold,predicted,labels=list(range(23))).tolist()
        splits[split]=dict(per_word=perword,macro_f1=float(f1_score(gold,predicted,labels=list(range(20)),average='macro',zero_division=0)),
                           raw_macro_f1=float(f1_score(gold,raw,labels=list(range(20)),average='macro',zero_division=0)),
                           accuracy=float((gold[known]==predicted[known]).mean()),
                           raw_tracked_accuracy=float((gold[known&(raw!=22)]==raw[known&(raw!=22)]).mean()),
                           unknown_false_accept=false,unknown_tracked=n,unknown_far=false/n if n else None,
                           unknown_far_upper_95=upper(false,n),fresh_unknown_false_accept=new_false,fresh_unknown_tracked=new_n,
                           fresh_unknown_far_upper_95=upper(new_false,new_n),unknown_tracking_failures=failed['UNKNOWN'],
                           confusion_matrix=matrix,confusion_labels=labels+['REJECT','TRACKING_FAILURE'],counts=dict(counts))
    result=dict(candidate=str(candidate),checkpoint_sha256=hashlib.sha256(candidate.read_bytes()).hexdigest(),
                selection=selection,labels=labels,gate=gate,splits=splits,production_promoted=False,
                test_scope='Previously exposed known-word regression set plus newly reserved unknown glosses; not a fresh independent known-word benchmark.',
                confidence='Uncalibrated model scores; rejection gate chosen only from validation.',
                physical_webcam_tested=False)
    final.write_text(json.dumps(result,indent=2))
    candidate.with_suffix('.report.json').write_text(json.dumps(dict(labels=labels,selected_gate=gate,ready=False,
                                                                   checkpoint_sha256=result['checkpoint_sha256']),indent=2))
    write_reports(result,manifest)
    print(json.dumps({s:{k:v for k,v in m.items() if k not in ('per_word','confusion_matrix','confusion_labels','counts')} for s,m in splits.items()},indent=2))


def write_reports(result,manifest):
    test=result['splits']['test'];val=result['splits']['val'];labels=result['labels'][:20]
    with (ROOT/'target20_per_word_evaluation.csv').open('w',newline='',encoding='utf-8') as f:
        fields=['word','train_samples','validation_samples','test_samples',*test['per_word'][labels[0]].keys()]
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for label in labels:
            counts={s:sum(r['label']==label and r['split']==s for r in manifest['samples']) for s in ('train','val','test')}
            writer.writerow(dict(word=label,train_samples=counts['train'],validation_samples=counts['val'],test_samples=counts['test'],**test['per_word'][label]))
    matrix=np.array(test['confusion_matrix']);fig,ax=plt.subplots(figsize=(15,12));im=ax.imshow(matrix,cmap='Blues');fig.colorbar(im,ax=ax)
    ax.set_xticks(range(23),test['confusion_labels'],rotation=90);ax.set_yticks(range(23),test['confusion_labels'])
    for i,j in zip(*np.nonzero(matrix)):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=7,color='white' if matrix[i,j]>matrix.max()/2 else 'black')
    ax.set(xlabel='Prediction',ylabel='Reference',title='Target-20: locked recorded-clip regression evaluation, including rejection/tracking failures')
    fig.tight_layout();fig.savefig(ROOT/'target20_confusion_matrix.png',dpi=160);plt.close(fig)
    commands=['.\\.venv\\Scripts\\python.exe -X utf8 training/target20_expand_unknown.py',
              '.\\.venv\\Scripts\\python.exe -X utf8 training/audit_target20_data.py',
              '.\\.venv\\Scripts\\python.exe -X utf8 training/train_target20_v2.py',
              '.\\.venv\\Scripts\\python.exe -X utf8 training/train_target20_v3.py',
              "$env:HANDSPEAK_TARGET20_RUN='target20-v3'",
              '.\\.venv\\Scripts\\python.exe -X utf8 training/evaluate_target20_v2.py',
              '.\\.venv\\Scripts\\python.exe -X utf8 -m unittest discover -s training -v',
              '.\\.venv\\Scripts\\python.exe -X utf8 -m unittest discover -s training/accuracy -v']
    training=['# Target-20 training report — NOT READY','',f"Candidate: `{result['candidate']}`",f"SHA-256: `{result['checkpoint_sha256']}`",'',
              result['test_scope'],result['confidence'],'','## Validation-only architecture comparison','',
              '| Candidate | Pretrained | Selected gate | Validation macro F1 | Unknown false accepts |','| --- | --- | ---: | ---: | ---: |']
    for trial in result['selection']['trials']:
        m=trial['validation'];training.append(f"| {trial['name']} | {trial['pretrained']} | {m['gate']:.3f} | {m['macro_f1']:.3f} | {m['unknown_false_accept']}/{m['unknown_total']} |")
    training+=['','TCN: masked positions, valid-only velocities, palm-relative shape, temporal convolution, group normalization, balanced cross entropy, mild endpoint-preserving augmentation, AdamW, ReduceLROnPlateau, 20-epoch patience; seeds 42 and 71. Full TCN configuration/history is private in ../handspeak-training/target20-v2/selection.json. The subsequent v3 RBF correction uses a frozen from-scratch TCN embedding, three predeclared kernel widths (2,8,32), balanced kernel ridge penalty .1, and fixed logit scale .15; the distance kernel decays toward uncertainty on distant embeddings. Full trial and threshold records are in ../handspeak-training/target20-v3/selection.json. No test predictions were used for either iteration.',
               'The preserved ST-GCN is compared under the same expanded validation set. Its historical source exposure is not independently audited. Selection is not proof that its inherited test provenance is clean.',
               'Validation was reused for early stopping, selection, and thresholds; the selection estimate is optimistic. Binomial bounds assume independent clips; repeated signers introduce clustering.',
               'No test predictions were read by the selection script. After selection was locked, the final evaluator ran once. Do not use its failures for further tuning on this same benchmark.','',
               '## Recorded-clip results','',f"Validation target macro F1: {val['macro_f1']:.3f}; test target macro F1: {test['macro_f1']:.3f}.",
               f"Test end-to-end correct recognition: {test['accuracy']:.1%}; raw tracked accuracy: {test['raw_tracked_accuracy']:.1%}.",
               f"Unknown false acceptance: {test['unknown_false_accept']}/{test['unknown_tracked']}; one-sided 95% binomial upper bound {test['unknown_far_upper_95']:.1%}.",
               f"Newly reserved unknowns only: {test['fresh_unknown_false_accept']}/{test['fresh_unknown_tracked']}; upper bound {test['fresh_unknown_far_upper_95']:.1%}.",
               'Per-word latency is CPU inference only, not browser tracking/capture/network latency. Raw top-1 excludes tracking failures; recall and end-to-end accuracy count them as unsuccessful. False acceptance per word uses all other classes as its denominator.',
               'Linguistic label/variant correctness still needs qualified ASL review. A finite full capture window does not prove a linguistically complete sign.','',
               '## Reproduction','', 'Run from C:/Users/Squid/Desktop/capstonev2. Versioned trainers/evaluator refuse overwrites; use a clean private research directory or an explicitly new run version for reproduction. Never erase old results to retune against the test set.','```powershell',*commands,'```','',
               'Dataset: https://www.microsoft.com/en-us/research/project/asl-citizen/ . Terms: https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/ . Raw clips and derived landmarks are restricted research materials; keep them outside the web root.','']
    (ROOT/'target20_training_report.md').write_text('\n'.join(training),encoding='utf-8')
    webcam=['# Target-20 physical webcam report — BLOCKED','',
            'The user explicitly confirmed that no physical webcam or ASL signer is available. Windows Camera/Image enumeration returned no present devices. No physical recording was counted. Prerecorded reference videos are not substituted for real-user attempts.','',
            '| Word | Required independent attempts | Actual attempts | Correct | Status |','| --- | ---: | ---: | ---: | --- |']
    webcam += [f'| {label} | 10 | 0 | Not measured | BLOCKED |' for label in labels]
    webcam += ['', 'Speed, distance, lighting, background, position, incomplete/unknown signs, temporary tracking loss, and end-to-end latency remain unmeasured on a real webcam.',
               'Automated capture-controller tests and direct/API recorded-landmark tests are software checks only, not independent webcam attempts.','',
               'Resume with a connected webcam and a consenting ASL signer. Use the real browser panel, explicitly enable server landmark processing, perform 10 fresh complete attempts per word, and record expected label, predicted label/state, latency, condition, tracking failures and attempt identifier. Preserve all failures. Reserve new signers/data before tuning again.','']
    (ROOT/'target20_webcam_test_report.md').write_text('\n'.join(webcam),encoding='utf-8')
    failed=[l for l in labels if test['per_word'][l]['recall']<.8]
    checks=['# Target-20 acceptance checklist — NOT ACCEPTED','',
            '- PASS: all 20 exact requested labels represented and evaluated individually.',
            '- PASS (subset audit): source mappings, source hashes and official subset signer/hash separation verified; see private data audit. Linguistic expert review and inherited pretraining provenance remain unresolved.',
            f"- {'PASS' if val['macro_f1']>=.9 else 'FAIL'}: validation macro F1 >=90% ({val['macro_f1']:.1%}).",
            f"- {'PASS' if test['macro_f1']>=.85 else 'FAIL'}: regression-test macro F1 >=85% ({test['macro_f1']:.1%}); NOT an untouched new known-word test.",
            '- '+('FAIL' if failed else 'PASS')+': per-word test recall >=80%. Failing words: '+(', '.join(failed) or 'None')+'.',
            f"- {'PASS ON THIS CLIP SAMPLE' if test['unknown_far_upper_95']<=.05 else 'FAIL'}: unknown-FAR uncertainty bound <=5% ({test['unknown_far_upper_95']:.1%}); signer clustering and domain shift remain limitations.",
            '- BLOCKED: 200 independent physical-webcam attempts and >=8/10 correct for every word; no webcam/signer available.',
            '- NOT ESTABLISHED: real incomplete-sign rejection; capture-window checks do not establish linguistic completeness.',
            '- See final automated-test log/summary for remaining legacy-suite failures; do not mark all tests passed merely because target-20 tests pass.',
            '- PASS: stable checkpoint preserved; no production promotion or replacement performed.',
            '- Production approval: NOT REQUESTED; NOT READY.','']
    (ROOT/'target20_acceptance_checklist.md').write_text('\n'.join(checks),encoding='utf-8')
    summary=['# Target-20 final summary — INCOMPLETE / NOT READY','',
             f"Versioned candidate: `{result['candidate']}`.",f"Selection: {result['selection']['selected']}.",
             f"Validation/test target macro F1: {val['macro_f1']:.1%} / {test['macro_f1']:.1%}.",
             f"Test recall below 80%: {', '.join(failed) or 'None'}.",
             'Fixed explicit-consent handling, bounded capture/timeout behavior, duplicate-frame suppression, stale callback guards, malformed/no-hand/incomplete capture rejection, and distinct recognized/uncertain/unknown/incomplete/tracking-failure responses.',
             'Completed data audit, fixed validation-only architecture comparison, expanded unknown evidence, versioned training/selection/evaluation, per-word metrics and confusion matrix. Restricted inputs remain private.',
             'Physical webcam and signer are externally unavailable (confirmed by user). Known-word test was previously exposed; a fresh signer-held-out benchmark is required. Small per-class validation sets and inherited model provenance constrain further scientifically valid tuning. Do not keep optimizing against the final regression test.',
             'Remaining software-test failures are retained in the test logs; no passing result has been fabricated. Existing stable checkpoint was not overwritten. Do not promote this candidate.', '',
             'Next external requirements: physical webcam + consenting ASL signer; qualified linguistic review; additional consented signer-diverse training data and a genuinely untouched known-word evaluation set.','']
    (ROOT/'target20_final_summary.md').write_text('\n'.join(summary),encoding='utf-8')


if __name__=='__main__': main()
