# Local 20-word training

Run with `.venv\Scripts\python.exe -u training/run_local_training.py`.

Data: Microsoft's ASL Citizen, official download and signer-disjoint splits.
License: https://www.microsoft.com/en-us/research/project/asl-citizen/dataset-license/
Official download: https://www.microsoft.com/en-us/download/details.aspx?id=105253

Raw clips, landmarks, logs, and output checkpoints stay in `../handspeak-training`, outside the web root. Do not publish the cache. Retain dataset notices and follow the license, including its personal-data requirements.

Progress: `../handspeak-training/pipeline-status.json` and stage-specific `.log` files.
Environment: `training/requirements-local-training.lock.txt` (Python 3.10).
Architecture source and pinned commit: `third_party/microsoft_asl_citizen/SOURCE.json`.

The driver downloads/extracts the 20-word subset, trains a candidate with an UNKNOWN class, trains the five-word candidate, and runs its rejection evaluation. Model selection uses validation, not test performance. A failed run records the stage/error and stops; it does not silently fall back or deploy.

This is a new local training run, not a new independent benchmark: the warm-start checkpoint and historical experiments have prior exposure to the source dataset. Test scores must not be used for further tuning. Readiness requires independent signer-separated evaluation, adequate unknown-sign rejection coverage, and end-to-end camera validation. No automatic promotion or claim of readiness is made. Even a completed training run remains experimental.

Before deployment, inspect the reports. The existing project acceptance checklist calls for validation macro-F1 >=90%, independent test macro-F1 >=85%, per-word recall >=80%, and browser correctness >=8/10 per word. The driver only records a preliminary offline per-word gate (recall >=80%, precision >=85%); that is not the full acceptance check.
