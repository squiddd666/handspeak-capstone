# V5 root cause audit

V4 forensic results only; never used for model selection. Primary stages are exclusive; overlapping window and hand evidence is retained in the CSV. Missing instrumentation cannot establish an exact internal cause.

## Primary stages
- insufficient_visible_hands: 120
- model_abstention: 60
- incorrect: 10
- full_source_window_missing: 8
- correct: 1
- capture_never_started: 1

## Breakdown by word
- HELLO: insufficient_visible_hands=9, capture_never_started=1
- THANK YOU: model_abstention=4, insufficient_visible_hands=6
- PLEASE: insufficient_visible_hands=5, model_abstention=4, full_source_window_missing=1
- SORRY: insufficient_visible_hands=9, full_source_window_missing=1
- YES: insufficient_visible_hands=7, model_abstention=2, incorrect=1
- NO: insufficient_visible_hands=4, model_abstention=4, full_source_window_missing=2
- HELP: insufficient_visible_hands=6, model_abstention=4
- LOVE: insufficient_visible_hands=7, model_abstention=2, incorrect=1
- I / ME: insufficient_visible_hands=6, model_abstention=4
- YOU: insufficient_visible_hands=7, model_abstention=2, full_source_window_missing=1
- WANT: insufficient_visible_hands=6, incorrect=1, model_abstention=3
- NEED: model_abstention=2, insufficient_visible_hands=6, incorrect=1, full_source_window_missing=1
- LIKE: correct=1, insufficient_visible_hands=5, model_abstention=3, full_source_window_missing=1
- GOOD: incorrect=1, insufficient_visible_hands=7, model_abstention=2
- BAD: model_abstention=5, insufficient_visible_hands=5
- WHAT: model_abstention=3, insufficient_visible_hands=5, incorrect=2
- WHERE: model_abstention=4, incorrect=1, insufficient_visible_hands=5
- WHO: insufficient_visible_hands=4, model_abstention=5, full_source_window_missing=1
- EAT: insufficient_visible_hands=4, incorrect=1, model_abstention=5
- WATER: insufficient_visible_hands=7, model_abstention=2, incorrect=1
## Reproducible defects and changes

- The old frontend started sending after just three hand frames; the server required eight and 60% active-interval continuity. V5 enforces that check before submitting and checks source-frame timing, not tracker callback timing. A capture can still fail to contain the intended sign, even with adequate landmarks.
- The recorder checked consent at startup but not before upload. V5 rechecks it before submission. A stale tracker rejection is ignored for a different capture.
- The legacy motion crop measures differences from zero-filled missing hands before it consults any visibility masks. Hand appearance/disappearance can dominate the crop, and interpolation can blend a real coordinate with an absent hand. The model's later velocity mask cannot restore frames already cropped out. The old encoder was factored into one shared function without changing its semantics. A mask-aware encoder needs its own version and compatible training; it is not silently applied to the locked checkpoint.
- The encoder resamples by frame index, not source time. Both paths agree for identical landmark inputs, but the browser drops frames while Holistic is busy, while offline samples at an approximately fixed stride. Different Holistic builds and independent smoothing state mean matching configuration is not proof of identical extraction.
- Validation-only evidence: the frozen 0.975 gate yielded 30.9% macro F1 with 0/115 false accepts on validation. The archived validation sweep reached 82.0% F1 at 0.55, but accepted 5/115 unknowns (one-sided 95% upper bound 8.9%). Neither operating point establishes acceptance. No gate was changed.
- No V4 exposed test prediction was used to choose features, architecture, thresholds, or data. Missing hand frames indicate a quality failure, not proof that a particular tracker graph failed. Unobserved backend stages are not assigned a fabricated cause.
