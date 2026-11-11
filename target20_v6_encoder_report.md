# Target-20 V6 mask-aware encoder

Implemented in target20_encoder_v6.py as target20-mask-time-v6. V3 tensors, inference, threshold, and checkpoints are unchanged. V6 has no compatible trained model. Feeding its representation to V3 would be invalid.

Legacy issue: the motion-peak crop sees differences between a real hand coordinate and zero before masking. V6 instead trims only idle edges using the union of observed hand timestamps; it does not infer sign completion or crop on a motion peak. Coordinates use median shoulder midpoint and shoulder span to keep them body-relative without per-frame normalization jitter. Left/right visibility is independent. XY, visibility, velocity, and velocity validity are explicit arrays; an invalid zero is padding, never an observation.

A visibility break or a source gap over 200 ms starts a new segment. Interpolation and velocities stay within a single segment, even when the gap lies between adjacent output samples. Source timestamps remain intact. The encoder rejects malformed landmarks, duplicate or backward timestamps, degenerate shoulder scale, fewer than 8 visible-hand frames, insufficient active interval continuity, and sparse resampled support. These are engineering guards, not a classifier gate or a trained optimum.

In local opt-in QA, HANDSPEAK_TARGET20_V6_DIAGNOSTICS=1 appends only an aggregate encoder status to existing Target-20 API responses. The frontend's real captured payload is used; no alternate V6 prediction is returned. Capture failures, encoder rejects, and V3 model outcomes are distinct.
