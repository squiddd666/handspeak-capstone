import { useNavigate, useParams } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { startCamera, startDetectLoop } from "@/lib/camera";
import { connect } from "@/engine/local";
import { setupOverlay, drawLandmarks } from "@/lib/overlay";
import { PageLayout } from "@/components/PageLayout";
import { PageHeader } from "@/components/PageHeader";
import { ReferenceImage } from "@/components/ReferenceImage";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

const signDescriptions: Record<string, string> = {
  A: "Make a fist with thumb alongside",
  B: "Fingers together pointing up, thumb across palm",
  C: "Curved hand forming C shape",
  D: "Index finger up, other fingers touch thumb",
  E: "All fingertips touching thumb",
  F: "Index and thumb touching in circle, other fingers up",
  G: "Index finger and thumb pointing forward",
  H: "Index and middle finger extended sideways",
  I: "Pinky finger extended up",
  J: "Draw a J with pinky finger",
  K: "Index and middle finger up, thumb between them",
  L: "Thumb and index forming L shape",
  M: "Thumb under three fingers",
  N: "Thumb under two fingers",
  O: "All fingertips touching in circle",
  P: "Like K but pointing down",
  Q: "Index finger and thumb pointing down",
  R: "Index and middle fingers crossed",
  S: "Fist with thumb across fingers",
  T: "Thumb between index and middle",
  U: "Index and middle fingers together, pointing up",
  V: "Index and middle fingers apart, pointing up",
  W: "Three fingers up and apart",
  X: "Index finger curved like a hook",
  Y: "Thumb and pinky extended",
  Z: "Draw a Z with index finger",
};

const feedbackStyles: Record<string, string> = {
  "Great!": "border-green-500/40 bg-green-500/10 text-green-600 dark:text-green-400",
  Different: "border-amber-500/40 bg-amber-500/10 text-amber-600 dark:text-amber-400",
  "Very different": "border-destructive/40 bg-destructive/10 text-destructive",
};

const Practice = () => {
  const navigate = useNavigate();
  const { letter } = useParams();
  const targetLetter = String(letter || "").toUpperCase();
  const description = letter ? signDescriptions[targetLetter] : "";
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayRef = useRef<HTMLCanvasElement | null>(null);
  const wsRef = useRef<ReturnType<typeof connect> | null>(null);
  const overlayCtxRef = useRef<CanvasRenderingContext2D | null>(null);
  const completedRef = useRef(false);

  const [predSign, setPredSign] = useState<string | null>(null);
  const [predProba, setPredProba] = useState<number | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);
  const [holdProgress, setHoldProgress] = useState<number>(0);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    completedRef.current = false;
    setIsComplete(false);
    let stopFrames: (() => void) | null = null;
    let stream: MediaStream | null = null;
    const video = videoRef.current;
    const overlay = overlayRef.current;
    if (!video || !overlay || !targetLetter) return;

    const ws = connect("/ws/practice", {
      onOpen: () => {
        setIsConnected(true);
        ws.sendJSON({ action: "start", letter: targetLetter });
      },
      onClose: () => setIsConnected(false),
      onError: () => setIsConnected(false),
      onMessage: (data) => {
        overlayCtxRef.current = overlayCtxRef.current ?? setupOverlay(video, overlay);
        drawLandmarks(overlayCtxRef.current, data.landmarks as number[][] | null, video);

        if (completedRef.current) {
          return;
        }

        const prediction = data.prediction ? String(data.prediction) : null;
        const confidence = data.confidence !== undefined ? Number(data.confidence) : 0;
        setPredSign(prediction);
        // Integer percent: unchanged values skip the per-frame React re-render.
        setPredProba(confidence > 0 ? Math.round(confidence * 100) : null);

        const mode = (data.mode || {}) as Record<string, unknown>;

        const progress = Number(mode.hold_progress ?? 0);
        setHoldProgress(progress);

        const isCorrect = prediction === targetLetter && confidence > 0.6;
        if (mode.success) {
          completedRef.current = true;
          setIsComplete(true);
          setHoldProgress(1);
          setFeedback("Great!");
          ws.sendJSON({ action: "reset" });
          toast.success("🎉 Great Job! Practice session complete.", {
            id: "practice-session-complete",
            duration: 5000,
          });
        } else if (isCorrect) {
          setFeedback("Great!");
        } else if (prediction && confidence > 0.5) {
          setFeedback("Different");
        } else if (prediction) {
          setFeedback("Very different");
        } else {
          setFeedback(null);
        }
      },
    });
    wsRef.current = ws;

    (async () => {
      try {
        stream = await startCamera(video);
        setCameraError(null);
        stopFrames = startDetectLoop({
          video,
          fps: 30,
          onFrame: (v) => ws.sendFrame(v),
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        setCameraError("Camera access blocked or unavailable");
        toast.error(`Camera access blocked or unavailable: ${message}`);
      }
    })();

    return () => {
      ws.sendJSON({ action: "reset" });
      stopFrames?.();
      stream?.getTracks().forEach((track) => track.stop());
      ws.close();
    };
  }, [targetLetter]);

  const feedbackLabel =
    feedback === "Great!"
      ? "Great match!"
      : feedback === "Different"
        ? "Close — adjust shape"
        : feedback === "Very different"
          ? "Try again"
          : "Show the sign";

  return (
    <PageLayout onBack={() => navigate("/guide")} backAriaLabel="Back to guide">
      <PageHeader
        title={`Practice Letter ${targetLetter}`}
        subtitle="Hold the sign steady inside the guide box until the hold timer completes"
      />

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="stat-card text-center">
          <span className="stat-label">Target Letter</span>
          <span className="text-4xl sm:text-5xl font-bold text-primary neon-text">{targetLetter}</span>
        </div>

        <div className="stat-card text-center">
          <span className="stat-label">Live Prediction</span>
          <span className="text-4xl sm:text-5xl font-bold text-foreground">{predSign ?? "—"}</span>
        </div>

        <div className="stat-card text-center">
          <span className="stat-label">Confidence</span>
          <span className="text-4xl sm:text-5xl font-bold text-foreground">
            {predProba !== null ? `${predProba}%` : "—"}
          </span>
        </div>

        <div
          className={cn(
            "stat-card text-center border-2 transition-colors",
            feedback ? feedbackStyles[feedback] : "border-border",
          )}
          role="status"
          aria-live="polite"
        >
          <span className="stat-label">Feedback</span>
          <span className="text-base sm:text-lg font-semibold">{feedbackLabel}</span>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-6 lg:gap-8">
        <section className="space-y-4">
          <h2 className="section-heading">Reference Sign</h2>
          <ReferenceImage letter={targetLetter} frameClassName="min-h-[280px] lg:min-h-[320px]" />
          {description && (
            <p className="text-sm sm:text-base text-muted-foreground text-center px-2">{description}</p>
          )}
        </section>

        <section className="space-y-4">
          <h2 className="section-heading">Your Practice</h2>
          <div className="relative aspect-video panel-card overflow-hidden border-2 border-primary shadow-md">
            <video
              ref={videoRef}
              className="w-full h-full object-cover"
              playsInline
              muted
              autoPlay
              style={{ transform: "scaleX(-1)" }}
            />
            <canvas ref={overlayRef} className="absolute inset-0 w-full h-full pointer-events-none" />
            {cameraError && (
              <div className="absolute inset-0 z-40 flex items-center justify-center bg-black/60 text-white text-base sm:text-lg px-4 text-center">
                {cameraError}
              </div>
            )}

            <div className="absolute inset-0 flex items-center justify-center p-6 sm:p-8 pointer-events-none">
              <div className="w-48 h-48 sm:w-56 sm:h-56 guide-box rounded-2xl" />
            </div>
          </div>

          <div className="stat-card space-y-2">
            <div className="flex justify-between items-center text-sm">
              <span className="stat-label mb-0">Hold Progress</span>
              <span className="text-muted-foreground font-mono">
                {isComplete ? "5.0 / 5.0s" : `${(holdProgress * 5).toFixed(1)} / 5.0s`}
              </span>
            </div>
            <Progress
              value={isComplete ? 100 : holdProgress * 100}
              className="h-2"
              aria-label="Hold progress"
            />
            <p className="text-xs sm:text-sm text-muted-foreground text-center">
              {isComplete
                ? "🎉 Great Job! Practice session complete."
                : isConnected
                  ? "Match your hand gesture with the reference sign above."
                  : "Loading on-device AI model…"}
            </p>
          </div>
        </section>
      </div>
    </PageLayout>
  );
};

export default Practice;
