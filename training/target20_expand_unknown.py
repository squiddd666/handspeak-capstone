"""Deterministically reserve new unknown glosses; keep all research data private."""
import concurrent.futures as cf
import csv
import hashlib
import json
from pathlib import Path

from target20_data import TARGETS, get_archive, worker

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT.parent / 'handspeak-training'


def main():
    output = CACHE / 'target20-v2-manifest.json'
    if output.exists():
        manifest = json.loads(output.read_text())
    else:
        base = json.loads((CACHE / 'target20-manifest.json').read_text())
        tables = {s: list(csv.DictReader((CACHE / f'{s}.csv').open(encoding='utf-8-sig')))
                  for s in ('train', 'val', 'test')}
        excluded = set(TARGETS) | {r['gloss'] for r in base['samples']}
        common = set.intersection(*(set(r['Gloss'] for r in table) for table in tables.values())) - excluded
        glosses = sorted(common, key=lambda g: hashlib.sha256(('target20-v2-20261111:' + g).encode()).hexdigest())
        # Fixed before any new unknown predictions: disjoint glosses as well as official signers.
        selection = {'train': glosses[:40], 'val': glosses[40:70], 'test': glosses[70:140]}
        rows = list(base['samples'])
        with get_archive() as archive:
            for split, selected in selection.items():
                for gloss in selected:
                    matches = sorted((r for r in tables[split] if r['Gloss'] == gloss),
                                     key=lambda r: hashlib.sha256(r['Video file'].encode()).hexdigest())[:3]
                    for row in matches:
                        member = 'ASL_Citizen/videos/' + row['Video file']
                        path = CACHE / split / row['Video file']
                        size = archive.getinfo(member).file_size
                        if not path.exists() or path.stat().st_size != size:
                            data = archive.read(member)  # ZipFile verifies the entry CRC.
                            assert len(data) == size
                            temporary = path.with_suffix('.download')
                            temporary.write_bytes(data)
                            temporary.replace(path)
                        rows.append(dict(file=str(path.resolve()), label='UNKNOWN', gloss=gloss, split=split,
                                         participant=row['Participant ID'], member=member,
                                         sha256=hashlib.sha256(path.read_bytes()).hexdigest(), fresh_unknown=True))
                print('Reserved unknown clips', split, sum(r.get('fresh_unknown', False) and r['split'] == split for r in rows), flush=True)
        for a, b in [('train', 'val'), ('train', 'test'), ('val', 'test')]:
            for key in ('participant', 'sha256'):
                assert not {r[key] for r in rows if r['split'] == a} & {r[key] for r in rows if r['split'] == b}
        manifest = dict(source=base['source'], labels=base['labels'], samples=rows,
                        protocol='Deterministic v2 supplementary unknown reservation; old known test is exposed regression data.',
                        unknown_selection=selection)
        output.write_text(json.dumps(manifest, indent=2))
    rows = [r for r in manifest['samples'] if r.get('fresh_unknown')]
    with cf.ProcessPoolExecutor(max_workers=4) as pool:
        results = []
        for i, result in enumerate(pool.map(worker, [(r, CACHE) for r in rows])):
            results.append(result)
            if i % 30 == 0:
                print('Extracted new unknown', i + 1, '/', len(rows), flush=True)
    (CACHE / 'target20-v2-unknown-extraction.json').write_text(json.dumps(results, indent=2))
    print('Unknown expansion complete', len(rows), flush=True)


if __name__ == '__main__':
    main()
