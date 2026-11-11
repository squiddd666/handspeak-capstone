# Target-20 V6 browser/offline tracking parity

Same development source, approximately paired by the virtual three-second playback schedule and nearest native source timestamp. No frame-exact or same-decoded-pixel parity is claimed. Differences mix tracker build, resolution/padding, cadence, warm-up, and smoothing. Detection side disagreement is not proof of a swap.

| Word | Browser / Python frames | Browser / Python median interval ms | Left longest runs B/P | Right longest runs B/P | Approx. pairs | Left/right presence disagreement | Raw body XY MAE |
|---|---:|---:|---:|---:|---:|---|---:|
| PLEASE (V6) | 37/35 | 108.5/66.7 | 10/5 | 12/0 | 27 | 0.259/0.444 | 0.041 |
| YES (V6) | 37/59 | 107.7/66.7 | 13/1 | 0/21 | 28 | 0.500/0.357 | 0.076 |
| YOU (V6) | 48/28 | 81.3/66.7 | 0/13 | 6/0 | 36 | 0.472/0.250 | 0.080 |
| GOOD (V6) | 54/63 | 70.5/66.7 | 0/2 | 12/21 | 42 | 0.071/0.095 | 0.029 |
| WHO (V5 archival validation) | 42/31 | 101.8/65.6 | 5/0 | 0/9 | 30 | 0.333/0.300 | 0.073 |
| EAT (V6) | 39/58 | 102.4/66.7 | 0/0 | 11/18 | 28 | 0.000/0.143 | 0.014 |

## Displacement and smoothing

- **PLEASE**: median step displacement browser [pose=0.0043, left=0.0260, right=0.0884], Python smoothing on [pose=0.0032, left=0.0638, right=unobserved], off [pose=0.0080, left=0.0524, right=unobserved]. Python initialization/first frame 41.3/226.9 ms. Nearest-pair timestamp residual 16.253566666678353 ms (not sync error).
- **YES**: median step displacement browser [pose=0.0026, left=0.0222, right=unobserved], Python smoothing on [pose=0.0026, left=unobserved, right=0.0294], off [pose=0.0057, left=unobserved, right=0.0284]. Python initialization/first frame 40.8/218.8 ms. Nearest-pair timestamp residual 16.905333889834083 ms (not sync error).
- **YOU**: median step displacement browser [pose=0.0016, left=unobserved, right=0.0309], Python smoothing on [pose=0.0036, left=0.0242, right=unobserved], off [pose=0.0094, left=0.0238, right=unobserved]. Python initialization/first frame 48.1/251.9 ms. Nearest-pair timestamp residual 17.602387166665423 ms (not sync error).
- **GOOD**: median step displacement browser [pose=0.0013, left=unobserved, right=0.0094], Python smoothing on [pose=0.0021, left=0.0892, right=0.0365], off [pose=0.0047, left=0.0962, right=0.0411]. Python initialization/first frame 43.4/236.7 ms. Nearest-pair timestamp residual 15.732508499991127 ms (not sync error).
- **WHO**: median step displacement browser [pose=0.0031, left=0.0526, right=unobserved], Python smoothing on [pose=0.0058, left=unobserved, right=0.0105], off [pose=0.0113, left=unobserved, right=0.0098]. Python initialization/first frame 42.0/228.4 ms. Nearest-pair timestamp residual 14.89205464480608 ms (not sync error).
- **EAT**: median step displacement browser [pose=0.0020, left=unobserved, right=0.0550], Python smoothing on [pose=0.0009, left=unobserved, right=0.0075], off [pose=0.0033, left=unobserved, right=0.0090]. Python initialization/first frame 41.1/229.7 ms. Nearest-pair timestamp residual 15.341811344819348 ms (not sync error).

Browser start-to-ready (camera + tracker initialization and warm-up; controls run): [27784] ms. This is not an isolated tracker initialization measurement.
The private aggregate also records left/right raw XY displacement error on jointly visible pairs and per-side continuity transitions. Missing landmarks upstream are tracking/capture evidence, while an encoder rejection describes insufficient sequence support.
