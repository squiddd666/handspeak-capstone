# CLERC 34-class audit and deployment decision

## Artifacts
- `candidate34.json`, `evaluation34.json`: first fine-tune, held-out ECHO/HOTEL.
- `per_word_audit.csv/json`: per-class counts, signer coverage, errors for first split.
- `candidate34_v2.json`, `evaluation34_v2.json`: revised fine-tune with ALPHA/DELTA/HOTEL held out, so every one of 34 classes has a test example.
- `per_word_audit_v2.csv/json`: per-class results and confusion pairs for revised split.
- `virtual_camera_v2.json`, `virtual_camera_unknown_book.json`: full browser tests with file-backed camera; candidate/model metadata injected in the isolated test browser only. Website files were not replaced.
- `cache/`: downloaded CLERC keypoints/annotations, outside the web-served site.

## Revised signer-independent split
Training: BRAVO, CHARLIE, ECHO, FOXTROT, GOLF, 2,109 sign segments. Held out: ALPHA, DELTA, HOTEL, 1,224 sign segments. All 34 labels have at least one example in both sets. Best epoch 24: **75.7% overall** top-1; **46.1%** on the ten added classes combined. This is isolated, annotated-segment evaluation, not webcam accuracy. Rare-class estimates have high uncertainty.

| Added label | Total | Training | Held out | Held-out top-1 | Main confusion |
|---|---:|---:|---:|---:|---|
| HELLO | 17 | 5 | 12 | 8.3% | FATHER (10) |
| THANK YOU | 10 | 4 | 6 | 33.3% | GOOD / SEE (2 each) |
| I | 275 | 190 | 85 | 42.4% | YOU (17) |
| HOW | 51 | 28 | 23 | 91.3% | HELP / YOU (1 each) |
| GOOD | 19 | 13 | 6 | 66.7% | HELP (2) |
| EAT | 37 | 13 | 24 | 33.3% | WHO (5) |
| DRINK | 11 | 3 | 8 | 37.5% | STUDENT / BROTHER / YOUR (1 each) |
| GO | 26 | 16 | 10 | 40.0% | YOU (4) |
| HUNGRY | 16 | 3 | 13 | 53.8% | LIKE (4) |
| UNDERSTAND | 9 | 3 | 6 | 50.0% | WHY (3) |

## Live-pipeline checks
File-backed virtual camera, unmodified media pixels through getUserMedia and the actual separate-site camera capture/tracking/window-voting flow:
- LIKE clip: predicted LIKE, but only 12 captured frames and a 9.1% aggregated score.
- HELLO clip: predicted YOUR (41.8%), 18 captured frames.
- Unsupported BOOK clip: falsely predicted FEEL (42.6%) from just 4 frames.
- Unsupported AIRPLANE clip: no capture/result in the test interval; that is not evidence of reliable unknown rejection.
No browser exceptions observed. These are four examples, not an accuracy estimate. The true CLERC webcam model and this site's capture pipeline do not have demonstrated parity.

## Data limits / next steps
The source dataset has only 9–17 total examples for several added words. The revised split leaves 3–5 training examples for DRINK, HUNGRY, UNDERSTAND, THANK YOU, and HELLO. Reweighting or synthetic augmentation cannot create new signer diversity. Obtain consented, correctly labeled clips from additional signers for those classes and hold those signers out for evaluation. Audit sign variants and annotation boundaries, especially HELLO→FATHER and HUNGRY→LIKE. Then retrain and calibrate an explicit unknown/rejection path with negative signs and no-sign video. Require full browser/virtual-camera and live-device tests before promotion.

## Deployment decision
**Do not enable the 34-class candidate**. It fails added-class accuracy and unknown-rejection criteria. Keep the original 24-class CLERC model in `clerc-model-test`; the ten extra labels remain dataset/reference-only. No main HandSpeak files changed.

Data/model derived from CLERC Épée v0.4, CC BY-NC-SA 4.0; source: https://huggingface.co/datasets/CLERC-DATA/epee .


**Storage note (2026-11-13):** Private training cache, candidate weights, manifests, and scripts were moved to `C:\Users\Squid\Desktop\clerc-34-training-private` so they are outside both web-served roots. Public-facing reports are in `clerc-model-test/`.
