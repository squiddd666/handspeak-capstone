"""Freeze private V7 eligibility decisions; no media downloads or model use."""
import hashlib, io, json, urllib.request, zipfile
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT.parent/'handspeak-training'
OUT=CACHE/'target20-v7-proposed-split.json'
sha=lambda b:hashlib.sha256(b).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def aliases(word):return {'i','me','i / me','i/me'} if word=='I / ME' else {'thank you','thanks'} if word=='THANK YOU' else {word.lower()}
def main():
    src=read(CACHE/'target20-v2-manifest.json')
    labels=src['labels'][:20]
    originals={s:{r['participant'] for r in src['samples'] if r['split']==s} for s in ('train','val','test')}
    assert all(not originals[a]&originals[b] for a,b in [('train','val'),('train','test'),('val','test')])
    entries=[];seen=set();held={r['sha256'] for r in src['samples'] if r['split']=='test'}
    for r in src['samples']:
        path=Path(r['file'])
        if not path.resolve().is_relative_to(CACHE.resolve()):raise ValueError('Recording outside private cache')
        status='excluded'
        reason='Previously exposed official test; not an untouched benchmark'
        if r['split']!='test':
            if not path.is_file():reason='Media missing'
            elif sha(path.read_bytes())!=r['sha256']:reason='Media hash mismatch'
            elif r['sha256'] in seen or r['sha256'] in held:reason='Duplicate or held-out hash'
            else:
                status='unknown_candidate' if r['label']=='UNKNOWN' else 'eligible_development_'+r['split']
                reason='Existing licensed research subset; source gloss mapping and exact hash verified; no new linguistic or near-duplicate certification'
                seen.add(r['sha256'])
        entries.append(dict(dataset='ASL Citizen',status=status,reason=reason,word=r['label'],gloss=r['gloss'],
                            signer=r['participant'],source_id=r['member'],sha256=r['sha256'],source_split=r['split']))
    # Metadata only, no linked source recordings requested.
    with urllib.request.urlopen('https://download.microsoft.com/download/3/c/a/3ca92c78-1c4a-4a91-a7ee-6980c1d242ec/MS-ASL.zip',timeout=25) as req:
        archive=req.read(20_000_001)
    if len(archive)>20_000_000:raise ValueError('Metadata archive exceeds cap')
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        classes=json.loads(z.read('MS-ASL/MSASL_classes.json'))
        for split in ('train','val','test'):
            for r in json.loads(z.read(f'MS-ASL/MSASL_{split}.json')):
                gloss=classes[r['label']].lower()
                word=next((w for w in labels if gloss in aliases(w)),None)
                if word:
                    entries.append(dict(dataset='MS-ASL',status='unverified_catalog',word=word,gloss=gloss,
                        signer=r.get('signer_id'),source_id=r.get('url'),source_split=split,sha256=None,
                        reason='Source media, rights, variants and cross-corpus overlap unverified'))
    for g in read(CACHE/'target20-v6-wlasl-catalog.json'):
        gloss=g['gloss'].lower()
        word=next((w for w in labels if gloss in aliases(w)),None)
        if not word:continue
        for r in g['instances']:
            entries.append(dict(dataset='WLASL',status='unverified_catalog',word=word,gloss=gloss,
                signer=r.get('signer_id'),source_id=r.get('video_id'),source_split=r.get('split'),sha256=None,
                reason='Source media, rights, variants and cross-corpus overlap unverified; published splits share signer IDs'))
    frozen=dict(protocol='V7 development-only eligibility freeze; new evaluation requires separately qualified signer groups and hashes',
                dataset_source=src['source'],labels=labels,untouched_test_candidates=[],samples=entries)
    payload=(json.dumps(frozen,sort_keys=True,indent=2)+'\n').encode()
    if OUT.exists() and OUT.read_bytes()!=payload:raise ValueError('Frozen manifest differs; create a new version')
    if not OUT.exists():OUT.write_bytes(payload)
    print('Frozen SHA-256',sha(payload),'counts',dict(Counter(r['status'] for r in entries)))
if __name__=='__main__':main()
