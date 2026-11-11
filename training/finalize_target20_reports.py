"""Finalize transparent aggregate reports from locked evidence; never retrain."""
import csv
import hashlib
import json
import shutil
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT.parent/'handspeak-training'
RUN=CACHE/'target20-v3'


def main():
    final=json.loads((RUN/'final-evaluation.json').read_text())
    manifest=json.loads((CACHE/'target20-v2-manifest.json').read_text())
    audit=json.loads((CACHE/'target20-v2-data-audit.json').read_text())
    checks=json.loads((CACHE/'target20-automated-checks-final.json').read_text())
    reproduction=json.loads((RUN/'reproduction-check.json').read_text())
    api=json.loads((CACHE/'target20-v2-api-checks.json').read_text())
    assert audit['passed'] and reproduction['passed'] and api['passed']
    baseline=hashlib.sha256((CACHE/'target20-candidate.pt').read_bytes()).hexdigest()
    assert baseline=='e9e558d6e0b4bd003e1bc4e4696160d1b5421df0a337c6a891960a21f4d0559d'
    path=ROOT/'target20_per_word_evaluation.csv'
    extras=[]
    for label in final['labels'][:20]:
        counts={}
        for split in ('train','val','test'):
            rows=[r for r in manifest['samples'] if r['split']==split and r['label']==label]
            tracked=sum((CACHE/'landmarks-v1'/(r['sha256']+'.npz')).exists() for r in rows)
            counts[split+'_tracked']=tracked;counts[split+'_tracking_failures']=len(rows)-tracked
        extras.append({'word':label,**counts,**{'val_'+k:v for k,v in final['splits']['val']['per_word'][label].items()}})
    rows=list(csv.DictReader(path.open(encoding='utf-8')))
    for row,extra in zip(rows,extras):
        assert row['word']==extra['word'];row.update(extra)
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    metrics={k:final[k] for k in ('labels','gate','checkpoint_sha256','splits','test_scope','confidence','physical_webcam_tested','production_promoted')}
    (ROOT/'target20_evaluation.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
    failures=[n for c in checks['checks'] for n in c.get('failures',[])]
    total=sum(c.get('tests') or 0 for c in checks['checks'])
    evidence=['','## Final software verification','',
              f'{total} discovered unit tests across both suites: {total-len(failures)} passed, {len(failures)} failed. All 24 focused target-20 contract/tracker/capture tests passed; all six checked JavaScript files parsed. Five HTTP consent/input checks passed. Locked-candidate validation/test per-word and unknown counts were independently re-inferred and reproduced exactly.',
              '', 'Remaining failures (preserved, not hidden or changed to match predictions):',
              *['- '+f for f in failures], '',
              'The static-letter test uses a seven-letter-era normalized-feature fixture against the current orientation-preserving 24-letter model; the first mismatch is reference A, predicted Y. The DTW test fixture expects rejection for a HELLO recording that the current per-label HELLO cutoff accepts. These model/fixture provenance mismatches require compatible source artifacts and an independent re-evaluation; expected predictions were not regenerated from the tested model to manufacture a pass.',
              '', 'Dependency versions: '+', '.join(f'{k}={v}' for k,v in checks['dependencies'].items())+'.',
              '', 'An initial Windows training attempt failed because NumPy labels became Int32 tensors; targets were explicitly changed to torch.long before successful candidate training. This failed attempt is retained in the task record. No metrics or checkpoint from that failed fit were treated as successful.',
              '', 'Runtime investigation also found multiple stale local test servers sharing the same Windows port. Those task-owned servers were stopped, the actual current backend was restarted, and Windows address reuse is disabled in the server class so a conflicting bind fails rather than silently reaching old code.',
              '', '## Remaining scientific/technical gaps','',
              '- Physical webcam and a consenting signer are unavailable (explicit user confirmation); all 200 required attempts remain unperformed.',
              '- Browser Tasks Pose Lite/Hands versus offline Holistic remains an unverified domain mismatch. Hand/body association guards were fixed, but tracker parity is not established.',
              '- Legacy movement cropping can react to missing-hand discontinuities; the new temporal candidate masks invalid velocities but does not undo already-cropped legacy training sequences. Aspect-ratio invariance of that legacy encoding is not established.',
              '- Linguistic correctness of mapped variants and lexical unknowns needs an ASL expert. Lexical unknowns can be semantically related (for example ASSIST versus HELP); CSV mapping checks are not linguistic certification.',
              '- Real incomplete-sign detection is unverified; software checks prove complete capture windows only.',
              '- All known-word test recordings were previously exposed. Further model tuning must not use these final test failures; new consented signer-diverse data and a genuinely untouched known-word benchmark are required.',
              '- The low gated recall is a failed quality target, not a success: the selected rejection policy trades most true signs for low false acceptance. It must not replace the stable model.',
              '', '## Reproduce without overwriting artifacts','',
              'Run from C:/Users/Squid/Desktop/capstonev2. The private data cache already contains the audited source clips and features. Use new run directories for a training reproduction; never erase the locked run.',
              '```powershell',
              '.\\.venv\\Scripts\\python.exe -X utf8 training/train_target20_v2.py --run-name target20-v2-repro',
              '.\\.venv\\Scripts\\python.exe -X utf8 training/train_target20_v3.py --run-name target20-v3-repro --source-run target20-v2-repro',
              '.\\.venv\\Scripts\\python.exe -X utf8 training/evaluate_target20_v2.py --run-name target20-v3-repro',
              '.\\.venv\\Scripts\\python.exe -X utf8 training/reproduce_target20_metrics.py',
              '.\\.venv\\Scripts\\python.exe -X utf8 training/run_target20_checks.py',
              '.\\.venv\\Scripts\\python.exe -X utf8 training/check_target20_api.py',
              '```',
              'The last command requires the actual project server running on localhost:8000. It exercises synthetic HTTP contract inputs, not a physical camera. The checks runner intentionally exits nonzero while the two legacy regressions remain.',
              '', 'The per-word CSV has 20 rows; unprefixed metrics describe the final test, val_ fields describe validation, and source/tracked/failure counts are separate for every split. Latency excludes image tracking and capture. No restricted recording or landmark array is published.','']
    for name in ('target20_training_report.md','target20_final_summary.md'):
        p=ROOT/name;text=p.read_text(encoding='utf-8')
        text=text.split('\n## Final software verification')[0]
        p.write_text(text+'\n'.join(evidence),encoding='utf-8')
    p=ROOT/'target20_acceptance_checklist.md';text=p.read_text(encoding='utf-8')
    text += f'\n- FAIL: all available automated tests pass ({len(failures)} of {total} failed).\n- PASS: five HTTP input/consent checks and locked-candidate metric reproduction.\n- NOT ESTABLISHED: browser/offline tracker parity, linguistic expert review, genuinely untouched known-word benchmark.\n'
    p.write_text(text,encoding='utf-8')
    p=ROOT/'target20_webcam_test_report.md';text=p.read_text(encoding='utf-8')
    text += '\n## Browser-only observations\n\nThe actual HandSpeak interface displayed all 20 words. Selecting practice did not check server consent; Record was refused with “Enable landmark processing for this model first.” A camera startup attempt timed out with no video track. No physical signing, no simulated reference video, and no completed webcam recording were counted. See target20_browser_consent_check.png for the consent observation.\n'
    p.write_text(text,encoding='utf-8')
    p=ROOT/'target20_audit.md';text=p.read_text(encoding='utf-8')
    text += '\n## Executed follow-up\n\nExpanded the deterministic, signer-disjoint subset to 1,243 clips, including 420 newly reserved unknown clips. 1,232 sequences were usable. Source CSV/gloss/participant mappings and SHA-256 file checks passed, with no subset participant/hash overlap across splits. Trained two from-scratch TCN seeds, compared the preserved ST-GCN on expanded validation, then ran a predeclared three-width RBF novelty correction. No new test predictions informed selection. Final known-word evaluation is explicitly an exposed regression benchmark; new unknown evaluation is separately reserved. The rejection policy still fails all per-word recall gates. See the training report for resolved safeguards and unresolved tracker/crop/linguistic/benchmark issues.\n'
    p.write_text(text,encoding='utf-8')
    links=['','## Deliverables','',*['- ['+n+']('+n+')' for n in ['target20_audit.md','target20_training_report.md','target20_per_word_evaluation.csv','target20_confusion_matrix.png','target20_webcam_test_report.md','target20_acceptance_checklist.md']],'']
    p=ROOT/'target20_final_summary.md';p.write_text(p.read_text(encoding='utf-8')+'\n'.join(links),encoding='utf-8')
    snapshot=RUN/'final-runtime-source';snapshot.mkdir(exist_ok=True)
    hashes={}
    for name in ['target20_candidate.py','target20_quality.py','beginner_asl.py','training/train_target20_v2.py','training/train_target20_v3.py','training/evaluate_target20_v2.py']:
        source=ROOT/name;destination=snapshot/Path(name).name
        shutil.copy2(source,destination);hashes[name]=hashlib.sha256(source.read_bytes()).hexdigest()
    (snapshot/'sha256.json').write_text(json.dumps(hashes,indent=2))
    print(json.dumps(dict(ready=False,unit_tests=total,failures=failures,production_promoted=False),indent=2))


if __name__=='__main__':main()
