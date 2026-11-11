# V5 simulated virtual-camera diagnostic

20/20 validation cases logged, one distinct source clip per available label. 20 verified streams, 20 verified full source windows, 18 HTTP 200 responses and 0 correct end-to-end predictions. This is a development run, not an independent benchmark. V4 test clips were not replayed or used for tuning.

Chromium file-backed getUserMedia delivered 640×480 at 15 FPS via the actual HandSpeak UI, browser Holistic and the local Python service. Tracker throughput can be lower than input FPS. Capture time and quality failures are distinct from model confidence. Backend scores are uncalibrated. See the per-word CSV for frontend output, capture diagnostics and backend status.

Reproduce with a local QA server on port 8001 using the private frozen v3 checkpoint, then run training/target20_virtual_camera.py --playlist --parity --split val --limit 20 --workers 1 --output <new private directory>. The V5 parity and report scripts read the original private run folder virtual-v5-validation. No physical webcam is required.

## Invalid-input controls (validation transformations)

- no-hands: Capture quality insufficient: hand visibility or frame continuity. Nothing was submitted.; backend response absent. No capture failure is credited as model rejection.
- incomplete: Recording timed out before a complete capture. Nothing was submitted.; backend response absent. No capture failure is credited as model rejection.
- missing-hands: Unknown sign — no word added.; backend response present. No capture failure is credited as model rejection.
