/** Port of backend/sessions/practice.py. */
import {
  BaseSession,
  CONFIDENCE_THRESHOLD,
  type ControlMsg,
  type FrameResult,
} from "./base";

const SUCCESS_HOLD_S = 5.0;

export class PracticeSession extends BaseSession {
  private targetLetter: string | null = null;
  private holdStartTs: number | null = null;
  private success = false;

  async processFrame(
    source: HTMLCanvasElement | HTMLVideoElement,
    timestampMs: number,
  ): Promise<FrameResult> {
    const { raw, prediction, confidence } = await this.process(source, timestampMs);
    const now = Date.now() / 1000;
    let holdProgress = 0;

    if (this.targetLetter !== null && !this.success) {
      const matching =
        prediction === this.targetLetter && confidence >= CONFIDENCE_THRESHOLD;
      if (matching) {
        if (this.holdStartTs === null) this.holdStartTs = now;
        holdProgress = Math.min((now - this.holdStartTs) / SUCCESS_HOLD_S, 1.0);
        if (holdProgress >= 1.0) this.success = true;
      } else {
        this.holdStartTs = null;
      }
    }

    return {
      landmarks: raw,
      prediction,
      confidence,
      mode: {
        target_letter: this.targetLetter,
        hold_progress: Math.round(holdProgress * 1000) / 1000,
        success: this.success,
      },
    };
  }

  handleControl(msg: ControlMsg): FrameResult | null {
    const action = msg.action;
    if (action === "start") {
      const letter = String(msg.letter ?? "").toUpperCase();
      if (letter.length === 1 && /[A-Z]/.test(letter)) {
        this.targetLetter = letter;
        this.holdStartTs = null;
        this.success = false;
        this.resetBuffer();
      }
    } else if (action === "reset" || action === "next") {
      this.targetLetter = null;
      this.holdStartTs = null;
      this.success = false;
    }
    return null;
  }
}
