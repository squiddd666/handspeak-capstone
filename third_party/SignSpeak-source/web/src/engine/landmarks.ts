/**
 * On-device hand landmark extraction via MediaPipe Tasks Vision.
 * Port of backend/inference/landmarks.py — the normalization here must stay
 * identical to the Python version the model was trained with.
 */
import { FilesetResolver, HandLandmarker } from "@mediapipe/tasks-vision";

export type RawLandmarks = number[][]; // (21, 3) image-relative 0..1 coords

let landmarkerPromise: Promise<HandLandmarker> | null = null;

async function createLandmarker(delegate: "GPU" | "CPU"): Promise<HandLandmarker> {
  const fileset = await FilesetResolver.forVisionTasks("/wasm");
  return HandLandmarker.createFromOptions(fileset, {
    baseOptions: { modelAssetPath: "/models/hand_landmarker.task", delegate },
    runningMode: "VIDEO",
    numHands: 1,
    minHandDetectionConfidence: 0.5,
    minTrackingConfidence: 0.5,
  });
}

/** Lazily create the singleton HandLandmarker (wasm + model served locally for offline use). */
export function getLandmarker(): Promise<HandLandmarker> {
  if (!landmarkerPromise) {
    // GPU delegate keeps the ~30 Hz landmark inference off the main CPU thread
    // (the difference between "extremely slow" and smooth on phones). Some
    // WebViews can't init it, so fall back to CPU.
    landmarkerPromise = createLandmarker("GPU").catch((err) => {
      console.warn("GPU delegate unavailable, falling back to CPU:", err);
      return createLandmarker("CPU");
    });
    landmarkerPromise.catch(() => {
      landmarkerPromise = null; // allow retry after a failed load
    });
  }
  return landmarkerPromise;
}

/**
 * Extract landmarks from a raw (unmirrored) camera frame source.
 * Returns { raw, normalized } like the Python extractor, or nulls when no hand.
 *
 * Detection runs directly on the video element (no intermediate canvas copy —
 * that per-frame copy + readback was a major mobile bottleneck). The training
 * pipeline mirrored frames with cv2.flip(frame, 1), so we mirror by flipping
 * landmark x afterwards, which yields the same geometry far cheaper.
 */
export function extract(
  landmarker: HandLandmarker,
  source: HTMLCanvasElement | HTMLVideoElement,
  timestampMs: number,
): { raw: RawLandmarks | null; normalized: Float32Array | null } {
  const result = landmarker.detectForVideo(source, timestampMs);
  const hand = result.landmarks?.[0];
  if (!hand || hand.length < 21) return { raw: null, normalized: null };
  const raw: RawLandmarks = hand.map((lm) => [1 - lm.x, lm.y, lm.z]);
  return { raw, normalized: normalize(raw) };
}

/**
 * Translate by wrist, scale by wrist→middle-finger-MCP distance.
 * Returns flat (63,) Float32Array or null. Mirrors backend normalize().
 */
export function normalize(landmarks: RawLandmarks): Float32Array | null {
  const [wx, wy, wz] = landmarks[0];
  const centered = landmarks.map(([x, y, z]) => [x - wx, y - wy, z - wz]);
  const [mx, my, mz] = centered[9];
  const scale = Math.sqrt(mx * mx + my * my + mz * mz);
  if (scale < 1e-6) return null;
  const out = new Float32Array(63);
  for (let i = 0; i < 21; i++) {
    out[i * 3] = centered[i][0] / scale;
    out[i * 3 + 1] = centered[i][1] / scale;
    out[i * 3 + 2] = centered[i][2] / scale;
  }
  return out;
}
