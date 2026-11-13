# OpenHands local test sandbox

Upstream: https://github.com/jaredslorenz/OpenHands
Pinned checkout: `third_party/OpenHands-source`
Commit: `6219c4d5d017457da220ff3037ea209c739fd663`

Start from HandSpeak's root:

```powershell
.\.venv\Scripts\python.exe openhands-test/server.py
```

Open http://localhost:8001. HandSpeak on port 8000 is not modified by this
sandbox. The server binds only to 127.0.0.1 and does not enable cross-origin
access. Browser recordings are processed on this computer in temporary files,
then deleted; the server does not save user recordings or trial results.
Export the in-page trial JSON before refreshing if you want to keep results.

## Measurement

Choose an expected word before recording or uploading. That label is used only
for scoring, never as a classifier input. Top-1 and top-5 accuracy count all
submitted trials, including failed/no-hand captures. Use several attempts per
word and multiple signers. Confidence is a model score, not measured accuracy.
The UI labels are supplied by the tester, not verified by an ASL expert.

The downloaded checkpoint has 100 classes, epoch 103, and stored validation
accuracy 69.1588785046729%. A shape/finite-logits smoke test is NOT an accuracy
evaluation. No official WLASL evaluation dataset ships in this checkout.

`evaluate.py` evaluates the existing local `media/signs/<word>.mp4` reference
clips whose names exactly match model labels, and writes
`reference-results.json` incrementally. It uses every matching clip once,
without threshold tuning. Failures count as incorrect. These reference clips
are a convenience set, usually one clip per word: not a representative webcam
test, not a signer-independent benchmark, and overlap with model training has
not been established. Source manifests remain beside the original media.
Results include the exact file SHA-256 hashes for traceability.

## Inference parity and differences

The harness imports the upstream `ASLClassifier`, video landmark extraction,
feature preparation, and test-time augmentation helpers unchanged. It loads
the checkpoint with PyTorch `weights_only=True` and checks state dict shape.
Upstream config is replaced with a constants-only module to avoid unrelated
model loads. It runs one base pass and eight augmentation passes, like upstream.
Seeds are fixed at 42 per clip for reproducibility. No-hand clips are explicitly
rejected by the harness instead of receiving upstream's unconditional guess.
Both the cloned upstream project and original model files remain unmodified.

Dependencies used: existing PyTorch, MediaPipe, OpenCV, NumPy, plus
`python-dotenv` installed in the existing .venv. No alphabet model is downloaded.

The upstream repository states WLASL academic-use restrictions and does not
include a general root LICENSE file in this checkout. Local testing does not
establish permission to redistribute or commercially deploy the code or model.
