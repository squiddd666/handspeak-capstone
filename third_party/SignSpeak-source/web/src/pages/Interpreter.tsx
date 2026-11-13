import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Cpu, Loader2, Keyboard, Clock, Plus, Delete, CornerDownLeft } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { startCamera, startDetectLoop } from "@/lib/camera";
import { connect } from "@/engine/local";
import { setupOverlay, drawLandmarks } from "@/lib/overlay";
import { PageLayout } from "@/components/PageLayout";
import { PageHeader } from "@/components/PageHeader";

const Interpreter = () => {
  const navigate = useNavigate();

  const [predSign, setPredSign] = useState<string | null>(null);
  const [predProba, setPredProba] = useState<number | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [currentWord, setCurrentWord] = useState<string>("");
  const [wordLog, setWordLog] = useState<string[]>([]);

  const lastHandTimeRef = React.useRef(Date.now());
  const lastFullTextRef = React.useRef("");
  const videoRef = React.useRef<HTMLVideoElement>(null);
  const canvasRef = React.useRef<HTMLCanvasElement>(null);
  const overlayRef = React.useRef<HTMLCanvasElement>(null);
  const wsRef = React.useRef<ReturnType<typeof connect> | null>(null);
  const overlayCtxRef = React.useRef<CanvasRenderingContext2D | null>(null);

  useEffect(() => {
    let stopFrames: (() => void) | null = null;
    let stream: MediaStream | null = null;
    const video = videoRef.current;
    const overlay = overlayRef.current;
    if (!video || !overlay) return;

    const ws = connect("/ws/decoder", {
      onOpen: () => setIsConnected(true),
      onClose: () => setIsConnected(false),
      onError: () => setIsConnected(false),
      onMessage: (data) => {
        overlayCtxRef.current = overlayCtxRef.current ?? setupOverlay(video, overlay);
        drawLandmarks(overlayCtxRef.current, data.landmarks as number[][] | null, video);

        if (data.prediction) {
          setPredSign(String(data.prediction));
          lastHandTimeRef.current = Date.now();
        } else {
          setPredSign(null);
        }
        // Integer percent: unchanged values skip the 30×/s React re-render
        // a raw float confidence would trigger.
        setPredProba(
          data.confidence !== undefined && data.confidence !== null
            ? Math.round(Number(data.confidence) * 100)
            : null,
        );

        const mode = (data.mode || {}) as Record<string, unknown>;
        setCurrentWord(String(mode.current_word || ""));

        const fullText = String(mode.full_text || "");
        if (fullText !== lastFullTextRef.current) {
          lastFullTextRef.current = fullText;
          const completed = fullText.trim().split(/\s+/).filter(Boolean);
          if (completed.length) setWordLog(completed.reverse());
        }
      },
    });
    wsRef.current = ws;

    (async () => {
      try {
        stream = await startCamera(video);
        stopFrames = startDetectLoop({
          video,
          fps: 30,
          onFrame: (v) => ws.sendFrame(v),
        });
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : String(err);
        toast.error(`Camera access blocked or unavailable: ${message}`, { duration: 6000 });
      }
    })();

    return () => {
      stopFrames?.();
      stream?.getTracks().forEach((track) => track.stop());
      ws.close();
    };
  }, []);

  const addCurrentLetter = () => {
    if (predSign) {
      const letter = predSign.toUpperCase();
      setCurrentWord((prev) => prev + letter);
      toast.success(`Added letter: "${letter}"`);
    }
  };

  const deleteLastLetter = () => setCurrentWord((prev) => prev.slice(0, -1));

  const commitWord = () => {
    if (currentWord.trim()) {
      const w = currentWord.trim();
      setWordLog((prev) => [w, ...prev]);
      toast.success(`Completed word logged: "${w}"`);
      setCurrentWord("");
      wsRef.current?.sendJSON({ action: "reset" });
    }
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space") {
        e.preventDefault();
        addCurrentLetter();
      } else if (e.code === "Backspace") {
        deleteLastLetter();
      } else if (e.code === "Enter") {
        commitWord();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [predSign, currentWord]);

  useEffect(() => {
    const timer = setInterval(() => {
      if (currentWord.trim()) {
        const elapsed = Date.now() - lastHandTimeRef.current;
        if (elapsed > 2500) {
          const w = currentWord.trim();
          setWordLog((prev) => [w, ...prev]);
          toast.info(`Auto‑logged word: "${w}" (inactive hand)`);
          setCurrentWord("");
          wsRef.current?.sendJSON({ action: "reset" });
        }
      }
    }, 500);
    return () => clearInterval(timer);
  }, [currentWord]);

  return (
    <PageLayout onBack={() => navigate("/")} backAriaLabel="Back to home">
      <PageHeader
        title="AI Sign Interpreter"
        subtitle="Spell letters and build words in real‑time using American Sign Language (ASL)"
      />

      <div className="grid lg:grid-cols-2 gap-6 lg:gap-8">
        <section className="space-y-3">
          <h2 className="section-heading">Live Camera Feed</h2>
          <div className="relative aspect-video panel-card overflow-hidden border-2 border-primary shadow-md">
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
              style={{ transform: "scaleX(-1)" }}
            />
            <canvas ref={overlayRef} className="absolute inset-0 w-full h-full pointer-events-none" />
            <canvas ref={canvasRef} width={320} height={240} style={{ display: "none" }} />
          </div>
        </section>

        <section className="space-y-4 flex flex-col justify-between">
          <div className="space-y-4">
            <div className="stat-card flex flex-col justify-between min-h-[7rem]">
              <span className="stat-label">Current Letter</span>
              <div className="flex items-center justify-center flex-grow">
                <span className="text-5xl font-bold text-primary neon-text">{predSign ?? "—"}</span>
                {predSign && predProba !== null && (
                  <span className="text-sm text-muted-foreground ml-3">
                    ({predProba}%)
                  </span>
                )}
              </div>
            </div>

            <div className="stat-card flex flex-col justify-between min-h-[7rem]">
              <span className="stat-label">Current Word</span>
              <div className="flex items-center justify-center flex-grow">
                <span className="text-2xl sm:text-3xl font-mono font-bold tracking-widest text-primary break-all text-center px-2">
                  {currentWord || (
                    <span className="text-sm font-normal text-muted-foreground italic">Spelling…</span>
                  )}
                </span>
              </div>
            </div>

            <div className="stat-card flex flex-col">
              <span className="stat-label">Word Log</span>
              <div className="h-32 overflow-y-auto border border-border/40 rounded-lg p-3 bg-secondary/10 space-y-1">
                {wordLog.length > 0 ? (
                  wordLog.map((w, i) => (
                    <div
                      key={i}
                      className="text-md font-medium text-foreground border-b border-border/20 py-1 last:border-0 flex justify-between items-center gap-2"
                    >
                      <span className="truncate">{w}</span>
                      <span className="text-xs text-muted-foreground flex items-center gap-1 shrink-0">
                        <Clock className="w-3 h-3" /> Logged
                      </span>
                    </div>
                  ))
                ) : (
                  <div className="h-full flex items-center justify-center text-sm text-muted-foreground italic">
                    No words logged yet
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <Button
              onClick={addCurrentLetter}
              disabled={!predSign}
              variant="outline"
              size="lg"
              className="flex items-center justify-center gap-1.5 rounded-xl border-2 border-primary/30 hover:border-primary transition-all"
            >
              <Plus className="w-4 h-4" aria-hidden="true" />
              <span className="text-sm">Add</span>
            </Button>
            <Button
              onClick={deleteLastLetter}
              disabled={!currentWord}
              variant="outline"
              size="lg"
              className="flex items-center justify-center gap-1.5 rounded-xl border-2 border-primary/30 hover:border-primary transition-all"
            >
              <Delete className="w-4 h-4" aria-hidden="true" />
              <span className="text-sm">Delete</span>
            </Button>
            <Button
              onClick={commitWord}
              disabled={!currentWord.trim()}
              variant="outline"
              size="lg"
              className="flex items-center justify-center gap-1.5 rounded-xl border-2 border-primary/30 hover:border-primary transition-all"
            >
              <CornerDownLeft className="w-4 h-4" aria-hidden="true" />
              <span className="text-sm">Commit</span>
            </Button>
          </div>

          <div
            className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-center transition-all ${
              isConnected
                ? "bg-primary/10 border-primary/30 text-primary drop-shadow-[0_0_6px_hsl(var(--primary)/0.2)]"
                : "bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400"
            }`}
            role="status"
            aria-live="polite"
          >
            {isConnected ? (
              <>
                <Cpu className="w-4 h-4" aria-hidden="true" />
                <span className="text-sm font-semibold tracking-wide">On-device AI ready — works offline</span>
              </>
            ) : (
              <>
                <Loader2 className="w-4 h-4 animate-spin" aria-hidden="true" />
                <span className="text-sm font-semibold tracking-wide">Loading on-device AI model…</span>
              </>
            )}
          </div>
        </section>
      </div>

      <div className="info-panel flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="p-3 bg-primary/10 rounded-lg text-primary">
            <Keyboard className="w-6 h-6" aria-hidden="true" />
          </div>
          <div>
            <h3 className="font-semibold text-primary text-md">Controls</h3>
            <p className="text-sm text-muted-foreground">How to build words with the tap buttons</p>
          </div>
        </div>
        <div className="text-sm text-muted-foreground space-y-1.5 flex-grow sm:max-w-md w-full">
          <div className="flex justify-between gap-4 border-b border-border/40 pb-1">
            <span>Hold a sign steady (2s)</span>
            <span className="font-medium text-foreground shrink-0">Auto‑adds Letter</span>
          </div>
          <div className="flex justify-between gap-4 border-b border-border/40 pb-1">
            <span className="flex items-center gap-1.5">
              Tap{" "}
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-secondary border rounded text-xs font-semibold">
                <Plus className="w-3 h-3" aria-hidden="true" /> Add
              </span>
            </span>
            <span className="font-medium text-foreground shrink-0">Add Letter Instantly</span>
          </div>
          <div className="flex justify-between gap-4 border-b border-border/40 pb-1">
            <span className="flex items-center gap-1.5">
              Tap{" "}
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-secondary border rounded text-xs font-semibold">
                <Delete className="w-3 h-3" aria-hidden="true" /> Delete
              </span>
            </span>
            <span className="font-medium text-foreground shrink-0">Delete Last Letter</span>
          </div>
          <div className="flex justify-between gap-4 border-b border-border/40 pb-1">
            <span className="flex items-center gap-1.5">
              Tap{" "}
              <span className="inline-flex items-center gap-1 px-1.5 py-0.5 bg-secondary border rounded text-xs font-semibold">
                <CornerDownLeft className="w-3 h-3" aria-hidden="true" /> Commit
              </span>
            </span>
            <span className="font-medium text-foreground shrink-0">Save Word to Log</span>
          </div>
          <div className="flex justify-between gap-4">
            <span>Rest your hand (2.5s)</span>
            <span className="font-medium text-foreground shrink-0">Auto‑logs Current Word</span>
          </div>
        </div>
      </div>
    </PageLayout>
  );
};

export default Interpreter;
