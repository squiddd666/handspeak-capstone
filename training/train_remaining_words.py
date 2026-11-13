"""Versioned validation-only experiment; never replaces website checkpoints."""
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT.parent / 'handspeak-training'
RUN = CACHE / 'remaining-words-20261112'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    RUN.mkdir(parents=True, exist_ok=True)
    lock = RUN / 'running.lock'
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    stage = 'initializing'
    protected = [CACHE / 'target20-candidate.pt', ROOT / 'models/target20-passed.json']
    hashes = {str(path): digest(path) for path in protected}
    passed = json.loads(protected[1].read_text())['words']
    labels = json.loads((CACHE / 'target20-manifest.json').read_text())['labels']
    remaining = [label for label in labels if label != 'UNKNOWN' and label not in passed]

    def status(state, **extra):
        (RUN / 'status.json').write_text(json.dumps(dict(
            stage=state, updated=datetime.now(timezone.utc).isoformat(),
            pid=os.getpid(), remaining_words=remaining, protected_sha256=hashes,
            ready=False, automatically_deployed=False, **extra), indent=2))

    def run(name, *args):
        nonlocal stage
        stage = name
        status(stage)
        with (RUN / (name + '.log')).open('a', encoding='utf-8') as log:
            subprocess.run([sys.executable, '-u', *args], cwd=ROOT,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
        if any(digest(Path(path)) != expected for path, expected in hashes.items()):
            raise RuntimeError('Protected website artifacts changed during training')

    try:
        if (RUN / 'selection.json').exists():
            raise RuntimeError('Completed run exists; choose a new version rather than overwrite')
        (RUN / 'protocol.json').write_text(json.dumps(dict(
            targets=remaining, selection='Two from-scratch temporal models, seeds 42 and 71, compared to preserved ST-GCN using validation only.',
            test_arrays_used=False, auto_promotion=False,
            limitations=['Existing test results are exposed; not a new independent benchmark.',
                         'Validation selection is optimistic; independent evaluation and camera checks remain required.']), indent=2))
        run('expand-unknown-data', 'training/target20_expand_unknown.py')
        run('train-validation-only', 'training/train_target20_v2.py', '--run-name', RUN.name)
        selection = json.loads((RUN / 'selection.json').read_text())
        status('complete-review-required', selected=selection['selected'],
               selected_checkpoint=selection['selected_checkpoint'],
               validation=next(trial['validation'] for trial in selection['trials']
                               if trial['name'] == selection['selected']),
               test_evaluation_performed=False)
    except Exception as error:
        status('failed', failed_stage=stage, error=str(error))
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
