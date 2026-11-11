"""Download the five target signs using official signer-disjoint CSV splits.

Keep the cache outside the web root. Raw research videos must not be published.
Requires remotezip. Existing completed downloads are verified and reused.
"""
import argparse
import csv
import hashlib
import io
import json
import time
from pathlib import Path
from remotezip import RemoteZip

URL = 'https://download.microsoft.com/download/b/8/8/b88c0bae-e6c1-43e1-8726-98cf5af36ca4/ASL_Citizen.zip'
GLOSSES = {'HELP': 'HELP', 'ME': 'I / ME', 'YOU': 'YOU', 'NEED': 'NEED', 'WHERE': 'WHERE'}

def download(cache):
    cache.mkdir(parents=True, exist_ok=True)
    with RemoteZip(URL) as archive:
        (cache / 'use.txt').write_bytes(archive.read('ASL_Citizen/use.txt'))
        rows, participants = [], {}
        for split in ('train', 'val', 'test'):
            data = archive.read(f'ASL_Citizen/splits/{split}.csv')
            (cache / f'{split}.csv').write_bytes(data)
            selected = [r for r in csv.DictReader(io.StringIO(data.decode('utf-8-sig'))) if r['Gloss'] in GLOSSES]
            participants[split] = {r['Participant ID'] for r in selected}
            for row in selected:
                rows.append(dict(split=split, label=GLOSSES[row['Gloss']], gloss=row['Gloss'], participant=row['Participant ID'], member='ASL_Citizen/videos/' + row['Video file']))
        assert not (participants['train'] & participants['val'] or participants['train'] & participants['test'] or participants['val'] & participants['test']), 'Signer overlap'
        for i, row in enumerate(rows):
            path = cache / row['split'] / Path(row['member']).name
            path.parent.mkdir(exist_ok=True)
            info = archive.getinfo(row['member'])
            if not path.exists() or path.stat().st_size != info.file_size:
                for attempt in range(3):
                    try:
                        data = archive.read(row['member'])
                        assert len(data) == info.file_size, 'Incomplete download'
                        path.write_bytes(data)
                        break
                    except Exception:
                        if attempt == 2:
                            raise
                        time.sleep(2)
            row.update(file=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size)
            print(f'{i+1}/{len(rows)} {row["split"]} {row["label"]}', flush=True)
    manifest = dict(source=URL, labels=list(GLOSSES.values()), signer_disjoint=True, samples=rows)
    (cache / 'essential-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(dict(clips=len(rows), bytes=sum(r['bytes'] for r in rows), manifest=str(cache / 'essential-manifest.json'))), flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cache = args.cache.resolve()
    if cache == root or root in cache.parents:
        parser.error('Cache must be outside the served website directory')
    download(cache)
