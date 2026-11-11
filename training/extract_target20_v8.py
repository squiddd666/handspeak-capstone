"""Package real Chromium submissions into private V6 development artifacts."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from target20_artifact_v8 import SCHEMA, TRACKER, ENCODER_VERSION, seal, validate, validate_batch

CACHE=ROOT.parent/'handspeak-training'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',choices=['virtual-v8-validation','virtual-v8-repeat'])
    args=parser.parse_args()
    run=CACHE/args.run
    out=run/'canonical-v1'
    if out.exists():raise ValueError('Canonical artifact directory already exists')
    m=read(CACHE/'target20-v2-manifest.json')
    known={r['sha256']:r for r in m['samples'] if r['split']=='val'}
    results=read(run/'results.json')
    protocol=read(run/'protocol.json')
    code=read(CACHE/(args.run+'-code-profile.json'))
    assert code==dict(frontend_sha256=sha(ROOT/'beginner-recognition.js'),
                     harness_sha256=sha(ROOT/'training/target20_virtual_camera.py'))
    assert results['split']=='val' and results['phase']=='known'
    assert results['resolution']==[640,480] and results['source_fps']==15
    records=[];artifacts=[]
    for r in results['results']:
        src=known[r['source_sha256']]
        assert r['scenario']=='normal' and r['split']=='val' and r['label']==src['label']
        assert any(p['sha256']==src['sha256'] and p['label']==src['label'] for p in protocol['sources'])
        path=Path(src['file']).resolve()
        assert path.is_relative_to(CACHE.resolve()) and sha(path)==src['sha256']
        rec=dict(case_id=r['case_id'],label=r['label'],capture=r['capture_outcome'],encoder=r['encoder_outcome'],model=r['v3_outcome'])
        files=list(run.glob(f"playlist-*/parity-{r['case_id']}.json"))
        if not files:
            rec['status']='not_submitted';records.append(rec);continue
        assert len(files)==1
        req=read(files[0]);d=r['backend_response'];fs=req['frames']
        assert req['consent'] is True and req['vocabulary']=='target20' and d['frames']==len(fs)
        e=d['experimentalEncoder']
        if e['state']=='encoded':
            assert e['source_first_ms']==fs[0]['timestampMs'] and e['source_last_ms']==fs[-1]['timestampMs']
        usable=r['capture_outcome']=='verified' and e['state']=='encoded'
        body=dict(schema=SCHEMA,encoder=ENCODER_VERSION,split='val',status='usable_development' if usable else 'excluded',
            reason=None if usable else f"{r['capture_outcome']} / {e['state']}",
            source=dict(id=src['member'],sha256=src['sha256'],label=src['label'],gloss=src['gloss'],
                variant='source gloss retained; not independently reviewed',signer=src['participant'],
                license_ref='https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/',
                permission_ref='Existing private ASL Citizen non-commercial research subset; no redistribution'),
            extraction=dict(tracker=TRACKER,resolution=results['resolution'],fps=results['source_fps'],
                browser=r['browser_user_agent'],**code,profile='chromium-y4m-playlist',
                clip_seconds=results['full_reference_playback_seconds'],lead_seconds=results['source_lead_seconds'],
                warmup_policy='one warm-up capture; tracker state retained across slots'),
            capture={**req['capture'],'qa_verified_window':r['full_source_window_captured']},
            frames=[{**f,'left_visible':f['left'] is not None,'right_visible':f['right'] is not None} for f in fs])
        a=seal(body);validate(a)
        artifacts.append((f"{r['case_id']:02d}.json",a))
        rec.update(status=body['status'],artifact_sha256=a['artifact_sha256'],file=artifacts[-1][0])
        records.append(rec)
    validate_batch([a for _,a in artifacts])
    out.mkdir()
    for name,a in artifacts:(out/name).write_text(json.dumps(a,indent=2,allow_nan=False),encoding='utf-8')
    (out/'index.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    print('Canonical artifacts:',len(artifacts),'usable:',sum(a['status']=='usable_development' for _,a in artifacts))
if __name__=='__main__':main()
