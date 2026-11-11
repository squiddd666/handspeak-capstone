# V7 browser/Python tracking investigation

Browser Holistic 0.5.1675471629 versus Python MediaPipe 0.10.21, both complexity 1, 0.5 tracking/detection cutoffs and smoothing enabled for primary comparisons. Python smoothing off was also measured. Same public options do not guarantee the same tracker build or state.

Browser letterboxes to 640×480 and retimes to three seconds with idle padding; Python processes native frames at an approximate 15 FPS stride. Browser does a warm-up send before countdown, retains tracker state across captures, skips repeated/currently busy frames and uses a 65 ms processing guard. Python starts a fresh graph per clip. Measurements pair by approximate retimed timestamp, not identical decoded pixels. Raw XY is image-normalized; V6 subsequently uses shoulder centering and scale.

| Word | Source | Browser/Python median interval ms | Left longest run B/P | Right longest run B/P | Left/right presence disagreement | Body XY MAE |
|---|---|---|---|---|---|---:|
| PLEASE | virtual-v7-validation | 111.1/66.7 | 8/5 | 7/0 | 0.308/0.385 | 0.042 |
| YES | virtual-v7-validation | 112.6/66.7 | 11/1 | 0/21 | 0.423/0.346 | 0.077 |
| YOU | virtual-v7-validation | 99.3/66.7 | 0/13 | 11/0 | 0.452/0.355 | 0.080 |
| GOOD | virtual-v7-validation | 96.7/66.7 | 0/2 | 10/21 | 0.065/0.581 | 0.027 |
| WHO | V5 archival validation | 101.8/65.6 | 5/0 | 0/9 | 0.333/0.300 | 0.073 |
| EAT | virtual-v7-validation | 118.8/66.7 | 0/0 | 10/18 | 0.000/0.480 | 0.014 |

### Smoothing and initialization
- PLEASE: Python graph initialization/first frame 98.0/313.1 ms; median pose step smoothing on/off 0.0032/0.0080. Approximate paired observations 26.
- YES: Python graph initialization/first frame 63.3/397.9 ms; median pose step smoothing on/off 0.0026/0.0057. Approximate paired observations 26.
- YOU: Python graph initialization/first frame 60.0/353.7 ms; median pose step smoothing on/off 0.0036/0.0094. Approximate paired observations 31.
- GOOD: Python graph initialization/first frame 51.0/316.5 ms; median pose step smoothing on/off 0.0021/0.0047. Approximate paired observations 31.
- WHO: Python graph initialization/first frame 55.9/312.8 ms; median pose step smoothing on/off 0.0058/0.0113. Approximate paired observations 30.
- EAT: Python graph initialization/first frame 54.2/288.1 ms; median pose step smoothing on/off 0.0009/0.0033. Approximate paired observations 25.

Run training/target20_v6_tracking.py virtual-v7-validation for private hand-coordinate, displacement and continuity aggregates. V5 fallback payloads, if available, are explicitly tagged and not counted as V7 captures. Presence disagreement is reproducible but not proof of hand swaps. Build, decoded pixels, padding, cadence and warm-up are confounded. No tracker setting or production frontend behavior was changed on this evidence.
