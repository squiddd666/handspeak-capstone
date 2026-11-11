# Hand-landmark runtime/model attribution

The ONNX palm detector and 21-joint hand model are from OpenCV Zoo, at the
commit and SHA-256 hashes in `models/hand-landmarks/manifest.json`.
Upstream explicitly licenses all files in each corresponding model directory
under Apache-2.0. The original license notices are retained here.

Sources:
- https://github.com/opencv/opencv_zoo/tree/main/models/palm_detection_mediapipe
- https://github.com/opencv/opencv_zoo/tree/main/models/handpose_estimation_mediapipe

`onnx-hand-detector.js` is a modified browser/Canvas implementation of the
upstream preprocessing and coordinate transforms. It adds label-blind region
proposals and confidence-gated fresh ROI landmark inference, and uses proper
xyxy-box IoU NMS. Modified for HandSpeak on 11 November 2026.

ONNX Runtime Web 1.23.2 is loaded from its pinned npm distribution under the
MIT license: https://github.com/microsoft/onnxruntime/blob/v1.23.2/LICENSE.

MediaPipe Tasks Vision 0.10.22-rc.20250304 and its existing Google task asset
remain the primary detector. MediaPipe's Apache-2.0 notice is at
https://github.com/google-ai-edge/mediapipe/blob/master/LICENSE.
Do not mistake the classifier reference dataset's separate/partly unresolved
license status for the runtime or ONNX model licenses.

The evaluated TFJS and legacy Hands alternatives were not adopted as replacements.
