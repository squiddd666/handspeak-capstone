"""Summarize completed camera attempts without changing acceptance scoring."""
import json,statistics
from pathlib import Path
from collections import defaultdict,Counter
p=Path(__file__).resolve().parents[1]/'reports/alphabet-phase3'
d=json.loads((p/'camera/results.json').read_text()); groups=defaultdict(list); confusion=defaultdict(Counter); fps=[]
for r in d['attempts']:
    groups[r['round']].append(r)
    commits=[v['letter'] for v in r.get('commits',[])]
    confusion[r['letter']].update(commits or ['abstain'])
    try: fps.append(json.loads(r['diagnostics'])['processedFps'])
    except (ValueError,KeyError):pass
repeats=[v for k,v in groups.items() if k.startswith('repeat-')]
out=dict(complete=len(d['attempts'])==130 and len(d['negatives'])==10, attempts=len(d['attempts']), rounds={k:dict(attempts=len(v),passed=sum(r['passed']for r in v),failed=[r['letter']for r in v if not r['passed']])for k,v in groups.items()},consistentOriginal=(sorted(set.intersection(*(set(r['letter']for r in v if r['passed'])for v in repeats))) if len(repeats)==3 and all(len(v)==26 for v in repeats) else None),negativeChecks=len(d['negatives']),negativePasses=sum(r['passed']for r in d['negatives']),pageErrors=d['pageErrors'],medianProcessedFps=statistics.median(fps) if fps else None,commitConfusion=confusion,scope='Each emitted commit counts once; an attempt without a commit counts as one abstention. Passes use original UI scoring.')
(p/'camera-summary.json').write_text(json.dumps(out,indent=2))
print({k:v for k,v in out.items()if k!='commitConfusion'})
