"""Convenience-set evaluation; not a WLASL benchmark or webcam evaluation."""
import json, hashlib
from pathlib import Path
from runtime import ROOT,LABELS,CHECKPOINT,predict

rows=[]
for label in LABELS:
    path=ROOT/'media'/'signs'/f'{label}.mp4'
    if not path.exists():continue
    try:
        result=predict(path)
    except Exception as e:
        result=dict(predicted=None,confidence=None,top5=[],error=str(e))
    row=dict(expected=label,file=str(path.relative_to(ROOT)),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),**result)
    row['correct']=row['predicted']==label
    row['top5_correct']=label in [p['word'] for p in row['top5']]
    rows.append(row)
    print(f"{len(rows)} {label}: {row['predicted']} correct={row['correct']}",flush=True)
    report=dict(scope='Local existing reference clips; convenience set, generally one clip per word. Not official WLASL test, not signer-independent, not webcam accuracy. Training overlap not established.',checkpoint_reported_validation=CHECKPOINT.get('val_acc'),total=len(rows),correct=sum(r['correct'] for r in rows),top5_correct=sum(r['top5_correct'] for r in rows),failures=sum(r['predicted'] is None for r in rows),rows=rows)
    report['top1_accuracy']=report['correct']/len(rows)
    report['top5_accuracy']=report['top5_correct']/len(rows)
    (Path(__file__).parent/'reference-results.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2))
