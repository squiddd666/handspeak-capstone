# Dataset for the requested everyday words

Source checked: 2026-11-11.

ASL Citizen is the first-choice source for improving the five words missing from
the current ready vocabulary. The project already maps these exact glosses in
`models/beginner-100-label-map.json`:

| App label | ASL Citizen gloss |
| --- | --- |
| HELP | HELP |
| I / ME | ME |
| YOU | YOU |
| NEED | NEED |
| WHERE | WHERE |

Official dataset and terms:
https://www.microsoft.com/en-us/research/project/asl-citizen/datasheet/

Official download page (42.8 GB full archive):
https://www.microsoft.com/en-us/download/details.aspx?id=105253

Archive URL published in the datasheet:
https://download.microsoft.com/download/b/8/8/b88c0bae-e6c1-43e1-8726-98cf5af36ca4/ASL_Citizen.zip

Baseline code:
https://github.com/microsoft/ASL-citizen-code

The dataset contains 83,399 isolated-sign videos, 2,731 signs, and 52 participants.
Read the dataset's own license; the baseline code's MIT license does not license
the video dataset. Keep downloaded research data outside the served project.

## Required work before calling the words ready

1. Retrieve the dataset and its official split metadata; select the glosses above.
2. Extract hand and upper-body landmarks compatible with `beginner_asl.py`:
   27 nodes, four channels (XY and hand masks), normalized by shoulder width,
   and resampled to the checkpoint sequence length.
3. Fine-tune a candidate checkpoint using training data only. Preserve existing
   words to avoid losing their recognition while improving the five targets.
4. Select rejection thresholds on validation data. Evaluate on separate signers
   and include unsupported signs, reporting rejections and false matches.
5. Compare with the current checkpoint before updating ready-word metadata.
6. Verify camera capture, server inference, and reviewed message entry locally.

The existing `models/beginner-ready-eval.json` refers to an older checkpoint than
the active ready metadata. Its per-word numbers cannot validate a new release.
Finding a dataset or adding labels does not retrain a model. No dataset download,
landmark extraction, or retraining was completed by the initial source audit.

## Local preparation result (2026-11-11)

- Installed Python 3.11 in a local `.venv`, with PyTorch, MediaPipe, NumPy,
  and the range-download dependency.
- Downloaded 154 official clips (81,013,617 bytes) into
  `C:/Users/genesis_narito/Downloads/handspeak-training`, outside the website.
- Preserved official CSV splits and research license. The manifest records
  source members, labels, participants, file sizes, and SHA-256 hashes.
- Verified the selected train, validation, and test participant sets do not overlap.
- `training/download_essential_citizen.py` reproduces the subset and reuses
  existing files. Run using `.venv/Scripts/python.exe` with `--cache` set to
  the external directory above.
- Initial blocker (resolved after the user installed the runtime): PyTorch could not load `c10.dll`; it reported a missing Microsoft Visual
  C++ Redistributable. MediaPipe's native bindings also fail to load. Automatic
  approval review rejected the attempted runtime installation. Install the
  official x64 runtime from https://aka.ms/vs/17/release/vc_redist.x64.exe before
  resuming extraction and training.
- The user installed the runtime; PyTorch and MediaPipe imports now pass.

## Completed training and optional preview

Run from the project root using:

```powershell
.venv/Scripts/python.exe training/train_essential.py --cache ../handspeak-training
.venv/Scripts/python.exe training/check_essential_rejection.py
.venv/Scripts/python.exe -m unittest discover -s training -p test_essential.py -v
.venv/Scripts/python.exe server.py
```

The encoder and non-target classifier rows are frozen. The five target classifier
rows were fine-tuned for 60 epochs, selecting the highest validation score.
There were three target tracking failures: two training and one validation.
All 63 target test clips tracked successfully. Raw full-vocabulary top-1 improved
from 39/63 to 56/63. Per-word candidate counts: HELP 13/13, I / ME 11/13,
YOU 11/12, NEED 9/12, WHERE 12/13.

The validation-selected 0.90 rejection gate correctly accepted 22/63 target test
clips, rejected 41, and made zero wrong accepted target predictions. One of 17
tracked negative test clips was falsely accepted. This small regression check
does not establish live-camera accuracy or independence from the base model's
historical training/evaluation data. No repeat tuning used the final test results.

In Words in motion, choose one of the five words in **20 everyday words**, then
enable landmark-processing consent and use the Beginner recording controls. The
selector also allows returning to the original ready vocabulary. This is an
opt-in experimental preview; it does not replace the existing model. Personal
training remains available when the candidate is not installed on a server.

The checkpoint and full reports remain outside the served website at
`../handspeak-training/essential-candidate.pt`. The backend loads that path by
default; set `HANDSPEAK_ESSENTIAL_MODEL` to use another private location, keeping
`essential-rejection-report.json` beside it. Restart the server after changes.
Aggregate results are in `reports/essential-words-training.json`.

Validation completed: three targeted tests (encoding parity and rejection guards),
headless Chrome interaction checks for all 20 cards, preview selection, preserved
consent, return to ready vocabulary, and mobile width. No browser page errors.
Actual webcam signing by the user remains untested.
