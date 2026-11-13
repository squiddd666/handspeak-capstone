"""Wait for locked model selection, then evaluate once without deployment."""
import csv
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT.parent / 'handspeak-training' / 'remaining-words-20261112'


def main():
    lock = RUN / 'evaluation.lock'
    descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    os.close(descriptor)
    def status(stage, **extra):
        (RUN / 'evaluation-status.json').write_text(json.dumps(dict(
            stage=stage, updated=datetime.now(timezone.utc).isoformat(),
            automatically_deployed=False, **extra), indent=2))

    try:
        if (RUN / 'final-evaluation.json').exists():
            status('already-evaluated', note='Locked results preserved; no repeated test evaluation.')
            return
        status('waiting-for-training')
        deadline = time.monotonic() + 24*60*60
        while not (RUN / 'selection.json').exists():
            training = json.loads((RUN / 'status.json').read_text())
            if training['stage'] == 'failed':
                raise RuntimeError('Training failed: ' + training.get('error', 'unknown error'))
            if time.monotonic() > deadline:
                raise TimeoutError('Training has not produced a selection within 24 hours')
            time.sleep(30)
        status('evaluating-locked-candidate')
        import evaluate_target20_v2 as evaluator
        protocol = json.loads((RUN / 'protocol.json').read_text())
        targets = set(protocol['targets'])

        def write_local_reports(result, manifest):
            rows = []
            for label, metrics in result['splits']['test']['per_word'].items():
                rows.append(dict(word=label, remaining_target=label in targets,
                                 offline_threshold_passed=metrics['recall'] >= .8 and metrics['precision'] >= .85,
                                 **metrics))
            with (RUN / 'per-word-evaluation.csv').open('w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=list(rows[0]))
                writer.writeheader()
                writer.writerows(rows)
            summary = dict(selected=result['selection']['selected'], gate=result['gate'],
                           remaining_words={row['word']: row for row in rows if row['remaining_target']},
                           scope=result['test_scope'], physical_webcam_tested=False,
                           ready=False, automatically_deployed=False,
                           unknown_false_accept=result['splits']['test']['unknown_false_accept'],
                           unknown_tracked=result['splits']['test']['unknown_tracked'])
            (RUN / 'remaining-word-results.json').write_text(json.dumps(summary, indent=2))

        # Keep reports local: the legacy writer overwrites prior root-level evidence.
        evaluator.write_reports = write_local_reports
        import sys
        sys.argv = [sys.argv[0], '--run-name', RUN.name]
        evaluator.main()
        status('evaluation-complete', results=str(RUN / 'remaining-word-results.json'),
               note='Recorded-clip regression, not independent known-word or live-camera verification.')
    except Exception as error:
        status('failed', error=str(error))
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
