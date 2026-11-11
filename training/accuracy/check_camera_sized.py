import json,subprocess,hashlib
from pathlib import Path
import imageio_ffmpeg
ROOT=Path('/opt/handspeak-training/accuracy-v4');PY='/opt/handspeak-training/venv/bin/python';directory=ROOT/'camera-videos';directory.mkdir(exist_ok=True)
rows=json.loads(Path('/opt/handspeak-training/popsign/manifest.json').read_text());sources={name:Path('/opt/handspeak/asl-examples')/(name+'.mp4') for name in ['hello','thank-you','please','yes','no']};sources['finish']=Path(next(r['file'] for r in rows if r['label']=='FINISH' and r['split']=='train'))
records=[]
for name,src in sources.items():
 dst=directory/(name+'.mp4')
 if not dst.exists():subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-loglevel','error','-threads','2','-i',str(src),'-vf','scale=480:640','-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart','-y',str(dst)],check=True)
 records.append(dict(name=name,source=str(src),sourceSha256=hashlib.sha256(src.read_bytes()).hexdigest(),derived=str(dst),derivedSha256=hashlib.sha256(dst.read_bytes()).hexdigest()))
 print('Resized',name,flush=True)
(ROOT/'camera-video-provenance.json').write_text(json.dumps(records,indent=2))
s=Path('/opt/handspeak/current/training/accuracy/realtime_browser.py').read_text().replace('with sync_playwright() as p:',"videos={name:ROOT/'camera-videos'/(name+'.mp4') for name in videos}\nwith sync_playwright() as p:").replace("(ROOT/('realtime-'", "(ROOT/('realtime-camera-sized-'")
(ROOT/'realtime_camera_sized.py').write_text(s)
s=(Path(__file__).resolve().parent/'realtime_candidate.py').read_text().replace('with sync_playwright() as p:',"videos={name:ROOT/'camera-videos'/(name+'.mp4') for name in videos}\nwith sync_playwright() as p:").replace("ROOT/'realtime-candidate.json'", "ROOT/'realtime-candidate-camera-sized.json'")
(ROOT/'realtime_candidate_camera_sized.py').write_text(s)
for args in [[str(ROOT/'realtime_camera_sized.py'),'--cpu'],[str(ROOT/'realtime_candidate_camera_sized.py')]]:
 print('START',args,flush=True);subprocess.run([PY,*args],check=True)
print('CAMERA SIZED CHECKS COMPLETE',flush=True)
