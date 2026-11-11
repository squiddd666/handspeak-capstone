"""Select additional PopSign clips before fitting; keep fresh test payloads sealed."""
import concurrent.futures,hashlib,json,re,tarfile,time,urllib.request
from pathlib import Path
ROOT=Path('/opt/handspeak-training/accuracy-v4');OLD=Path('/opt/handspeak-training/popsign')
LABELS=['hello','thankyou','please','yes','no','finish'];NEGATIVE=['drink','water','book']
def request(url,start,size):
 for attempt in range(4):
  try:
   req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{start+size-1}'})
   with urllib.request.urlopen(req,timeout=60) as r:
    if r.status!=206:raise RuntimeError('Range unsupported')
    data=r.read()
   if len(data)!=size:raise RuntimeError('Incomplete response')
   return data
  except Exception:
   if attempt==3:raise
   time.sleep(1+attempt)
def select(job):
 label,split,count=job;url=f'https://signdata.cc.gatech.edu/data/popsign_v1_0/game/{split}/{label}.tar'
 out=ROOT/'indexes'/f'{split}-{label}.json';out.parent.mkdir(parents=True,exist_ok=True)
 if out.exists():return json.loads(out.read_text())
 old=json.loads((OLD/'manifest.json').read_text());excluded={r['member'] for r in old if r['source']==url}
 offset=0;rows=[];signers={};seen=0
 while len(rows)<count and seen<2000:
  header=request(url,offset,512)
  if header==bytes(512):break
  info=tarfile.TarInfo.frombuf(header,'utf-8','replace');start=offset+512;offset=start+((info.size+511)//512)*512;seen+=1
  if not info.isfile() or not info.name.endswith('.mp4') or info.name in excluded:continue
  match=re.search(r'4a\.(\d+)',info.name)
  if not match:continue
  participant=match.group(1)
  if signers.get(participant,0)>=3:continue
  signers[participant]=signers.get(participant,0)+1
  rows.append(dict(label='THANK YOU' if label=='thankyou' else label.upper(),split=split,participant=participant,source=url,member=info.name,offset=start,size=info.size,file=str(ROOT/'videos'/split/label/Path(info.name).name),kind='unsupported' if label in NEGATIVE else 'supported'))
 out.write_text(json.dumps(rows,indent=2));print('Selected',label,split,len(rows),flush=True);return rows
def download(row):
 path=Path(row['file']);path.parent.mkdir(parents=True,exist_ok=True)
 if not path.exists():
  if sum(p.stat().st_size for p in (ROOT/'videos').rglob('*.mp4'))>3_000_000_000:raise RuntimeError('3GB experiment video budget exceeded')
  data=request(row['source'],row['offset'],row['size']);tmp=path.with_suffix('.partial');tmp.write_bytes(data);tmp.replace(path)
 row['sha256']=hashlib.sha256(path.read_bytes()).hexdigest();return row
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--test',action='store_true');args=p.parse_args()
 ROOT.mkdir(parents=True,exist_ok=True)
 jobs=[(l,s,(24 if l in ['no','finish','hello'] else 12) if s=='train' else 6) for l in LABELS for s in ['train','val','test']]+[(l,s,12 if s=='train' else 6) for l in NEGATIVE for s in ['train','val','test']]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:rows=[r for group in pool.map(select,jobs) for r in group]
 old=json.loads((OLD/'manifest.json').read_text())
 signers={s:{r['participant'] for r in rows+old if r['split']==s} for s in ['train','val','test']}
 assert not(signers['train']&signers['val'] or signers['train']&signers['test'] or signers['val']&signers['test']),signers
 manifest=ROOT/'selection.json'
 text=json.dumps(rows,indent=2)
 if manifest.exists():assert manifest.read_text()==text,'Frozen selection changed'
 else:manifest.write_text(text)
 selected=[r for r in rows if (r['split']=='test')==args.test]
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:downloaded=list(pool.map(download,selected))
 name='fresh-test-manifest.json' if args.test else 'development-manifest.json'
 (ROOT/name).write_text(json.dumps(downloaded,indent=2));print('Downloaded',len(downloaded),'clips',flush=True)
