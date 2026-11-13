/** Port of backend/sessions/hangman.py (word list from backend/assets/words.txt). */
import { BaseSession, type ControlMsg, type FrameResult } from "./base";

const WORDS = [
  "HELLO", "WORLD", "SIGN", "HAND", "LOVE", "PEACE", "LIGHT", "SOUND",
  "WATER", "MUSIC", "RIVER", "HOUSE", "PAPER", "NIGHT", "DREAM", "HEART",
  "SMILE", "FRIEND", "GARDEN", "WINDOW",
];

const MAX_WRONG = 6;
const MAX_HINTS = 2;

export class HangmanSession extends BaseSession {
  private word = "";
  private revealed: string[] = [];
  private wrongGuesses: string[] = [];
  private guessed = new Set<string>();
  private lastGuess: string | null = null;
  private status: "playing" | "won" | "lost" = "playing";
  private hintsUsed = 0;
  private started = false;

  private newGame() {
    this.word = WORDS[Math.floor(Math.random() * WORDS.length)];
    this.revealed = Array.from(this.word, () => "_");
    this.wrongGuesses = [];
    this.guessed = new Set();
    this.lastGuess = null;
    this.status = "playing";
    this.hintsUsed = 0;
    this.resetBuffer();
  }

  private ensureGame() {
    if (!this.started) {
      this.newGame();
      this.started = true;
    }
  }

  private modePayload(): Record<string, unknown> {
    return {
      word_mask: this.revealed.join(" "),
      wrong_guesses: this.wrongGuesses,
      lives_left: MAX_WRONG - this.wrongGuesses.length,
      max_lives: MAX_WRONG,
      last_guess: this.lastGuess,
      status: this.status,
      word: this.status !== "playing" ? this.word : null,
      hints_used: this.hintsUsed,
      max_hints: MAX_HINTS,
    };
  }

  private controlResponse(): FrameResult {
    return {
      landmarks: null,
      prediction: null,
      confidence: 0,
      mode: this.modePayload(),
    };
  }

  async processFrame(
    source: HTMLCanvasElement | HTMLVideoElement,
    timestampMs: number,
  ): Promise<FrameResult> {
    this.ensureGame();
    const { raw, prediction, confidence, committed } = await this.process(
      source,
      timestampMs,
    );

    if (committed && this.status === "playing" && !this.guessed.has(committed)) {
      this.guessed.add(committed);
      this.lastGuess = committed;
      if (this.word.includes(committed)) {
        for (let i = 0; i < this.word.length; i++) {
          if (this.word[i] === committed) this.revealed[i] = committed;
        }
        if (!this.revealed.includes("_")) this.status = "won";
      } else {
        this.wrongGuesses.push(committed);
        if (this.wrongGuesses.length >= MAX_WRONG) this.status = "lost";
      }
    }

    return {
      landmarks: raw,
      prediction,
      confidence,
      mode: this.modePayload(),
    };
  }

  handleControl(msg: ControlMsg): FrameResult | null {
    this.ensureGame();
    const action = msg.action;
    if (action === "new_game") {
      this.newGame();
      return this.controlResponse();
    }
    if (action === "hint") {
      if (this.status !== "playing" || this.hintsUsed >= MAX_HINTS) {
        return this.controlResponse();
      }
      const unrevealed: number[] = [];
      this.revealed.forEach((ch, i) => {
        if (ch === "_") unrevealed.push(i);
      });
      if (unrevealed.length === 0) return this.controlResponse();
      const idx = unrevealed[Math.floor(Math.random() * unrevealed.length)];
      const letter = this.word[idx];
      this.revealed[idx] = letter;
      this.guessed.add(letter);
      this.hintsUsed += 1;
      this.lastGuess = letter;
      if (!this.revealed.includes("_")) this.status = "won";
      return this.controlResponse();
    }
    return null;
  }
}
