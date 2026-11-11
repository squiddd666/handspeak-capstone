# V8 final status

**Canonical extraction implemented; independent evaluation blocked.** The private browser-landmark reader and packager accepted 10 primary and one repeat capture; the repeat is not an additional independent source. Two encoded primary payloads failed QA window verification and were excluded. Eight primary attempts never submitted. All 20 labels were attempted, but canonical capture did not succeed for every label. Reprocessing the same usable artifact is deterministic; repeated live capture was not comparable enough to certify tracking reproducibility.

Automated test results: 124 training-directory unit tests passed (including all six V8 tests), plus four accuracy experiment tests passed. Evidence: private target20-v8-tests.log. The simulated browser result was zero correct out of 10 verified captures (nine abstentions, one incorrect). It is development QA, not an untouched recognition benchmark. See the canonical extraction and virtual-camera reports for reproduction commands and stage counts.

- No model training, threshold tuning, checkpoint promotion or exposed-test tuning/evaluation was performed.
- V3 inference behavior, frontend behavior and the default engine were not changed; the harness and private artifact tools are experimental. No V6 tensors or predictions went into V3. Thirteen real requests returned exactly matching V3 results with and without diagnostics.
- Locked V3 SHA-256: 2912b105a306a1f7f0556ff7d91cd73b82423093aa308baf7ddbf39f9450a17f.
- Existing candidate SHA-256: e9e558d6e0b4bd003e1bc4e4696160d1b5421df0a337c6a891960a21f4d0559d.
- No external footage was admitted. Zero qualified untouched known examples for every target, and no untouched unknown benchmark. Accessible authorized source footage, gloss/variant confirmation, signer-group verification and overlap screening are required before freezing a test split. Keep V7 manifest and prior artifacts unchanged.
