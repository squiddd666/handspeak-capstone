# Local evaluation results

Downloaded upstream commit: `6219c4d5d017457da220ff3037ea209c739fd663`.
Checkpoint: 100 classes; epoch 103; stored validation accuracy 69.1588785046729%.

## Existing HandSpeak reference clips

- 31 local clips with filenames matching supported labels.
- Top-1: **9/31 = 29.03%**.
- Top-5: **17/31 = 54.84%**.
- Failed/no-prediction clips: 0.
- Upstream video preprocessing and model, one base plus eight TTA passes.
- Fixed augmentation RNG seeds for reproducibility.

This is a small convenience-set transfer test, using the existing reference
clip labels, generally one clip per word. It is not a 100-word benchmark, an
official WLASL evaluation, a signer-independent measurement, or live webcam
accuracy. Training overlap has not been established. The 69.16% checkpoint
figure and this 29.03% result measure different sets and must not be equated.

Full predictions and input hashes: `reference-results.json`.
Flat export: `reference-results.csv`.
Logs: `evaluation.stdout.log`, `evaluation.stderr.log`.

## Runtime / API checks

- Checkpoint state dict loaded with weights_only=True.
- Synthetic input produced 100 finite logits (not an accuracy measurement).
- Local page and health endpoint returned HTTP 200.
- HTTP video upload accepted and processed a generated blank video; no-hand
  rejection returned an incorrect/failed trial rather than a fake prediction.
- Browser script passed JavaScript syntax checking.
- A live camera recording and actual browser interaction have not been tested
  by the assistant. Use http://localhost:8001 for your own labeled trials.
