# Target-20 V6 simulated virtual-camera report

20 distinct validation clips; 20 verified 640×480 / 15 FPS streams; 20 full source windows; 19 API responses. Encoder states: {'encoded': 19}. V3 recognition states: {'uncertain': 17, 'recognized': 2}. V3 end-to-end correct: 0/20. V6 recognition: not applicable.

Actual Chromium getUserMedia, HandSpeak frontend, browser Holistic and local Python API. V6 ran in parallel to V3 on the real capture request, not as input to V3. Capture failure is not model rejection. No exposed V4 clips were used for tuning or tested here.

## Transformed validation controls
- no-hands: Capture quality insufficient: hand visibility or frame continuity. Nothing was submitted.; V6 state not submitted; accepted V3 prediction none. Not independent clips.
- incomplete: Recording timed out before a complete capture. Nothing was submitted.; V6 state not submitted; accepted V3 prediction none. Not independent clips.
- missing-hands: Unknown sign — no word added.; V6 state encoded; accepted V3 prediction none. Not independent clips.

Exact legacy response parity: 19 real validation request replays matched every V3 response field, excluding only the V6 diagnostic field. Stable and locked model hashes were verified.

Automated suites: Ran 109 tests in 187.978s; OK; Ran 4 tests in 0.063s; OK.

Reproduction: start a loopback QA server on port 8001 with the locked V3 checkpoint and HANDSPEAK_TARGET20_V6_DIAGNOSTICS=1; run training/target20_virtual_camera.py --playlist --parity --split val --limit 20 --workers 1 --output <new private directory>. The analysis scripts read the original private run folders. Raw recordings and submitted landmarks stay outside the served directory.
