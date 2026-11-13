# CLERC 34-class training improvement report

**Status: experimental; not deployed.** The main HandSpeak recognizer and original separate-site 24-class CLERC weights were not replaced. Training inputs and candidate weights remain outside the web-served directory in `../../clerc-34-training-private/`.

## Scope and reproducibility

- CLERC Épée v0.4 public keypoints and gloss annotations; 1,564 cached clips, 3,333 target sign segments after excluding segments shorter than three source frames.
- Labels: original 24 plus HELLO, THANK YOU, I, HOW, GOOD, EAT, DRINK, GO, HUNGRY, UNDERSTAND.
- Fit signers BRAVO, CHARLIE, FOXTROT, GOLF; model/configuration selection on ECHO; final refit also included ECHO. ALPHA, DELTA, HOTEL were held out until one final test. See `../../clerc-34-training-private/experiments/split_manifest_segments.csv` for clip/segment/signer groups.
- Fixed seed 46, 25-epoch ceiling, patience 7, AdamW 0.0005, batch 64, gradient clipping. Compared weighted loss, balanced sampling, and balanced sampling plus monotonic temporal jitter, dropout, and weight decay. Only training samples were augmented. The selected variant was balanced sampling plus temporal jitter at epoch 21 by validation macro-F1. See `../../clerc-34-training-private/experiments/REPORT.md`.
- The earlier `candidate34_v2.json` **selected its epoch using test accuracy**, so its apparent 75.7% top-1 and 49.5% added-class macro-F1 are biased and should not be used as a deployment claim.

## Controlled results on unseen signers

| Metric | Controlled candidate | Proposed target | Status |
|---|---:|---:|---|
| Overall top-1 (1,224 segments) | 74.5% (Wilson 95% CI 72.0–76.9%) | ≥85% | FAIL |
| Overall macro-F1 | 62.6% | — | Measured |
| Balanced accuracy | 67.1% | — | Measured |
| Added-class aggregate top-1 (193 segments) | 44.6% | — | Measured |
| Added-class macro-F1 | 42.7% | ≥80% | FAIL |
| All ten added words ≥70% recall | 2/10 (HOW, GO) | 10/10 | FAIL; low support |

Unseen-signer top-1 varied substantially: ALPHA 83.5% (n=581), DELTA 70.6% (n=395), HOTEL 59.7% (n=248). Stable cross-signer performance is **NOT VERIFIED**.

`per_word_evaluation.csv` has support, precision, recall, F1, Wilson recall intervals, and confusion pairs. `confusion_matrix.csv` contains the full 34×34 held-out matrix. The original 24-class release model scored 90.0% on the common-label subset of these corpus signers, **but was trained on the release signers** and therefore is not a signer-independent comparator; it also cannot predict the ten new words. See `model_comparison.json`.

## Data and root-cause audit

- `dataset_quality_audit.csv` and `dataset_quality_findings.md` document signer coverage, missing landmarks, frame lengths, and potential variants. Annotation/metadata sequences and IDs matched; no exact cross-signer duplicate keypoint arrays or overlapping annotations were found in the cached subset. This does not establish human gloss correctness or absence of semantic near-duplicates.
- 1,535/3,333 target segments have fewer than 12 source frames. 622/3,333 have >20% hand-missing frames. **I** has 206/275 clips shorter than 12 frames and 128/275 with >20% missing hands. Expanding a 3–6-frame sign to 24 model frames cannot restore unseen motion.
- In the controlled fit pool, HELLO has 5 examples; THANK YOU 4; DRINK, HUNGRY and UNDERSTAND 3 each. If restricted to ≥12 frames and ≤20% missing hands, HUNGRY would have only 1 fit example. Aggressive filtering cannot solve the sparse-class problem.
- Suffix gloss variants such as GO_2 and HOW_LEFT_MOVE exist. They were not merged without ASL-qualified review. The public dataset lacks raw video, so exact sign-form and boundary correctness cannot be visually confirmed here.
- Major errors on held-out signers: HELLO→FATHER 9/12, HUNGRY→LIKE 7/13, UNDERSTAND→WHY 4/6. Class imbalance, signer/variant differences, short boundaries, and missing hands are plausible contributors; their causal shares are not proven.

## Browser/preprocessing parity

Python feature normalization vs JS `slr.js` matched within 4.77e-7 on the tested cached sequence; controlled PyTorch vs JS BiLSTM logits matched within 1.43e-6 on three identical 24×96 feature sequences. These checks verify transform/model arithmetic, **not** MediaPipe extraction from webcam pixels or automatic boundary parity. The camera pipeline can still produce much shorter/noisier bursts than annotation-defined training segments. `webcam_pipeline_audit.md` records verified fixes and remaining defects.

## End-to-end virtual-camera evaluation

`virtual_camera_results.json` records 33 real file-backed browser-camera runs of the controlled candidate. Among 23 ordinary-speed supported clips, 4 were correct, 2 produced wrong words, and 17 were rejected or produced no result. None of six speed variants was correct. Two of three unsupported signs were falsely accepted as known words; the gray no-sign case produced no result. There were no browser exceptions. These clips are from separate local sign libraries, but exact independence from CLERC source video cannot be proven because the CLERC public release has no raw video. The matrix is a failure diagnosis, not a population accuracy estimate. Most supported failures are short/tracking-limited captures.

## Unknown rejection and deployment

`unknown_sign_evaluation.json` contains a validation-only confidence/margin sweep on the **pre-refit** model. A threshold meeting ≤5% false acceptance on a limited cached negative set rejected **71% of true test signs** and is not valid for the final refit model. Unknown-sign rejection, physical webcam performance, and stable live capture are **NOT VERIFIED**. The candidate is not promoted. See `deployment_decision.md`.


## Capture follow-up
The next task prioritized capture before another model training run. Two isolated capture variants were tested and rejected because neither improved correct completion safely. No new model was trained or promoted. See `capture_experiment_report.md`.
