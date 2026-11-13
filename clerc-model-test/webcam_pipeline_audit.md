# Separate CLERC website: camera pipeline audit

Scope: `clerc-model-test` only. No production HandSpeak files or original CLERC 24-class weights were changed. CLERC upstream source consulted: `https://huggingface.co/spaces/CLERC-DATA/read-the-hands/blob/main/app.js` and `slr.js` (public Space, CC BY-NC-SA 4.0).

## Actual path
Browser camera (`getUserMedia`) -> MediaPipe HandLandmarker and PoseLandmarker (IMAGE mode, GPU then CPU fallback) -> anatomical hand slots -> CLERC `buildFrame`/`normalizeFrame` (48 x/y points) -> motion gate -> CLERC BiLSTM 24-frame resampling -> mirrored inference -> 12/16/22-frame sliding-window vote -> result. The production HandSpeak recognizer is separate.

## Verified defects and changes

1. **Four-frame captures were accepted for classification.** Earlier unsupported BOOK virtual-camera input became FEEL from only four frames. A four-frame movement cannot provide a trustworthy sample of the model's 24-frame temporal input; resampling silently expanded it. Added an explicit quality gate requiring >=12 captured frames, >=75% hand-landmark frames, and >=75% shoulder-landmark frames. Rejected captures now show `Try Again` with measured frame/visibility counts, not a word. This is a conservative engineering gate, not a calibrated unknown-sign detector.
2. **Short-window vote score understated confidence.** The existing `readBurst` divided each winning window's probabilities by 3 even when fewer than 3 windows existed. A 12-frame clip has only one candidate window; its score was divided by 3. Changed divisor to the actual selected-window count. Scores are still **not calibrated probabilities of correctness** and are never used for deployment claims.
3. **"Manual sign" button did not record.** It only disabled automatic capture. It now starts a manual capture and changes to `Finish sign`; clicking again evaluates through the same quality gate. Five-second timeout still applies. Both automatic and manual paths return to auto mode after evaluation.
4. **Tracking gaps and aspect.** This site processes detected hand/pose landmarks using CLERC's anatomical slots and normalization. The video overlay is letterbox-aware. The existing contrast fallback is not part of the upstream CLERC app and has not been shown to improve recognition reliably. The browser still sometimes drops hands, yielding short or rejected captures.
5. **No unsupported-sign rejection.** The 24-class and experimental 34-class heads are closed-set classifiers. A quality gate catches incomplete/noisy captures, not plausible unsupported signs that track well. A diverse, held-out negative set and calibrated confidence/margin policy are still needed.

## Real browser / virtual-camera regression
Headless Chrome with file-backed `getUserMedia`, not injected landmarks or predictions. The video is processed through the actual separate-site JS tracking and capture path. Results in `pipeline_regression.json`.

| Expected source clip | Prior observed behavior | After quality gate |
|---|---|---|
| LIKE | Previously predicted LIKE or FEEL inconsistently from sparse captures | `Try Again`: 11 frames, 100% tracked hands/shoulders; below 12-frame minimum |
| BOOK (unsupported) | False FEEL from a four-frame burst | `Try Again`: too-short capture |

Manual capture UI check: button changed `Manual sign` -> `Finish sign` -> `Manual sign`; a poor 30-frame capture with 17% hand/23% shoulder tracking was rejected. Browser page errors: none in these checks. These are **not** an accuracy estimate and do not verify physical webcam performance.

## Training/browser parity findings
The JS `slr.js` is the CLERC Space's inference implementation. It uses 48 2D hand/arm points, shoulder-midpoint centering and shoulder-width scaling, 24-frame interpolation, PyTorch-order BiLSTM gates, and mirrored inference. The project's Python training script uses the same 48 slots and shoulder normalization concept. However, **numeric parity of the JS and Python normalization on 7 identical cached Épée frames was checked (maximum absolute feature difference 2.38e-7; fixture at `../../clerc-34-training-private/parity_fixture.json`), but parity for actual browser-extracted camera frames has not been established**. The camera path scales x by `(video aspect)/(16/9)` before normalization, as upstream CLERC does; this is absent from cached `.npy` training data because it was extracted under the dataset's canonical framing. Capture windows contain raising/lowering context absent from annotated training segments, and only 12/16/22-frame subwindows mitigate that mismatch. This remains a verified domain/pipeline gap, not proof of identical input distributions.

## Remaining actions / status
- Collect sufficient independent signers and negative signs before training unknown rejection; quality rejection alone is not unknown rejection.
- Run a larger virtual-camera matrix with independent, nontraining media, speeds, backgrounds and no-sign cases. Report capture failures separately from classification errors.
- Compare frame-level MediaPipe outputs and normalized vectors numerically between Python and browser on shared source frames.
- Conduct physical-device testing with a real camera and signer.
- **Deployment: NOT VERIFIED / do not promote** the 34-class candidate.


## Additional controlled-model parity check
The exported 34-class controlled candidate was evaluated on three identical 24x96 feature sequences in PyTorch and browser JavaScript. Maximum absolute logit difference was 1.43e-6 (clerc-34-training/model_parity_fixture.json, check_model_parity.mjs). This verifies exported model inference numerical parity for those fixtures, not browser camera extraction or motion-boundary parity.

