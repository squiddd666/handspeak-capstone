# V8 private landmark artifact schema

Schema: handspeak-target20-browser-landmarks-v1. Generated only outside the
project tree under the private run's canonical-v1 directory. The index lists
every attempt, including cases with no submitted payload. A missing payload
never results in a fabricated landmark artifact.

- source: ASL Citizen archive member identifier, expected target label,
  source gloss, variant-review status, source-local participant identifier,
  license and permission evidence references, and SHA-256 of the actual source file.
- split: original validation assignment. Test material is rejected by the reader.
- extraction: pinned Holistic package and options, actual Chromium user-agent,
  frontend and harness SHA-256, 640×480 / 15 FPS input, preprocessing and
  warm-up policy. Pose indexes and 21-point hand contract are explicit.
- frames: original browser video clock timestamps in ms; 7 pose XYZ points,
  independent nullable left/right 21-point XYZ arrays and corresponding
  visibility booleans. The retimed virtual camera clock is retained as
  observed, not presented as original MP4 presentation timestamps.
- capture: application capture metadata plus QA source-window result.
- status: usable_development or excluded, with a reason when excluded.
- encoder: unchanged target20-mask-time-v6 contract.
- artifact_sha256: SHA-256 over the entire body without the hash field,
  using sorted compact UTF-8 JSON, with no NaN/Infinity allowed.

Reader verifies hashes, profile, split, shape, finite values, time order,
mask consistency, capture status and duration, V6 support and per-batch
source duplication. Excluded evidence is validated structurally but never
returns an encoding. Source hash is rechecked against the media file during
packaging. A repeated capture of the same source is permitted only in a
separate explicitly named reproducibility run and is not an independent example.

Implementation: target20_artifact_v8.py, training/extract_target20_v8.py and
training/test_target20_v8.py. Tests use mathematical fixtures and are not
recognition or capture evidence.
