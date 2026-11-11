# V8 canonical browser extraction

The reference path is Chromium virtual getUserMedia (640×480, source 15 FPS) → actual HandSpeak frame preprocessing and Holistic 0.5.1675471629 → browser request → local Python backend → private archived request → versioned reader and unchanged V6 encoder. Extraction means the landmarks HandSpeak actually submitted, not every decoded frame or callback. The archived timestamps are the browser's source-video clock, not re-created frame-index times or original MP4 PTS. Warm-up and retained tracker state are recorded in the profile.

The harness records the actual Chromium user-agent and protects runs against overwrites. Freeze frontend/harness SHA-256 per run before packaging; the extractor verifies both, source SHA-256, frame counts and the backend's V6 timestamp endpoints. Failed windows may be retained as excluded evidence; attempts without a submission have index entries only. Output is outside the website tree. No production inference code, checkpoint or threshold was changed.

Reproduce on Windows from the workspace with the QA backend listening on 8001 and the locked V3 checkpoint. Set HANDSPEAK_TARGET20_MODEL to the private target20-v3/target20-v3-selected.pt and HANDSPEAK_TARGET20_V6_DIAGNOSTICS=1 in the QA server environment only, then run:

    .venv/Scripts/python.exe -c "import server; server.run(port=8001)"
    .venv/Scripts/python.exe training/target20_virtual_camera.py --playlist --parity --split val --limit 20 --workers 1 --output ../handspeak-training/virtual-v8-validation

For repeat use limit 3 and output virtual-v8-repeat. These are the historical run names, so preserve or relocate old evidence privately before reusing names. Before packaging, save a JSON file in the private parent named RUN-code-profile.json with lowercase Get-FileHash SHA256 digests under frontend_sha256 (beginner-recognition.js) and harness_sha256 (training/target20_virtual_camera.py), captured from the exact code used for playback.

    .venv/Scripts/python.exe training/extract_target20_v8.py virtual-v8-validation
    .venv/Scripts/python.exe training/check_target20_v6_compatibility.py virtual-v8-validation
    .venv/Scripts/python.exe -m unittest discover -s training -p test_target20_v8.py -v

Verified exact array equality on JSON reload and re-encoding of all 11 usable artifacts. This does not establish repeatable browser tracking: only HELLO qualified in both runs. It yielded 46 versus 31 delivered frames and 873 versus 1,205 ms of resampled active span. On normalized active-grid sample indices (not physical-time alignment), pose mask agreement was 100%, left 21.875%, right 12.5%; normalized XY RMSE was 0.1102 for pose and 0.5736 over the one jointly visible left-hand grid step (10 points). No right-hand grid step was jointly visible. THANK YOU and PLEASE had no submitted repeat. Frame-exact or statistically reliable live extraction has not been demonstrated.
