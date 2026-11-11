# Kai motion reconstructed from the displayed reference

All **40 currently listed Watch & practice words with a local reference video**
have a separate `*-reference.glb`. These take priority **only when that exact
reference file is being displayed**. BYE, MY, BUY and other words without a local
reference retain the existing captured/hand-authored demo. The 47-word catalog,
reference recordings and camera-recognition models are unchanged.

This fixes pairing a PopSign/ASL Citizen recording with an unrelated Studio Galt
performance or a generic authored animation. In particular, a one-handed/left-
handed variant is no longer replaced by a two-handed/right-handed performance.

## Reconstruction and limitations

- MediaPipe pose wrists, classifier evidence and temporal continuity identify
  **anatomical left/right hands**. Screen X is not a hand identifier: hands can cross.
- Detected finger segments, including the thumb, and each palm orientation are
  reconstructed independently in 3D, with Kai's original joint-roll calibration.
- Image-space wrist paths are anchored to the chest/face. Two-bone IK preserves
  Kai's fixed arm lengths. No root translation, leg motion or mesh replacement.
- The video is the single playback clock, including slow motion, replay, pause,
  seeking and looping. A mismatched/missing/corrupt reconstruction falls back to
  the previous demo rather than borrowing another video's fingers.
- Monocular depth and occluded/blurred fingers are **estimates**, not certified
  ASL motion capture or independently verified instruction. `index.json` records
  hand coverage, estimated gaps and reach clamping; the player identifies
  reconstructed 3D and flags clips needing review. Use the recording/lesson to
  verify the sign. DRAG, EDIT, GO and HOME have lower tracking coverage.
- MICROSCOPE's supporting left hand is visible but entirely missed by both hand
  tracking and the pose wrist. Frame-by-frame review of that exact video restores
  its forearm-cupping support, plus the dominant C hand's eye contact on Kai's
  different proportions. The supporting palm/depth/occluded finger curls remain
  **estimated** and are flagged for review, never counted as tracked observations.
  The hash-locked timestamps and contact parameters are recorded in
  `scripts/kai-reference-corrections.json` and the GLB/index metadata. This reviewed
  exception does not activate a second hand in other one-handed recordings.

## Provenance and licence

The index and each GLB include the exact reference path/SHA-256, Kai model hash,
task-model URLs/hashes, tracking versions and reconstruction method. Every output
contains only Kai-native rotation tracks and rig nodes; **`signer.glb` is untouched**.
The verified CC0 HELLO frame-zero pose is used only as the unseen-hand rest fallback.

Reference recordings remain credited in [`../../signs/README.md`](../../signs/README.md)
and its source manifests. PopSign-derived motion follows its CC BY 4.0 terms;
ASL Citizen-derived motion remains subject to that dataset's research-use terms.
This is not a CC0 re-licensing of those recordings or their derived motion.
Kai remains separately CC BY 4.0, credited to VTubeMe.

## Reproduce locally

```powershell
python -X utf8 scripts/extract_reference_motion.py
& 'C:\Program Files\Blender Foundation\Blender 4.5\blender.exe' --background --factory-startup --python scripts/retarget_reference_motion.py --
node --test training/test_kai_reference.mjs training/test_kai_mocap.mjs training/test_watch_practice.mjs
python -X utf8 -m unittest training.test_kai_mocap_http training.test_reference_tracking
```

Extraction downloads the official pose/hand task models into git-ignored
`asl-cache/kai-reference/`; videos and landmarks are never uploaded. Cached
landmarks allow rebaking without repeating detection. `--ids` limits either
script to selected words; `--all-local` on the Blender script additionally exports
reference videos not currently listed in Watch & practice.
