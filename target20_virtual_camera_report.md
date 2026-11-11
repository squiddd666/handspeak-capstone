# Target-20 virtual-camera report — simulated, not accepted

Chromium file-backed getUserMedia, 640×480 at 15 FPS, through the real HandSpeak capture UI, browser Holistic tracking and local Python API. No landmarks or predictions were injected. Warm-ups and transformed clips are not counted as distinct test recordings. The candidate and rejection threshold were pinned before these browser results.

Known-word test is a regression on recordings already exposed to prior offline evaluation, not an untouched benchmark. 200/200 distinct reserved clips logged across 20/20 words; 199 had a started capture with verified camera settings, 92 had a verified full source window, and 1 were correctly recognized. 93 missed-slot retries logged; a retry replaces the original in the summary only when no recording started previously and the retry has verified camera settings. Missing and failed slots are retained separately.

Virtual end-to-end macro F1 (capture failures included): 0.8%. This is not an untouched test result. A reserved clip with no actual recording is a failed case, not an independent signing attempt. Full-source-window verification uses media-time bounds; it does not prove per-frame tracker quality.

## Pipeline findings

The isolated browser hand detector initially produced no hands despite body tracking. Switching the Target-20 capture path to Holistic restored hand observations and API submissions in validation pilots. A capture-level check now evaluates continuity within the visible-hand interval rather than rejecting every sign that uses less than half of the full capture window. This does not establish linguistic completeness. Cold tracker initialization was moved ahead of the countdown. Timing failures in the full playlist are retained; they are not model rejections.

## Rejection controls

| Scenario | Observed result |
|---|---|
| no-hands | Not enough visible-hand frames; record again.; prediction: none |
| incomplete | Not enough visible-hand frames; record again.; prediction: none |
| missing-hands | Recording timed out before a complete capture. Nothing was submitted.; prediction: none |
| low-quality | Missed reserved clip slot; no partial recording submitted; prediction: none |
| delayed | Missed reserved clip slot; no partial recording submitted; prediction: none |
| dropped-frames | Recording timed out before a complete capture. Nothing was submitted.; prediction: none |
| interrupted | Missed reserved clip slot; no partial recording submitted; prediction: none |
| low-quality | Not enough visible-hand frames; record again.; prediction: none |
| delayed | Not enough visible-hand frames; record again.; prediction: none |
| dropped-frames | Not enough visible-hand frames; record again.; prediction: none |
| interrupted | Beginner recording canceled.; prediction: none |
| similar-looking | Not enough visible-hand frames; record again.; prediction: none |
| incorrect-target | Not enough visible-hand frames; record again.; prediction: none |

Independent browser unknown clips: 100/100 attempted, 3 with a verified full capture and recognition decision, 0 falsely accepted. Capture failures are not counted as successful model rejections. The separate historical offline result (1/224) is not browser evidence. Zero decisions from invalid/failed captures are not credited toward unknown-sign model rejection. MY and OUR are source-labeled validation controls, not expert-certified examples of visual confusability or deliberately malformed signing.

## Reproduce

Start the local QA server on port 8001 with HANDSPEAK_TARGET20_MODEL pointing to the private target20-v3-selected.pt. From the project root run:

    .venv/Scripts/python.exe -X utf8 training/target20_virtual_camera.py --playlist --split test --per-word 10 --limit 200 --workers 2 --output ../handspeak-training/virtual-v4-known-final
    .venv/Scripts/python.exe -X utf8 training/target20_virtual_camera.py --playlist --split val --phase rejections --limit 7 --workers 1 --output ../handspeak-training/virtual-v4-rejection-controls
    .venv/Scripts/python.exe -X utf8 training/target20_virtual_camera.py --playlist --split test --phase rejections --offset 7 --limit 100 --workers 2 --output ../handspeak-training/virtual-v4-unknown-final
    .venv/Scripts/python.exe -X utf8 training/report_target20_virtual.py

Use new private run folders for reruns. Keep recordings, generated streams, screenshots of signers, and detailed attempt logs private.
