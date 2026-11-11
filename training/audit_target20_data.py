"""Verify official file/label/signer mappings and hashes, without model selection."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

from target20_data import TARGETS

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT.parent / 'handspeak-training'


def main():
    path = CACHE / 'target20-v2-manifest.json'
    m = json.loads(path.read_text())
    csvs = {s: {r['Video file']: r for r in csv.DictReader((CACHE/f'{s}.csv').open(encoding='utf-8-sig'))}
            for s in ('train','val','test')}
    errors = []
    for row in m['samples']:
        file = Path(row['file']); official = csvs[row['split']].get(file.name)
        if not official or official['Gloss'] != row['gloss'] or official['Participant ID'] != row['participant']:
            errors.append(dict(error='official_mapping_mismatch', file=file.name))
        if row['label'] != TARGETS.get(row['gloss'], 'UNKNOWN'):
            errors.append(dict(error='label_mismatch', file=file.name))
        if not file.exists() or hashlib.sha256(file.read_bytes()).hexdigest() != row['sha256']:
            errors.append(dict(error='hash_mismatch', file=file.name))
    for a,b in [('train','val'),('train','test'),('val','test')]:
        for key in ('participant','sha256'):
            if {r[key] for r in m['samples'] if r['split']==a} & {r[key] for r in m['samples'] if r['split']==b}:
                errors.append(dict(error='split_overlap', splits=[a,b], key=key))
    report = dict(passed=not errors, errors=errors, total_clips=len(m['samples']),
                  source=m['source'], labels=m['labels'],
                  counts={s:dict(Counter(r['label'] for r in m['samples'] if r['split']==s)) for s in csvs},
                  signers={s:len({r['participant'] for r in m['samples'] if r['split']==s}) for s in csvs},
                  caveats=['Byte-level duplicates checked; perceptual near-duplicate and linguistic expert review not completed.',
                           'The warm-start baseline has historical source exposure; its pretraining split integrity is not established.'])
    (CACHE/'target20-v2-data-audit.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
    if errors: raise RuntimeError('Dataset integrity checks failed')


if __name__=='__main__': main()
