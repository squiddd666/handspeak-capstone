"""Collection/annotation integrity, signer-group splits and legacy audit.

Raw media belongs outside the public web root. Unknown signer identity is
development-only, never silently treated as an independent test participant.
"""
import argparse
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import string

ROOT=Path(__file__).resolve().parents[1]
LABELS=set(string.ascii_uppercase)|{'NO_HAND','UNKNOWN'}
TRAIN_LICENSES={'CC0-1.0','CC-BY-4.0','CC-BY-SA-4.0','consented-project-use'}

def signer_split(signer_id,verified,seed='handspeak-alphabet-v1'):
    if not signer_id or not verified:return 'development'
    n=int(hashlib.sha256((seed+'|'+signer_id).encode()).hexdigest()[:8],16)%100
    return 'train' if n<70 else 'validation' if n<85 else 'test'

def validate(manifest,root=None,strict_coverage=False):
    errors=[];warnings=[];seen={};groups=defaultdict(set);signers=defaultdict(set);coverage=defaultdict(set)
    if manifest.get('schema')!='handspeak-alphabet-recordings-v1':errors.append('Unsupported manifest schema')
    records=manifest.get('recordings',[])
    for i,r in enumerate(records):
        key=r.get('id',str(i));split=r.get('split');label=r.get('label');verified=r.get('signer_verified') is True
        if split not in {'train','validation','test','development'}:errors.append(f'{key}: invalid split')
        if label not in LABELS:errors.append(f'{key}: unknown label')
        if split!='development' and (not r.get('signer_id')or not verified or not r.get('identity_evidence')):errors.append(f'{key}: independent grouping requires verified signer identity/evidence')
        if split=='train' and (r.get('license')not in TRAIN_LICENSES or not r.get('rights_evidence')):errors.append(f'{key}: training rights not verified')
        if split!='development' and (r.get('review_status')!='accepted' or not r.get('reviewer_id')):errors.append(f'{key}: annotation has not been reviewed')
        if r.get('signer_id'):signers[r['signer_id']].add(split)
        for field in ['recording_id','parent_media_sha256']:
            if r.get(field):groups[(field,r[field])].add(split)
            else:errors.append(f'{key}: missing {field}')
        if r.get('session_id'):
            groups[('session_id',r['session_id'])].add(split)
        elif strict_coverage and split!='development':
            errors.append(f'{key}: missing session_id')
        if strict_coverage and split!='development' and not r.get('rights_evidence'):
            errors.append(f'{key}: missing evaluation rights evidence')
        digest=r.get('sha256')
        if not isinstance(digest,str)or len(digest)!=64:errors.append(f'{key}: missing/invalid content SHA-256')
        elif digest in seen and seen[digest]!=split:errors.append(f'{key}: identical media crosses partitions')
        else:seen[digest]=split
        timestamps=r.get('timestamps_ms',[])
        if any(not isinstance(t,(int,float))for t in timestamps)or any(b<=a for a,b in zip(timestamps,timestamps[1:])):errors.append(f'{key}: duplicate/reversed/invalid frame timestamps')
        if label in {'J','Z'} and (r.get('kind')!='motion' or len(timestamps)<6):errors.append(f'{key}: J/Z require a complete reviewed motion sequence, not a snapshot')
        for field in ['handedness','lighting','background','distance','rotation','device','source_url']:
            if not r.get(field):warnings.append(f'{key}: missing {field}')
        if root and r.get('file'):
            target=(Path(root)/r['file']).resolve()
            if not target.is_relative_to(Path(root).resolve()):errors.append(f'{key}: path escapes dataset root')
            elif not target.is_file():errors.append(f'{key}: media file missing')
            elif hashlib.sha256(target.read_bytes()).hexdigest()!=digest:errors.append(f'{key}: file hash mismatch')
        coverage[split].add(label)
    for group,splits in groups.items():
        if len(splits)>1:errors.append(f'{group[0]} {group[1]} crosses partitions {sorted(splits)}')
    for signer,splits in signers.items():
        if len(splits)>1:errors.append(f'Signer {signer} crosses partitions {sorted(splits)}')
    for split in ['train','validation','test']:
        missing=(LABELS if strict_coverage else set(string.ascii_uppercase))-coverage[split]
        if missing:(errors if strict_coverage else warnings).append(f'{split}: missing letters '+','.join(sorted(missing)))
        if strict_coverage and len({r.get('signer_id') for r in records if r.get('split')==split and r.get('signer_verified') is True and r.get('signer_id')})<2:
            errors.append(f'{split}: fewer than two verified signers')
    if not records:errors.append('No recordings: collection has not yet taken place')
    return {'valid':not errors,'errors':errors,'warnings':warnings,'counts':dict(Counter(r.get('split')for r in records)),
            'independentSignerTestingAvailable':bool(coverage['test'])and not errors,
            'limitations':'A valid split is necessary, not proof of annotation accuracy or representative signer coverage.'}

def audit_legacy():
    model=json.loads((ROOT/'models/asl-knn.json').read_text());fixture=json.loads((ROOT/'models/asl-test-fixture.json').read_text())
    vectors=[hashlib.sha256(json.dumps(s['features'],separators=(',',':')).encode()).hexdigest()for s in model['samples']]
    coordinate_rotated=sum(abs(r['features'][27])<1e-4 and r['features'][28]>0 for r in fixture)
    return {'modelSha256':hashlib.sha256((ROOT/'models/asl-knn.json').read_bytes()).hexdigest(),'samples':len(vectors),'uniqueExactVectors':len(set(vectors)),
      'perLetter':dict(Counter(s['label']for s in model['samples'])),'modelNormalization':model['normalization'],
      'legacyFixtureRows':len(fixture),'legacyFixtureLabels':sorted(set(r['label']for r in fixture)),
      'legacyFixtureRotationNormalizedRows':coordinate_rotated,'legacyFixtureCompatible':False,
      'signerMetadataAvailable':False,'sampleSourceHashesAvailable':False,'license':model.get('source'),
      'conclusion':'Do not regenerate expected predictions from this model to hide fixture incompatibility. Recover original data/provenance or keep this parity check explicitly blocked.'}

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['template','validate','split','audit-legacy']);p.add_argument('--manifest',type=Path);p.add_argument('--root',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--strict-coverage',action='store_true');a=p.parse_args()
    if a.command=='template':
        value={'schema':'handspeak-alphabet-recordings-v1','protocol':'One person/recording group cannot cross partitions; unknown identities remain development-only. Store media outside the web root. Review J/Z trajectory and ambiguous static poses before training.','recordings':[]}
    elif a.command=='audit-legacy':value=audit_legacy()
    else:
        if not a.manifest:p.error('--manifest is required')
        value=json.loads(a.manifest.read_text())
        if a.command=='split':
            for r in value['recordings']:r['split']=signer_split(r.get('signer_id'),r.get('signer_verified')is True)
        else:value=validate(value,a.root,a.strict_coverage)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2),encoding='utf-8');print(json.dumps(value if a.command=='validate' else {'output':str(a.output)},indent=2))

if __name__=='__main__':main()
