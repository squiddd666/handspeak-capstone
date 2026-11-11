# Six-word accuracy experiment

Development-only scripts; they do not replace the live model. Data, candidates,
and detailed reports are written outside the served website under
`/opt/handspeak-training/accuracy-v4`.

The frozen protocol and clip selection are saved before candidate fitting. Fresh
source-test videos exclude all clips used by prior versions. Signer IDs must be
disjoint from development data. The test signer population itself is not new:
prior versions evaluated different recordings from these same source splits.

Run with the project's Python 3.11 training environment (MediaPipe, OpenCV,
NumPy, SciPy, QuickJS, CPU PyTorch, Playwright/Chromium):

```sh
python training/accuracy/prepare.py
python training/accuracy/extract.py
python training/accuracy/temporal.py
python training/accuracy/dtw.py
python training/accuracy/evaluate.py --freeze
python training/accuracy/prepare.py --test
python training/accuracy/extract.py --test
python training/accuracy/evaluate.py
python training/accuracy/browser_benchmark.py
python training/accuracy/realtime_browser.py --cpu
python -m unittest discover -s training/accuracy -p test_experiment.py
```

Extraction keeps 30 source-timestamped hand samples per clip and uses a center-frame upper-body reference for body-relative coordinates. The
reference is held fixed across the clip; hand motion retains all 30 samples.
Temporal input consists of local hand shape, wrist trajectories, body-relative
hand position, upper-body geometry, and visibility indicators. It is resampled to
32 frames for two small temporal convolution layers. Validation selects width,
checkpoint, and rejection thresholds. Synthetic stationary hands, mild camera
drift, jitter, and no-hands sequences are explicitly labeled as synthetic.

The DTW candidate adds supported references and an UNKNOWN class of unsupported
training signs; predictions of UNKNOWN are rejected. It is an evaluation-only
model format and cannot simply be substituted into the live UI's vocabulary.

The fresh test is a final check, not a tuning loop. If a candidate fails, preserve
that result. Real-time virtual-camera tests use normal video playback, not stepped
frame seeking. They do not replace recordings from a physical webcam or establish
accuracy on everyday nonsigning movements. Browser classifier timing excludes
landmark extraction; temporal deployment would additionally require a matching
upper-body tracker and validated browser feature extraction.

No deployment script is provided: promotion requires all agreed accuracy,
false-suggestion, boundary, and browser-performance gates to pass.

For the final camera-sized timing comparison, run
`python training/accuracy/check_camera_sized.py` (requires imageio-ffmpeg). This
creates bounded 480x640 H.264 derivatives outside the website and compares the
current camera flow with the frozen candidate. The high-resolution source replay
was decoder-bound on this host and is retained only as a diagnostic.

The completed experiment directory is immutable evidence, not a tuning workspace.
Preserve it before starting another experiment with a new cache and untouched test
selection. Exact recorded results use the saved feature cache; some early cached
pose estimates were obtained with video tracking, while fresh extraction uses a
static center-frame estimate.
