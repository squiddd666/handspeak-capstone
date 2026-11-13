"""Run the local licensed-data pipeline, preserving logs and experimental status.
No server restart or automatic checkpoint promotion is performed.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT.parent / 'handspeak-training'

def main():
    CACHE.mkdir(exist_ok=True)
    status_path = CACHE / 'pipeline-status.json'
    def status(stage, **extra):
        status_path.write_text(json.dumps(dict(stage=stage, updated=datetime.now(timezone.utc).isoformat(), ready=False, **extra), indent=2))
    def run(stage, *arguments):
        status(stage)
        with (CACHE / (stage + '.log')).open('a', encoding='utf-8') as log:
            subprocess.run([sys.executable, '-u', *arguments], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
    try:
        run('download-extract', 'training/target20_data.py')
        manifest=json.loads((CACHE/'target20-manifest.json').read_text())
        selected=[row for row in manifest['samples'] if row['label'] in ['HELP','I / ME','YOU','NEED','WHERE']]
        (CACHE/'essential-manifest.json').write_text(json.dumps(dict(source=manifest['source'], labels=['HELP','I / ME','YOU','NEED','WHERE'], signer_disjoint=True,samples=selected),indent=2))
        run('train-target20', 'training/train_target20.py')
        run('train-essential', 'training/train_essential.py', '--cache', str(CACHE))
        run('evaluate-essential', 'training/check_essential_rejection.py')
        report=json.loads((CACHE/'target20-report.json').read_text())
        metrics=report['splits']['test']
        per_word=metrics['per_word']
        passed=all(per_word[label]['recall']>=.8 and per_word[label]['precision']>=.85 for label in report['labels'] if label!='UNKNOWN')
        status('training-complete-review-required', offline_per_word_gate_passed=passed, live_camera_verified=False,
               note='Do not iterate against test scores. New independent evaluation and camera checks are required before readiness.')
    except Exception as error:
        status('failed', error=str(error))
        raise

if __name__ == '__main__':
    main()
