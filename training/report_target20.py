"""Publish aggregate evidence only, never raw research clips or landmarks."""
import csv,json,statistics,hashlib
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from train_essential import ROOT

def main():
    cache=ROOT.parent/'handspeak-training';out=ROOT/'reports'/'target20';out.mkdir(parents=True,exist_ok=True)
    report=json.loads((cache/'target20-report.json').read_text())
    cameras=[]
    for name in ['target20-webcam.json','target20-webcam-variations.json','target20-webcam-retry.json','target20-webcam-variations-retry.json']:
        if (cache/name).exists():cameras+=json.loads((cache/name).read_text())['results']
    val=report['splits']['val'];test=report['splits']['test'];labels=report['labels'][:-1]
    clean_camera=[{k:v for k,v in r.items() if k not in ['camera_stream','source_sha256']} for r in cameras]
    diagnostic_runs={}
    for name in ['target20-webcam-initial.json','target20-webcam-before-alignment.json','target20-webcam-pilot.json','target20-webcam-aligned-pilot.json']:
        if (cache/name).exists():diagnostic_runs[name]=json.loads((cache/name).read_text())['results']
    evidence={k:v for k,v in report.items() if k not in ['checkpoint']}
    evidence.update(camera_results=clean_camera,diagnostic_runs=diagnostic_runs,physical_camera_tested=False,os_virtual_camera_tested=False,camera_scope='Chromium simulated webcam; user requested virtual-camera testing without OBS',ready=False)
    unknown_camera=[]
    if (cache/'target20-webcam-unknown.json').exists():
        unknown_camera=json.loads((cache/'target20-webcam-unknown.json').read_text())['results']
        if (cache/'target20-webcam-unknown-retry.json').exists():unknown_camera+=json.loads((cache/'target20-webcam-unknown-retry.json').read_text())['results']
        evidence['unknown_camera_results']=[{k:v for k,v in r.items() if k not in ['camera_stream','source_sha256']} for r in unknown_camera]
    (out/'evaluation.json').write_text(json.dumps(evidence,indent=2))
    config=dict(checkpoint='target20-candidate.pt',sha256=hashlib.sha256((cache/'target20-candidate.pt').read_bytes()).hexdigest(),labels=report['labels'],sequence_length=32,input_channels=['x','y','left_hand_mask','right_hand_mask'],rejection_gate=report['selected_gate'],pretrained_source_sha256=hashlib.sha256((ROOT/'models/beginner-need79-v6.pt').read_bytes()).hexdigest(),deployment_ready=False)
    (out/'model-config.json').write_text(json.dumps(config,indent=2))
    with (out/'per-word.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['word','samples','tracked','raw_correct','correct','incorrect','rejected','tracking_failures','accuracy','precision','recall','f1','camera_correct','camera_trials']);writer.writeheader()
        for label in labels:
            rows=[r for r in cameras if r['label']==label]
            writer.writerow(dict(word=label,**test['per_word'][label],camera_correct=sum(r['correct'] for r in rows),camera_trials=len(rows)))
    matrix=np.array(test['confusion_matrix']);fig,ax=plt.subplots(figsize=(15,12))
    im=ax.imshow(matrix,cmap='Blues');fig.colorbar(im,ax=ax)
    ax.set_xticks(range(len(matrix)),test['confusion_labels'],rotation=90);ax.set_yticks(range(len(matrix)),test['confusion_labels'])
    for i,j in zip(*np.nonzero(matrix)):ax.text(j,i,str(matrix[i,j]),ha='center',va='center',fontsize=8,color='white' if matrix[i,j]>matrix.max()/2 else 'black')
    ax.set(xlabel='Predicted',ylabel='Actual',title='20-word candidate: test confusion matrix (rejections and tracking failures included)');fig.tight_layout();fig.savefig(out/'confusion-matrix.png',dpi=160);plt.close(fig)
    pct=lambda v:f'{v*100:.1f}%'
    lines=['# 20-word recognition audit — NOT READY','',
      'Training and evaluation were executed. This candidate is an optional research preview; the original recognition features remain available.','',
      f"Validation raw target accuracy: **{pct(val['raw_accuracy'])}**; with rejection: **{pct(val['gated_accuracy'])}**.",
      f"Test raw target accuracy: **{pct(test['raw_accuracy'])}**; with rejection: **{pct(test['gated_accuracy'])}**.",
      f"Unknown test false accepts: **{test['unknown_false_accept']}/{test['unknown_tracked']}** tracked clips. Threshold {report['selected_gate']} was selected on validation only.",'',
      'Raw accuracy chooses the highest score without rejection and excludes tracking failures. Accepted accuracy below counts rejections and tracking failures as unsuccessful recognition; it is not accuracy only among accepted predictions.','',
      '| Word | Test clips | Raw correct | Accepted correct | Wrong | Rejected | Tracking failures | Accuracy | Precision | Recall | F1 | Camera correct/trials |',
      '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    weak=[]
    for label in labels:
        m=test['per_word'][label];rows=[r for r in cameras if r['label']==label]
        lines.append(f"| {label} | {m['samples']} | {m['raw_correct']} | {m['correct']} | {m['incorrect']} | {m['rejected']} | {m['tracking_failures']} | {pct(m['accuracy'])} | {pct(m['precision'])} | {pct(m['recall'])} | {m['f1']:.3f} | {sum(r['correct'] for r in rows)}/{len(rows)} |")
        if m['recall']<.9 or not rows or not all(r['correct'] for r in rows):weak.append(label)
    lines+=['','## Camera evidence','',f'{len(cameras)} automated trials ran through Chromium simulated `getUserMedia` camera input, the application tracker, recognition API, and result display. These are not OBS/OS virtual-camera or physical-webcam tests.',
      'Windows device enumeration and browser media-device enumeration found no physical camera; no OBS installation was found. Source videos were converted to Y4M for Chrome camera input. No predicted labels or landmark coordinates were injected. Warm-up captures were discarded; measured captures and failures are retained.',
      'Normal trials use one test clip per target. The variation run assigns slow, fast, dim, farther, or left-shifted input across the 20 targets. Failed initial trials may be repeated after a server fix; both original and retry results are included. This is not every condition for every signer or word.','']
    lines.append('The automated harness runs at most two camera trials concurrently. Latency includes that shared CPU/server load; it is not a calibrated single-user hardware benchmark.')
    lines.append('Initial startup-race failures and pre-alignment pilot attempts are retained separately under `diagnostic_runs` in evaluation.json. The scheduled normal/variation trials above use the corrected final pipeline; no failed measured final trial is removed.')
    if unknown_camera:lines.append(f"Additional virtual-camera unknown-sign trials: {len(unknown_camera)}; successful rejection through the recognition API: {sum(r['correct'] for r in unknown_camera)}. Missing API responses are capture failures, not successful rejections.")
    for key in ['capture_to_display_ms','api_to_display_ms']:
        times=[r[key] for r in cameras if r.get(key) is not None]
        if times:lines.append(f'{key}: median {statistics.median(times):.0f} ms; p95 {np.percentile(times,95):.0f} ms. Includes failed captures when measured; missing API times are not counted as zero.')
    lines += [f"Offline batched model time: {test['model_ms_per_clip']:.1f} ms/clip; this excludes tracking and is not webcam latency.",'',
      '## Additional recordings and remaining requirements','',
      'Words needing more recordings, model work, or successful camera verification: **'+', '.join(weak)+'**.',
      'Collect additional consented examples from new signers with varied camera distance, lighting, and signing speed. Reserve a genuinely new signer-held-out benchmark; do not repeatedly tune on this test set. The table identifies the observed per-word failures; more sample counts alone do not guarantee an accuracy target.',
      '95% validation, 90% unseen-test performance, per-word virtual-camera reliability, and unknown-sign rejection must all be verified before marking READY. A high aggregate score cannot substitute for these checks. Per the latest user instruction, testing uses a virtual camera without OBS; physical-camera testing is outside this run.','',
      *report['limitations'],'','## Reproduction and artifacts','',
      'Python 3.11 environment: `.venv`. Research data, full manifests, logs, Y4M camera input, and model weights remain outside the website in `../handspeak-training/`.',
      'Checkpoint: `target20-candidate.pt`; configuration and threshold: `target20-report.json` beside the checkpoint. Set `HANDSPEAK_TARGET20_MODEL` for a different private deployment path.',
      'Run `training/target20_data.py`, `training/train_target20.py`, `training/webcam_target20.py`, `training/webcam_target20.py --variations`, and `training/report_target20.py` with `.venv/Scripts/python.exe`. Start the application server separately before camera tests.',
      'See `evaluation.json`, `per-word.csv`, and `confusion-matrix.png` for machine-readable counts and the plotted confusion matrix.']
    (out/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(out/'README.md')
if __name__=='__main__':main()
