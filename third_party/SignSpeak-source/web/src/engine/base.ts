/**
 * Shared per-session logic: sequence buffer + debounced commit.
 * Port of backend/sessions/_base.py.
 */
import type { HandLandmarker } from "@mediapipe/tasks-vision";
import type * as ort from "onnxruntime-web";
import { extract, type RawLandmarks } from "./landmarks";
import { predict, SEQ_LEN, FEATURES } from "./predictor";

export const BUFFER_SIZE = SEQ_LEN;
export const CONFIDENCE_THRESHOLD = 0.85;
// Time-based (not frame-based) so the hold feels identical on a 30fps laptop
// and a slower phone. Manual add (Add button / spacebar) bypasses this.
export const HOLD_TO_COMMIT_MS = 2000;

export interface FrameResult {
  landmarks: RawLandmarks | null;
  prediction: string | null;
  confidence: number;
  mode: Record<string, unknown>;
}

export type ControlMsg = Record<string, unknown>;

export abstract class BaseSession {
  protected buffer: Float32Array[] = [];
  protected consecutiveLetter: string | null = null;
  protected holdStartMs = 0;
  protected lastCommitted: string | null = null;

  constructor(
    protected landmarker: HandLandmarker,
    protected session: ort.InferenceSession,
  ) {}

  protected resetBuffer() {
    this.buffer = [];
    this.holdStartMs = 0;
    this.consecutiveLetter = null;
    this.lastCommitted = null;
  }

  /**
   * Run extraction + prediction + debounce for one frame.
   * `committed` fires once when the same letter is held steadily for
   * HOLD_TO_COMMIT_MS at confidence >= CONFIDENCE_THRESHOLD; resets on hand
   * release, letter change, or confidence drop.
   */
  protected async process(
    source: HTMLCanvasElement | HTMLVideoElement,
    timestampMs: number,
  ): Promise<{
    raw: RawLandmarks | null;
    prediction: string | null;
    confidence: number;
    committed: string | null;
  }> {
    const { raw, normalized } = extract(this.landmarker, source, timestampMs);

    if (normalized === null) {
      this.resetBuffer();
      return { raw: null, prediction: null, confidence: 0, committed: null };
    }

    this.buffer.push(normalized);
    if (this.buffer.length > BUFFER_SIZE) this.buffer.shift();

    let prediction: string | null = null;
    let confidence = 0;
    let committed: string | null = null;

    if (this.buffer.length === BUFFER_SIZE) {
      const seq = new Float32Array(BUFFER_SIZE * FEATURES);
      for (let i = 0; i < BUFFER_SIZE; i++) seq.set(this.buffer[i], i * FEATURES);
      [prediction, confidence] = await predict(this.session, seq);

      if (prediction !== null && confidence >= CONFIDENCE_THRESHOLD) {
        if (prediction !== this.consecutiveLetter) {
          this.consecutiveLetter = prediction;
          this.holdStartMs = timestampMs;
        }
        if (
          timestampMs - this.holdStartMs >= HOLD_TO_COMMIT_MS &&
          prediction !== this.lastCommitted
        ) {
          committed = prediction;
          this.lastCommitted = prediction;
        }
      } else {
        this.consecutiveLetter = null;
        this.holdStartMs = 0;
      }
    }

    return { raw, prediction, confidence, committed };
  }

  abstract processFrame(
    source: HTMLCanvasElement | HTMLVideoElement,
    timestampMs: number,
  ): Promise<FrameResult>;

  handleControl(_msg: ControlMsg): FrameResult | null {
    return null;
  }
}
