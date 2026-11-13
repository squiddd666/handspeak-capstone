"""Resumable 100-label reference test, not independent benchmark accuracy."""
import json,hashlib,urllib.request,concurrent.futures,csv,datetime,shutil
from pathlib import Path
import cv2
from runtime import ROOT,LABELS,CHECKPOINT,UPSTREAM,predict

HERE=Path(__file__).parent
DEST=HERE/'reference-videos';DEST.mkdir(exist_ok=True)
REFS={r['word']:r for r in json.loads((ROOT/'openhands-reference-videos.json').read_text())['rows']}
BASE=HERE/'reference-results-31.json'
if not BASE.exists():shutil.copy2(HERE/'reference-results.json',BASE)
cached={r['expected']:r for r in json.loads(BASE.read_text())['rows']}
OUTPUT=HERE/'all100-results.json'
previous={r['expected']:r for r in json.loads(OUTPUT.read_text())['rows']} if OUTPUT.exists() else {}
model_hash=hashlib.sha256((UPSTREAM/'lstm_model_v7.pth').read_bytes()).hexdigest()

def download(item):
    word,ref=item;path=DEST/f'{word}.mp4'
    try:
        if not path.exists():
            request=urllib.request.Request(ref['video'],headers={'User-Agent':'Mozilla/5.0'})
            temp=path.with_suffix('.part')
            with urllib.request.urlopen(request,timeout=45) as response,temp.open('wb') as f:
                total=0
                while True:
                    block=response.read(1024*256)
                    if not block:break
                    total+=len(block)
                    if total>50*1024*1024:raise ValueError('Video exceeds 50 MB safety limit')
                    f.write(block)
            temp.replace(path)
        cap=cv2.VideoCapture(str(path));ok,frame=cap.read();frames=int(cap.get(cv2.CAP_PROP_FRAME_COUNT));fps=cap.get(cv2.CAP_PROP_FPS);cap.release()
        if not ok:raise ValueError('Downloaded media does not decode')
        return word,dict(path=path,frames=frames,fps=fps,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    except Exception as e:return word,dict(error=str(e))

with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    downloads=dict(pool.map(download,REFS.items()))
print(f'Downloads: {sum("error" not in r for r in downloads.values())}/{len(REFS)} decodable',flush=True)
download_report={w:{k:str(v) if isinstance(v,Path) else v for k,v in row.items()} for w,row in downloads.items()}
(HERE/'download-manifest.json').write_text(json.dumps(download_report,indent=2))
rows=[]
def save():
    report=dict(scope='100-word reference convenience set: one clip per label; 31 previous local clips plus 69 dictionary references. Not independent WLASL benchmark or live webcam accuracy. Training overlap and sign variants not independently audited.',planned_total=100,complete=len(rows)==100,checkpoint_sha256=model_hash,checkpoint_reported_validation=CHECKPOINT.get('val_acc'),checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),total=len(rows),correct=sum(r['correct'] for r in rows),top5_correct=sum(r['top5_correct'] for r in rows),failures=sum(r['predicted'] is None for r in rows),rows=rows)
    report['top1_accuracy']=report['correct']/len(rows);report['top5_accuracy']=report['top5_correct']/len(rows)
    temp=OUTPUT.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2));temp.replace(OUTPUT)
    public=HERE/'reference-results.json';temp=public.with_suffix('.tmp');temp.write_text(json.dumps(report,indent=2));temp.replace(public)
    return report
for label in LABELS:
    if label in cached:
        row=dict(cached[label],source_type='previous-local-reference',reused_previous_prediction=True)
    else:
        info=downloads[label];ref=REFS[label]
        row=dict(expected=label,source_page=ref['page'],video_url=ref['video'],source_type='online-dictionary-reference',reused_previous_prediction=False)
        if 'error' in info:
            row.update(predicted=None,confidence=None,top5=[],error='Download failed: '+info['error'])
        else:
            row.update(file=str(info['path'].relative_to(ROOT)),sha256=info['sha256'],frames=info['frames'],fps=info['fps'])
            old=previous.get(label)
            if old and old.get('sha256')==info['sha256'] and 'error' not in old:
                row=old
            else:
                try:row.update(predict(info['path']))
                except Exception as e:row.update(predicted=None,confidence=None,top5=[],error=str(e))
        row['correct']=row['predicted']==label
        row['top5_correct']=label in [p['word'] for p in row['top5']]
    rows.append(row);report=save()
    print(f'{len(rows)}/100 {label}: {row["predicted"]} correct={row["correct"]}',flush=True)
with (HERE/'all100-results.csv').open('w',newline='') as f:
    writer=csv.DictWriter(f,fieldnames=['expected','predicted','correct','top5_correct','confidence','seconds','file','source_page','video_url','sha256','error']);writer.writeheader();writer.writerows({k:r.get(k) for k in writer.fieldnames} for r in rows)
print(json.dumps({k:v for k,v in report.items() if k!='rows'},indent=2),flush=True)
