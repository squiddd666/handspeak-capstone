"""Replay real V6 validation requests through unchanged V3 inference."""
import hashlib,json,os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
cache=root.parent/'handspeak-training'
run=cache/(sys.argv[1] if len(sys.argv)>1 else 'virtual-v6-validation')
checkpoint=cache/'target20-v3/target20-v3-selected.pt'
expected=json.loads((checkpoint.parent/'final-evaluation.json').read_text())['checkpoint_sha256']
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==expected
assert hashlib.sha256((cache/'target20-candidate.pt').read_bytes()).hexdigest()=='e9e558d6e0b4bd003e1bc4e4696160d1b5421df0a337c6a891960a21f4d0559d'
os.environ['HANDSPEAK_TARGET20_MODEL']=str(checkpoint)
from beginner_asl import recognize
val={r['sha256'] for r in json.loads((cache/'target20-v2-manifest.json').read_text())['samples'] if r['split']=='val'}
count=0
for r in json.loads((run/'results.json').read_text())['results']:
    assert r['split']=='val' and r['source_sha256'] in val
    for file in run.glob(f"playlist-*/parity-{r['case_id']}.json"):
        actual=recognize(json.loads(file.read_text()))
        assert actual=={k:v for k,v in r['backend_response'].items() if k!='experimentalEncoder'},r['label']
        count+=1
(run/'v6-v3-compatibility.json').write_text(json.dumps(dict(exact_response_matches=count)))
print(count,'exact V3 responses, checkpoint hashes verified')
