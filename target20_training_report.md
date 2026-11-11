# Target-20 training report — NOT READY

Candidate: `C:\Users\Squid\Desktop\handspeak-training\target20-v3\target20-v3-selected.pt`
SHA-256: `2912b105a306a1f7f0556ff7d91cd73b82423093aa308baf7ddbf39f9450a17f`

Previously exposed known-word regression set plus newly reserved unknown glosses; not a fresh independent known-word benchmark.
Uncalibrated model scores; rejection gate chosen only from validation.

## Validation-only architecture comparison

| Candidate | Pretrained | Selected gate | Validation macro F1 | Unknown false accepts |
| --- | --- | ---: | ---: | ---: |
| target20-v3-rbf-g2 | False | 0.975 | 0.309 | 0/115 |
| target20-v3-rbf-g8 | False | 0.950 | 0.137 | 1/115 |
| target20-v3-rbf-g32 | False | 0.925 | 0.033 | 0/115 |
| target20-v2-tcn-s42 | False | 0.990 | 0.253 | 0/115 |

TCN: masked positions, valid-only velocities, palm-relative shape, temporal convolution, group normalization, balanced cross entropy, mild endpoint-preserving augmentation, AdamW, ReduceLROnPlateau, 20-epoch patience; seeds 42 and 71. Full TCN configuration/history is private in ../handspeak-training/target20-v2/selection.json. The subsequent v3 RBF correction uses a frozen from-scratch TCN embedding, three predeclared kernel widths (2,8,32), balanced kernel ridge penalty .1, and fixed logit scale .15; the distance kernel decays toward uncertainty on distant embeddings. Full trial and threshold records are in ../handspeak-training/target20-v3/selection.json. No test predictions were used for either iteration.
The preserved ST-GCN is compared under the same expanded validation set. Its historical source exposure is not independently audited. Selection is not proof that its inherited test provenance is clean.
Validation was reused for early stopping, selection, and thresholds; the selection estimate is optimistic. Binomial bounds assume independent clips; repeated signers introduce clustering.
No test predictions were read by the selection script. After selection was locked, the final evaluator ran once. Do not use its failures for further tuning on this same benchmark.

## Recorded-clip results

Validation target macro F1: 0.309; test target macro F1: 0.225.
Test end-to-end correct recognition: 15.4%; raw tracked accuracy: 79.2%.
Unknown false acceptance: 1/224; one-sided 95% binomial upper bound 2.1%.
Newly reserved unknowns only: 1/209; upper bound 2.2%.
Per-word latency is CPU inference only, not browser tracking/capture/network latency. Raw top-1 excludes tracking failures; recall and end-to-end accuracy count them as unsuccessful. False acceptance per word uses all other classes as its denominator.
Linguistic label/variant correctness still needs qualified ASL review. A finite full capture window does not prove a linguistically complete sign.

## Reproduction

Run from C:/Users/Squid/Desktop/capstonev2. Versioned trainers/evaluator refuse overwrites; use a clean private research directory or an explicitly new run version for reproduction. Never erase old results to retune against the test set.
```powershell
.\.venv\Scripts\python.exe -X utf8 training/target20_expand_unknown.py
.\.venv\Scripts\python.exe -X utf8 training/audit_target20_data.py
.\.venv\Scripts\python.exe -X utf8 training/train_target20_v2.py
.\.venv\Scripts\python.exe -X utf8 training/train_target20_v3.py
$env:HANDSPEAK_TARGET20_RUN='target20-v3'
.\.venv\Scripts\python.exe -X utf8 training/evaluate_target20_v2.py
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s training -v
.\.venv\Scripts\python.exe -X utf8 -m unittest discover -s training/accuracy -v
```

Dataset: https://www.microsoft.com/en-us/research/project/asl-citizen/ . Terms: https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/ . Raw clips and derived landmarks are restricted research materials; keep them outside the web root.

## Final software verification

90 discovered unit tests across both suites: 88 passed, 2 failed. All 24 focused target-20 contract/tracker/capture tests passed; all six checked JavaScript files parsed. Five HTTP consent/input checks passed. Locked-candidate validation/test per-word and unknown counts were independently re-inferred and reproduced exactly.

Remaining failures (preserved, not hidden or changed to match predictions):
- test_held_out_predictions_match_python (test_model.ModelTests.test_held_out_predictions_match_python)
- test_browser_matches_heldout_evaluation (test_words.PretrainedWordTests.test_browser_matches_heldout_evaluation)

The static-letter test uses a seven-letter-era normalized-feature fixture against the current orientation-preserving 24-letter model; the first mismatch is reference A, predicted Y. The DTW test fixture expects rejection for a HELLO recording that the current per-label HELLO cutoff accepts. These model/fixture provenance mismatches require compatible source artifacts and an independent re-evaluation; expected predictions were not regenerated from the tested model to manufacture a pass.

Dependency versions: torch=2.15.0, numpy=1.26.4, mediapipe=0.10.21, scipy=1.17.1, scikit-learn=1.9.1, quickjs=1.19.4, remotezip=0.12.6.

An initial Windows training attempt failed because NumPy labels became Int32 tensors; targets were explicitly changed to torch.long before successful candidate training. This failed attempt is retained in the task record. No metrics or checkpoint from that failed fit were treated as successful.

Runtime investigation also found multiple stale local test servers sharing the same Windows port. Those task-owned servers were stopped, the actual current backend was restarted, and Windows address reuse is disabled in the server class so a conflicting bind fails rather than silently reaching old code.

## Remaining scientific/technical gaps

- Physical webcam and a consenting signer are unavailable (explicit user confirmation); all 200 required attempts remain unperformed.
- Browser Tasks Pose Lite/Hands versus offline Holistic remains an unverified domain mismatch. Hand/body association guards were fixed, but tracker parity is not established.
- Legacy movement cropping can react to missing-hand discontinuities; the new temporal candidate masks invalid velocities but does not undo already-cropped legacy training sequences. Aspect-ratio invariance of that legacy encoding is not established.
- Linguistic correctness of mapped variants and lexical unknowns needs an ASL expert. Lexical unknowns can be semantically related (for example ASSIST versus HELP); CSV mapping checks are not linguistic certification.
- Real incomplete-sign detection is unverified; software checks prove complete capture windows only.
- All known-word test recordings were previously exposed. Further model tuning must not use these final test failures; new consented signer-diverse data and a genuinely untouched known-word benchmark are required.
- The low gated recall is a failed quality target, not a success: the selected rejection policy trades most true signs for low false acceptance. It must not replace the stable model.

## Reproduce without overwriting artifacts

Run from C:/Users/Squid/Desktop/capstonev2. The private data cache already contains the audited source clips and features. Use new run directories for a training reproduction; never erase the locked run.
```powershell
.\.venv\Scripts\python.exe -X utf8 training/train_target20_v2.py --run-name target20-v2-repro
.\.venv\Scripts\python.exe -X utf8 training/train_target20_v3.py --run-name target20-v3-repro --source-run target20-v2-repro
.\.venv\Scripts\python.exe -X utf8 training/evaluate_target20_v2.py --run-name target20-v3-repro
.\.venv\Scripts\python.exe -X utf8 training/reproduce_target20_metrics.py
.\.venv\Scripts\python.exe -X utf8 training/run_target20_checks.py
.\.venv\Scripts\python.exe -X utf8 training/check_target20_api.py
```
The last command requires the actual project server running on localhost:8000. It exercises synthetic HTTP contract inputs, not a physical camera. The checks runner intentionally exits nonzero while the two legacy regressions remain.

The per-word CSV has 20 rows; unprefixed metrics describe the final test, val_ fields describe validation, and source/tracked/failure counts are separate for every split. Latency excludes image tracking and capture. No restricted recording or landmark array is published.
