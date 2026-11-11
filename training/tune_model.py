"""Choose rejection thresholds on validation images, then evaluate once on test images."""
import json
import numpy as np
from train_asl import LABELS, SOURCE, REVISION, predict as baseline_predict


def distance_matrix(rows, samples, z_weight):
    weights = np.tile([1, 1, z_weight], 21)
    a = np.array([r['features'] for r in rows])*weights
    b = np.array([r['features'] for r in samples])*weights
    mirrored = a.copy()
    mirrored[:, ::3] *= -1
    def distance(x):
        return np.sqrt(np.maximum(0, ((x*x).sum(1)[:, None]+(b*b).sum(1)[None, :]-2*x@b.T)/63))
    return np.minimum(distance(a), distance(mirrored))


def predictions(distances, samples, parameters):
    labels = np.array([LABELS.index(r['label']) for r in samples])
    indices = np.argsort(distances, axis=1)[:, :parameters['k']]
    nearest = np.take_along_axis(distances, indices, axis=1)
    neighbor_labels = labels[indices]
    votes = np.array([((neighbor_labels == i)/(nearest+.001)).sum(1) for i in range(len(LABELS))]).T
    winners = votes.argmax(1)
    agreement = votes.max(1)/votes.sum(1)
    other = np.where(labels[None, :] != winners[:, None], distances, np.inf).min(1)
    accepted = ((agreement >= parameters['minAgreement']) & (nearest[:, 0] <= parameters['maxDistance'])
                & (other/(nearest[:, 0]+1e-8) >= parameters['minRatio']))
    return [LABELS[label] if accept else None for label, accept in zip(winners, accepted)]


def metrics(rows, results):
    correct = sum(r['label'] == result for r, result in zip(rows, results))
    rejected = results.count(None)
    wrong = len(rows)-correct-rejected
    return {'correct': correct, 'wrong': wrong, 'rejected': rejected, 'total': len(rows),
            'accuracyIncludingRejections': correct/len(rows), 'coverage': (len(rows)-rejected)/len(rows),
            'accuracyWhenAccepted': correct/(len(rows)-rejected) if len(rows)>rejected else 0}


def build_model(extraction, output):
    # Preserve the previous test split. Threshold selection sees validation only.
    rng = np.random.default_rng(42)
    original_train, test = [], []
    for label in LABELS:
        rows = [r for r in extraction['records'] if r['label'] == label]
        rng.shuffle(rows)
        count = max(1, round(len(rows)*.2))
        test.extend(rows[:count])
        original_train.extend(rows[count:])
    rng = np.random.default_rng(17)
    fit, validation = [], []
    for label in LABELS:
        rows = [r for r in original_train if r['label'] == label]
        rng.shuffle(rows)
        count = round(len(rows)*.2)
        validation.extend(rows[:count])
        fit.extend(rows[count:])
    best = None
    for z in [.25, .5, 1.]:
        distances = distance_matrix(validation, fit, z)
        for k in [3, 5, 7]:
            for agreement in [.7, .8, .9]:
                for limit in [.15, .25, .35]:
                    for ratio in [1., 1.2, 1.5]:
                        parameters = dict(zWeight=z, k=k, minAgreement=agreement, maxDistance=limit, minRatio=ratio)
                        stats = metrics(validation, predictions(distances, fit, parameters))
                        score = stats['wrong']*5+stats['rejected']
                        if best is None or score < best[0]:
                            best = (score, parameters, stats)
    _, parameters, validation_stats = best
    samples = [{'label': r['label'], 'features': r['features']} for r in fit]
    test_predictions = predictions(distance_matrix(test, fit, parameters['zWeight']), fit, parameters)
    test_stats = metrics(test, test_predictions)
    baseline_stats = metrics(test, [baseline_predict(r['features'], original_train) for r in test])
    confusion = {label: dict.fromkeys(LABELS+['rejected'], 0) for label in LABELS}
    for row, result in zip(test, test_predictions):
        confusion[row['label']][result or 'rejected'] += 1
    report = {
        'version': 2, 'source': SOURCE, 'revision': REVISION,
        'license': 'No license specified in source dataset card at download time.',
        'split': 'Original seed-42 stratified 20% image test retained. Seed 17 takes 20% of remaining images for validation. Exact decoded images deduplicated before splitting.',
        'selectionObjective': 'Minimize 5 * wrong + rejected on validation only. Never refit with validation or test samples.',
        'limitations': 'Not signer-independent or live-camera accuracy; near-duplicates may remain. Only images with detected hands evaluated. No unsupported-sign test set. Digit 5 requires personal samples. Personalization is not evaluated here.',
        'uniqueImages': extraction['uniqueImages'], 'undetectedImages': extraction['undetected'],
        'trainingSamples': len(fit), 'validationSamples': len(validation), 'testSamples': len(test),
        'parameters': parameters, 'validation': validation_stats, 'test': test_stats,
        'previousModelSameTest': baseline_stats, 'confusion': confusion,
    }
    model = {'version': 2, 'normalization': 'wrist-palm-rotation-v1', 'labels': LABELS,
             'source': SOURCE, 'revision': REVISION, 'parameters': parameters, 'samples': samples}
    (output/'asl-knn.json').write_text(json.dumps(model, separators=(',', ':')))
    (output/'asl-evaluation.json').write_text(json.dumps(report, indent=2)+'\n')
    # Include every test prediction, including rejection cases, for Python/JS parity.
    fixtures = [{'label': r['label'], 'features': r['features'], 'expected': result}
                for r, result in zip(test, test_predictions)]
    (output/'asl-test-fixture.json').write_text(json.dumps(fixtures, separators=(',', ':')))
    print(json.dumps(report, indent=2), flush=True)
