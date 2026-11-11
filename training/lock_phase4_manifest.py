"""Freeze a qualified, private manifest before fitting. Refuses incomplete data."""
import argparse,hashlib,json,math
from pathlib import Path
from alphabet_dataset import validate

ROOT=Path(__file__).resolve().parents[1]

def capture_errors(records):
    errors=[]
    for r in records:
        if r.get('split')=='development':continue
        def num(k):
            v=r.get(k)
            return v if type(v) in (int,float) and math.isfinite(v) else -1
        start,end,fps=num('start_ms'),num('end_ms'),num('source_fps')
        if not (0<=start<end and fps>0 and num('width')>0 and num('height')>0):
            errors.append(f"{r.get('id')}: invalid interval, source frame rate or resolution")
        times=r.get('timestamps_ms')
        if not isinstance(times,list) or not times or any(type(t) not in (int,float) or not math.isfinite(t) or not start<=t<=end for t in times):
            errors.append(f"{r.get('id')}: timestamps must be finite source times inside the reviewed interval")
        if not r.get('file') or not r.get('consent_evidence') or not isinstance(r.get('occlusions'),list) or r.get('incomplete') is not False:
            errors.append(f"{r.get('id')}: incomplete capture, media, occlusion annotation or consent metadata")
        if r.get('handedness') not in ('left','right','both','none') or not isinstance(r.get('visible_hand_counts'),list) or not r['visible_hand_counts'] or any(type(v) is not int or not 0<=v<=2 for v in r['visible_hand_counts']):
            errors.append(f"{r.get('id')}: missing or invalid hand visibility annotation")
        elif not isinstance(times,list) or len(r['visible_hand_counts'])!=len(times):
            errors.append(f"{r.get('id')}: visibility annotations must align with observations")
        if not all(r.get(k) for k in ('lighting','background','distance','rotation','device')):
            errors.append(f"{r.get('id')}: missing capture conditions")
    for split in ('train','validation','test'):
        sides={r.get('handedness') for r in records if r.get('split')==split}
        if not {'left','right'} <= sides:errors.append(f'{split}: both left- and right-handed recordings required')
    return errors

def main():
    p=argparse.ArgumentParser()
    p.add_argument('manifest',type=Path);p.add_argument('--media-root',type=Path,required=True);p.add_argument('--lock',type=Path,required=True)
    a=p.parse_args()
    for path in (a.manifest,a.media_root,a.lock):
        if path.resolve().is_relative_to(ROOT):p.error('Private data must be outside the workspace')
    raw=a.manifest.read_bytes();data=json.loads(raw.decode('utf-8-sig'))
    errors=validate(data,a.media_root,strict_coverage=True)['errors']+capture_errors(data['recordings'])
    if errors:p.error('; '.join(errors))
    test=[r for r in data['recordings'] if r['split']=='test']
    lock=dict(schema='handspeak-phase4-test-lock-v1',manifestSha256=hashlib.sha256(raw).hexdigest(),testRecordings=len(test),
              testSigners=len({r['signer_id'] for r in test}))
    with a.lock.open('x',encoding='utf-8') as f:json.dump(lock,f,indent=2)

if __name__=='__main__':main()
