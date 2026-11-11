"""Check a frozen candidate against a small, separate other-sign subset."""
import csv,hashlib,io,json
from pathlib import Path
from remotezip import RemoteZip
from train_essential import extract,_build_runtime,torch,ROOT
from download_essential_citizen import URL

def main():
    cache=ROOT.parent/'handspeak-training';torch.set_num_threads(2)
    negatives=[]
    glosses=['HELLO','YES','NO','GOOD','BAD','SORRY','LOVE','WANT','WATER','EAT1']
    with RemoteZip(URL) as z:
        for split in ['val','test']:
            rows=list(csv.DictReader(io.StringIO((cache/f'{split}.csv').read_text())))
            for gloss in glosses:
                selected=[r for r in rows if r['Gloss']==gloss][:2]
                for r in selected:
                    member='ASL_Citizen/videos/'+r['Video file'];path=cache/'negative'/split/r['Video file'];path.parent.mkdir(parents=True,exist_ok=True)
                    if not path.exists():path.write_bytes(z.read(member))
                    negatives.append(dict(file=str(path),split=split,label=gloss,participant=r['Participant ID'],member=member,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (cache/'negative-manifest.json').write_text(json.dumps(negatives,indent=2))
    _,model,labels,length=_build_runtime(cache/'essential-candidate.pt')
    targets=set(json.loads((cache/'essential-manifest.json').read_text())['labels'])
    scored=[];failures=[]
    rows=json.loads((cache/'essential-manifest.json').read_text())['samples']+negatives
    for n,r in enumerate(rows):
        if r['split']=='train':continue
        try:x=extract(r,cache,length)
        except ValueError as e:failures.append(dict(file=r['file'],error=str(e)));continue
        with torch.no_grad():p=model(torch.tensor(x[None])).softmax(1)[0]
        index=int(p.argmax());scored.append(dict(split=r['split'],expected=r['label'],predicted=labels[index],score=float(p[index]),known=r['label'] in targets))
        print('check',n+1,'/',len(rows),flush=True)
    def metrics(split,gate):
        rows=[r for r in scored if r['split']==split];result=dict(correct=0,wrong=0,rejected=0,known=0,negative=0,false_accept=0)
        for r in rows:
            accept=r['predicted'] in targets and r['score']>=gate
            if r['known']:
                result['known']+=1;result['correct' if accept and r['predicted']==r['expected'] else 'wrong' if accept else 'rejected']+=1
            else:result['negative']+=1;result['false_accept']+=int(accept)
        return result
    gates=[.3,.4,.5,.6,.7,.8,.9]
    gate=min(gates,key=lambda g:(lambda m:5*(m['wrong']+m['false_accept'])+m['rejected'])(metrics('val',g)))
    result=dict(gate=gate,validation=metrics('val',gate),test=metrics('test',gate),tracking_failures=failures,records=scored,scope='Small recorded-video regression check; not live-camera or independent pretraining evaluation.')
    (cache/'essential-rejection-report.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2),flush=True)
if __name__=='__main__':main()
