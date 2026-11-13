# CLERC 34-label dataset quality audit

Scope: 1,564 cached Épée v0.4 clips containing at least one of the 34 target glosses; 3,333 usable target sign segments. This is a structural/keypoint audit, **not human validation of ASL gloss correctness**. Source data remain outside the served website in `../../clerc-34-training-private/cache/`. Machine-readable per-word results are in `clerc-model-test/dataset_quality_audit.csv`; per-segment measurements remain in `../../clerc-34-training-private/segment_quality.csv`.

## Findings

- All 1,564 cached arrays loaded as `(frames,128,3)` finite `float32` landmarks; cached annotation IDs, signer IDs, frame counts and target segment bounds passed structural checks; all 1,564 cached annotation gloss sequences exactly matched their metadata gloss sequences. No overlapping annotated segments were found in these cached clips. A clean structure does **not** prove each sign boundary is linguistically accurate.
- Revised split is signer-independent: BRAVO/CHARLIE/ECHO/FOXTROT/GOLF train; ALPHA/DELTA/HOTEL test. There is no signer overlap. There were no byte-identical target-segment keypoint arrays shared across signers. Parallel-grid clips intentionally contain the same phrases signed by different people; that is not same-signer leakage.
- Target examples are not uniformly observed: 622/3,333 segments have >20% frames without either hand landmarks; 784 begin or end without a detected hand; 1,535 are shorter than 12 original frames. This is especially important because the training pipeline expands even 3-frame segments to 24 model frames. Such resampling cannot reconstruct missing motion.
- **I** has 275 examples but 206 are <12 original frames, 128 have >20% missing-hand frames, and 137 start or end with no detected hand. Its volume overstates usable temporal evidence. Its median annotated duration is 0.30 s.
- **HELLO** has only five training examples in the revised split versus 12 held out, nine of them from HOTEL. Four of 17 HELLO segments have >20% hand absence; seven have missing hands at a boundary; two are <12 frames. The HELLO→FATHER confusion may be a signer/variant issue, but cannot be diagnosed from labels alone without human sign review.
- **THANK YOU**, **DRINK**, **HUNGRY**, and **UNDERSTAND** have only 4, 3, 3, and 3 training examples, respectively. Their held-out scores are unstable and do not support deployment.
- The current exact-gloss pipeline excludes labelled suffix variants such as `GO_2` (1 cached token), `WHAT_2` (7), and `HOW_RIGHT_MOVE`/`HOW_LEFT_MOVE` (3 each). Those should not be silently merged; ASL-knowledgeable review is needed to decide whether they are equivalent forms and whether each model class should accept them.
- No obvious feature-format mismatch was found from static code inspection: both Python training and `clerc-model-test/slr.js` use the first 48 hand/arm x-y landmarks, shoulder-centre/shoulder-width normalization, and 24-frame linear temporal resampling. Browser preprocessing also applies CLERC's image-aspect adjustment. A numerical parity check on 15 frames from cached clip clerc_v04_0002 found maximum absolute differences of 5.96e-8 for one normalized frame and 4.77e-7 after 24-frame resampling. This validates the tested feature transforms, not full camera/keypoint extraction parity. Browser hand/pose tracking gaps and automatic sign boundaries still differ from annotated segments.

## Limits / follow-up

This audit does not inspect the original signer video, which is not in the public Épée release. It cannot verify whether HELLO's held-out signing form differs from training or whether an annotation includes transition frames. Expert review and consented additional signer recordings are needed; augmentation cannot provide new signer diversity. Use the per-word CSV to select weak/short/missing-landmark samples for review. Keep test signers completely outside further training and tuning.


