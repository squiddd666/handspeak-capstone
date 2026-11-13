# HandSpeak Web

HandSpeak Web is a browser-based capstone prototype that recognizes selected static American Sign Language (ASL) gestures and converts them into readable text.

## Features

- Real-time, on-device hand landmark detection using MediaPipe
- Pretrained weighted k-nearest-neighbor recognition for static alphabet letters
- Experimental pretrained moving-sign vocabulary: HELLO, THANK YOU, PLEASE, YES, NO, FINISH
- Optional personal training in AI Studio, including digit 5 after capturing examples
- Stable-sign filtering to reduce accidental input
- Message composition, copy, text-to-speech, and editing controls
- Built-in presentation demo when a camera is unavailable
- Responsive design, keyboard support, high-contrast mode, and reduced-motion support
- No video frames are uploaded or stored

## Run the complete system

Camera access requires a secure context. `localhost` is considered secure, so serve the folder instead of opening `index.html` directly.

```powershell
python server.py
```

For the trained 20-word motion research preview, use the project Python 3.11
environment rather than a system Python without PyTorch:

```powershell
.\.venv\Scripts\python.exe server.py
# Or: .\start-server.ps1
```

The private candidate and threshold report are loaded from
`../handspeak-training/target20-candidate.pt` and `target20-report.json`.
`HANDSPEAK_TARGET20_MODEL` can override the checkpoint path. In **Words in
motion**, select a word in **20 words in motion**, allow server landmark
processing, then record a complete sign and review the suggestion. This is a
recorded-sign research model, not continuous translation or verified webcam
accuracy. See `reports/target20-current/README.md` for this run's evidence.
ASL Citizen training inputs remain outside the served directory and are subject
to Microsoft's non-commercial research license; do not redistribute them.

Then open <http://localhost:8000> in Chrome or Edge and allow camera access. The first run needs an internet connection to download the MediaPipe runtime and hand-landmark model. The server creates `handspeak.db` automatically.

## Accounts and administration

The deployed application includes registration/sign-in, password changes, private saved history, CSV export, message editing/reuse/deletion, and an administrator dashboard for accounts and feedback. Sign-in is optional for using the camera. Guest history is scoped to a browser cookie and transfers to the account on registration/sign-in. Email verification and delivery are not configured; administrators provide single-use password-reset links.

The owner creates the first administrator with a private one-time setup link generated on the server. See [deployment and recovery instructions](ops/DEPLOYMENT.md). Production data and backups are outside the website. Do not publish the setup token or database.

## Persistent system functions

- Private saved translation sessions and detection details
- Gesture library delivered from the database
- Anonymous 5-point research evaluation questionnaire
- Personal session/match statistics and aggregate user feedback ratings (not measured recognition accuracy)
- CSV session export for research analysis
- JSON API health check and validated server inputs

## Run automated tests

```powershell
python -m unittest discover -s training -v
```

## Recognition guidance

Use one hand, face your palm toward the camera, keep the hand inside the guide, and use even front lighting. Hold a sign steady for roughly one second. Lower the hand briefly before repeating the same character.

## Scope and limitations

This prototype recognizes selected static hand shapes and a small vocabulary of isolated moving signs, with rejection of uncertain matches. It is not a complete ASL translator: it does not interpret continuous signing, ASL grammar, facial grammar, or body posture. Similar hand shapes and side-on poses may be misclassified. A production version should use a diverse, validated training dataset and evaluation with Deaf/Hard-of-Hearing users and qualified sign-language experts.

## Project files

- `index.html` — semantic page structure
- `styles.css` — responsive visual design and accessibility modes
- `app.js` — camera, MediaPipe integration, recognition, and message tools
- `server.py` — HTTP server, validated JSON API, SQLite persistence, and CSV export
- `training/test_model.py` — pretrained model validation and browser-classifier integration tests

## Pretrained ASL model

The website automatically downloads `models/asl-knn.json` from this server. No personal
training is required to try its 24 pretrained static letters. AI Studio reports the loaded
reference count. Captured examples stay in browser localStorage and supplement the
reference set; resetting personal samples leaves the pretrained model intact.
Digit 5 is not in the alphabet training set and must be taught before use.
Uncertain predictions stay blank. Static-letter recognition uses the weighted kNN
reference model; no class-specific landmark override is used.

Source: [Marxulia/asl_sign_languages_alphabets_v03](https://huggingface.co/datasets/Marxulia/asl_sign_languages_alphabets_v03),
revision `1adf43b2d31eb9d7aea5855edaeac0231d8a2757`.
The source dataset card did not specify a license at download time; redistribution
and commercial permissions have not been established. Raw images are not bundled.

The reference set also includes 704 converted static-landmark samples from
[ASL Static Landmarks v1](https://huggingface.co/datasets/Siruyy/asl-static-landmarks-v1),
licensed CC BY 4.0. Its published 63 MediaPipe coordinates were converted to the
same browser normalization before merging; derived features and motion-letter
classes were not imported.

The browser fixture calibration adds 72 normalized landmark samples (three
captures for each of the 24 static letters) to cover the camera fixture domain.
J and Z remain motion letters because ASL defines them by tracing movement. Their
lesson cards now use the credited remote motion-reference videos (including the
pinky path for J and index-finger path for Z) listed in
`models/motion-letters-sources.json`; the videos are not redistributed in this
repository. J/Z are not included in the static kNN model and are evaluated by
the separate temporal matcher.
The temporal matcher combines the reference templates with stroke geometry: J
requires an initial pinky pose followed by its downward-and-hooking path, while
Z requires three alternating index strokes. A stationary I or X pose cannot emit
J or Z.

`training/train_asl.py` extracts the same 21 MediaPipe landmarks and wrist/palm/rotation
normalization used in the browser. kNN training stores labeled reference examples;
it does not fit neural-network weights. Exact duplicate decoded images are removed.
The original seed-42 20% image test is preserved; a seed-17 split reserves 20% of the
remaining images for validation. Reference training uses 1,463 images, validation
uses 367, and testing uses 456. Threshold selection uses validation only, minimizing
`5 * wrong predictions + rejections`. Neither validation nor test images enter the
reference model. The selected distance weights depth by 0.5, compares both mirrored
orientations, and uses three neighbors with distance, agreement, and class-separation
checks. This improves handling of handedness without duplicating training images.

On the same test images, the previous model gave 441 correct, 8 wrong, and 7 rejected
predictions. The revised model gives 425 correct, 1 wrong, and 30 rejected predictions:
99.77% correct among accepted predictions, 93.42% coverage, and 93.20% correct across
all test images. This is a deliberate reduction in wrong outputs at the cost of more
abstentions, not an improvement in overall recall. See `models/asl-evaluation.json`
for validation metrics, detection failures, and the confusion matrix.

These are image-holdout results, not signer-independent or live-camera results:
signer identities are unavailable and near-duplicate photos may remain. Images
without detected hands are excluded. There is no unsupported-sign test set and
personalized recognition has not been evaluated. Neighbor agreement is not a
calibrated probability. Camera processing skips duplicate video frames, rejects
clipped or very small hands, and pauses text entry during personal capture. Capture
locks the selected label and saves complete batches only; stopping the camera
cancels an incomplete batch.

To reproduce using Python 3.11 with MediaPipe 0.10.21, NumPy 1.26.4, PyArrow and Pillow:

```sh
python training/train_asl.py --cache /path/outside/website/asl-cache
# Additional test dependency: quickjs
python -m unittest discover -s training -v
```

On servers without graphics libraries, use `opencv-contrib-python-headless==4.11.0.86`
in place of `opencv-contrib-python`. Downloaded images and extraction caches should
remain outside the served website directory. The browser needs internet access for
its MediaPipe runtime/model on first use, but classification stays on-device.

## Words in motion (experimental)

The website automatically loads `models/asl-words.json`. No personal training is
required for **HELLO, THANK YOU, PLEASE, YES, NO, and FINISH**.

1. Select **Words in motion** and start the camera.
2. Leave **Automatic words** enabled (the default). Sign one supported word, then pause briefly.
3. A possible match appears over the camera. Review it and select **Add matched word** before adding it to the message.

Automatic capture keeps a short 350 ms lead-in, starts on hand movement, and
finishes after a 600 ms pause with at least 12 samples, or after 4.5 seconds.
It requires a quiet interval and cooldown before the next sign, avoiding repeated
suggestions from ongoing movement. Camera gaps and orientation changes discard
partial movements. This is experimental isolated-sign segmentation, not sentence
translation; it does not improve the classifier's measured accuracy.

**Record a word** remains available for a manual countdown and timed capture.
Disable Automatic words to use only manual recording. Face inference pauses
during active word capture to give hand tracking more processing time. Matches
are suggestions only: automatic capture never appends text or speaks by itself.

This is a nearest-template sequence classifier trained from a small subset of
[PopSign ASL v1.0](https://signdata.cc.gatech.edu/view/guides/downloading_popsign/index.html),
game category, CC BY 4.0. See `models/WORDS-SOURCE.md` for attribution.
It does not train a new neural network: MediaPipe supplies hand landmarks and
training builds labeled motion references. Up to two hands are tracked, leading
and trailing untracked frames are trimmed, and internal gaps of at most two frames
are interpolated. Coordinates are corrected for camera aspect ratio. Hand paths are centered over the full movement and normalized by palm width,
resampled to 20 frames, and compared using banded dynamic time warping. Matching
checks both mirrored orientations. A continuous run containing at least 70% of
usable frames can replace isolated entry/exit fragments; long disconnected runs
are not joined. Validation selects distance, class-separation, and neighbor-vote
cutoffs. Two nearby references must agree, unless the closest competing word is
at least 1.5 times farther away. The maximum-distance check still applies.

The source's train/validation/test partitions are preserved, with no overlapping
participant IDs. Validation selects rejection thresholds; test recordings never
enter the template library. DRINK is reserved as an unsupported-word check.
`models/asl-words-evaluation.json` reports counts, tracking failures, confusion,
and accuracy both with and without rejected predictions. `asl-words-sources.json`
records source archive members and SHA-256 hashes for audit/reproduction.
The revised v3 model contains 116 usable training examples. On 57 tracked test
clips, 38 predictions were correct, 4 wrong, and 15 rejected: 90.48% correct among
accepted matches, 73.68% coverage, and 66.67% correct including rejections. Another
15 of the 72 known-word test videos failed tracking/sequence checks, giving 38/72
correct over the complete selected known-word test set. The prior version gave
31/72 correct and also made 4 wrong predictions; its report is preserved in
`models/asl-words-evaluation-v2.json`. This is a regression comparison on previously
evaluated recordings, not a new independent benchmark. On validation, 26/31
tracked known-word clips were correct, none wrong, and five rejected.
Of 11 tracked unsupported DRINK test clips, 6 were incorrectly accepted and 5
rejected. This remains a significant limitation: rejection of signs outside the
vocabulary is unreliable.
The evaluation uses a small subset of isolated videos; it does not establish
live-camera or continuous-signing accuracy. Unsupported signs can still match a
known word. Distance is not a calibrated confidence probability. Review every
suggestion before adding it. Face/body/grammar/LLM interpretation is not used.

**Optional personalization:** Expand **Optional: add your own word examples**,
enter a label, and record at least three examples for a new word. Personal
recordings store coordinates only in `handspeak-motion-v3` in browser localStorage;
no video/audio is recorded or uploaded. The personal library allows 8 recordings
per word and 96 overall. Removing personal examples preserves pretrained words.
Personal examples supplement the references but have no evaluated accuracy.
Older `handspeak-motion-v1` and `handspeak-motion-v2` recordings are retained in
storage but not loaded because v3 changed movement centering and segmentation. They can be
re-recorded optionally; the pretrained vocabulary works without them.
Stopping the camera, changing modes, or Cancel discards an unfinished recording.
A fresh recording never adds text or speaks until the user confirms the match.
The standard Save button stores the confirmed message through the existing API;
motion similarity is not mixed into static-letter confidence statistics.

To rebuild the bundled vocabulary, use Python 3.11 with MediaPipe 0.10.21,
NumPy 1.26.4, SciPy, QuickJS, and OpenCV (headless is suitable on a server):

```sh
# Downloads selected original clips (~1.4 GB); keep this cache outside the website.
python training/download_words.py --cache /path/outside/website/popsign
python training/train_words.py --cache /path/outside/website/popsign --hand-model /path/outside/website/hand_landmarker.task
python training/fit_words.py --cache /path/outside/website/popsign
python -m unittest discover -s training -p 'test_*motion*.py' -v
python -m unittest discover -s training -p test_words.py -v
```

Extraction uses the same browser sequence encoding and reuses cached landmarks.
Exported models/evaluation files are written to `models/` in this checkout.
`motion-model.js` handles matching, `motion-studio.js` handles recording and
confirmation, and tests cover recording behavior, automatic model loading, source
split integrity, and exact Python/browser reserved-test prediction agreement.

`training/check_word_videos.py --videos /path/to/asl-examples` replays the five
provided MP4 examples through the actual browser MediaPipe hand detector, checks
video seeking, and resets tracking between clips. It requires Playwright/Chromium
and the website running on localhost:8000. Its clips were selected from training
recordings, so this is a functional integration check, not an accuracy benchmark.
Only the summary is bundled in `models/asl-words-browser-check.json`.

## Face tracking

The camera also loads MediaPipe Face Landmarker and draws one face's outline,
eye/lip contours, and sparse landmarks. Use the **Face tracking** checkbox under
the camera to turn it off or on. The visible status reports loading, readiness,
face presence, or unavailability. Face inference is limited to roughly 10 Hz to
leave processing time for hand tracking; GPU initialization falls back to CPU.
A face-model failure is contained and hand recognition continues. Runtime GPU
errors retry face tracking on CPU. If both paths fail, select **Retry face tracking**
or restart the camera. Hand inference errors no longer stop the face drawing loop.
The face outline uses a bright stroke, and detection uses MediaPipe's default 0.5
thresholds. The status gives framing guidance when no face is detected.

The camera also shows visible expression cues: Smiling, Mouth open, Brows raised,
and Brows lowered. These use MediaPipe blendshape coefficients with experimental
thresholds, smoothing, and a 300 ms stability check. They describe facial movements,
not happiness, sadness, anger, or a person's internal emotional state. No expression
accuracy benchmark is claimed. Missing faces, disabled tracking, and model errors
clear the previous cue. This feature does not recognize identity or change sign predictions. Face coordinates are never
saved, included in motion recordings, or sent to the server. The model and runtime
are downloaded on first use; frame processing stays in the browser. The existing
moving-sign recognizer still uses hands only.

Implementation: `face-tracker.js`. Model: Google's
[Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/web_js).
`training/test_face.py` covers throttling, toggle/reset behavior, CPU fallback,
and isolated loading/inference failures.

Slow word captures can extend by up to two seconds after the normal 2.5-second recording window to reach the existing 12-frame minimum. A stalled stream still times out; no frames are duplicated to pass the minimum. This does not guarantee word recognition.

The October 2026 accuracy experiment trained an additional temporal candidate. It remains evaluation-only: fresh whole-clip recognition improved, but automatic unsupported-sign suggestions increased. See `reports/accuracy-v4/README.md` in the Git checkout for the recorded results. Local application assets use a release query tag, and the server requests revalidation to avoid stale CDN code.

### Gesture example videos

The Moving signs section includes a silent example for HELLO, THANK YOU, PLEASE, YES, NO, FINISH, DRINK, WATER, and BOOK. Users can select normal, half, or quarter speed, repeat playback, and return to the camera in Words in motion mode. Playback requires a user action and pauses when the player leaves view or the page is hidden. Nine compressed clips total about 2.7 MiB; full training videos remain outside the website. See [video attribution and changes](media/signs/README.md) and [source provenance](media/signs/sources.json).

The **Try 3 extra words (preview)** checkbox enables optional recognition of DRINK, WATER, and BOOK. It is off by default: a held-out new-word check achieved 9/24 correct, and negative false suggestions increased. Selecting a new-word video and clicking **Practice at camera** enables the preview. Existing six-word and personal suggestions take precedence; disabling the preview restores the original vocabulary. See [the evaluation](models/asl-extra-words-evaluation.json).


## Alphabet repair regression (11 November 2026)

The letter pipeline now converts camera landmarks to pixel-isotropic coordinates
(`y *= videoHeight / videoWidth`) before matching. It no longer tries the inverse
aspect ratio. Letter tracking and independent image re-detection both use 0.5
palm/presence confidence, replacing the old 0.01 settings. A tracked alternative
is considered only when independent image detection confirms the same observed
hand. Short abstentions do not count as positive evidence; a commit requires at
least six accepted frames, an 850 ms hold, and 70% accepted evidence, with no
competing accepted letter and no gap over 500 ms.

Edge-on hands are checked using both palm span and palm length. For a severely
collapsed projected palm span, query and reference features are both re-scaled
by a stable anatomical palm dimension; this path uses **stricter** distance,
agreement, and separation gates. No class-specific forced predictions or new
reference-media training samples were added. The reference model is unchanged.

J/Z remain temporal-only. Their matcher requires at least six observations,
resets after tracking gaps, and handles the mirrored geometric J fallback.
After a recognized motion letter, withdraw the hand before the next static
letter, so its final I/index-like pose is not appended as a second character.

New personal captures use `handspeak-ai-samples-pixel-v3`. Older
`handspeak-ai-samples-static-v2` data is retained, not erased, but is not mixed
with the corrected camera coordinate system; re-record it if needed.

With the local server running:

```powershell
.venv/Scripts/python.exe -X utf8 -m unittest discover -s training -p test_alphabet_repair.py -v
.venv/Scripts/python.exe -X utf8 training/check_alphabet_camera.py --rounds 3 --variations
```

The camera regression preserves 640x480 at 15 FPS and the default face-tracking
setting. Expected labels are used only to score collected UI feedback, never by
the recognizer. Independent browser contexts and transformed copies of the same
reference are **not** independent signer accuracy. See
`reports/alphabet-repair-20261111/` for original failures, diagnostic sweeps,
iteration results, final UI traces, screenshots, and remaining blockers. Do not
interpret a synthetic/template unit-test pass as a real-media or live-user pass.


## OpenHands 70-word mode (local research integration)

Words mode now offers Jared Lorenz's pretrained OpenHands 100-class BiLSTM,
with an output allowlist of the 70 labels that passed our one-reference-per-word
comparison. The full model still competes across all 100 labels; an excluded
winner is rejected without promoting a runner-up or renormalizing scores.
These 70 are NOT verified webcam-accuracy classes. The existing 19 virtual-camera
passed legacy words remain separately available with their previous restrictions.

Use Words in motion, keep "Use OpenHands for Record a word" selected, enable
recorded-video processing, record one complete sign for 3 seconds, then choose
Add reviewed word. Record a word uses this selected mode. Watch & Learn has a
separate OpenHands selector with all 70 local reference videos.

This mode sends the recorded VIDEO (not only coordinates) to the local Python
server. The server writes a temporary file for MediaPipe decoding and removes it
after inference. Uploads require explicit consent, same-origin requests, and a
20 MB limit. A CPU subprocess isolates upstream model imports from legacy models.
Only one OpenHands job runs at a time; canceling the browser request discards its
UI result, while the bounded backend job may finish before deleting its file.

Endpoints: GET /api/openhands/status and POST /api/openhands/recognize.
Metadata/checkpoint pin: models/openhands-passed.json. Source checkout:
third_party/OpenHands-source, commit 6219c4d5d017457da220ff3037ea209c739fd663.
The upstream root has no general code/model LICENSE in this checkout. Local
integration does not establish redistribution or commercial-use rights. Dataset
and reference-video rights remain with their original owners.

Evidence: website-word-test/openhands70-live-api-smoke.json and
website-word-test/openhands70-browser-smoke.json (one end-to-end word only).


### Completed OpenHands70 website fake-camera test

The full 70-word Playwright/Chromium file-camera run is complete: 45 verified
correct UI/word-log matches, 9 wrong predictions, 5 rejections, and 11 incomplete
captures under the existing three-second recorder. This does not establish
physical-webcam accuracy. The 70 reference-passed words remain enabled; this test
did not automatically disable any. See website-word-test/OPENHANDS70-VIRTUAL-RESULTS.md
or http://localhost:8000/openhands70-virtual-results.html for per-word evidence.


### Combined browser + OpenHands workflow

The default combined word mode uses one camera stream and one three-second capture.
Browser hand-landmark frames from the capture are evaluated by the existing default/extra-word matcher, while the same capture's video is evaluated by the OpenHands endpoint. Model files and disabled-word policies are unchanged. Other legacy/category recognizers remain separate modes.

Matching labels are grouped into one review choice with both model sources. Different labels are presented as unranked choices; the app does not compare or renormalize confidence across models. A surviving browser result is still offered if OpenHands rejects or fails. No combined prediction is automatically inserted into the draft. Choose a candidate when necessary, then use Add reviewed word or the sidebar + Add. Cancel discards both results; mode changes stop the shared capture.

Actual manual virtual-camera checks: FOOD was predicted by Browser while OpenHands incorrectly predicted GIVE; both were offered for review and choosing FOOD logged exactly once. BEFORE was predicted by OpenHands, while Browser abstained; accepting it logged exactly once. See `website-word-test/combined-virtual/*.json`. These are two existing reference clips, not independent model accuracy or physical-webcam validation. Existing automatic-capture timing limitations are not fixed by combining model outputs.

Unit checks: `node training/test_combined_word_results.mjs`.


### Automatic combined words (pre-roll + pause segmentation)

In Words in motion, Automatic words is enabled by default. Start the camera, perform one sign, then pause. Record a word remains an optional manual fallback; it is not needed to trigger automatic recognition.

Automatic capture maintains at most three overlapping, short camera encoders in memory, providing roughly 1-2.6 seconds of real video pre-roll before hand movement is detected. Idle buffer bytes are discarded, never uploaded or saved. Once movement is selected, a pause ends the sign (with a minimum sign window to avoid clipping short words), or a seven-second recording bound ends the capture. The browser landmark matcher receives a bounded history covering the same video window; OpenHands receives the actual selected video. No source pixels or inference outputs are injected or replayed.

Blank/static appearance alone does not submit a clip. Only one sign is processed at a time. Pending results block new capture until reviewed or discarded; holding a pose must not repeatedly add a word. After review, a quiet interval rearms capture without requiring the hands to disappear. + Add is still required to accept a word, and conflicts require choosing a candidate. Model accuracy limitations and disabled-word policies are unchanged.

Stopping the camera, changing recognition mode, turning off Automatic words, cancelling capture, or hiding the page cancels active pre-roll/capture. Processing errors remain visible. Local processing and temporary server-video cleanup remain unchanged.

Unit checks: `node training/test_automatic_word_capture.mjs`.
Actual virtual-camera cases: `training/check_automatic_preroll_virtual.py WORD --automatic`; use `--repeat` to check review gating and another sign cycle. These are existing reference-clip workflow tests, not independent model accuracy or a full automatic-vocabulary guarantee.


### Boundary consensus and conservative endpoint checks

Word onset now needs three motion observations over a time window, or two sustained observations corroborated by scene movement; hand appearance alone is not a start. The detector normalizes displacement for hand size and frame cadence, uses different start/stop thresholds, and estimates a limited idle-noise floor. Primary endpoint evidence is a multi-frame stable final pose. A local 64x48 motion thumbnail can corroborate a still scene after tracking drops; it cannot override observed ongoing hand movement. Only the previous thumbnail is retained, and reset clears the off-screen image memory. No thumbnail is saved or sent to a service.

Brief missing-hand intervals do not immediately split a sign. Tracking gaps, moving scenes after tracking loss, and a recording deadline without a confirmed endpoint reject the clip instead of forcing a model prediction. A short pause inside a sign is not an endpoint. The bounded real-video pre-roll and shared two-model review flow are unchanged.

These are heuristic quality checks, not a learned continuous-ASL boundary model or proof of A-Z-level reliability. Users should sign once, briefly hold the final pose still, and review the prediction. Classification accuracy is a separate problem; model weights and confidence scores were not changed.

Boundary tests: `node training/test_word_boundaries.mjs` (19 scenarios/cadences), `node training/test_scene_motion.mjs`, and `node training/test_automatic_word_capture.mjs`. Actual camera checks: `training/check_boundary_consensus_virtual.py` and `training/check_boundary_safety.py`.


Combined-mode hand tracking runs in a worker with a latest-frame-only queue so old observations cannot accumulate behind UI rendering. Face-overlay inference is paused in this mode to prioritize hand tracking; this does not alter the recorded camera stream or OpenHands server inputs. The camera waits for browser word-model loading, and the UI asks the user to hold their hands in view until tracking is ready before signing. First-sign cold-start performance and physical-webcam recall are not guaranteed by the reference-video checks.


### Tracking visibility and worker health

The word overlay displays finite raw tracked landmarks separately from the stricter recognition-quality filter. Display freshness uses result-arrival time; word-boundary timing still uses the original captured-frame timestamp. A compact status distinguishes a tracked hand, a partly cropped hand, missing hands, and delayed tracking. A raised/cropped palm is not treated as a completed motion word. Persistently cropped signing hands abort the clip with a retry instruction.

The latest-frame worker has an eight-second in-flight watchdog: an unresponsive worker stops the camera with a visible retry notification instead of leaving a misleading live feed indefinitely. This is a health check, not a change to model confidence or vocabulary. `training/check_tracking_visibility.py` verifies actual landmark pixels and BEFORE recognition/logging through a virtual camera. `training/check_tracker_watchdog.py` is explicitly a worker-stall fault-injection test, not model-accuracy evidence.


### False maximum-duration / held-pose timeout repair

The previous endpoint rule reset its pause timer on ordinary landmark jitter, including frames in the threshold dead band. A rolling pose-consensus window now tolerates bounded jitter and isolated noisy observations while checking the most displaced hand joints and recent frames. Genuine ongoing drift and recent substantial pose changes still block an endpoint. Visible stable hands do not need a motionless background.

Recording-buffer rotation and the hard capture deadline now use actual recording wall-clock time. Boundary geometry still uses captured-frame timestamps; variable worker delay cannot consume the video recording budget. The recording limit has not simply been extended, and incomplete clips are not automatically submitted at timeout.

Regression checks: `node training/test_pause_tolerance.mjs` (bounded hand jitter with moving background succeeds; slow continuing movement does not), `node training/test_capture_clock.mjs` (worker-lag-independent budget), and the existing 19 boundary, scene-motion, and sampler/lifecycle checks. Actual controlled held-hand/moving-background video test and normal BEFORE reference-camera results are under `website-word-test/pause-repair`. No model weights or confidence calibration changed.
