/** Port of backend/sessions/decoder.py. */
import { BaseSession, type ControlMsg, type FrameResult } from "./base";

const NO_HAND_FOR_SPACE_S = 5.0;

export class DecoderSession extends BaseSession {
  private currentWord = "";
  private fullText = "";
  private lastHandTs = Date.now() / 1000;

  async processFrame(
    source: HTMLCanvasElement | HTMLVideoElement,
    timestampMs: number,
  ): Promise<FrameResult> {
    const { raw, prediction, confidence, committed } = await this.process(
      source,
      timestampMs,
    );
    const now = Date.now() / 1000;
    const handPresent = raw !== null;

    if (handPresent) this.lastHandTs = now;
    if (committed !== null) this.currentWord += committed;

    const noHandSeconds = handPresent ? 0 : now - this.lastHandTs;
    if (noHandSeconds >= NO_HAND_FOR_SPACE_S && this.currentWord) {
      this.fullText += this.currentWord + " ";
      this.currentWord = "";
      this.lastHandTs = now; // reset so we don't fire repeatedly
    }

    return {
      landmarks: raw,
      prediction,
      confidence,
      mode: {
        current_word: this.currentWord,
        full_text: this.fullText,
        hand_present: handPresent,
        no_hand_seconds: Math.round(noHandSeconds * 10) / 10,
      },
    };
  }

  handleControl(msg: ControlMsg): FrameResult | null {
    if (msg.action === "reset") {
      this.currentWord = "";
      this.fullText = "";
      this.lastHandTs = Date.now() / 1000;
      return {
        landmarks: null,
        prediction: null,
        confidence: 0,
        mode: {
          current_word: "",
          full_text: "",
          hand_present: false,
          no_hand_seconds: 0,
        },
      };
    }
    return null;
  }
}
