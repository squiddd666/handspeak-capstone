# Target-20 acceptance checklist — NOT ACCEPTED

Virtual camera only. 20/20 words have reserved clip outcomes; 199/200 clips started with verified stream settings, 92/200 met the full-source-window rule, and 1 were correctly recognized. See the per-word CSV for missing, failed, rejected and recognized attempts. No candidate was promoted.

- Browser acceptance (8/10 per word): 0/20 words meet it.
- Frozen offline validation macro F1: 30.9% (target 90%).
- Frozen offline regression macro F1: 22.5% (target 85% on untouched data); the known-word benchmark is not untouched.
- Frozen offline per-word recall ≥80%: 0/20.
- Independent browser unknown rejection: 3 scored decisions; 0 false accepts; acceptance is not established without sufficient eligible coverage.
- Software suites: Ran 95 tests in 229.069s; OK; Ran 4 tests in 0.056s; OK. Legacy numeric fixtures were retained unchanged; parity checks use independent Python calculations and no longer assert those archived fixtures measure current model accuracy.

Further model/preprocessing tuning against these exposed final clips would invalidate the evaluation. New authorized signer-separated training/validation data and a genuinely untouched known-word test are required before another quality claim. The current pipeline and model still fail acceptance; this is not a successful release.

No physical webcam or signer is required. An authorized, genuinely untouched known-word dataset is still needed for the untouched-test gate. Do not tune against these regression results.
