"""Download and extract a reproducible 20-word ASL Citizen subset privately."""
import concurrent.futures as cf
import csv, hashlib, io, json, os, time
from pathlib import Path
from remotezip import RemoteZip
from train_essential import extract, ROOT
from download_essential_citizen import URL

TARGETS={'HELLO':'HELLO','THANKYOU':'THANK YOU','PLEASE':'PLEASE','SORRY':'SORRY',
 'YES':'YES','NO':'NO','HELP':'HELP','LOVE':'LOVE','ME':'I / ME','YOU':'YOU',
 'WANT1':'WANT','WANT2':'WANT','NEED':'NEED','LIKE':'LIKE','GOOD':'GOOD','BAD':'BAD',
 'WHAT1':'WHAT','WHAT2':'WHAT','WHERE':'WHERE','WHO':'WHO','EAT1':'EAT','EAT2':'EAT','WATER':'WATER'}
LABELS=list(dict.fromkeys(TARGETS.values()))+['UNKNOWN']
NEGATIVES={
 'train':['APPLE','CAR','BOOK','DRINK','NAME','HOME','FAMILY','FRIEND','WORK','SCHOOL','MONEY','TIRED','SAD','ANGRY','SLEEP','GO','BATHROOM','PHONE','FATHER','MOTHER'],
 'val':['AIRPLANE','BAG','BEFORE','BREAD','BROTHER','CHILD','CLOTHES','COME','FISH','FLOWER'],
 'test':['AFTER','BED','BOY','CALL','CAN','CHAIR','DOG','DOOR','FIND','FINE']}

def get_archive():
    for attempt in range(4):
        try:return RemoteZip(URL)
        except Exception:
            if attempt==3:raise
            time.sleep(2)

def download(cache):
    rows=[]
    with get_archive() as z:
        (cache/'use.txt').write_bytes(z.read('ASL_Citizen/use.txt'))
        for split in ['train','val','test']:
            data=z.read(f'ASL_Citizen/splits/{split}.csv');(cache/f'{split}.csv').write_bytes(data)
            source=list(csv.DictReader(io.StringIO(data.decode('utf-8-sig'))))
            selected=[r for r in source if r['Gloss'] in TARGETS]
            for gloss in NEGATIVES[split]:
                selected += [r for r in source if r['Gloss']==gloss][:4 if split=='train' else 3]
            for r in selected:
                member='ASL_Citizen/videos/'+r['Video file'];path=cache/split/r['Video file'];path.parent.mkdir(exist_ok=True)
                info=z.getinfo(member)
                if not path.exists() or path.stat().st_size != info.file_size:
                    for attempt in range(4):
                        try:
                            data=z.read(member)
                            if len(data)!=info.file_size:raise ValueError('Incomplete clip download')
                            partial=path.with_suffix(path.suffix+'.partial')
                            partial.write_bytes(data);partial.replace(path);break
                        except Exception:
                            if attempt==3:raise
                            time.sleep(2)
                rows.append(dict(file=str(path.resolve()),label=TARGETS.get(r['Gloss'],'UNKNOWN'),gloss=r['Gloss'],split=split,participant=r['Participant ID'],member=member,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
                print('download',len(rows),split,rows[-1]['label'],flush=True)
    participants={s:{r['participant'] for r in rows if r['split']==s} for s in ['train','val','test']}
    assert all(not participants[a]&participants[b] for a,b in [('train','val'),('train','test'),('val','test')])
    hashes={s:{r['sha256'] for r in rows if r['split']==s} for s in participants}
    assert all(not hashes[a]&hashes[b] for a,b in [('train','val'),('train','test'),('val','test')])
    (cache/'target20-manifest.json').write_text(json.dumps(dict(source=URL,labels=LABELS,samples=rows),indent=2))
    return rows

def worker(args):
    row,cache=args
    import cv2,torch
    cv2.setNumThreads(1);torch.set_num_threads(1)
    try:
        extract(row,cache,32)
        return dict(file=row['file'],ok=True)
    except ValueError as e:return dict(file=row['file'],ok=False,error=str(e))

def main():
    cache=ROOT.parent/'handspeak-training';cache.mkdir(exist_ok=True)
    manifest=cache/'target20-manifest.json'
    rows=json.loads(manifest.read_text())['samples'] if manifest.exists() else download(cache)
    # Cache reuse is safe: same SHA-256 input, extraction version, and length.
    results=[]
    with cf.ProcessPoolExecutor(max_workers=4) as pool:
        for n,result in enumerate(pool.map(worker,[(r,cache) for r in rows])):
            results.append(result)
            if n%10==0:print('extract',n+1,'/',len(rows),'failed',sum(not r['ok'] for r in results),flush=True)
    (cache/'target20-extraction.json').write_text(json.dumps(results,indent=2))
    print('EXTRACTION COMPLETE',len(rows),flush=True)

if __name__=='__main__':main()
