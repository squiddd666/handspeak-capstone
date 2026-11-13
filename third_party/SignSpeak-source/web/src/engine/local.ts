/**
 * Local on-device replacement for lib/ws.ts.
 * Mirrors the old WebSocket connection interface, but frames are processed
 * on-device (MediaPipe hand landmarks + ONNX LSTM) — no server involved.
 */
import { getLandmarker } from "./landmarks";
import { getPredictorSession } from "./predictor";
import { DecoderSession } from "./decoder";
import { PracticeSession } from "./practice";
import { HangmanSession } from "./hangman";
import type { BaseSession, FrameResult } from "./base";

export type LocalMessageHandler = (data: FrameResult) => void;

export interface LocalConnection {
  /** Process one (already mirrored) frame on-device. Drops frames while busy. */
  sendFrame: (source: HTMLCanvasElement | HTMLVideoElement) => void;
  sendJSON: (obj: Record<string, unknown>) => void;
  close: () => void;
}

export function connect(
  path: string,
  {
    onOpen,
    onMessage,
    onClose,
    onError,
  }: {
    onOpen?: () => void;
    onMessage?: LocalMessageHandler;
    onClose?: () => void;
    onError?: () => void;
  } = {},
): LocalConnection {
  let session: BaseSession | null = null;
  let closed = false;
  let busy = false;
  let pendingJSON: Record<string, unknown>[] | null = [];

  (async () => {
    try {
      const [landmarker, ortSession] = await Promise.all([
        getLandmarker(),
        getPredictorSession(),
      ]);
      if (closed) return;
      switch (path) {
        case "/ws/decoder":
          session = new DecoderSession(landmarker, ortSession);
          break;
        case "/ws/practice":
          session = new PracticeSession(landmarker, ortSession);
          break;
        case "/ws/hangman":
          session = new HangmanSession(landmarker, ortSession);
          break;
        default:
          throw new Error(`Unknown session path: ${path}`);
      }
      if (pendingJSON) {
        for (const msg of pendingJSON) {
          const result = session.handleControl(msg);
          if (result && !closed) onMessage?.(result);
        }
        pendingJSON = null;
      }
      onOpen?.();
    } catch (err) {
      console.error("Local engine init failed:", err);
      if (!closed) onError?.();
    }
  })();

  return {
    sendFrame: (source) => {
      if (closed || !session || busy) return;
      busy = true;
      session
        .processFrame(source, performance.now())
        .then((result) => {
          if (!closed) onMessage?.(result);
        })
        .catch((err) => console.error("Frame processing failed:", err))
        .finally(() => {
          busy = false;
        });
    },
    sendJSON: (obj) => {
      if (closed) return;
      if (session) {
        const result = session.handleControl(obj);
        if (result) onMessage?.(result);
      } else if (pendingJSON) {
        pendingJSON.push(obj);
      }
    },
    close: () => {
      if (closed) return;
      closed = true;
      // The landmarker/ONNX session singletons are intentionally kept alive for
      // reuse across pages; only the per-mode session state is dropped.
      session = null;
      onClose?.();
    },
  };
}
