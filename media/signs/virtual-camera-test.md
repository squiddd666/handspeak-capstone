# Virtual-camera sentence test videos

Full sequence: `test-i-want-water-please-finish.mp4`.
Automatic-flow diagnostic: `test-water-please-finish.mp4`.

These are edited compilations of separate sign examples, not one continuous signing performance. Both are silent H.264 MP4, 1280×720, 30 fps. Gestures play at 0.65× source speed with three-second no-hand gaps. A setup card precedes the signs and a ten-second wait follows FINISH.

For the automatic-flow diagnostic, enter `I WANT` using Edit message, select Words in motion, enable the seven extra words (for WATER), Automatic words, Automatically add motion matches, and Speak interpreted sentence when FINISH is recognized. Disable the five-word server preview. Play once through your virtual camera, then inspect the draft and LLM output. A missed or wrong match is a test result; speech is not guaranteed.

The full sequence cannot currently be recognized hands-free from start to finish. I/ME is not a supported motion word. WANT requires the manual five-word preview and explicit acceptance, followed by switching back to the default plus extra-word model for WATER, PLEASE, and FINISH. Pause/restart the video as needed. These limitations are not fixed by joining the clips.

## Sources and edits

- I/ME: Start ASL, “i me in ASL”, https://www.youtube.com/watch?v=nDncXyPwfmM . First 3.2 seconds of the frontal example; original source branding retained.
- WANT: ASL University / Bill Vicars, https://www.youtube.com/watch?v=IRUlCZ9jRjM , linked from https://www.lifeprint.com/asl101/pages-signs/w/want.htm .
- WATER, PLEASE, FINISH: PopSign ASL v1.0, Georgia Tech and DPAN, CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). See `sources.json` and `README.md` here for original archive members and credits.

Edits: concatenation, aspect-preserving resizing/letterboxing, slower playback, titles, blank pauses, and credit cards. The PopSign license statement applies to the PopSign segments, not the other creators’ clips. Per-clip times and sources are in the corresponding `.json` files.

These reuse lesson examples and are diagnostic inputs, not an independent recognition-accuracy evaluation.

## Revised portrait test — 3 October 2026

Use `test-water-please-finish-portrait-slow.mp4` (480×640, 30 fps, about 43 seconds) for the automatic-flow diagnostic. WATER and PLEASE run at 0.65×; FINISH runs at 0.35×. Keep the portrait aspect ratio in your virtual-camera software; do not stretch or crop the hands. Face tracking was off during the test. The live Mirror preview checkbox changes only presentation, not classifier input.

Timed browser CPU/canvas-capture results: the old landscape clip recognized only PLEASE in normal and horizontally flipped input. Portrait recognized WATER and PLEASE. Portrait with slower FINISH recognized all three in one run. This does not establish general recognition accuracy; it reuses existing lesson clips.
