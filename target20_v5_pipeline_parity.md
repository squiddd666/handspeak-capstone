# V5 browser/offline parity — validation only

Browser payloads were passively retained from real frontend POSTs in the private research cache. No landmark payload was injected. Offline tensor comparisons use the corresponding cached clip; matching the source clip does not imply identical decoded timestamps or tracker state.

18 browser/cached pairs; 18 exact top-label / score checks (tolerance 0.00002). Input shape 4 × 32 × 27; the two hand masks are separate. Coordinates are shoulder-centered XY; velocities are per resampled frame, not per physical second.

| Word | Browser frames | Median source interval ms | Body normalized XY MAE | Left / right mask disagreement | Velocity MAE | Mean score difference |
|---|---:|---:|---:|---:|---:|---:|
| THANK YOU | 38 | 110.0 | 0.0792 | 12.5% / 15.6% | 0.0643 | 0.0820 |
| PLEASE | 36 | 112.4 | 0.1117 | 43.8% / 65.6% | 0.0583 | 0.0899 |
| SORRY | 36 | 111.8 | 0.0662 | 59.4% / 87.5% | 0.0427 | 0.0721 |
| YES | 36 | 110.3 | 0.0791 | 71.9% / 87.5% | 0.0401 | 0.0925 |
| NO | 33 | 121.5 | 0.0330 | 43.8% / 6.2% | 0.0603 | 0.0878 |
| HELP | 38 | 104.2 | 0.0664 | 12.5% / 18.8% | 0.0349 | 0.0867 |
| LOVE | 42 | 95.2 | 0.0783 | 59.4% / 25.0% | 0.0404 | 0.0460 |
| I / ME | 39 | 101.8 | 0.0631 | 62.5% / 71.9% | 0.0603 | 0.0858 |
| YOU | 45 | 86.4 | 0.0800 | 81.2% / 75.0% | 0.0463 | 0.0931 |
| WANT | 40 | 107.3 | 0.0692 | 21.9% / 25.0% | 0.0615 | 0.0597 |
| NEED | 39 | 105.5 | 0.0745 | 6.2% / 25.0% | 0.0262 | 0.0807 |
| GOOD | 47 | 85.8 | 0.0611 | 12.5% / 12.5% | 0.0611 | 0.0929 |
| BAD | 45 | 87.2 | 0.0567 | 0.0% / 9.4% | 0.0258 | 0.0884 |
| WHAT | 43 | 86.6 | 0.0574 | 62.5% / 15.6% | 0.0427 | 0.0906 |
| WHERE | 48 | 82.4 | 0.0606 | 0.0% / 6.2% | 0.0344 | 0.0864 |
| WHO | 42 | 101.8 | 0.0916 | 62.5% / 75.0% | 0.0425 | 0.0930 |
| EAT | 45 | 87.2 | 0.0424 | 0.0% / 6.2% | 0.0180 | 0.0911 |
| WATER | 41 | 90.7 | 0.0934 | 0.0% / 6.2% | 0.0351 | 0.0896 |

Approximate raw XY timestamp matches (source time scaled to the three-second virtual clip; not exact decoded-frame pairing):
- THANK YOU: 27 pairs; body/left/right XY MAE 0.054429307146362536 / None / 0.08966460185391562. Missing-side agreement is recorded in the private aggregate; no hand swap is inferred from missing detections alone.
- PLEASE: 27 pairs; body/left/right XY MAE 0.041460584001566374 / 0.1454312228967273 / None. Missing-side agreement is recorded in the private aggregate; no hand swap is inferred from missing detections alone.
- SORRY: 27 pairs; body/left/right XY MAE 0.06358968545362431 / None / None. Missing-side agreement is recorded in the private aggregate; no hand swap is inferred from missing detections alone.

Shared tensor preprocessing and score replay are verified for matched inputs; **raw extraction equivalence is not established**. Normalized, jointly-visible per-hand XY errors and side-presence disagreements are retained in the private aggregate. Browser WASM and Python Holistic differ in build, input cadence, decoded pixels, idle padding and smoothing history. The legacy crop and interpolation remain frozen for v3.