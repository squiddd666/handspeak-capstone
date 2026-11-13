# SignSpeak alphabet model

Source: https://github.com/medhu0505/SignSpeak
Interpreter layout reference: https://sign-speak-rho.vercel.app/interpreter
interpreter-layout.js and interpreter-layout.css adapt the upstream Interpreter
page structure and dark palette while retaining HandSpeak branding and controls.
Commit: 9272bb86cd5343c5a20d649f332172ee030a31ac
Upstream asset: web/public/models/asl.onnx
Local asset: models/signspeak/asl.onnx (277,984 bytes, copied unchanged)
Alphabet reference assets: web/public/assets/reference/{A..Z}_test.jpg copied
unchanged to media/signspeak-alphabet/{A..Z}.jpg. Source and repository license
are credited beneath HandSpeak's alphabet grid. Upstream does not identify a
separate image-specific license in the inspected reference directory.
Copyright (c) 2026 Medhansh Sharma. MIT license: LICENSE in this directory.

signspeak-model.js adapts upstream web/src/engine/{landmarks,predictor}.ts.
Input is float32 [1,30,63]: 21 image-relative XYZ landmarks, mirror X,
subtract wrist, divide by the 3D wrist-to-middle-MCP distance. Do not apply
HandSpeak's aspect correction, palm rotation, or kNN normalization.
Output is 26 logits in A-Z order. Softmax threshold: 0.85.

## Using it

Run the existing Python server, use Letters mode and start the camera.
SignSpeak is now the sole active A-Z recognizer, including at the plain root
URL. Legacy alphabet assets remain inactive for archival purposes; they are
not loaded by the app or camera worker. Word recognition is unchanged.

This experimental option requires the worker camera path. It buffers 30 actual
observations and uses a two-second stable hold. Buffers reset on hand loss,
large wrist jumps, or gaps longer than 500 ms. It does not use personal samples,
does not change word recognition, and disables HandSpeak's separate J/Z matcher.
Failures stop recognition rather than silently substituting the kNN classifier.
ONNX Runtime Web 1.23.2 is loaded from jsDelivr (same version as the existing
hand recovery detector); this integration is not fully offline.

Model shape/inference and normalization/decoding smoke tests are run locally.
Live browser inference and recognition accuracy with real signers still require
testing. Softmax confidence is not independently calibrated recognition accuracy.
