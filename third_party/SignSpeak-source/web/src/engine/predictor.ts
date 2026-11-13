/**
 * On-device LSTM inference via onnxruntime-web.
 * Port of backend/inference/predictor.py — runs the exported asl.onnx model.
 */
// wasm-only entry: avoids bundling the (unused) 26 MB WebGPU/JSEP runtime.
import * as ort from "onnxruntime-web/wasm";

export const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

export const SEQ_LEN = 30;
export const FEATURES = 63;

// The wasm binary is bundled by vite (import.meta.url resolution), so inference
// is fully offline. Single thread: SharedArrayBuffer is unavailable in the
// Android WebView without cross-origin isolation, and the model is tiny anyway.
ort.env.wasm.numThreads = 1;

let sessionPromise: Promise<ort.InferenceSession> | null = null;

export function getPredictorSession(): Promise<ort.InferenceSession> {
  if (!sessionPromise) {
    sessionPromise = ort.InferenceSession.create("/models/asl.onnx", {
      executionProviders: ["wasm"],
    });
    sessionPromise.catch(() => {
      sessionPromise = null; // allow retry after a failed load
    });
  }
  return sessionPromise;
}

function softmax(logits: Float32Array): Float32Array {
  let max = -Infinity;
  for (const v of logits) if (v > max) max = v;
  let sum = 0;
  const out = new Float32Array(logits.length);
  for (let i = 0; i < logits.length; i++) {
    out[i] = Math.exp(logits[i] - max);
    sum += out[i];
  }
  for (let i = 0; i < out.length; i++) out[i] /= sum;
  return out;
}

/** sequence: flat (30*63,) Float32Array -> [letter, confidence] or [null, 0]. */
export async function predict(
  session: ort.InferenceSession,
  sequence: Float32Array,
): Promise<[string | null, number]> {
  const input = new ort.Tensor("float32", sequence, [1, SEQ_LEN, FEATURES]);
  const outputs = await session.run({ input });
  const logits = outputs.logits.data as Float32Array;
  const probs = softmax(logits);
  let idx = 0;
  for (let i = 1; i < probs.length; i++) if (probs[i] > probs[idx]) idx = i;
  return [LETTERS[idx], probs[idx]];
}
