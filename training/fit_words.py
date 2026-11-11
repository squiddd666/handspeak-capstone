"""Tune DTW rejection on PopSign validation and report reserved regression recordings."""
import json,itertools,hashlib
from pathlib import Path
from collections import Counter
import numpy as np
from scipy.spatial.distance import cdist
ROOT=Path(__file__).resolve().parents[1]
CACHE=Path('/opt/handspeak-training/popsign')
OUTPUT=ROOT/'models'

def mirror(a):
    out=np.concatenate([a[:,64:],a[:,:64]],axis=1).copy()
    out[:,1:64:3]*=-1;out[:,65:128:3]*=-1
    return out

def distance(a,b):
    cost=np.zeros((len(a),len(b)))
    for offset in [0,64]:
        present=a[:,offset,None]*b[None,:,offset]
        mismatch=a[:,offset,None]!=b[None,:,offset]
        weights=np.tile([1,1,.5],21)
        cost+=cdist(a[:,offset+1:offset+64]*weights,b[:,offset+1:offset+64]*weights)/np.sqrt(63)*present+2*mismatch
    previous=np.full(len(b)+1,np.inf);previous[0]=0
    for i in range(1,len(a)+1):
        current=np.full(len(b)+1,np.inf)
        for j in range(max(1,i-5),min(len(b),i+5)+1):
            current[j]=cost[i-1,j-1]+min(previous[j],current[j-1],previous[j-1])
        previous=current
    return previous[-1]/max(len(a),len(b))

def distances(rows,train):
    path=CACHE/('distances-'+rows[0]['split']+('-unknown' if rows[0]['label']=='DRINK' else '')+'.json')
    signature=hashlib.sha256(json.dumps([(r['sha256'],r['sequence']) for r in train+rows],separators=(',',':')).encode()).hexdigest()
    if path.exists():
        cache=json.loads(path.read_text())
        if cache['signature']==signature:return np.array(cache['distances'])
    references=[np.array(r['sequence']) for r in train];result=[]
    for i,row in enumerate(rows):
        a=np.array(row['sequence']);m=mirror(a)
        result.append([min(distance(a,b),distance(m,b)) for b in references])
        if i%12==0:print('Compared',row['split'],i+1,'/',len(rows),flush=True)
    path.write_text(json.dumps({'signature':signature,'distances':result}))
    return np.array(result)

def predict(matrix,train,p):
    labels=np.array([r['label'] for r in train]);outputs=[]
    for row in matrix:
        order=np.argsort(row,kind='stable');best=labels[order[0]];other=next(row[i] for i in order if labels[i]!=best)
        separation=other/(row[order[0]]+1e-6)
        outputs.append(str(best) if row[order[0]]<=p['maxDistance'] and separation>=p['minRatio'] and (sum(labels[order[:3]]==best)>=p['minVotes'] or separation>=p.get('strongRatio',float('inf'))) else None)
    return outputs

def metrics(rows,outputs):
    correct=sum(r['label']==p for r,p in zip(rows,outputs));rejected=outputs.count(None);wrong=len(rows)-correct-rejected
    return {'correct':correct,'wrong':wrong,'rejected':rejected,'total':len(rows),
            'coverage':(len(rows)-rejected)/len(rows),'accuracyAmongAccepted':correct/(len(rows)-rejected) if len(rows)>rejected else 0,
            'accuracyIncludingRejections':correct/len(rows)}

def main():
    OUTPUT.mkdir(parents=True,exist_ok=True)
    allrows=json.loads((CACHE/'extracted.json').read_text())
    for r in allrows:
        if r['label']=='THANKYOU':r['label']='THANK YOU'
    rows=[r for r in allrows if r['sequence'] is not None]
    train=[r for r in rows if r['split']=='train'];val=[r for r in rows if r['split']=='val' and r['label']!='DRINK'];test=[r for r in rows if r['split']=='test' and r['label']!='DRINK']
    negative_val=[r for r in rows if r['split']=='val' and r['label']=='DRINK'];negative_test=[r for r in rows if r['split']=='test' and r['label']=='DRINK']
    counts=Counter(r['label'] for r in train)
    assert len(counts)==6 and min(counts.values())>=3,counts
    assert len({r['sha256'] for r in allrows})==len(allrows),'Duplicate source videos'
    # Validate signer separation from the file's participant identifiers.
    signers={s:{r['participant'] for r in allrows if r['split']==s} for s in ['train','val','test']}
    assert all('unknown' not in participants for participants in signers.values()),'Missing participant identifier'
    assert not (signers['train']&signers['val'] or signers['train']&signers['test'] or signers['val']&signers['test']),signers
    vd=distances(val,train);nvd=distances(negative_val,train) if negative_val else None;best=None
    for limit,ratio,votes,strong in itertools.product([.2,.3,.4,.5,.65,.8,1.,1.2,2.,3.,4.],[1.,1.1,1.2,1.3,1.5],[1,2],[1.5,2.,2.5,3.,5.]):
        p={'maxDistance':limit,'minRatio':ratio,'minVotes':votes,'mirror':True,'strongRatio':strong}
        stats=metrics(val,predict(vd,train,p));false_accepts=sum(x is not None for x in predict(nvd,train,p)) if nvd is not None else 0
        score=stats['wrong']*4+stats['rejected']+false_accepts*4
        if best is None or score<best[0]:best=(score,p,stats)
    _,p,validation=best
    td=distances(test,train);outputs=predict(td,train,p);teststats=metrics(test,outputs)
    unknown_outputs=predict(distances(negative_test,train),train,p) if negative_test else []
    confusion={label:dict.fromkeys(list(counts)+['rejected'],0) for label in counts}
    for row,out in zip(test,outputs):confusion[row['label']][out or 'rejected']+=1
    report={'source':'PopSign ASL v1.0 (game category)','sourceUrl':'https://signdata.cc.gatech.edu/view/guides/downloading_popsign/index.html',
            'license':'CC-BY-4.0','encoding':'two-hand-motion-v3',
            'evaluationProtocol':'Feature revision and thresholds selected on validation only. This test subset was evaluated by the prior version, so results are a regression comparison rather than a fresh independent benchmark. Test recordings are never training references.',
            'selection':'First archive members, at most three per signer per word; 24 train, 8 validation, 12 test requested per word.',
            'signers':{s:sorted(v) for s,v in signers.items()},'signerOverlap':False,
            'downloaded':dict(Counter(r['split'] for r in allrows)),'usable':dict(Counter(r['split'] for r in rows)),
            'excludedForTracking':dict(Counter(r['split'] for r in allrows if r['sequence'] is None)),
            'unknownWordTest':{'label':'DRINK','total':len(negative_test),'falseAccepts':sum(x is not None for x in unknown_outputs),'rejected':unknown_outputs.count(None)},
            'validationUnknownWord':{'label':'DRINK','total':len(negative_val),'falseAccepts':sum(x is not None for x in predict(nvd,train,p)) if nvd is not None else 0},
            'trainingPerWord':dict(counts),'parameters':p,'validation':validation,'test':teststats,'confusion':confusion,
            'testIncludingTrackingFailures':{'correct':teststats['correct'],'total':sum(r['split']=='test' and r['label']!='DRINK' for r in allrows)},
            'limitations':'Small six-word subset; only sufficiently tracked clips evaluated. No live-camera accuracy benchmark. Unsupported-word evaluation covers DRINK only. Distance is not a probability. Review suggestions before adding them.',
            'selectionObjective':'Minimize 4*wrong + rejected + 4*unknown false accepts on validation only.'}
    model={'version':1,'encoding':'two-hand-motion-v3','parameters':p,'labels':list(counts),
           'attribution':'PopSign ASL v1.0, Starner et al. (2023), CC BY 4.0; converted to hand landmarks and normalized sequences.',
           'sourceUrl':'https://signdata.cc.gatech.edu/','samples':[{'label':r['label'],'sequence':r['sequence']} for r in train]}
    (OUTPUT/'asl-words.json').write_text(json.dumps(model,separators=(',',':')))
    (OUTPUT/'asl-words-evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    (OUTPUT/'asl-words-test.json').write_text(json.dumps([{'label':r['label'],'sequence':r['sequence'],'expected':o} for r,o in zip(test,outputs)],separators=(',',':')))
    (OUTPUT/'asl-words-sources.json').write_text(json.dumps([{k:r[k] for k in ['label','split','participant','source','member','sha256']}|{'tracked':r['sequence'] is not None} for r in allrows],indent=2)+'\n')
    print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache',type=Path,default=CACHE)
    parser.add_argument('--output',type=Path,default=OUTPUT)
    args=parser.parse_args();CACHE=args.cache.resolve();OUTPUT=args.output.resolve()
    main()
