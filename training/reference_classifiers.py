"""Independent numerical references for software parity, NOT accuracy labels."""
from collections import Counter
import numpy as np
from fit_words import distance, mirror


def static_prediction(features, samples, parameters):
    counts=Counter(s['label'] for s in samples)
    references=[s for s in samples if counts[s['label']]>=10]
    x=np.asarray(features);a=np.asarray([s['features'] for s in references]);weights=np.tile([1,1,parameters['zWeight']],21)
    reflected=x.copy();reflected[::3]*=-1
    distances=np.minimum(np.sqrt(np.mean(((a-x)*weights)**2,axis=1)),np.sqrt(np.mean(((a-reflected)*weights)**2,axis=1)))
    order=np.argsort(distances,kind='stable');votes={}
    for i in order[:parameters['k']]:
        label=references[i]['label'];votes[label]=votes.get(label,0)+1/(distances[i]+.001)
    label=max(votes,key=votes.get);agreement=votes[label]/sum(votes.values())
    nearest=distances[order[0]];other=min(d for s,d in zip(references,distances) if s['label']!=label)
    if agreement<parameters['minAgreement'] or nearest>parameters['maxDistance'] or other/(nearest+1e-8)<parameters['minRatio']:return None
    return label


def motion_prediction(sequence, samples, parameters):
    counts=Counter(s['label'] for s in samples)
    x=np.asarray(sequence);reflected=mirror(x)
    ranking=sorted([(min(distance(x,np.asarray(s['sequence'])),distance(reflected,np.asarray(s['sequence']))) if parameters['mirror'] else distance(x,np.asarray(s['sequence'])),s['label']) for s in samples if counts[s['label']]>=3],key=lambda r:r[0])
    nearest,label=ranking[0];other=next(d for d,l in ranking if l!=label)
    separation=other/(nearest+1e-6);votes=sum(l==label for _,l in ranking[:3])
    limit=parameters.get('maxDistanceByLabel',{}).get(label,parameters['maxDistance'])
    if nearest>limit or separation<parameters['minRatio'] or (votes<parameters['minVotes'] and separation<parameters.get('strongRatio',float('inf'))):return None
    return label
