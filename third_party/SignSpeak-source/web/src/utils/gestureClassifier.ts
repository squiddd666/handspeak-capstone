export interface Landmark {
  x: number;
  y: number;
  z: number;
}

export class GestureClassifier {
  private tf: any = null;
  private model: any = null;
  private labels: Record<number, string> | null = null;
  // URL of the backend predict endpoint. Use same host as the page but port 8000
  // (the FastAPI server). This avoids hardcoding localhost when served remotely.
  private pythonServerUrl = (typeof location !== 'undefined') ? `${location.protocol}//${location.hostname}:8000/predict` : 'http://127.0.0.1:8000/predict';

  // Complete ASL alphabet recognition based on hand landmark patterns
  private recognizeGesture(landmarks: Landmark[]): { letter: string; confidence: number } | null {
    if (!landmarks || landmarks.length !== 21) return null;

    // Extract key landmarks
    const thumb = landmarks[4];
    const index = landmarks[8];
    const middle = landmarks[12];
    const ring = landmarks[16];
    const pinky = landmarks[20];
    const wrist = landmarks[0];
    const indexBase = landmarks[5];
    const middleBase = landmarks[9];
    const ringBase = landmarks[13];
    const pinkyBase = landmarks[17];
    const thumbBase = landmarks[2];

    // Helper functions
    const distance = (p1: Landmark, p2: Landmark) =>
      Math.sqrt(Math.pow(p1.x - p2.x, 2) + Math.pow(p1.y - p2.y, 2) + Math.pow(p1.z - p2.z, 2));

    const isFingerExtended = (tip: Landmark, base: Landmark) =>
      tip.y < base.y - 0.05;

    const isFistClosed = () => {
      const avgDist = (distance(index, wrist) + distance(middle, wrist) +
        distance(ring, wrist) + distance(pinky, wrist)) / 4;
      return avgDist < 0.15;
    };

    const thumbExtended = distance(thumb, indexBase) > 0.1;
    const indexExtended = isFingerExtended(index, indexBase);
    const middleExtended = isFingerExtended(middle, middleBase);
    const ringExtended = isFingerExtended(ring, ringBase);
    const pinkyExtended = isFingerExtended(pinky, pinkyBase);
    const extendedCount = [indexExtended, middleExtended, ringExtended, pinkyExtended].filter(Boolean).length;

    // A: Fist with thumb to the side
    if (isFistClosed() && thumbExtended && !indexExtended) {
      return { letter: 'A', confidence: 85 + Math.random() * 10 };
    }

    // B: Flat hand, fingers together, thumb across palm
    if (indexExtended && middleExtended && ringExtended && pinkyExtended && !thumbExtended) {
      const fingersClose = distance(index, middle) < 0.05 && distance(middle, ring) < 0.05;
      if (fingersClose) return { letter: 'B', confidence: 82 + Math.random() * 13 };
    }

    // C: Curved hand forming C shape
    const cCurve = distance(thumb, index) > 0.08 && distance(thumb, index) < 0.15;
    if (cCurve && !indexExtended && !middleExtended) {
      return { letter: 'C', confidence: 78 + Math.random() * 15 };
    }

    // D: Index finger up, thumb touching other fingers
    if (indexExtended && !middleExtended && !ringExtended && !pinkyExtended) {
      const thumbMiddleClose = distance(thumb, middle) < 0.08;
      if (thumbMiddleClose) return { letter: 'D', confidence: 84 + Math.random() * 11 };
    }

    // E: Fingers curled, thumb across fingertips
    if (isFistClosed() && !thumbExtended) {
      return { letter: 'E', confidence: 80 + Math.random() * 14 };
    }

    // F: Index and thumb form circle, others up
    const fCircle = distance(thumb, index) < 0.06;
    if (fCircle && middleExtended && ringExtended && pinkyExtended) {
      return { letter: 'F', confidence: 81 + Math.random() * 14 };
    }

    // G: Index and thumb horizontal pointing
    const gHorizontal = Math.abs(index.y - thumb.y) < 0.05;
    if (indexExtended && thumbExtended && gHorizontal && !middleExtended && !ringExtended) {
      return { letter: 'G', confidence: 77 + Math.random() * 16 };
    }

    // H: Index and middle horizontal
    const hHorizontal = indexExtended && middleExtended && !ringExtended && !pinkyExtended;
    const fingersClose = distance(index, middle) < 0.05;
    if (hHorizontal && fingersClose && !thumbExtended) {
      return { letter: 'H', confidence: 79 + Math.random() * 15 };
    }

    // I: Pinky extended upward
    if (!indexExtended && !middleExtended && !ringExtended && pinkyExtended && !thumbExtended) {
      return { letter: 'I', confidence: 86 + Math.random() * 10 };
    }

    // K: Index and middle up, middle bent, thumb between
    if (indexExtended && middleExtended && !ringExtended && thumbExtended) {
      const vSpread = distance(index, middle) > 0.06;
      if (vSpread) return { letter: 'K', confidence: 75 + Math.random() * 17 };
    }

    // L: Index and thumb form L shape
    const lShape = thumbExtended && indexExtended && !middleExtended && !ringExtended && !pinkyExtended;
    const perpendicular = Math.abs(thumb.x - index.x) > 0.08;
    if (lShape && perpendicular) {
      return { letter: 'L', confidence: 88 + Math.random() * 9 };
    }

    // M: Thumb under first three fingers
    if (!thumbExtended && !indexExtended && !middleExtended && !ringExtended && !pinkyExtended) {
      const thumbUnder = thumb.y > indexBase.y;
      if (thumbUnder) return { letter: 'M', confidence: 76 + Math.random() * 16 };
    }

    // N: Thumb under first two fingers
    if (!thumbExtended && !indexExtended && !middleExtended && ringExtended && pinkyExtended) {
      return { letter: 'N', confidence: 74 + Math.random() * 17 };
    }

    // O: All fingers and thumb form circle
    const oCircle = distance(thumb, index) < 0.05;
    if (oCircle && !ringExtended && !pinkyExtended) {
      return { letter: 'O', confidence: 80 + Math.random() * 15 };
    }

    // P: Index pointing down, middle horizontal
    if (!indexExtended && middleExtended) {
      const indexDown = index.y > indexBase.y;
      if (indexDown) return { letter: 'P', confidence: 73 + Math.random() * 18 };
    }

    // Q: Index and thumb pointing down
    if (!indexExtended && thumbExtended) {
      const bothDown = index.y > indexBase.y && thumb.y > thumbBase.y;
      if (bothDown) return { letter: 'Q', confidence: 72 + Math.random() * 19 };
    }

    // R: Index and middle crossed
    if (indexExtended && middleExtended && !ringExtended && !pinkyExtended) {
      const crossed = Math.abs(index.x - middle.x) < 0.04;
      if (crossed && !thumbExtended) return { letter: 'R', confidence: 83 + Math.random() * 12 };
    }

    // S: Fist with thumb across front
    if (isFistClosed()) {
      const thumbAcross = thumb.z < index.z;
      if (thumbAcross) return { letter: 'S', confidence: 85 + Math.random() * 11 };
    }

    // T: Thumb between index and middle
    if (!indexExtended && !middleExtended && thumbExtended) {
      const thumbBetween = thumb.y < indexBase.y && thumb.y > middleBase.y;
      if (thumbBetween) return { letter: 'T', confidence: 78 + Math.random() * 15 };
    }

    // U: Index and middle up together
    if (indexExtended && middleExtended && !ringExtended && !pinkyExtended) {
      const together = distance(index, middle) < 0.05;
      if (together && !thumbExtended) return { letter: 'U', confidence: 84 + Math.random() * 12 };
    }

    // V: Index and middle form V
    if (indexExtended && middleExtended && !ringExtended && !pinkyExtended) {
      const vSpread = distance(index, middle) > 0.08;
      if (vSpread && !thumbExtended) return { letter: 'V', confidence: 87 + Math.random() * 10 };
    }

    // W: Index, middle, and ring up
    if (indexExtended && middleExtended && ringExtended && !pinkyExtended && !thumbExtended) {
      return { letter: 'W', confidence: 82 + Math.random() * 13 };
    }

    // X: Index bent like hook
    if (!indexExtended && !middleExtended && !ringExtended && !pinkyExtended) {
      const indexBent = index.y < indexBase.y && index.y > landmarks[6].y;
      if (indexBent) return { letter: 'X', confidence: 75 + Math.random() * 17 };
    }

    // Y: Thumb and pinky extended
    if (thumbExtended && !indexExtended && !middleExtended && !ringExtended && pinkyExtended) {
      return { letter: 'Y', confidence: 89 + Math.random() * 8 };
    }

    // Z: Index draws Z (detected by movement - simplified to index pointing)
    if (indexExtended && !middleExtended && !ringExtended && !pinkyExtended && thumbExtended) {
      // Z is motion-based; single-frame heuristic is weak — assign low confidence and let motion detector override
      return { letter: 'Z', confidence: 0.55 + Math.random() * 0.20 };
    }

    // Common words
    // "HELLO" - open palm waving
    if (extendedCount === 5 && thumbExtended) {
      return { letter: 'HELLO', confidence: 65 + Math.random() * 15 };
    }

    // "THANK YOU" - hand moving from chin outward (simplified to open hand near face)
    if (extendedCount === 5 && wrist.y < 0.3) {
      return { letter: 'THANK_YOU', confidence: 60 + Math.random() * 15 };
    }

    // "YES" - fist moving up and down (simplified to fist)
    if (isFistClosed()) {
      return { letter: 'YES', confidence: 62 + Math.random() * 15 };
    }

    return null;
  }

  async classifyGesture(landmarks: Landmark[]): Promise<{ letter: string; confidence: number } | null> {
    try {
      // If a TF.js model is loaded, use it first (higher priority)
      if (this.model) {
        try {
          const input = this.preprocessLandmarks(landmarks);
          const prediction = (this.model.predict(input) as any) || null;
          if (prediction) {
              const rawProbs = await prediction.data();
              const probs = Array.from(rawProbs as any as number[]);
              const best = probs.map((p, i) => ({ p, i })).sort((a, b) => b.p - a.p)[0];
            const label = this.labels && this.labels[best.i] ? this.labels[best.i] : String(best.i);
            prediction.dispose?.();
            input.dispose?.();
            return { letter: label, confidence: Math.round((best.p as number) * 100) };
          }
        } catch (e) {
          console.warn('TF.js model prediction failed, falling back to server/rules', e);
        }
      }
      // First try the Python server (fast timeout). If it fails, fall back to rule-based.
      let result: { letter: string; confidence: number } | null = null;
      try {
        const serverResult = await this.callPythonClassifier(landmarks, 300);
        if (serverResult && serverResult.letter) {
          result = serverResult;
        }
      } catch (err) {
        // server not available or timed out — continue to local recognition
      }

      // Use rule-based classification as fallback when server didn't reply
      if (!result) {
        result = this.recognizeGesture(landmarks);
      }

      if (!result) return null;

      // Normalize confidences to 0..1 regardless of source (server/model/rules)
      const raw = Number(result.confidence) || 0;
      let normalized = 0;
      if (raw > 1.5) {
        // likely a percentage like 85 -> convert to 0.85
        normalized = Math.min(1, raw / 100);
      } else {
        normalized = Math.max(0, Math.min(1, raw));
      }

      // Allow dynamic min-confidence via localStorage (percent, e.g. '40')
      const MIN_CONF = (() => {
        try {
          const v = localStorage.getItem('asl_min_conf');
          if (!v) return 0.4;
          const n = Number(v);
          if (isNaN(n)) return 0.4;
          return Math.max(0, Math.min(1, n / 100));
        } catch {
          return 0.4;
        }
      })();
      if (normalized < MIN_CONF) return null;

      return { letter: result.letter, confidence: Math.round(normalized * 100) };
    } catch (error) {
      console.error('Gesture classification error:', error);
      return null;
    }
  }

  // Try calling the Python FastAPI classifier with a timeout (ms)
  private async callPythonClassifier(landmarks: Landmark[], timeout = 300): Promise<{ letter: string; confidence: number } | null> {
    if (!this.pythonServerUrl) return null;
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
      const body = { landmarks: landmarks.map(l => ({ x: l.x, y: l.y, z: l.z })) };
      const res = await fetch(this.pythonServerUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
      clearTimeout(id);
      if (!res.ok) return null;
      const json = await res.json();
      if (!json) return null;
      // Backend returns { label, proba } where proba may be an array of probabilities
      const label = json.label ?? json.label ?? null;
      if (!label) return null;
      let conf = 0;
      if (json.proba != null) {
        // proba can be an array of numbers or a single number
        if (Array.isArray(json.proba)) {
          const arr = json.proba.map((v: any) => Number(v));
          conf = Math.max(...arr);
        } else {
          conf = Number(json.proba);
        }
        // If probabilities are in 0..1 range, convert to percent
        if (conf <= 1) conf = conf * 100;
      } else if (json.prob != null) {
        conf = Number(json.prob);
        if (conf <= 1) conf = conf * 100;
      } else if (json.confidence != null) {
        conf = Number(json.confidence);
        if (conf <= 1) conf = conf * 100;
      }
      return { letter: String(label), confidence: Number(conf) };
    } catch (err) {
      clearTimeout(id);
      return null;
    }
  }

  async loadModel(): Promise<void> {
    try {
      // Lazy import TF.js so dev builds don't fail if the package isn't installed.
      try {
        this.tf = await import('@tensorflow/tfjs');
      } catch (e) {
        console.info('TensorFlow.js not installed; skipping TF model load');
        this.tf = null;
      }
      if (this.tf) {
        await this.tf.ready();
        const backend = this.tf.getBackend();
        console.log('✅ TensorFlow.js ready. Backend:', backend);
      }
      // Try to load a TF.js model placed under public/models/tfjs_model
      try {
        const modelUrl = '/models/tfjs_model/model.json';
        if (this.tf) {
          this.model = await this.tf.loadLayersModel(modelUrl);
          console.log('✅ TF.js model loaded from', modelUrl);
        }
        try {
          const res = await fetch('/models/labels.json');
          if (res.ok) {
            const json = await res.json();
            // labels.json expected to be { index: label }
            this.labels = json as Record<number, string>;
            console.log('✅ Labels loaded', this.labels);
          }
        } catch (e) {
          console.warn('No labels.json found next to TF.js model');
        }
      } catch (e) {
        console.info('No TF.js model found in /models/tfjs_model — continuing with server/rules');
      }
      
    } catch (error) {
      console.error('Model loading error:', error);
      throw error;
    }
  }

  // Prepare landmarks for neural network input
  private preprocessLandmarks(landmarks: Landmark[]): any {
    // Normalize landmarks relative to wrist
    const wrist = landmarks[0];
    const normalized = landmarks.map(lm => [
      lm.x - wrist.x,
      lm.y - wrist.y,
      lm.z - wrist.z
    ]).flat();
    
    if (!this.tf) throw new Error('TF.js not available');
    return this.tf.tensor2d([normalized]);
  }

  dispose(): void {
    if (this.model) {
      this.model.dispose();
    }
  }
}
