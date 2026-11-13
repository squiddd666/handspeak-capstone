# CLERC-34 capture improvement investigation (2026-11-13)

**Outcome: capture bottleneck reproduced, but no experimental capture change passed regression. The default separate-site pipeline remains unchanged. No new full training run was started.** Production HandSpeak and original CLERC 24-class weights were untouched.

## Root causes supported by evidence

1. The file-backed camera processes many 1–2.5 s signs with only 4–11 usable landmark frames. The 12-frame/75%-tracked quality gate therefore rejected 17 of 23 normal-speed supported clips in the prior controlled-candidate matrix (`virtual_camera_results.json`). This is a **capture failure**, not a classifier error.
2. Browser MediaPipe IMAGE-mode pose detection + hand detection + optional second hand detection on contrast-enhanced pixels can be computationally expensive. Camera timestamps and extracted feature-rate distribution were not logged, so its exact contribution to dropped frames remains **not verified**. Do not claim FPS was the sole root cause.
3. CLERC's motion gate can end after 270 ms of low motion even if a valid sign contains a hold. It may truncate before the hand-down boundary. The current pre-roll is 560 ms; automatic segmentation still differs from annotated training segments. This is a plausible mechanism, not yet proven as the dominant cause.
4. Dataset shortness is distinct: 1,535/3,333 annotated CLERC sign segments have fewer than 12 source frames, and 622 have >20% missing-hand frames. The model was trained by resampling as few as three source frames to 24; this weakens temporal evidence even if browser capture is corrected (`dataset_quality_findings.md`).
5. The candidate is closed-set. A longer capture alone can turn an unsupported sign into a false known-word prediction. In the baseline virtual matrix BOOK and AIRPLANE were both falsely accepted. Quality gating must not be weakened solely to increase completion.

## Isolated experiments

Both experiments used the same 34-class controlled candidate by routing weights into an isolated Playwright browser; no predictions or landmarks were injected. Pixel clips entered through Chrome's file-backed `getUserMedia`. Seven cases: FATHER, DRINK, HELLO, LIKE, unsupported BOOK/AIRPLANE, and gray no-sign. Files: private `capture_experiment_matrix.json` and `capture_fast_matrix.json` in `C:\Users\Squid\Desktop\clerc-34-training-private`.

| Input | Original full-matrix result | Adaptive end-on-drop/850 ms idle | Contrast fallback every third miss |
|---|---|---|---|
| FATHER | FATHER (23 frames) | FATHER (13) | FATHER (14) |
| DRINK | Try Again (7) | Try Again (9) | Try Again (10) |
| HELLO | YOUR (21) | YOUR (18) | YOUR (17) |
| LIKE | Try Again (10) | YOU (12) | Try Again (11) |
| Unsupported BOOK | YOU (14) | YOU (15) | YOU (12) |
| Unsupported AIRPLANE | WHERE (14) | Try Again (11) | WHERE (13) |
| Gray no-sign | No result | No result | No result |

Adaptive end-on-drop improved completion for LIKE but **made a wrong-word prediction** and did not fix BOOK. Sparse contrast fallback did not materially improve capture. Both were **rejected** and are not enabled by the default site. The adaptive gate source is retained as an unused research module (`capture-experiment.js`); the app does not import it.

## Next measurable capture study before retraining

- Add opt-in diagnostic logging (not camera uploads): per-frame media timestamp, effective detector FPS, raw pose/hand presence, fallback use, motion score, gate transitions, captured frame count, and source-video duration. Avoid logging/saving face or image data.
- Run the same independent clips on controlled 15/30 FPS and actual webcam hardware, with normal/low light. Compare detected-frame distribution and segment start/end against human-reviewed sign boundaries.
- Investigate a capture quality score based on **time coverage plus observed landmarks**, with at least two negative sets; do not simply lower the 12-frame gate. Require improvement in correct completed signs **without** increasing unsupported false acceptance.
- Keep the 34-class candidate offline until the proposed accuracy, unknown-rejection, and webcam gates in `deployment_decision.md` pass.

## Dataset collection protocol

For HELLO, THANK YOU, DRINK, HUNGRY, UNDERSTAND, EAT, and other weak labels, recruit consenting ASL signers not present in CLERC or the held-out set. Record each sign variant as a separate, clearly labeled example with neutral lead-in/out and natural speed; capture multiple repetitions under varied lighting and device framing. Record signer-level consent, license/withdrawal terms, sign language and variant, device/FPS, and annotation boundaries. Have an ASL-qualified reviewer validate gloss and boundaries. Keep new signer identities partitioned **before** training into fit, validation, and untouched test groups; never move held-out signers into fit. Do not treat mirrored/augmented frames as additional signers. Do not include any new recording in an accuracy claim until its consent and provenance are verified.
