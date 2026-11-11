"""Fixed validation-only comparison. Never reads a test landmark array.

From-scratch temporal conv (two seeds) versus preserved warm-start ST-GCN.
Threshold selection uses validation only and a one-sided binomial bound.
Final regression/new-unknown evaluation is a separate, locked command.
"""
import copy
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch
from scipy.stats import beta
from sklearn.metrics import f1_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from target20_candidate import TemporalCandidate
from beginner_asl import _build_runtime

CACHE = ROOT.parent / 'handspeak-training'
RUN = CACHE / 'target20-v2'


def augment(x, rng):
    x = x.copy()
    # Preserve both endpoints; no random removal of sign starts/ends.
    index = np.linspace(0, 1, 32) ** rng.uniform(.85, 1.15) * 31
    lo = index.astype(int); hi = np.minimum(lo + 1, 31)
    w = (index - lo)[None, :, None].astype(np.float32)
    x[:2] = x[:2, lo] * (1 - w) + x[:2, hi] * w
    x[2:] = x[2:, np.round(index).astype(int)]
    visible = np.ones((32, 27), np.float32)
    visible[:, 7:17] = x[2, :, 7:17]; visible[:, 17:] = x[3, :, 17:]
    x[:2] += rng.normal(0, .003, x[:2].shape).astype(np.float32) * visible[None]
    if rng.random() < .5:
        x = x[:, :, [0,2,1,4,3,6,5] + list(range(17,27)) + list(range(7,17))]
        x[0] *= -1; x[[2,3]] = x[[3,2]]
    return x


def load_selection():
    manifest = json.loads((CACHE / 'target20-v2-manifest.json').read_text())
    groups = {'train': [], 'val': []}
    failures = []
    for row in manifest['samples']:
        if row['split'] not in groups:
            continue  # Never open test arrays in the selection process.
        path = CACHE / 'landmarks-v1' / (row['sha256'] + '.npz')
        if path.exists():
            with np.load(path) as data:
                x = data['x']
            assert x.shape == (4,32,27) and np.isfinite(x).all()
            groups[row['split']].append((x, manifest['labels'].index(row['label']), row))
        else:
            failures.append(row)
    return manifest, groups, failures


def probabilities(model, x):
    model.eval()
    with torch.no_grad():
        return torch.cat([model(batch).softmax(1) for batch in x.split(32)]).numpy()


def threshold(probs, y, missing):
    raw = probs.argmax(1); scores = probs.max(1); unknown = y == 20
    attempts = []
    for gate in [*np.arange(.05, 1, .025), .99, .999, .999999]:
        accept = (scores >= gate) & (raw != 20)
        false = int((accept & unknown).sum()); total = int(unknown.sum())
        upper = float(beta.ppf(.95, false + 1, total - false)) if false < total else 1.
        pred = np.where(accept, raw, 21)
        gold = np.r_[y, missing]; output = np.r_[pred, np.full(len(missing), 21)]
        macro = float(f1_score(gold, output, labels=list(range(20)), average='macro', zero_division=0))
        attempts.append(dict(gate=float(gate), macro_f1=macro, unknown_false_accept=false,
                             unknown_total=total, unknown_far_upper_95=upper))
    feasible = [a for a in attempts if a['unknown_far_upper_95'] <= .05]
    best = max(feasible or attempts, key=lambda a: (a['macro_f1'] if feasible else -a['unknown_false_accept'], a['gate']))
    return best, attempts


def main():
    global RUN
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-name',default='target20-v2')
    args=parser.parse_args()
    if Path(args.run_name).name!=args.run_name:raise ValueError('Run name must be a directory name')
    RUN=CACHE/args.run_name
    if (RUN / 'selection.json').exists():
        raise RuntimeError('Versioned selection already exists; choose a new run version instead of overwriting.')
    RUN.mkdir(exist_ok=True)
    torch.set_num_threads(3)
    manifest, groups, failures = load_selection()
    arrays = {s: torch.tensor(np.stack([r[0] for r in rows])) for s, rows in groups.items()}
    labels = {s: np.array([r[1] for r in rows]) for s, rows in groups.items()}
    vx = arrays['val']; vy = labels['val']
    missing = np.array([manifest['labels'].index(r['label']) for r in failures if r['split'] == 'val'], dtype=int)
    trials = []
    for seed in (42, 71):
        torch.manual_seed(seed); rng = np.random.default_rng(seed)
        model = TemporalCandidate(); optimizer = torch.optim.AdamW(model.parameters(), lr=.001, weight_decay=.01)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='max', factor=.5, patience=7)
        weights = 1 / np.bincount(labels['train'], minlength=21).clip(1)
        loss_fn = torch.nn.CrossEntropyLoss(weight=torch.tensor(weights / weights.mean(), dtype=torch.float32), label_smoothing=.03)
        best = -1; state = None; stale = 0; history = []
        for epoch in range(120):
            model.train()
            order = rng.permutation(len(arrays['train']))
            for chunk in np.array_split(order, max(1, int(np.ceil(len(order)/32)))):
                batch = torch.tensor(np.stack([augment(arrays['train'][i].numpy(), rng) for i in chunk]))
                target = torch.tensor(labels['train'][chunk],dtype=torch.long)
                optimizer.zero_grad(); loss = loss_fn(model(batch), target); loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1); optimizer.step()
            p = probabilities(model, vx)
            score = float(f1_score(vy, p.argmax(1), labels=list(range(20)), average='macro', zero_division=0))
            scheduler.step(score); history.append(dict(epoch=epoch+1, raw_macro_f1=score))
            if score > best + .0001:
                best = score; state = copy.deepcopy(model.state_dict()); stale = 0
            else:
                stale += 1
            if (epoch+1) % 10 == 0:
                print('tcn',seed,'epoch',epoch+1,'validation macro F1',round(score,4),'best',round(best,4),flush=True)
            if stale >= 20:
                break
        model.load_state_dict(state)
        p = probabilities(model, vx); selected, attempts = threshold(p, vy, missing)
        name = f'target20-v2-tcn-s{seed}'
        path = RUN / (name + '.pt')
        torch.save(dict(state_dict=state, architecture='target20-tcn-v2', width=64,
                        labels=manifest['labels'], T=32, version=name, seed=seed, gate=selected['gate']), path)
        trials.append(dict(name=name, checkpoint=str(path), validation=selected, history=history,
                           threshold_trials=attempts, pretrained=False))
    # Preserved baseline: compare with the same expanded validation set, not its test data.
    _, model, old_labels, _ = _build_runtime(CACHE / 'target20-candidate.pt')
    assert old_labels == manifest['labels']
    selected, attempts = threshold(probabilities(model, vx), vy, missing)
    trials.append(dict(name='preserved-stgcn-v1', checkpoint=str(CACHE/'target20-candidate.pt'),
                       validation=selected, threshold_trials=attempts, pretrained=True))
    best = max(trials, key=lambda r: (r['validation']['unknown_far_upper_95'] <= .05, r['validation']['macro_f1']))
    result = dict(protocol='Two from-scratch TCN seeds versus preserved ST-GCN; validation macro F1 under unknown-FAR constraint; no test arrays opened.',
                  labels=manifest['labels'], dataset_sha256=hashlib.sha256((CACHE/'target20-v2-manifest.json').read_bytes()).hexdigest(),
                  trials=trials, selected=best['name'], selected_checkpoint=best['checkpoint'],
                  selected_threshold=best['validation']['gate'], test_evaluation_performed=False,
                  limitations=['Validation reused for early stopping, selection and threshold estimation; optimistic selection estimate.',
                               'Binomial interval assumes independent clips; signer clustering weakens this assumption.',
                               'Known-word test was exposed before this task; no claim of a fresh independent benchmark.',
                               'No physical webcam or signer is available.'])
    (RUN / 'selection.json').write_text(json.dumps(result,indent=2))
    print('SELECTION LOCKED',best['name'],best['validation'],flush=True)


if __name__ == '__main__':
    main()
