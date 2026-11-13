import React, { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { RotateCcw, HelpCircle, Trophy, TrendingUp, AlertTriangle, Cpu, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { startCamera, startDetectLoop } from "@/lib/camera";
import { connect } from "@/engine/local";
import { setupOverlay, drawLandmarks } from "@/lib/overlay";
import { PageLayout } from "@/components/PageLayout";
import { PageHeader } from "@/components/PageHeader";

const PracticeGame = () => {
  const navigate = useNavigate();

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayRef = useRef<HTMLCanvasElement | null>(null);
  const wsRef = useRef<ReturnType<typeof connect> | null>(null);
  const overlayCtxRef = useRef<CanvasRenderingContext2D | null>(null);
  const lastStatusRef = useRef<string>("playing");
  const prevHintsUsedRef = useRef<number>(0);

  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [predLetter, setPredLetter] = useState<string | null>(null);
  const [predProba, setPredProba] = useState<number | null>(null);

  const [score, setScore] = useState<number>(0);
  const [streak, setStreak] = useState<number>(0);
  const [wordMask, setWordMask] = useState<string>("");
  const [wrongGuesses, setWrongGuesses] = useState<string[]>([]);
  const [livesLeft, setLivesLeft] = useState<number>(6);
  const [maxLives, setMaxLives] = useState<number>(6);
  const [isGameOver, setIsGameOver] = useState<boolean>(false);
  const [isGameWon, setIsGameWon] = useState<boolean>(false);
  const [revealedWord, setRevealedWord] = useState<string | null>(null);
  const [hintsUsed, setHintsUsed] = useState<number>(0);
  const [maxHints, setMaxHints] = useState<number>(2);

  const wrongGuessesCount = maxLives - livesLeft;
  const hintsRemaining = Math.max(0, maxHints - hintsUsed);
  const hintDisabledReason = !isConnected
    ? "AI model still loading"
    : isGameOver
      ? "Start a new game to use hints"
      : hintsRemaining <= 0
        ? `${maxHints} hint${maxHints === 1 ? "" : "s"} already used`
        : null;
  const canUseHint = hintDisabledReason === null;

  const maskChars = wordMask ? wordMask.split(" ") : [];
  const guessedLetters = [
    ...wrongGuesses,
    ...maskChars.filter((ch) => ch !== "_"),
  ];

  const startNewGame = () => {
    wsRef.current?.sendJSON({ action: "new_game" });
    lastStatusRef.current = "playing";
    setIsGameOver(false);
    setIsGameWon(false);
    setRevealedWord(null);
    setHintsUsed(0);
    prevHintsUsedRef.current = 0;
    toast.info("New Hangman game started! Good luck!");
  };

  const useHint = () => {
    if (hintDisabledReason) {
      toast.info(hintDisabledReason);
      return;
    }
    wsRef.current?.sendJSON({ action: "hint" });
  };

  const applyGameMode = (mode: Record<string, unknown>) => {
    setWordMask(String(mode.word_mask || ""));
    setWrongGuesses((mode.wrong_guesses as string[]) || []);
    setLivesLeft(Number(mode.lives_left ?? 6));
    setMaxLives(Number(mode.max_lives ?? 6));
    const newHintsUsed = Number(mode.hints_used ?? 0);
    setMaxHints(Number(mode.max_hints ?? 2));
    if (newHintsUsed > prevHintsUsedRef.current) {
      toast.info("Hint used - a letter was revealed.", { duration: 2500 });
    }
    prevHintsUsedRef.current = newHintsUsed;
    setHintsUsed(newHintsUsed);

    const status = String(mode.status || "playing");
    if (status !== lastStatusRef.current) {
      if (status === "won") {
        setScore((prev) => prev + 1);
        setStreak((prev) => prev + 1);
        setIsGameOver(true);
        setIsGameWon(true);
        setRevealedWord(mode.word ? String(mode.word) : null);
        toast.success(`You guessed it! The word was "${mode.word}".`, { duration: 4000 });
      } else if (status === "lost") {
        setStreak(0);
        setIsGameOver(true);
        setIsGameWon(false);
        setRevealedWord(mode.word ? String(mode.word) : null);
        toast.error(`Game Over! The word was "${mode.word}".`, { duration: 4000 });
      }
      lastStatusRef.current = status;
    }
  };

  useEffect(() => {
    let stopFrames: (() => void) | null = null;
    let stream: MediaStream | null = null;
    const video = videoRef.current;
    const overlay = overlayRef.current;
    if (!video || !overlay) return;

    const ws = connect("/ws/hangman", {
      onOpen: () => {
        setIsConnected(true);
      },
      onClose: () => {
        setIsConnected(false);
      },
      onError: () => setIsConnected(false),
      onMessage: (data) => {
        overlayCtxRef.current = overlayCtxRef.current ?? setupOverlay(video, overlay);
        drawLandmarks(overlayCtxRef.current, data.landmarks as number[][] | null, video);

        if (data.prediction) {
          setPredLetter(String(data.prediction).toUpperCase());
        } else {
          setPredLetter(null);
        }
        // Integer percent: unchanged values skip the per-frame React re-render.
        setPredProba(
          data.confidence !== undefined && data.confidence !== null
            ? Math.round(Number(data.confidence) * 100)
            : null,
        );

        const mode = (data.mode || {}) as Record<string, unknown>;
        applyGameMode(mode);
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
      stopFrames?.();
      stream?.getTracks().forEach((track) => track.stop());
      ws.close();
    };
  }, []);

  return (
    <PageLayout onBack={() => navigate("/")} backAriaLabel="Back to home">
      <PageHeader
        title="Hangman Practice"
        subtitle="Spell the secret word by showing ASL gestures to your camera"
      />

      <div className="grid lg:grid-cols-2 gap-6 lg:gap-8">
        <section className="panel-card p-6 flex flex-col items-center justify-center min-h-[280px]">
          <h2 className="section-heading text-center">Hangman Scaffold</h2>

          <svg
            viewBox="0 0 200 250"
            className="w-full max-w-xs h-auto stroke-primary fill-none stroke-[5] drop-shadow-[0_0_8px_hsl(var(--primary)/0.6)]"
            aria-label={`Hangman drawing with ${wrongGuessesCount} wrong guesses`}
            role="img"
          >
            <line x1="20" y1="230" x2="180" y2="230" strokeLinecap="round" />
            <line x1="60" y1="230" x2="60" y2="20" strokeLinecap="round" />
            <line x1="60" y1="20" x2="140" y2="20" strokeLinecap="round" />
            <line x1="140" y1="20" x2="140" y2="50" strokeLinecap="round" />

            {wrongGuessesCount >= 1 && (
              <circle cx="140" cy="75" r="20" className="stroke-destructive drop-shadow-[0_0_8px_hsl(var(--destructive)/0.8)]" />
            )}
            {wrongGuessesCount >= 2 && (
              <line x1="140" y1="95" x2="140" y2="155" strokeLinecap="round" className="stroke-destructive drop-shadow-[0_0_8px_hsl(var(--destructive)/0.8)]" />
            )}
            {wrongGuessesCount >= 3 && (
              <line x1="140" y1="115" x2="110" y2="135" strokeLinecap="round" className="stroke-destructive drop-shadow-[0_0_8px_hsl(var(--destructive)/0.8)]" />
            )}
            {wrongGuessesCount >= 4 && (
              <line x1="140" y1="115" x2="170" y2="135" strokeLinecap="round" className="stroke-destructive drop-shadow-[0_0_8px_hsl(var(--destructive)/0.8)]" />
            )}
            {wrongGuessesCount >= 5 && (
              <line x1="140" y1="155" x2="115" y2="205" strokeLinecap="round" className="stroke-destructive drop-shadow-[0_0_8px_hsl(var(--destructive)/0.8)]" />
            )}
            {wrongGuessesCount >= 6 && (
              <line x1="140" y1="155" x2="165" y2="205" strokeLinecap="round" className="stroke-destructive drop-shadow-[0_0_8px_hsl(var(--destructive)/0.8)]" />
            )}
          </svg>
        </section>

        <section className="space-y-4">
          <h2 className="section-heading">Live Camera</h2>
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

            <div className="absolute top-4 left-4 z-40 stat-card py-2 px-3 shadow-lg bg-card/90 backdrop-blur-sm">
              <span className="stat-label mb-0 text-[10px]">Live Prediction</span>
              <span className="text-sm font-bold text-primary">
                {predLetter ? `${predLetter} (${predProba ?? 0}%)` : "-"}
              </span>
            </div>
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="stat-card">
          <span className="stat-label flex items-center gap-1.5">
            <Trophy className="w-3.5 h-3.5 text-primary" aria-hidden="true" /> Score
          </span>
          <span className="text-3xl font-bold text-primary neon-text">{score}</span>
        </div>

        <div className="stat-card">
          <span className="stat-label flex items-center gap-1.5">
            <AlertTriangle className="w-3.5 h-3.5 text-destructive" aria-hidden="true" /> Wrong Guesses
          </span>
          <span className={`text-3xl font-bold ${wrongGuessesCount > 4 ? "text-destructive" : "text-amber-500"}`}>
            {wrongGuessesCount} / {maxLives}
          </span>
        </div>

        <div className="stat-card">
          <span className="stat-label flex items-center gap-1.5">
            <TrendingUp className="w-3.5 h-3.5 text-green-500" aria-hidden="true" /> Streak
          </span>
          <span className="text-3xl font-bold text-green-500">{streak}</span>
        </div>
      </div>

      <div className="panel-card p-6 sm:p-8 flex flex-col items-center justify-center gap-2">
        <div className="flex flex-wrap justify-center gap-3 sm:gap-4 text-2xl sm:text-4xl md:text-5xl font-mono font-bold tracking-widest text-primary">
          {maskChars.length > 0 ? (
            maskChars.map((char, index) => (
              <span
                key={index}
                className={`border-b-4 pb-2 px-1 min-w-[1.5ch] text-center ${
                  isGameOver && char === "_" && !isGameWon
                    ? "border-destructive text-destructive"
                    : "border-primary"
                }`}
              >
                {char === "_" ? (isGameOver && revealedWord ? revealedWord[index] : "_") : char}
              </span>
            ))
          ) : (
            <span className="text-sm font-normal text-muted-foreground italic">Waiting for game…</span>
          )}
        </div>
      </div>

      <div className="stat-card">
        <span className="stat-label">Guessed Letters</span>
        <div className="flex flex-wrap gap-2 mt-1">
          {guessedLetters.length > 0 ? (
            [...new Set(guessedLetters)].map((l, idx) => {
              const inWord = maskChars.includes(l);
              return (
                <span
                  key={idx}
                  className={`inline-block px-2 py-0.5 rounded text-sm font-semibold ${
                    inWord
                      ? "bg-primary/20 text-primary border border-primary/30"
                      : "bg-destructive/20 text-destructive border border-destructive/30"
                  }`}
                >
                  {l}
                </span>
              );
            })
          ) : (
            <span className="text-sm font-normal text-muted-foreground italic">None yet</span>
          )}
        </div>
      </div>

      <div
        className={`flex items-center justify-center gap-2 p-3 rounded-xl border text-center transition-all ${
          isConnected
            ? "bg-primary/10 border-primary/30 text-primary drop-shadow-[0_0_6px_hsl(var(--primary)/0.2)]"
            : "bg-destructive/10 border-destructive/30 text-destructive drop-shadow-[0_0_6px_hsl(var(--destructive)/0.2)]"
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

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Button
          onClick={startNewGame}
          size="lg"
          variant="outline"
          className="flex items-center justify-center gap-2 rounded-xl border-2 border-primary/30 hover:border-primary hover:neon-glow focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-300"
        >
          <RotateCcw className="w-4 h-4" aria-hidden="true" /> New Game
        </Button>

        <Button
          onClick={useHint}
          disabled={!canUseHint}
          size="lg"
          variant="outline"
          aria-label={
            hintDisabledReason ??
            (hintsRemaining > 0
              ? `Use hint, ${hintsRemaining} remaining`
              : "No hints remaining")
          }
          title={hintDisabledReason ?? undefined}
          className="flex items-center justify-center gap-2 rounded-xl border-2 border-primary/30 hover:border-primary hover:neon-glow focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-all duration-300 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:border-primary/30 disabled:hover:neon-glow-none"
        >
          <HelpCircle className="w-4 h-4" aria-hidden="true" />
          Hint{hintsRemaining > 0 ? ` (${hintsRemaining} left)` : ""}
        </Button>
      </div>

      <p className="text-sm text-center text-muted-foreground">
        {hintDisabledReason ??
          (hintsRemaining > 0
          ? `You have ${hintsRemaining} hint${hintsRemaining === 1 ? "" : "s"} this round. Each hint reveals one random letter.`
          : "All hints used for this round.")}
      </p>

      <div className="panel-card p-6 sm:p-8 space-y-4">
        <h3 className="text-lg font-semibold text-primary">How to Play</h3>
        <ol className="text-sm sm:text-base text-muted-foreground space-y-3 list-decimal pl-5 leading-relaxed">
          <li>Show ASL letters with your hand gesture to the camera feed.</li>
          <li>The system detects your letters automatically when you hold the sign stable.</li>
          <li>Correct letters will fill in the blanks in the secret word.</li>
          <li>
            You can make up to <span className="font-semibold text-destructive">6 wrong guesses</span> before you lose.
          </li>
          <li>
            You can use up to <span className="font-semibold text-primary">2 hints</span> per round to reveal a random letter.
          </li>
          <li>Press &quot;New Game&quot; to start a fresh round from the server word list.</li>
        </ol>
      </div>
    </PageLayout>
  );
};

export default PracticeGame;
