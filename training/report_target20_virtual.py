"""Summarize streamed QA logs, including interrupted runs. No video data exported."""
import csv,json
from collections import Counter
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

root=Path(__file__).resolve().parents[1]
cache=root.parent/'handspeak-training'
def read(name):
    p=cache/name
    if (p/'results.json').exists(): return json.loads((p/'results.json').read_text())['results']
    return [json.loads(l) for f in p.glob('playlist-*/results.jsonl') for l in f.read_text().splitlines() if l.strip()]
original=read('virtual-v4-known-final')
retries=read('virtual-v4-known-missed')
by_hash={r['source_sha256']:r for r in original}
for r in retries:
    earlier=by_hash.get(r['source_sha256'],{})
    if (earlier.get('error') or '').startswith('Missed reserved clip slot') and r.get('camera_configuration_ok'):
        by_hash[r['source_sha256']]=r
known=list(by_hash.values())
controls=read('virtual-v4-rejection-controls')+read('virtual-v4-controls-recheck')+read('virtual-v4-confusables')
unknown=read('virtual-v4-unknown-final')
offline=json.loads((root/'target20_evaluation.json').read_text())
labels=offline['labels'][:20]
matrix=np.zeros((20,24),dtype=int)
rows=[]
for i,label in enumerate(labels):
    cases={r['source_sha256']:r for r in known if r['label']==label}.values()
    counts=Counter()
    for r in cases:
        p=r.get('predicted')
        if not r.get('camera_configuration_ok') or not r.get('full_source_window_captured'):
            counts['capture_failure']+=1;matrix[i,22]+=1
        elif (r.get('backend_response') or {}).get('state')=='tracking_failure':
            counts['tracking_failure']+=1;matrix[i,21]+=1
        elif p in labels:
            counts['correct' if r.get('correct') else 'wrong']+=1;matrix[i,labels.index(p)]+=1
        else:
            counts['rejected']+=1;matrix[i,20]+=1
    matrix[i,23]=max(0,10-len(cases))
    rows.append(dict(word=label,planned=10,distinct_attempts=len(cases),verified_streams=sum(bool(r.get('camera_configuration_ok')) for r in cases),full_source_windows=sum(bool(r.get('full_source_window_captured')) for r in cases),correct=counts['correct'],wrong=counts['wrong'],rejected=counts['rejected'],tracking_failure=counts['tracking_failure'],capture_failure=counts['capture_failure'],not_run=int(matrix[i,23]),meets_8_of_10=len(cases)>=10 and counts['correct']>=8))
with (root/'target20_per_word_results.csv').open('w',newline='',encoding='utf-8') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
fig,ax=plt.subplots(figsize=(14,10));im=ax.imshow(matrix,cmap='Blues',vmin=0,vmax=10)
ax.set_xticks(range(24),labels+['Rejected','Tracking failure','Capture failure','Not run'],rotation=90)
ax.set_yticks(range(20),labels);ax.set(xlabel='Browser outcome',ylabel='Reference',title='Target-20 simulated camera: measured outcomes and missing trials')
for i,j in zip(*matrix.nonzero()):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>5 else 'black')
fig.colorbar(im,ax=ax);fig.tight_layout();fig.savefig(root/'target20_confusion_matrix.png',dpi=150);plt.close(fig)
val=offline['splits']['val'];test=offline['splits']['test']
precision=np.divide(np.diag(matrix[:,:20]),matrix[:,:20].sum(0),out=np.zeros(20),where=matrix[:,:20].sum(0)>0)
recall=np.diag(matrix[:,:20])/10
f1=np.divide(2*precision*recall,precision+recall,out=np.zeros(20),where=precision+recall>0)
virtual_macro=float(f1.mean())

n=sum(r['distinct_attempts'] for r in rows);ok=sum(r['correct'] for r in rows);coverage=sum(r['distinct_attempts']>0 for r in rows)
verified=sum(bool(r.get('camera_configuration_ok')) for r in known)
full=sum(bool(r.get('full_source_window_captured')) for r in known)
offline_far=f"{test['unknown_false_accept']}/{test['unknown_tracked']}"
report=f"""# Target-20 virtual-camera report — simulated, not accepted

Chromium file-backed getUserMedia, 640×480 at 15 FPS, through the real HandSpeak capture UI, browser Holistic tracking and local Python API. No landmarks or predictions were injected. Warm-ups and transformed clips are not counted as distinct test recordings. The candidate and rejection threshold were pinned before these browser results.

Known-word test is a regression on recordings already exposed to prior offline evaluation, not an untouched benchmark. {n}/200 distinct reserved clips logged across {coverage}/20 words; {verified} had a started capture with verified camera settings, {full} had a verified full source window, and {ok} were correctly recognized. {len(retries)} missed-slot retries logged; a retry replaces the original in the summary only when no recording started previously and the retry has verified camera settings. Missing and failed slots are retained separately.

Virtual end-to-end macro F1 (capture failures included): {virtual_macro:.1%}. This is not an untouched test result. A reserved clip with no actual recording is a failed case, not an independent signing attempt. Full-source-window verification uses media-time bounds; it does not prove per-frame tracker quality.

## Pipeline findings

The isolated browser hand detector initially produced no hands despite body tracking. Switching the Target-20 capture path to Holistic restored hand observations and API submissions in validation pilots. A capture-level check now evaluates continuity within the visible-hand interval rather than rejecting every sign that uses less than half of the full capture window. This does not establish linguistic completeness. Cold tracker initialization was moved ahead of the countdown. Timing failures in the full playlist are retained; they are not model rejections.

## Rejection controls

| Scenario | Observed result |
|---|---|
"""
for r in controls:
    report+=f"| {r['scenario']} | {r.get('status') or r.get('error') or 'Not recorded'}; prediction: {r.get('predicted') or 'none'} |\n"
if not controls:report+="| All controls | No completed control result yet |\n"
eligible=[r for r in unknown if r.get('full_source_window_captured') and (r.get('backend_response') or {}).get('state') in ['recognized','unknown','uncertain']]
report+=f"""
Independent browser unknown clips: {len(unknown)}/100 attempted, {len(eligible)} with a verified full capture and recognition decision, {sum(bool(r.get('predicted')) for r in eligible)} falsely accepted. Capture failures are not counted as successful model rejections. The separate historical offline result ({offline_far}) is not browser evidence. Zero decisions from invalid/failed captures are not credited toward unknown-sign model rejection. MY and OUR are source-labeled validation controls, not expert-certified examples of visual confusability or deliberately malformed signing.

## Reproduce

Start the local QA server on port 8001 with HANDSPEAK_TARGET20_MODEL pointing to the private target20-v3-selected.pt. From the project root run:

    .venv/Scripts/python.exe -X utf8 training/target20_virtual_camera.py --playlist --split test --per-word 10 --limit 200 --workers 2 --output ../handspeak-training/virtual-v4-known-final
    .venv/Scripts/python.exe -X utf8 training/target20_virtual_camera.py --playlist --split val --phase rejections --limit 7 --workers 1 --output ../handspeak-training/virtual-v4-rejection-controls
    .venv/Scripts/python.exe -X utf8 training/target20_virtual_camera.py --playlist --split test --phase rejections --offset 7 --limit 100 --workers 2 --output ../handspeak-training/virtual-v4-unknown-final
    .venv/Scripts/python.exe -X utf8 training/report_target20_virtual.py

Use new private run folders for reruns. Keep recordings, generated streams, screenshots of signers, and detailed attempt logs private.
"""
(root/'target20_virtual_camera_report.md').write_text(report,encoding='utf-8')
checks=cache/'target20-virtual-software.log'
software=checks.read_text(errors='replace') if checks.exists() else ''
software_summary='; '.join(l.strip() for l in software.splitlines() if l.startswith(('Ran ','OK','FAILED'))) or 'pending'
summary=f"""# Target-20 final summary — NOT ACCEPTED

Virtual camera only. {coverage}/20 words have reserved clip outcomes; {verified}/{n} clips started with verified stream settings, {full}/{n} met the full-source-window rule, and {ok} were correctly recognized. See the per-word CSV for missing, failed, rejected and recognized attempts. No candidate was promoted.

- Browser acceptance (8/10 per word): {sum(r['meets_8_of_10'] for r in rows)}/20 words meet it.
- Frozen offline validation macro F1: {val['macro_f1']:.1%} (target 90%).
- Frozen offline regression macro F1: {test['macro_f1']:.1%} (target 85% on untouched data); the known-word benchmark is not untouched.
- Frozen offline per-word recall ≥80%: {sum(v['recall']>=.8 for v in test['per_word'].values())}/20.
- Independent browser unknown rejection: {len(eligible)} scored decisions; {sum(bool(r.get('predicted')) for r in eligible)} false accepts; acceptance is not established without sufficient eligible coverage.
- Software suites: {software_summary}. Legacy numeric fixtures were retained unchanged; parity checks use independent Python calculations and no longer assert those archived fixtures measure current model accuracy.

Further model/preprocessing tuning against these exposed final clips would invalidate the evaluation. New authorized signer-separated training/validation data and a genuinely untouched known-word test are required before another quality claim. The current pipeline and model still fail acceptance; this is not a successful release.

No physical webcam or signer is required. An authorized, genuinely untouched known-word dataset is still needed for the untouched-test gate. Do not tune against these regression results.
"""
(root/'target20_acceptance_checklist.md').write_text(summary.replace('final summary','acceptance checklist'),encoding='utf-8')
(root/'target20_final_summary.md').write_text(summary+'\nReports: target20_virtual_camera_report.md, target20_per_word_results.csv, target20_confusion_matrix.png, target20_acceptance_checklist.md.\n',encoding='utf-8')


