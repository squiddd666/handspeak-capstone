/* slr.js: browser port of the Épée benchmark classifier.
 *
 * Faithful to bench_signer_generalization.py:
 *   normalize_frame  48 points (hands 0-41, arms 42-47), x/y only, centred on
 *                    the shoulder midpoint and divided by shoulder width;
 *                    a missing point stays [0,0], exactly as in training.
 *   resample         linear interpolation of the whole clip to T frames.
 *   BiLSTM           1 layer, hidden 64, bidirectional, mean-pooled over time,
 *                    then a linear head. Dropout is identity at eval.
 *
 * Any change here must keep parity with models/parity_fixture.json
 * (npm-free check: node parity_test.mjs).
 */

export const NPTS = 48;          // hands 0-41 + arms 42-47
export const FDIM = NPTS * 2;    // 96
export const LSH = 42, RSH = 43; // shoulders, used for normalisation

/* ---------------------------------------------------------------- weights */
function decode(entry) {
  const bin = atob(entry.b64);
  const buf = new ArrayBuffer(bin.length);
  const view = new Uint8Array(buf);
  for (let i = 0; i < bin.length; i++) view[i] = bin.charCodeAt(i);
  return new Float32Array(buf);
}

export function loadModel(json) {
  const w = {};
  for (const k of Object.keys(json.w)) w[k] = decode(json.w[k]);
  return { hid: json.hid, ncls: json.ncls, fdim: json.fdim, T: json.T, w,
           release: json.release, seed: json.seed, unseenAcc: json.unseen_acc };
}

/* ------------------------------------------------------------- features */
/** frame: Float32Array(128*2) of image-normalised x,y (0 for a missing point).
 *  Returns Float32Array(96). Mirrors normalize_frame(). */
export function normalizeFrame(frame) {
  const lx = frame[LSH * 2], ly = frame[LSH * 2 + 1];
  const rx = frame[RSH * 2], ry = frame[RSH * 2 + 1];
  let cx, cy, scale;
  if ((lx === 0 && ly === 0) || (rx === 0 && ry === 0)) {
    cx = 0.5; cy = 0.5; scale = 0.25;           // same fallback as training
  } else {
    cx = (lx + rx) / 2; cy = (ly + ry) / 2;
    scale = Math.hypot(lx - rx, ly - ry) + 1e-6;
  }
  const out = new Float32Array(FDIM);
  for (let i = 0; i < NPTS; i++) {
    const x = frame[i * 2], y = frame[i * 2 + 1];
    if (x === 0 && y === 0) { out[i * 2] = 0; out[i * 2 + 1] = 0; }
    else { out[i * 2] = (x - cx) / scale; out[i * 2 + 1] = (y - cy) / scale; }
  }
  return out;
}

/** seq: array of Float32Array(FDIM) -> Float32Array(T*FDIM), linear in time. */
export function resample(seq, T) {
  const n = seq.length, out = new Float32Array(T * FDIM);
  if (n === 0) return out;
  if (n === 1) { for (let t = 0; t < T; t++) out.set(seq[0], t * FDIM); return out; }
  for (let t = 0; t < T; t++) {
    const pos = (t * (n - 1)) / (T - 1);
    const i0 = Math.min(n - 1, Math.floor(pos));
    const i1 = Math.min(n - 1, i0 + 1);
    const a = pos - i0, A = seq[i0], Bv = seq[i1];
    for (let f = 0; f < FDIM; f++) out[t * FDIM + f] = A[f] + (Bv[f] - A[f]) * a;
  }
  return out;
}

/* ---------------------------------------------------------------- model */
const sigmoid = (x) => 1 / (1 + Math.exp(-x));

/** One LSTM direction over x (T x F). Returns T x H states in order of t. */
function lstmPass(x, T, F, H, Wi, Wh, bi, bh, reverse) {
  const h = new Float32Array(H), c = new Float32Array(H);
  const g = new Float32Array(4 * H);
  const states = new Float32Array(T * H);
  for (let s = 0; s < T; s++) {
    const t = reverse ? T - 1 - s : s;
    for (let k = 0; k < 4 * H; k++) g[k] = bi[k] + bh[k];
    for (let k = 0; k < 4 * H; k++) {
      let acc = 0;
      const row = k * F, base = t * F;
      for (let f = 0; f < F; f++) acc += Wi[row + f] * x[base + f];
      g[k] += acc;
    }
    for (let k = 0; k < 4 * H; k++) {
      let acc = 0;
      const row = k * H;
      for (let j = 0; j < H; j++) acc += Wh[row + j] * h[j];
      g[k] += acc;
    }
    // PyTorch gate order: input, forget, cell, output
    for (let j = 0; j < H; j++) {
      const i = sigmoid(g[j]);
      const f = sigmoid(g[H + j]);
      const gg = Math.tanh(g[2 * H + j]);
      const o = sigmoid(g[3 * H + j]);
      c[j] = f * c[j] + i * gg;
      h[j] = o * Math.tanh(c[j]);
    }
    states.set(h, t * H);   // store at the real timestep, not the loop index
  }
  return states;
}

/** x: Float32Array(T*FDIM) -> Float32Array(ncls) logits. */
export function forward(m, x) {
  const { hid: H, ncls, fdim: F, T, w } = m;
  const fwd = lstmPass(x, T, F, H, w.weight_ih_l0, w.weight_hh_l0,
                       w.bias_ih_l0, w.bias_hh_l0, false);
  const rev = lstmPass(x, T, F, H, w.weight_ih_l0_reverse, w.weight_hh_l0_reverse,
                       w.bias_ih_l0_reverse, w.bias_hh_l0_reverse, true);
  // mean-pool the concatenated [forward, reverse] state over time
  const pooled = new Float32Array(2 * H);
  for (let t = 0; t < T; t++) {
    for (let j = 0; j < H; j++) {
      pooled[j] += fwd[t * H + j];
      pooled[H + j] += rev[t * H + j];
    }
  }
  for (let j = 0; j < 2 * H; j++) pooled[j] /= T;
  const logits = new Float32Array(ncls);
  for (let cIdx = 0; cIdx < ncls; cIdx++) {
    let acc = w.head_b[cIdx];
    const row = cIdx * 2 * H;
    for (let j = 0; j < 2 * H; j++) acc += w.head_w[row + j] * pooled[j];
    logits[cIdx] = acc;
  }
  return logits;
}

export function softmax(logits) {
  let max = logits[0];
  for (let i = 1; i < logits.length; i++) if (logits[i] > max) max = logits[i];
  const out = new Float32Array(logits.length);
  let sum = 0;
  for (let i = 0; i < logits.length; i++) { out[i] = Math.exp(logits[i] - max); sum += out[i]; }
  for (let i = 0; i < out.length; i++) out[i] /= sum;
  return out;
}

export function topK(probs, vocab, k = 3) {
  return Array.from(probs)
    .map((p, i) => ({ gloss: vocab[i], p }))
    .sort((a, b) => b.p - a.p)
    .slice(0, k);
}

/* ------------------------------------------- MediaPipe -> Épée 128 slots */
/* Épée layout: 0-20 hand A, 21-41 hand B, 42-47 = pose 11..16
   (L/R shoulder, L/R elbow, L/R wrist).                                    */
export const POSE_IDS = [11, 12, 13, 14, 15, 16];

/** Build one 128*2 frame. handA/handB are arrays of 21 {x,y} or null.
 *  pose is the 33-landmark array or null. */
export function buildFrame(handA, handB, pose) {
  const frame = new Float32Array(128 * 2);
  const put = (lms, off) => {
    if (!lms) return;
    for (let i = 0; i < 21; i++) {
      frame[(off + i) * 2] = lms[i].x;
      frame[(off + i) * 2 + 1] = lms[i].y;
    }
  };
  put(handA, 0);
  put(handB, 21);
  if (pose) {
    POSE_IDS.forEach((pid, i) => {
      const p = pose[pid];
      if (p) { frame[(42 + i) * 2] = p.x; frame[(42 + i) * 2 + 1] = p.y; }
    });
  }
  return frame;
}

/** Épée v0.4 slot convention: each hand goes in the slot of its own pose wrist
 *  (slot A = pose 15, slot B = pose 16), whatever MediaPipe's handedness label
 *  says. Same rule as the release build (handslot.py): hand root vs pose wrist.
 *  hands: the HandLandmarker landmark lists; pose: 33 landmarks or null.
 *  Returns [handA, handB], either may be null. */
export function anatomicalSlots(hands, pose) {
  const w15 = pose && pose[15], w16 = pose && pose[16];
  if (!w15 || !w16 || !hands || !hands.length) return [null, null];
  const d = (h, w) => Math.hypot(h[0].x - w.x, h[0].y - w.y);
  if (hands.length === 1) {
    const h = hands[0];
    return d(h, w15) <= d(h, w16) ? [h, null] : [null, h];
  }
  const [h0, h1] = hands;
  return d(h0, w15) + d(h1, w16) <= d(h1, w15) + d(h0, w16) ? [h0, h1] : [h1, h0];
}

/* ------------------------------------------- motion gate (clerc.io/demo) --
 * No button: the sign is bracketed by hand motion. Same constants as the live
 * demo, so it feels the same. Kept pure and at module scope so gate_test.mjs
 * can drive it without a camera.
 */
export const GATE = { PREROLL_MS: 560, LOW_HOLD_MS: 270, MIN_BURST_MS: 120,
                      MAX_BURST_MS: 8000, MAX_FRAMES: 240, HAND_END: 84,
                      // frames that actually exceeded the threshold. The duration
                      // test alone cannot reject a twitch: the pre-roll and the
                      // low-hold tail pad every burst well past MIN_BURST_MS.
                      MIN_HOT: 3,
                      // a single word rarely runs longer than this: past it,
                      // ask for hands down rather than wait out the ceiling
                      DROP_ALERT_MS: 2500 };

/** Sum of absolute change over the hand landmarks. A hand missing from either
 *  frame is skipped, so entering or leaving the frame is not read as a big move. */
export function handMotion(v, pv) {
  if (!pv) return 0;
  let m = 0;
  for (const base of [0, 42]) {            // 21 points each, x/y interleaved
    let cur = false, old = false;
    for (let i = base; i < base + 42; i++) if (v[i] !== 0) { cur = true; break; }
    for (let i = base; i < base + 42; i++) if (pv[i] !== 0) { old = true; break; }
    if (!cur || !old) continue;
    for (let i = base; i < base + 42; i++) m += Math.abs(v[i] - pv[i]);
  }
  return m;
}

export function handsGone(v) {
  for (let i = 0; i < GATE.HAND_END; i++) if (v[i] !== 0) return false;
  return true;
}

/** Returns push(vec, ts, motion). onStart fires when a sign begins, onEnd gets
 *  the trimmed frames, or null when the burst was too short to read. */
export function createGate({ getThreshold, onStart, onEnd, onStuck = () => {} }) {
  let signing = false, burst = [], burstTs = [], preRoll = [], lowSince = 0, hot = 0, coached = false;

  function finish() {
    signing = false;
    let frames = burst.slice(), tss = burstTs.slice();
    const hotCount = hot;
    burst = []; burstTs = []; lowSince = 0; hot = 0;
    // drop the tail where the hands have left: it reads as its own little sign
    let end = frames.length;
    while (end > 1 && handsGone(frames[end - 1])) end--;
    if (end >= 4) { frames = frames.slice(0, end); tss = tss.slice(0, end); }
    const tooShort = frames.length < 4 || hotCount < GATE.MIN_HOT ||
                     tss[tss.length - 1] - tss[0] < GATE.MIN_BURST_MS;
    onEnd(tooShort ? null : frames);
  }

  return function push(vec, ts, motion) {
    if (motion > getThreshold()) {
      if (!signing) {
        signing = true; burst = []; burstTs = []; lowSince = 0; hot = 0; coached = false;
        // prefix the attack: frames just before the peak carry the start of the sign
        const cut = ts - GATE.PREROLL_MS;
        for (const p of preRoll) if (p.ts >= cut && !handsGone(p.v)) { burst.push(p.v); burstTs.push(p.ts); }
        onStart();
      }
      burst.push(vec); burstTs.push(ts); lowSince = 0; hot++;
      if (!coached && ts - burstTs[0] > GATE.DROP_ALERT_MS) { coached = true; onStuck(); }
      if (burst.length >= GATE.MAX_FRAMES || ts - burstTs[0] > GATE.MAX_BURST_MS) finish();
    } else if (signing) {
      burst.push(vec); burstTs.push(ts);
      if (!lowSince) lowSince = ts;
      if (ts - lowSince >= GATE.LOW_HOLD_MS) finish();
    }
    preRoll.push({ v: vec, ts });
    const pcut = ts - GATE.PREROLL_MS - 120;
    while (preRoll.length && preRoll[0].ts < pcut) preRoll.shift();
  };
}

/* ------------------------------------ guided calibration (clerc.io/demo) --
 * Four phases, each with a condition that must HOLD for its clock to run.
 * Without the condition the scan is a stopwatch that ends in "calibrated" even
 * for someone who never raised their hands, which is the bug this exists to
 * catch. Ported from the live demo, constants included.
 */
export const POSE = { LSH: 11, RSH: 12, LWR: 15, RWR: 16, LHIP: 23, RHIP: 24 };

export const SCAN_PHASES = [
  { label: "Stand still",             sub: "arms relaxed by your side",     sec: 2, need: "pose", wait: "Step into the frame" },
  { label: "Open and close both hands", sub: "hold them up, in full view",  sec: 3, need: "both", wait: "Raise both hands in front of your chest" },
  { label: "Move your hands around",  sub: "fill your whole signing space", sec: 3, need: "move", wait: "Keep your hands up and moving" },
  { label: "Hands near, then far",    sub: "toward the camera, then back",  sec: 3, need: "one",  wait: "Keep at least one hand up" },
];
export const SCAN_TOTAL = SCAN_PHASES.reduce((a, p) => a + p.sec, 0);

const seen = (p) => !!p && (p.visibility === undefined || p.visibility > 0.5);

/** The box that counts as signing space. The floor is the hip line: that is what
 *  separates "ready to sign" from "arms resting at my sides". */
export function signingSpace(pl) {
  if (!pl) return null;
  const ls = pl[POSE.LSH], rs = pl[POSE.RSH];
  if (!seen(ls) || !seen(rs)) return null;
  const sw = Math.abs(ls.x - rs.x);
  if (!(sw > 0.02)) return null;                 // shoulders collapsed, pose unusable
  const cx = (ls.x + rs.x) / 2, shY = (ls.y + rs.y) / 2;
  const lh = pl[POSE.LHIP], rh = pl[POSE.RHIP];
  const rawHip = (seen(lh) && seen(rh)) ? (lh.y + rh.y) / 2 : (shY + sw * 1.6);
  // the floor must stay inside the picture, or arms hanging at the sides count as up
  const hipY = Math.min(rawHip, 0.92);
  return { x0: cx - sw * 1.45, x1: cx + sw * 1.45, y0: shY - sw * 2.2, y1: hipY, sw };
}

/** How many wrists sit inside the signing space (0, 1 or 2). */
export function wristsUp(pl) {
  const s = signingSpace(pl);
  if (!s) return 0;
  let n = 0;
  for (const idx of [POSE.LWR, POSE.RWR]) {
    const w = pl[idx];
    if (!seen(w)) continue;
    if (w.x >= s.x0 && w.x <= s.x1 && w.y >= s.y0 && w.y <= s.y1) n++;
  }
  return n;
}

export function phaseHolds(phase, pl, motion) {
  const up = wristsUp(pl);
  if (phase.need === "pose") return !!pl;
  if (phase.need === "both") return up >= 2;
  if (phase.need === "move") return up >= 1 && motion > 0.004;
  return up >= 1;
}

const median = (a) => {
  if (!a.length) return 0;
  const s = [...a].sort((x, y) => x - y);
  return s[Math.floor(s.length / 2)];
};

/** Returns tick(pl, motion, nowMs). Advances only while the phase condition
 *  holds; onDone hands back the detection threshold tuned to this person. */
export function createScan({ onPhase, onHint, onProgress, onDone }) {
  let idx = 0, held = 0, stall = 0, last = 0, motions = [], done = false;
  onPhase(SCAN_PHASES[0], 0);

  return function tick(pl, motion, now) {
    if (done) return;
    // bounded dt: a backgrounded tab must never bank seconds it did not observe
    const dt = last ? Math.min(0.25, (now - last) / 1000) : 0;
    last = now;
    const phase = SCAN_PHASES[idx];
    const holds = phaseHolds(phase, pl, motion);

    if (holds) { held += dt; stall = 0; onHint(""); motions.push(motion); }
    else { stall += dt; onHint(stall >= 6 ? phase.wait : ""); }

    const doneSec = SCAN_PHASES.slice(0, idx).reduce((a, p) => a + p.sec, 0) +
                    Math.min(held, phase.sec);
    onProgress(Math.min(100, Math.round((doneSec / SCAN_TOTAL) * 100)));

    if (held >= phase.sec) {
      if (idx >= SCAN_PHASES.length - 1) {
        done = true;
        // tune the detection threshold to this person's own movement scale
        let thr = median(motions) * 0.5;
        thr = Math.max(0.008, Math.min(0.05, thr));
        onDone(thr);
        return;
      }
      idx++; held = 0; stall = 0;
      onPhase(SCAN_PHASES[idx], idx);
    }
  };
}
