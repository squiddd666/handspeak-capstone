"""Train all targets; choose on validation only, then evaluate test once.

Input data and checkpoints stay in the external research directory.
"""
import copy,json,time
from pathlib import Path
import numpy as np
import torch
from sklearn.metrics import classification_report,confusion_matrix,f1_score
from train_essential import ROOT,_build_runtime
from target20_data import LABELS

CACHE=ROOT.parent/'handspeak-training'

def augment(x,rng):
    x=x.copy()
    # Time-window variation, small coordinate noise, and handedness variation.
    start=int(rng.integers(0,4));end=int(rng.integers(28,33))
    index=np.linspace(start,end-1,32);lo=index.astype(int);hi=np.minimum(lo+1,31)
    w=(index-lo)[None,:,None].astype(np.float32)
    x=x[:,lo]*(1-w)+x[:,hi]*w
    x[:2]+=rng.normal(0,.005,x[:2].shape).astype(np.float32)
    if rng.random()<.5:
        nodes=[0,2,1,4,3,6,5]+list(range(17,27))+list(range(7,17))
        x=x[:,:,nodes];x[0]*=-1;x[[2,3]]=x[[3,2]]
    return x

def load():
    manifest=json.loads((CACHE/'target20-manifest.json').read_text())
    groups={s:[] for s in ['train','val','test']};failures=[]
    for row in manifest['samples']:
        path=CACHE/'landmarks-v1'/(row['sha256']+'.npz')
        if not path.exists():failures.append(row);continue
        with np.load(path) as data:x=data['x']
        groups[row['split']].append((x,LABELS.index(row['label']),row))
    return groups,failures

def predict(model,x):
    model.eval();parts=[]
    with torch.no_grad():
        for chunk in x.split(16):parts.append(model(chunk).softmax(1))
    return torch.cat(parts)

def validation_score(probs,y):
    return float((probs.argmax(1)==y).float().mean())

def main():
    torch.set_num_threads(4);torch.manual_seed(42);rng=np.random.default_rng(42)
    groups,failures=load()
    def tensors(split):return torch.tensor(np.stack([r[0] for r in groups[split]])),torch.tensor([r[1] for r in groups[split]])
    x,y=tensors('train');vx,vy=tensors('val')
    print('usable splits',{s:len(r) for s,r in groups.items()},'failed',len(failures),flush=True)
    _,model,old_labels,length=_build_runtime(ROOT/'models/beginner-need79-v6.pt')
    old_head=model.decoder.classifier
    head=torch.nn.Linear(old_head.in_features,len(LABELS))
    with torch.no_grad():
        for i,label in enumerate(LABELS):
            if label in old_labels:
                head.weight[i]=old_head.weight[old_labels.index(label)]
                head.bias[i]=old_head.bias[old_labels.index(label)]
    model.decoder.classifier=head
    for p in model.encoder.parameters():p.requires_grad=False
    ax=torch.tensor(np.stack([augment(a,rng) for a,_,_ in groups['train'] for _ in range(6)]))
    ay=y.repeat_interleave(6)
    model.eval()
    with torch.no_grad():
        features=torch.cat([model.encoder(c) for c in ax.split(16)])
        validation_features=torch.cat([model.encoder(c) for c in vx.split(16)])
    weights=1/torch.bincount(ay,minlength=len(LABELS)).float().clamp(min=1)
    weights/=weights.mean()
    loss_fn=torch.nn.CrossEntropyLoss(weight=weights)
    optimizer=torch.optim.AdamW(model.decoder.parameters(),lr=.003,weight_decay=.01)
    best=-1;best_state=None;history=[]
    for epoch in range(180):
        model.decoder.train()
        order=torch.randperm(len(features));loss_total=0
        for chunk in order.split(128):
            optimizer.zero_grad();loss=loss_fn(model.decoder(features[chunk]),ay[chunk]);loss.backward();optimizer.step();loss_total+=float(loss.detach())
        model.eval()
        with torch.no_grad():score=validation_score(model.decoder(validation_features).softmax(1),vy)
        history.append(dict(phase='head',epoch=epoch+1,val_accuracy=score))
        if score>best:best=score;best_state=copy.deepcopy(model.state_dict())
        if (epoch+1)%30==0:print('head',epoch+1,'validation',round(score,4),'best',round(best,4),flush=True)
    model.load_state_dict(best_state)
    for p in model.parameters():p.requires_grad=True
    optimizer=torch.optim.AdamW([{'params':model.encoder.parameters(),'lr':.00003},{'params':model.decoder.parameters(),'lr':.0001}],weight_decay=.01)
    # BatchNorm uses pretrained running statistics; very small batches otherwise
    # introduce an avoidable train/serve distribution shift.
    for epoch in range(35):
        model.train()
        for module in model.modules():
            if isinstance(module,torch.nn.BatchNorm1d) or isinstance(module,torch.nn.BatchNorm2d):module.eval()
        order=torch.randperm(len(x))
        for chunk in order.split(16):
            batch=torch.tensor(np.stack([augment(x[int(i)].numpy(),rng) for i in chunk]))
            optimizer.zero_grad();loss=loss_fn(model(batch),y[chunk]);loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),1);optimizer.step()
        score=validation_score(predict(model,vx),vy)
        history.append(dict(phase='fine-tune',epoch=epoch+1,val_accuracy=score))
        if score>best:best=score;best_state=copy.deepcopy(model.state_dict())
        print('fine-tune',epoch+1,'validation',round(score,4),'best',round(best,4),flush=True)
    model.load_state_dict(best_state);model.eval()
    vp=predict(model,vx);unknown=LABELS.index('UNKNOWN')
    def rejection_cost(gate):
        pred=vp.argmax(1);accept=(vp.max(1).values>=gate)&(pred!=unknown)
        wrong=accept&(pred!=vy);reject=(~accept)&(vy!=unknown)
        return int(wrong.sum())*5+int(reject.sum())
    gate=min([.3,.4,.5,.6,.7,.8,.9,.95],key=rejection_cost)
    report={'labels':LABELS,'selected_gate':gate,'best_validation_accuracy':best,'history':history,'splits':{},'failed_clips':[dict(label=r['label'],split=r['split']) for r in failures],
      'limitations':['Warm-start checkpoint has historical exposure to this source dataset. Official split signer separation is preserved, but this is not a newly independent pretraining benchmark.','Physical camera and OS virtual-camera verification are separate required checks.','Tracking failures are counted as unsuccessful recognition in end-to-end totals.']}
    for split in ['val','test']:
        sx,sy=tensors(split);start=time.perf_counter();probs=predict(model,sx);elapsed=(time.perf_counter()-start)*1000/len(sx)
        raw=probs.argmax(1).numpy();gold=sy.numpy();accepted=(probs.max(1).values.numpy()>=gate)&(raw!=unknown)
        gated=np.where(accepted,raw,len(LABELS))
        known=gold!=unknown
        counts={label:sum(r['label']==label and r['split']==split for r in json.loads((CACHE/'target20-manifest.json').read_text())['samples']) for label in LABELS}
        perword={}
        for i,label in enumerate(LABELS):
            mask=gold==i;correct=int(((gated==i)&mask).sum());wrong=int(((gated!=i)&(gated!=len(LABELS))&mask).sum())
            tp=correct;fp=int(((gated==i)&(~mask)).sum());total=counts[label];precision=tp/(tp+fp) if tp+fp else 0;recall=tp/total if total else 0
            perword[label]=dict(samples=total,tracked=int(mask.sum()),correct=correct,incorrect=wrong,rejected=int(((gated==len(LABELS))&mask).sum()),tracking_failures=total-int(mask.sum()),accuracy=recall,precision=precision,recall=recall,f1=2*precision*recall/(precision+recall) if precision+recall else 0,raw_correct=int(((raw==i)&mask).sum()))
        matrix_gold=gold.tolist()+[LABELS.index(r['label']) for r in failures if r['split']==split]
        matrix_pred=gated.tolist()+[len(LABELS)+1 for r in failures if r['split']==split]
        report['splits'][split]=dict(raw_accuracy=float((raw[known]==gold[known]).mean()),gated_accuracy=float(((gated==gold)&known).sum()/sum(counts[l] for l in LABELS[:-1])),unknown_false_accept=int((accepted&~known).sum()),unknown_tracked=int((~known).sum()),confusion_labels=LABELS+['REJECT','TRACKING_FAILURE'],confusion_matrix=confusion_matrix(matrix_gold,matrix_pred,labels=list(range(len(LABELS)+2))).tolist(),per_word=perword,model_ms_per_clip=elapsed)
    out=CACHE/'target20-candidate.pt'
    torch.save(dict(state_dict=best_state,labels=LABELS,T=32,version='target20-v1',seed=42,gate=gate),out)
    report['checkpoint']=str(out);report['ready']=False
    (CACHE/'target20-report.json').write_text(json.dumps(report,indent=2))
    print('TRAINING COMPLETE',json.dumps({s:{k:v for k,v in m.items() if k in ['raw_accuracy','gated_accuracy','unknown_false_accept','unknown_tracked']} for s,m in report['splits'].items()}),flush=True)

if __name__=='__main__':main()
