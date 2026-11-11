"""Reserve 100 new lexical unknown clips before any virtual-camera predictions."""
import csv
import hashlib
import json
from pathlib import Path
from target20_data import get_archive

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT.parent/'handspeak-training'


def main():
    output=CACHE/'virtual-v4-unknown-manifest.json'
    if output.exists():raise RuntimeError('Unknown reservation already exists; do not resample against test results')
    existing=json.loads((CACHE/'target20-v2-manifest.json').read_text())
    excluded={r['gloss'] for r in existing['samples']}
    rows=list(csv.DictReader((CACHE/'test.csv').open(encoding='utf-8-sig')))
    glosses=sorted({r['Gloss'] for r in rows}-excluded,key=lambda g:hashlib.sha256(('virtual-v4-unknown:'+g).encode()).hexdigest())[:100]
    selected=[]
    with get_archive() as archive:
        for i,gloss in enumerate(glosses):
            row=min((r for r in rows if r['Gloss']==gloss),key=lambda r:hashlib.sha256(r['Video file'].encode()).hexdigest())
            member='ASL_Citizen/videos/'+row['Video file'];path=CACHE/'test'/row['Video file']
            size=archive.getinfo(member).file_size
            if not path.exists() or path.stat().st_size!=size:
                data=archive.read(member);assert len(data)==size
                tmp=path.with_suffix('.download');tmp.write_bytes(data);tmp.replace(path)
            selected.append(dict(file=str(path.resolve()),label='UNKNOWN',gloss=gloss,split='test',participant=row['Participant ID'],
                                 sha256=hashlib.sha256(path.read_bytes()).hexdigest(),independent_unknown=True))
            if (i+1)%20==0:print('Reserved untouched unknown clips',i+1,flush=True)
    assert not {r['participant'] for r in selected}&{r['participant'] for r in existing['samples'] if r['split']=='train'}
    assert not {r['sha256'] for r in selected}&{r['sha256'] for r in existing['samples']}
    output.write_text(json.dumps(dict(source=existing['source'],protocol='100 previously unused lexical glosses, one official-test recording each; never used for model or threshold selection.',
                                     caveat='Lexical labels are source mappings, not expert certification of distinct sign semantics.',samples=selected),indent=2))
    print('Reserved',len(selected),'clips',flush=True)


if __name__=='__main__':main()
