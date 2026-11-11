"""Publish this run's aggregate results, without claiming webcam validation.

Raw clips, landmark sequences, and the research checkpoint remain private.
"""
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT.parent / 'handspeak-training'


def main():
    report = json.loads((CACHE / 'target20-report.json').read_text())
    manifest = json.loads((CACHE / 'target20-manifest.json').read_text())
    labels = report['labels'][:-1]
    assert len(labels) == len(set(labels)) == 20
    groups = {s: [r for r in manifest['samples'] if r['split'] == s]
              for s in ('train', 'val', 'test')}
    for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]:
        for key in ('participant', 'sha256'):
            assert not {r[key] for r in groups[a]} & {r[key] for r in groups[b]}
    out = ROOT / 'reports' / 'target20-current'
    out.mkdir(parents=True, exist_ok=True)
    checkpoint = CACHE / 'target20-candidate.pt'
    config = dict(labels=report['labels'], checkpoint_sha256=hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                  pretrained_source_sha256=hashlib.sha256((ROOT / 'models' / 'beginner-need79-v6.pt').read_bytes()).hexdigest(),
                  sequence_length=32, rejection_gate=report['selected_gate'], deployment_ready=False)
    evidence = {k: v for k, v in report.items() if k != 'checkpoint'}
    evidence.update(source=manifest['source'], license='Microsoft Research License: non-commercial research; no data redistribution',
                    generated_at_utc=datetime.now(timezone.utc).isoformat(),
                    signer_disjoint=True, duplicate_hashes_across_splits=False,
                    split_counts={s: dict(Counter(r['label'] for r in rows)) for s, rows in groups.items()},
                    physical_camera_tested=False, simulated_camera_tested=False,
                    scope='Offline recorded-video evaluation only; not live-camera accuracy')
    (out / 'evaluation.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    (out / 'model-config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
    with (out / 'per-word.csv').open('w', newline='', encoding='utf-8') as f:
        rows = report['splits']['test']['per_word']
        writer = csv.DictWriter(f, fieldnames=['word', *rows[labels[0]]])
        writer.writeheader()
        for label in labels:
            writer.writerow(dict(word=label, **rows[label]))
    lines = ['# 20-word motion model — experimental', '',
             'This run trained a new candidate on real ASL Citizen motion clips. It is not deployment-ready.', '',
             'Words: ' + ', '.join(labels) + '.', '',
             '## Recorded-video results', '',
             '| Split | Raw top-1 on tracked known signs | Correct after rejection, including tracking failures | Unknown clips falsely accepted |',
             '| --- | ---: | ---: | ---: |']
    for s in ('val', 'test'):
        m = report['splits'][s]
        lines.append(f"| {s} | {m['raw_accuracy']:.1%} | {m['gated_accuracy']:.1%} | {m['unknown_false_accept']}/{m['unknown_tracked']} |")
    lines += ['', f"Rejection threshold: {report['selected_gate']}; selected using validation only.", '',
              'Training, validation, and test use the official separate signers. File hashes were checked for cross-split duplicates.',
              'The pretrained checkpoint has historical exposure to this source. These results are not a newly independent pretraining benchmark.',
              'No physical or simulated webcam test was performed for this run. Offline accuracy is not live-camera accuracy.', '',
              '## Use', '',
              'Start the Python server. Select Words in motion, choose a word under 20 words in motion, enable server landmark-processing consent, then record one complete sign and review the result.',
              'The private checkpoint and its threshold report are in ../handspeak-training/. Raw videos and landmarks are not published by the website.', '',
              '## Sources and terms', '',
              '- https://www.microsoft.com/en-us/research/project/asl-citizen/',
              '- https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/',
              '- Non-commercial research only; do not redistribute the downloaded data or landmark derivatives.', '',
              '## Reproduce', '',
              'Run training/target20_data.py, training/train_target20.py, and training/publish_target20_offline.py using the project Python 3.11 environment.', '']
    (out / 'README.md').write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps(config, indent=2))
    print(out / 'README.md')


if __name__ == '__main__':
    main()
