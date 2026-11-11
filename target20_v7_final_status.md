# V7 final status — not ready for independent evaluation

QA request association and outcome reporting repaired; V6 gap and timestamp guards hardened. Production frontend, V3 model, inference, threshold, default and checkpoints not changed. Exact V3 response replays: 17. Stable and locked hashes are checked by the replay script. No training or promotion.

Validation-only simulated browser run: 20 clips. Capture {'verified': 16, 'capture_failure': 1, 'insufficient_tracking': 3}. Encoder {'encoded': 17, 'not_observed': 3}. V3 {'abstention': 15, 'incorrect': 1, 'not_scored': 4}. Suites: Ran 118 tests in 189.771s; OK; Ran 4 tests in 0.040s; OK. Passing software tests are not recognition accuracy.

Data: {'eligible_development_train': 336, 'unknown_candidate': 309, 'eligible_development_val': 88, 'excluded': 510, 'unverified_catalog': 1547}; zero qualified untouched test clips. No independent all-20 signer-separated dataset is ready. The blockers are source media authorization and availability, variants, and independent signer/hash/perceptual duplicate checks, not camera hardware.

Changed code: target20_encoder_v6.py, training/target20_virtual_camera.py, training/target20_v6_tracking.py, training/check_target20_v6_compatibility.py, training/test_target20_v7.py, training/prepare_target20_v7_split.py, training/report_target20_v7.py. Seven V7 reports and the private manifest are new. Prior reports and checkpoints remain intact.
