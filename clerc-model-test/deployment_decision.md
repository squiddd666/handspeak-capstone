# CLERC 34-class deployment decision

**Decision: DO NOT DEPLOY / DO NOT ENABLE THE TEN NEW WORDS.** The original 24-class CLERC model remains active only in the separate `clerc-model-test` site. The production HandSpeak website and its Beginner/Words in Motion workflows were not modified.

| Proposed criterion | Evidence | Result |
|---|---|---|
| Overall signer-independent top-1 ≥85% | 74.5% on 1,224 annotated segments (95% Wilson CI 72.0–76.9%) | **FAIL** |
| Added-class macro-F1 ≥80% | 42.7% across ten new labels | **FAIL** |
| Every added class ≥70% recall with adequate independent support | 2/10 reached 70%; several had only 6–13 test segments and 3–5 training segments | **FAIL** |
| No critical capture/preprocessing defects | Quality gate now blocks <12-frame bursts, but many real virtual-camera signs remain too short or untracked | **FAIL / incomplete** |
| Browser/model preprocessing parity | Cached-feature normalization and exported-model logits match numerically; camera extraction/boundaries not independently matched | **PARTIAL / NOT VERIFIED** |
| Unknown-sign false acceptance ≤5% on diverse negatives | Limited keypoint negatives met 3.3% at 71% false rejection for a pre-refit model; threshold not transferable to final model; unsupported BOOK was misclassified before quality gate | **NOT VERIFIED** |
| Stable unseen-signer performance | ALPHA 83.5%, DELTA 70.6%, HOTEL 59.7% top-1 | **FAIL** |
| Successful end-to-end virtual-camera tests | Actual browser/file-backed camera matrix in `virtual_camera_results.json`; 4/23 normal-speed supported clips correct; 17/23 reject/no-result; 2/3 unsupported signs falsely accepted | **FAIL** |
| Successful physical-webcam tests | No independent signer/device trial performed in this run | **NOT VERIFIED** |

The prior 34-class v2 benchmark selected its epoch on the test signer set and is test-selection biased. The controlled experiment selected on ECHO validation and tested ALPHA/DELTA/HOTEL once. The original 24-class model was trained on the CLERC release signers and is not a fair signer-independent comparator on these clips.

To reconsider deployment, collect consented examples from additional signers for rare labels, independently verify sign variants/boundaries, reserve untouched signer-level test data, calibrate rejection on a representative negative set without reusing calibration signers for training, and pass full virtual- and physical-camera tests. Do not treat a high closed-set softmax score as proof of a known sign.


## Capture follow-up (2026-11-13)
An adaptive end-on-drop gate and a reduced-frequency contrast fallback were evaluated on seven file-backed camera cases; neither improved correct recognition without false acceptance. The default gate was restored. See `capture_experiment_report.md`. Decision remains **DO NOT DEPLOY**.
