"""Summarize capture evidence without changing the regression scoring."""
import argparse,json,statistics
from collections import Counter,defaultdict
from pathlib import Path

p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
d=json.loads(a.input.read_text(encoding='utf-8'))
rounds=defaultdict(list);letters=defaultdict(Counter);stages=defaultdict(list);rates=[];worker_rates=[]
for r in d['attempts']:
    letter=r['letter'];rounds[r['round']].append(r);m=letters[letter]
    m['attempts']+=1;m['uiPasses']+=int(r['passed'])
    if r.get('error'):
        m['captureErrors']+=1;continue
    commits=[x['letter'] for x in r.get('commits',[])]
    m['correctCommits']+=commits.count(letter);m['wrongCommits']+=len(commits)-commits.count(letter);m['noCommit']+=not commits
    frames=r.get('frames',[])
    m['auditedFrames']+=len(frames);m['missingRawLandmarks']+=sum(f['raw']==0 for f in frames)
    if frames and all('usable' in f for f in frames):
        m['usableAuditedFrames']+=sum(f['usable']>0 for f in frames)
    m['motionEvaluationsMoving']+=sum(f['moving'] for f in frames)
    m['motionMatches']+=sum(bool(f['motion']) for f in frames)
    for f in frames:
        for k,v in (f.get('timings') or {}).items():
            if v>0:stages[k].append(v)
    try:
        diag=json.loads(r['diagnostics'])
        rates.append(diag['processedFps'])
        if diag.get('letterWorker'):worker_rates.append(diag['letterWorker']['modelInferenceFps'])
    except (KeyError,ValueError,TypeError):pass
original=[rs for k,rs in rounds.items() if k.startswith('repeat-')]
result=dict(attempts=len(d['attempts']),rounds={k:sum(r['passed'] for r in rs) for k,rs in rounds.items()},
    consistentOriginal=sorted(set.intersection(*(set(r['letter'] for r in rs if r['passed']) for rs in original))) if len(original)==3 and all(len(rs)==26 for rs in original) else None,
    letters=letters,negativePasses=sum(r['passed'] for r in d['negatives']),negativeChecks=len(d['negatives']),pageErrors=d['pageErrors'],
    processedFpsMedian=statistics.median(rates) if rates else None,workerModelFpsMedian=statistics.median(worker_rates) if worker_rates else None,
    nonzeroStageTimingMs={k:{'median':statistics.median(v),'samples':len(v)} for k,v in stages.items()},
    scope='Default rate is UI diagnostic snapshots, worker rate is completed model observations; raw detection misses are not the same as usable-hand rejects. Audit frames include normal video transitions.')
a.output.write_text(json.dumps(result,indent=2),encoding='utf8')
print({k:v for k,v in result.items() if k!='letters'})
