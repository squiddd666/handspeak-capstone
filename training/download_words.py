"""Download a reproducible small PopSign subset without fetching entire archives."""
import urllib.request,tarfile,json,time,re,hashlib,concurrent.futures,argparse
from pathlib import Path
ROOT=Path('/opt/handspeak-training/popsign');BASE='https://signdata.cc.gatech.edu/data/popsign_v1_0/game/'
LABELS=['hello','thankyou','please','yes','no','finish']
def fetch(label,split,count):
 url=f'{BASE}{split}/{label}.tar';out=ROOT/split/label;out.mkdir(parents=True,exist_ok=True)
 manifest=out/'manifest.json'
 if manifest.exists():return json.loads(manifest.read_text())
 rows=[];offset=0;participants={};examined=0
 while len(rows)<count and examined<count*5:
  req=urllib.request.Request(url,headers={'Range':f'bytes={offset}-{offset+511}'})
  with urllib.request.urlopen(req,timeout=40) as r:
   if r.status!=206:raise ValueError('Server did not honor byte range')
   header=r.read(512)
  if header==bytes(512):break
  info=tarfile.TarInfo.frombuf(header,'utf-8','replace');start=offset+512;offset=start+((info.size+511)//512)*512
  if not info.isfile() or not info.name.endswith('.mp4'):continue
  examined+=1
  match=re.search(r'4a\.(\d+)',info.name);participant=match.group(1) if match else 'unknown'
  if participants.get(participant,0)>=3:continue
  path=out/Path(info.name).name
  if not path.exists():
   req=urllib.request.Request(url,headers={'Range':f'bytes={start}-{start+info.size-1}'})
   for attempt in range(3):
    try:
     with urllib.request.urlopen(req,timeout=60) as r:
      if r.status!=206:raise ValueError('Range not honored')
      data=r.read()
     if len(data)!=info.size:raise ValueError('Incomplete video')
     path.write_bytes(data);break
    except Exception:
     if attempt==2:raise
     time.sleep(1)
  participants[participant]=participants.get(participant,0)+1
  rows.append({'label':label.upper(),'split':split,'participant':participant,'file':str(path),'source':url,'member':info.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
 manifest.write_text(json.dumps(rows,indent=2));print(label,split,len(rows),'clips',len(participants),'signers',flush=True);return rows
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--cache',type=Path,default=ROOT,help='Video cache outside the served website')
 args=parser.parse_args();ROOT=args.cache.resolve()
 jobs=[(l,s,n) for l in LABELS for s,n in [('train',24),('val',8),('test',12)]]
 jobs += [('drink','val',8),('drink','test',12)]
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
  results=list(ex.map(lambda args:fetch(*args),jobs))
 (ROOT/'manifest.json').write_text(json.dumps([r for rows in results for r in rows],indent=2))
 print('Downloaded',sum(map(len,results)),'clips',flush=True)
