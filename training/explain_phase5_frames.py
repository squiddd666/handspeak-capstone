"""Explain actual captured static reference landmarks without rerunning or changing UI scoring."""
import argparse,json,math
from pathlib import Path
import quickjs

root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('results',type=Path);p.add_argument('output',type=Path)
a=p.parse_args()
js=quickjs.Context()
for n in ('gesture-model.js','letter-recognition.js'):
    js.eval('\n'.join(l for l in (root/n).read_text(encoding='utf8').splitlines() if not l.startswith('import ')).replace('export ',''))
js.eval('const model='+ (root/'models/asl-knn.json').read_text()+';')
js.eval('''function explain(points,aspect){
  if(!points)return {reason:'no-landmarks'};
  if(!isUsableLetterHand(points,aspect))return {reason:'unusable-landmarks'};
  const decisions=[];
  const prediction=classifyLetter(points,model.samples,model.parameters,aspect,v=>decisions.push(v));
  const dist=(a,b)=>Math.hypot(points[a].x-points[b].x,(points[a].y-points[b].y)*aspect);
  const span=dist(5,17),length=dist(0,9);
  return {prediction,decisions,reason:decisions[decisions.length-1]?.reason||'no-score',
    palmSpan:span,palmLength:length,spanToLength:length?span/length:null,
    wrist:points[0],palmAxisRadians:Math.atan2((points[9].y-points[0].y)*aspect,points[9].x-points[0].x)};
}''')
result=json.loads(a.results.read_text())
cases=[]
for r in result['attempts']:
    if r['letter'] not in 'KOUX':continue
    audit=[]
    for f in r.get('frames',[]):
        if 'points' not in f:continue
        points=f['points'][0] if f['points'] else None
        ts=f['timestamp'];time=f['observedAt']
        # Compare UI only with the next actually sampled observation, not an
        # assertion that both clocks or camera/render cycles are identical.
        ui=next((v for v in r['trace'] if v['t']>=time),None)
        static=json.loads(js.eval('JSON.stringify(explain('+json.dumps(points)+','+str(f['aspect'])+'))'))
        tracked=None
        for t in f.get('trackedPoints',[]):
            if points and js.eval('sameObservedHand('+json.dumps(points)+','+json.dumps(t)+','+str(f['aspect'])+')'):
                tracked=json.loads(js.eval('JSON.stringify(explain('+json.dumps(t)+','+str(f['aspect'])+'))'));break
        audit.append(dict(timestamp=ts,observedAt=time,moving=f['moving'],handIds=f['handIds'],
            raw=f['raw'],handedness=f.get('handedness'),image=static,associatedVideo=tracked,nextUiSample=ui))
    cases.append(dict(letter=r['letter'],round=r['round'],passed=r['passed'],commits=r.get('commits',[]),frames=audit))
a.output.write_text(json.dumps(dict(scope='Offline static classifier audit of actual captured browser landmarks; not recognition rerun or training',cases=cases),indent=2))
