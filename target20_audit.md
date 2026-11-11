# Target-20 initial system audit — 2026-11-11

Written before this task's implementation changes. Status: NOT ACCEPTED.

## Pipeline inventory

- Interface: index.html, essential-words.js, guided-experience.js, app.js.
- Camera: app.js getUserMedia and hand detector; beginner-recognition.js captures a 4-second segment after a 1.5-second countdown, up to 8 seconds before timeout.
- Target-20 body tracking: target20-tracker.js uses Tasks Pose Landmarker Lite plus independent hand tracking; offline extraction uses legacy MediaPipe Holistic model_complexity=1. These are different trackers, not proven equivalent.
- Backend: server.py GET /api/beginner-asl/status and POST /api/beginner-asl; consent required by the POST route. beginner_asl.py loads and normalizes landmarks, then invokes the model.
- Features: 7 upper-body/face points plus 10 selected landmarks per hand; XY and two visibility masks; shoulder normalization; movement crop; 32 resampled frames; shape 4 x 32 x 27.
- Model: third_party/microsoft_asl_citizen/architecture ST-GCN, 256-dimensional pooled encoder, linear dropout head, 21 outputs including UNKNOWN.
- Data: training/target20_data.py, training/train_essential.py; private ../handspeak-training/target20-manifest.json and landmarks-v1/.
- Training: training/train_target20.py: frozen warm-start encoder/head fitting then fine-tuning; weighted cross-entropy; validation accuracy selection; fixed epoch counts.
- Release report: training/publish_target20_offline.py; reports/target20-current/.
- Existing private checkpoint: ../handspeak-training/target20-candidate.pt; version target20-v1; SHA-256 e9e558d6e0b4bd003e1bc4e4696160d1b5421df0a337c6a891960a21f4d0559d. Preserve this file.

## Baseline evidence

823 selected source clips: train 408, validation 115, test 300. 814 tracked sequences; 9 extraction failures. All 20 requested labels exist, including I / ME. WANT1/2, WHAT1/2, EAT1/2 are explicitly mapped variants, not replacements of requested labels; linguistic variant correctness is not certified by this audit.

Existing rejection gate 0.9 was selected by validation error cost, not calibration. Existing target macro F1 computed from published per-class gated metrics: validation 0.7482, test 0.6673. Neither meets acceptance. Raw tracked target top-1 89.7% validation / 78.4% test is not gated end-to-end accuracy. Test unknown set has only 15 tracked clips; 0 false accepts cannot establish a <=5% population false-accept rate (one-sided 95% upper bound about 18.1%).

## Confirmed problems and risks

1. **Evaluation provenance:** warm-start encoder had historical exposure to ASL Citizen. Official subset signer separation does not establish independent pretraining/test separation. The old test results are already exposed; they cannot be relabeled an untouched benchmark for this task.
2. **Small data:** most classes have only 13–16 training and 3–5 validation clips; three merged-variant classes have roughly twice the samples. Validation estimates are noisy and vulnerable to repeated selection.
3. **Tracker mismatch:** offline Holistic versus browser independent Pose Lite/Hands; hand identity is assigned by nearest body wrist without a visibility/distance check. Missing/low-confidence wrists can create incorrect side assignment.
4. **Motion crop:** _active_span computes velocity without masks. Tracking loss/reappearance can dominate motion and be mistaken for signing.
5. **Missing coordinates:** missing hands become normalized coordinates that look like real off-body motion unless every downstream model respects masks. Interpolation blends coordinates across visibility boundaries.
6. **API input quality:** only frame-count range is checked before array indexing. Non-finite values, malformed hands, degenerate shoulders, and no-hand clips are not robustly rejected. UNKNOWN, uncertainty, incomplete capture, and tracking failure have no distinct response state.
7. **Capture race:** cancel during pending Holistic send can allow an old callback into a later recording; duplicate/late results are not comprehensively guarded. Deadline may submit sparse/incomplete recordings. There are no per-frame timestamps or explicit capture-completeness metadata.
8. **Frontend quality:** guided-experience.js automatically checks server landmark consent during beginner practice. This contradicts explicit consent requirements. Switching panels can advertise pretrained availability without validating dependency/model compatibility.
9. **Runtime:** system Python 3.14 has no torch; project Python 3.11 does. File presence alone can make status appear available despite an unusable runtime. Use the project environment; do not conceal import failures.
10. **Model selection:** validation accuracy (including imbalanced UNKNOWN) rather than target macro F1; no scheduler or early stopping; threshold cost has no statistically grounded unknown-FAR constraint. Softmax scores are not calibrated probabilities.
11. **Reproducibility/release:** legacy trainer overwrites the same candidate and report; cache key lacks explicit extraction configuration; download reuse verifies existence, not archive CRC/size. New work must use versioned private outputs and never auto-promote.
12. **Incomplete evidence:** public reports omit several required per-word counts, raw/gated separation, latency distributions and statistical bounds; no verified physical-webcam attempts. Present-device enumeration returned no Camera/Image devices at audit time. Browser enumeration still must be checked; no passing live result may be invented.

## Fix and evaluation plan

Preserve baseline. Run all available tests and audit manifest/landmark integrity. Correct consent and input/capture safeguards without altering existing alphabet models. Compare a small, predeclared set of temporal representations/classifiers on training and validation ONLY. Keep test arrays out of model/threshold selection, record the selection protocol and all trials, and run one locked final evaluation; clearly label the existing known-word test as a previously exposed regression benchmark. Expand independently reserved unknown evidence where practical. Save versioned candidates, exact configuration, dependencies, checksums and aggregate results privately/publicly as appropriate. Test browser/API behavior and enumerate real cameras. Collect 200 independent real-user recordings only with actual webcam/signer participation and explicit consent; prerecorded videos are not a substitute.

Source and terms: https://www.microsoft.com/en-us/research/project/asl-citizen/ and https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/. Restricted clips and derived landmark arrays remain outside the website. Production promotion requires explicit approval and all quality gates.

## Executed follow-up

Expanded the deterministic, signer-disjoint subset to 1,243 clips, including 420 newly reserved unknown clips. 1,232 sequences were usable. Source CSV/gloss/participant mappings and SHA-256 file checks passed, with no subset participant/hash overlap across splits. Trained two from-scratch TCN seeds, compared the preserved ST-GCN on expanded validation, then ran a predeclared three-width RBF novelty correction. No new test predictions informed selection. Final known-word evaluation is explicitly an exposed regression benchmark; new unknown evaluation is separately reserved. The rejection policy still fails all per-word recall gates. See the training report for resolved safeguards and unresolved tracker/crop/linguistic/benchmark issues.
