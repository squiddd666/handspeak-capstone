"""Replay distinct timestamped observations at fixed upper sampling rates."""
import argparse,json
from pathlib import Path
import quickjs
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('observations',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--stable-palm',action='store_true');a=p.parse_args()
results=[]
for c in 'jzid':
 data=json.loads((a.observations/f'{c}-observations.json').read_text())
 for hz in (5,10,15,30,60):
  js=quickjs.Context()
  js.eval((root/'motion-letters.js').read_text().replace('export {letterSequence};','').replace('export ',''))
  js.eval('const m=createMultiHandMotionLetters();m.setModel('+(root/'models/motion-letters.json').read_text()+');')
  next_at=None; count=0; commits=[]
  for f in data['frames']:
   ts=f['timestampMs']
   if next_at is None:next_at=ts
   if ts<round(next_at):continue
   while round(next_at)<=ts:next_at+=1000/hz
   count+=1
   pts=[[dict(zip('xyz',q)) for q in h['points']] for h in f['hands'] if h['inFrame']]
   r=json.loads(js.eval(f"JSON.stringify(m.frame({json.dumps(pts)},{ts},{f['width']/f['height']},{str(a.stable_palm).lower()}))"))
   if r['result']:commits.append({'timestampMs':ts,**r['result']})
  results.append(dict(label=c.upper(),targetHz=hz,distinctObservations=count,commits=commits))
a.output.write_text(json.dumps({'scope':'Cached development clip landmarks; artificial subsampling, not measured browser FPS or independent accuracy','cases':results},indent=2))
for r in results:print(r['label'],r['targetHz'],r['distinctObservations'],[e['letter'] for e in r['commits']])
