import json,sys
from pathlib import Path
sys.path.insert(0,str(Path('training').resolve()))
import full_live_camera_audit as a
from playwright.sync_api import sync_playwright
out=Path('website-word-test/capture-repair-v2');out.mkdir(exist_ok=True)
a.OUT=Path('../handspeak-training/capture-repair-v2').resolve();a.OUT.mkdir(exist_ok=True)
manifest=json.loads(Path('website-word-test/full-camera-audit-v1/manifest.json').read_text())
labels=['BLACK','BOWLING','MEDICINE','BIRD','EAT','BEFORE','APPLE']
rows=[]
with sync_playwright() as p:
 for label in labels:
  row=next(x for x in manifest if x['id']=='word-'+label)
  d=a.automatic_case(p,row);rows.append({'label':label,**d})
  (out/'results.json').write_text(json.dumps(rows,indent=2))
  print(label,d['outcome'],d.get('captureFullReference'),d.get('choices'),flush=True)
