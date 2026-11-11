/** Stylized ASL teaching approximations for the 3D signer demo. Not certified instruction. */

const d = Math.PI / 180;
const deg = (x, y = 0, z = 0) => [x * d, y * d, z * d];

const open = {curl: 0.05, thumb: 0.15, spread: 0.55};
const flat = {curl: 0.04, thumb: 0.35, index: 0.04, middle: 0.04, ring: 0.04, pinky: 0.04, spread: 0.04};
/** Flat B-hand (fingers pressed together, thumb across palm) — PopSign HELLO / PLEASE / THANK YOU. */
const bHand = {curl: 0.02, thumb: 0.88, index: 0.02, middle: 0.02, ring: 0.02, pinky: 0.02, spread: 0.0};
/** Open 5-hand for FINISH. */
const five = {curl: 0.02, thumb: 0.12, spread: 0.95};
const fist = {curl: 0.98, thumb: 0.82, index: 0.98, middle: 0.98, ring: 0.98, pinky: 0.98, spread: 0.02};
const claw = {curl: 0.55, thumb: 0.45};
const point = {curl: 0.92, index: 0.05, thumb: 0.55};
const two = {curl: 0.92, index: 0.05, middle: 0.05, thumb: 0.55};
const three = {curl: 0.92, index: 0.05, middle: 0.05, ring: 0.05, thumb: 0.4};
const cHand = {curl: 0.45, thumb: 0.35};
const oHand = {curl: 0.7, thumb: 0.55};
const yHand = {curl: 0.92, pinky: 0.05, thumb: 0.1};
const wHand = {curl: 0.92, index: 0.08, middle: 0.08, ring: 0.08, thumb: 0.55};
const hHand = {curl: 0.92, index: 0.05, middle: 0.05, thumb: 0.6};
const beak = {curl: 0.35, thumb: 0.25};
/** NO: index+middle extended with thumb, then close onto thumb (Lifeprint). */
const noOpen = {curl: 0.95, index: 0.02, middle: 0.02, ring: 0.95, pinky: 0.95, thumb: 0.2, spread: 0.12};
const noClose = {curl: 0.95, index: 0.78, middle: 0.78, ring: 0.95, pinky: 0.95, thumb: 0.88, spread: 0.02};

/**
 * Kai VRM-calibrated joint space (radians). Measured so:
 * hang ≈ sides, temple ≈ forehead B-hand, chin ≈ thank-you start, chest ≈ please.
 */
const hangL = {shoulderL: [0.55, 0.35, 0.25], elbowL: [0.05, 0, 0.75], wristL: [-0.15, -0.15, 0.15]};
const hangR = {shoulderR: [0.55, -0.75, -0.35], elbowR: [0.05, 0, -0.4], wristR: [-0.25, 0.2, -0.3]};
/**
 * PopSign hello.mp4 (measured): right B-hand at temple height, palm toward camera,
 * fingers up & together, small side-to-side wave. Wrist eulers tuned so palm faces viewer.
 */
/**
 * hello.mp4: B-hand at temple (close to head), elbow softer, palm toward camera.
 * Tuned against video mid frames (palm_z toward camera, wrist near temple).
 */
const helloC = {shoulderR: [-0.55, 0.25, -0.4], elbowR: [0.05, 0.05, -1.55], wristR: [0.45, 0.85, -1.75]};
const helloIn = {shoulderR: [-0.55, 0.55, -0.35], elbowR: [0.05, 0.1, -1.58], wristR: [0.5, 0.9, -1.8]};
const helloOut = {shoulderR: [-0.55, 0.0, -0.4], elbowR: [0.05, 0.0, -1.5], wristR: [0.4, 0.8, -1.7]};
/** PopSign / Lifeprint THANK YOU: flat hand near chin → forward toward viewer. */
const chinR = {shoulderR: [-0.55, 0.28, -0.78], elbowR: [0.05, 0, -1.38], wristR: [0.55, 0.35, -0.25]};
const thankOutR = {shoulderR: [0.05, -0.5, -0.6], elbowR: [0.05, 0, -0.9], wristR: [0.35, 0.3, -0.45]};
const chestR = {shoulderR: [-1.35, 0.35, -1.15], elbowR: [0.05, 0, -1.55], wristR: [0.55, 0.1, -0.35]};
const chestTL = {shoulderR: [-1.25, 0.55, -1.05], elbowR: [0.1, 0.15, -1.5], wristR: [0.5, 0.0, -0.4]};
const chestBR = {shoulderR: [-1.4, 0.05, -1.2], elbowR: [0.05, -0.1, -1.55], wristR: [0.55, 0.2, -0.3]};
const chestTR = {shoulderR: [-1.2, -0.2, -1.05], elbowR: [0.05, -0.15, -1.45], wristR: [0.5, 0.25, -0.35]};
const yesHoldR = {shoulderR: [-0.85, 0.15, -0.95], elbowR: [0.05, 0, -1.45], wristR: [0.55, 0.2, -0.35]};
const noHoldR = {shoulderR: [-0.9, 0.1, -0.9], elbowR: [0.05, 0, -1.4], wristR: [0.25, 0.35, -0.4]};
const finishIn = {
  shoulderL: [-0.85, 0.45, 0.55], elbowL: [0.05, 0, 1.35], wristL: [0.35, -0.2, 0.85],
  shoulderR: [-0.85, -0.45, -0.55], elbowR: [0.05, 0, -1.35], wristR: [0.35, 0.2, -0.85],
};
const finishOut = {
  shoulderL: [-0.45, 0.7, 0.35], elbowL: [0.05, 0, 1.0], wristL: [-0.15, -0.25, 1.35],
  shoulderR: [-0.45, -0.7, -0.35], elbowR: [0.05, 0, -1.0], wristR: [-0.15, 0.25, -1.35],
};

/** Neutral rest: both arms hang; one-handed Lifeprint signs keep L down. */
const rest = {
  head: [0, 0, 0],
  ...hangL,
  ...hangR,
  handL: {...open, spread: 0.12, thumb: 0.2},
  handR: {...open, spread: 0.12, thumb: 0.2},
  face: {smile: 0.16, brow: 0, blink: 0},
};

/** Legacy procedural rest used by older clips — remapped into Kai space below. */
const legacyRest = {
  head: deg(0, 0, 0),
  shoulderL: deg(4, 6, -6),
  elbowL: deg(8, 0, 0),
  wristL: deg(0, 0, 0),
  shoulderR: deg(6, -6, 8),
  elbowR: deg(10, 0, 0),
  wristR: deg(0, 0, 0),
};

function clip(duration, frames) {
  return {duration, frames};
}

function frame(t, joints) {
  return {t, ...joints};
}

function remapLegacyVec(vec, key) {
  const o = legacyRest[key];
  const h = rest[key];
  return [h[0] + (vec[0] - o[0]), h[1] + (vec[1] - o[1]), h[2] + (vec[2] - o[2])];
}

function isAbsoluteRestVec(vec, key) {
  const h = rest[key];
  return h && Math.abs(vec[0] - h[0]) < 1e-6 && Math.abs(vec[1] - h[1]) < 1e-6 && Math.abs(vec[2] - h[2]) < 1e-6;
}

function legacyFrame(t, joints = {}) {
  const out = {t, ...joints};
  for (const key of ['head', 'shoulderL', 'elbowL', 'wristL', 'shoulderR', 'elbowR', 'wristR']) {
    if (!out[key]) continue;
    out[key] = isAbsoluteRestVec(out[key], key) ? out[key] : remapLegacyVec(out[key], key);
  }
  return out;
}

function legacyClip(duration, frames) {
  return clip(duration, frames.map((f) => {
    const {t, ...joints} = f;
    return legacyFrame(t, joints);
  }));
}

export const SIGN_ANIMATIONS = {
  // PopSign hello.mp4 (~2.13s): raise B-hand → wave out/in → lower. Left hangs.
  hello: clip(2.13, [
    frame(0, rest),
    frame(0.1, {...helloC, ...hangL, handR: bHand, handL: rest.handL, face: {smile: 0.35}}),
    frame(0.28, {...helloOut, ...hangL, handR: bHand, handL: rest.handL, face: {smile: 0.4}}),
    frame(0.45, {...helloIn, ...hangL, handR: bHand, handL: rest.handL, face: {smile: 0.4}}),
    frame(0.62, {...helloOut, ...hangL, handR: bHand, handL: rest.handL, face: {smile: 0.35}}),
    frame(0.78, {...helloIn, ...hangL, handR: bHand, handL: rest.handL, face: {smile: 0.3}}),
    frame(0.9, {...helloC, ...hangL, handR: bHand, handL: rest.handL, face: {smile: 0.25}}),
    frame(1, rest),
  ]),

  // thank-you.mp4 (~1.11s): flat B near chin → push forward/down toward viewer.
  'thank-you': clip(1.11, [
    frame(0, rest),
    frame(0.12, {...chinR, ...hangL, handR: bHand, handL: rest.handL, face: {smile: 0.55}}),
    frame(0.4, {...thankOutR, ...hangL, handR: bHand, handL: rest.handL, face: {smile: 0.7}}),
    frame(0.72, {
      shoulderR: [-0.1, -0.4, -0.35], elbowR: [0.05, 0, -0.5], wristR: [-0.05, 0.2, -0.35],
      ...hangL, handR: bHand, handL: rest.handL, face: {smile: 0.5},
    }),
    frame(1, rest),
  ]),

  // please.mp4 (~1.1s): flat B on chest, palm to body, small circle.
  please: clip(1.1, [
    frame(0, rest),
    frame(0.1, {...chestR, ...hangL, handR: bHand, handL: rest.handL, face: {smile: 0.22, brow: 0.1}}),
    frame(0.28, {...chestTL, ...hangL, handR: bHand, handL: rest.handL}),
    frame(0.48, {...chestBR, ...hangL, handR: bHand, handL: rest.handL}),
    frame(0.68, {...chestTR, ...hangL, handR: bHand, handL: rest.handL}),
    frame(0.88, {...chestR, ...hangL, handR: bHand, handL: rest.handL, face: {smile: 0.28}}),
    frame(1, rest),
  ]),

  // yes.mp4 (~1.7s): S-fist at chest, wrist nods (palm slightly down/away).
  yes: clip(1.7, [
    frame(0, rest),
    frame(0.12, {
      ...yesHoldR, ...hangL, wristR: [0.55, 0.15, -0.4],
      handR: fist, handL: rest.handL, head: [-0.08, 0, 0], face: {smile: 0.3},
    }),
    frame(0.32, {
      ...yesHoldR, ...hangL, wristR: [-0.7, 0.15, -0.4],
      handR: fist, handL: rest.handL, head: [0.18, 0, 0],
    }),
    frame(0.52, {
      ...yesHoldR, ...hangL, wristR: [0.55, 0.15, -0.4],
      handR: fist, handL: rest.handL, head: [-0.08, 0, 0],
    }),
    frame(0.72, {
      ...yesHoldR, ...hangL, wristR: [-0.6, 0.15, -0.4],
      handR: fist, handL: rest.handL, head: [0.14, 0, 0], face: {smile: 0.35},
    }),
    frame(0.9, {
      ...yesHoldR, ...hangL, wristR: [0.4, 0.15, -0.4],
      handR: fist, handL: rest.handL,
    }),
    frame(1, rest),
  ]),

  // no.mp4 (~2.0s): index+middle open → pinch thumb (repeat). Palm toward camera mid-sign.
  no: clip(2.0, [
    frame(0, rest),
    frame(0.12, {
      ...noHoldR, ...hangL, handR: noOpen, handL: rest.handL,
      head: [0, -0.12, 0], face: {smile: 0.04, brow: 0.25},
    }),
    frame(0.3, {...noHoldR, ...hangL, handR: noClose, handL: rest.handL, head: [0, 0.12, 0]}),
    frame(0.48, {...noHoldR, ...hangL, handR: noOpen, handL: rest.handL, head: [0, -0.12, 0]}),
    frame(0.66, {...noHoldR, ...hangL, handR: noClose, handL: rest.handL, head: [0, 0.1, 0]}),
    frame(0.85, {
      ...noHoldR, ...hangL, handR: noClose, handL: rest.handL,
      face: {smile: 0.04, brow: 0.2},
    }),
    frame(1, rest),
  ]),

  // finish.mp4 (~1.69s): both 5-hands flip palms out.
  finish: clip(1.69, [
    frame(0, rest),
    frame(0.15, {...finishIn, handL: five, handR: five, face: {smile: 0.25, brow: 0.08}}),
    frame(0.4, {...finishOut, handL: five, handR: five}),
    frame(0.6, {...finishIn, handL: five, handR: five}),
    frame(0.82, {...finishOut, handL: five, handR: five, face: {smile: 0.3}}),
    frame(1, rest),
  ]),

  drink: clip(2.0, [
    frame(0, rest),
    frame(0.3, {shoulderR: deg(-55, -5, 15), elbowR: deg(110, 0, 0), wristR: deg(-30, 0, 0), handR: cHand}),
    frame(0.55, {shoulderR: deg(-60, 0, 10), elbowR: deg(120, 0, 0), wristR: deg(-50, 15, 0), handR: cHand, head: deg(-8, 5, 0)}),
    frame(0.8, {shoulderR: deg(-55, -5, 15), elbowR: deg(110, 0, 0), wristR: deg(-30, 0, 0), handR: cHand}),
    frame(1, rest),
  ]),

  water: clip(1.8, [
    frame(0, rest),
    frame(0.25, {shoulderR: deg(-50, 0, 20), elbowR: deg(105, 0, 0), wristR: deg(0, 0, 0), handR: wHand}),
    frame(0.45, {shoulderR: deg(-52, 0, 20), elbowR: deg(110, 0, 0), wristR: deg(0, 0, 0), handR: wHand}),
    frame(0.65, {shoulderR: deg(-48, 0, 20), elbowR: deg(100, 0, 0), wristR: deg(0, 0, 0), handR: wHand}),
    frame(0.85, {shoulderR: deg(-52, 0, 20), elbowR: deg(110, 0, 0), wristR: deg(0, 0, 0), handR: wHand}),
    frame(1, rest),
  ]),

  book: clip(2.0, [
    frame(0, rest),
    frame(0.3, {
      shoulderL: deg(-25, 15, -35), elbowL: deg(85, 0, 0), wristL: deg(0, 0, 70), handL: flat,
      shoulderR: deg(-25, -15, 35), elbowR: deg(85, 0, 0), wristR: deg(0, 0, -70), handR: flat,
    }),
    frame(0.7, {
      shoulderL: deg(-20, 25, -50), elbowL: deg(70, 0, 0), wristL: deg(0, 0, 10), handL: flat,
      shoulderR: deg(-20, -25, 50), elbowR: deg(70, 0, 0), wristR: deg(0, 0, -10), handR: flat,
    }),
    frame(1, rest),
  ]),

  food: clip(1.8, [
    frame(0, rest),
    frame(0.25, {shoulderR: deg(-50, -5, 20), elbowR: deg(115, 0, 0), wristR: deg(-15, 0, 0), handR: oHand}),
    frame(0.45, {shoulderR: deg(-45, -5, 20), elbowR: deg(100, 0, 0), wristR: deg(0, 0, 0), handR: oHand}),
    frame(0.65, {shoulderR: deg(-50, -5, 20), elbowR: deg(115, 0, 0), wristR: deg(-15, 0, 0), handR: oHand}),
    frame(0.85, {shoulderR: deg(-45, -5, 20), elbowR: deg(100, 0, 0), wristR: deg(0, 0, 0), handR: oHand}),
    frame(1, rest),
  ]),

  hungry: clip(1.8, [
    frame(0, rest),
    frame(0.3, {shoulderR: deg(-35, 5, 40), elbowR: deg(95, 0, 0), wristR: deg(0, 0, -30), handR: cHand}),
    frame(0.7, {shoulderR: deg(5, 10, 45), elbowR: deg(70, 0, 0), wristR: deg(0, 0, -20), handR: cHand}),
    frame(1, rest),
  ]),

  like: clip(1.7, [
    frame(0, rest),
    frame(0.3, {shoulderR: deg(-25, 10, 45), elbowR: deg(95, 0, 0), wristR: deg(0, 0, -25), handR: {...open, curl: 0.4, middle: 0.15, thumb: 0.2}}),
    frame(0.7, {shoulderR: deg(-30, -15, 35), elbowR: deg(40, 0, 0), wristR: deg(0, 0, 0), handR: {...open, curl: 0.4, middle: 0.15, thumb: 0.2}}),
    frame(1, rest),
  ]),

  go: clip(1.6, [
    frame(0, rest),
    frame(0.3, {
      shoulderL: deg(-40, 10, -25), elbowL: deg(50, 0, 0), wristL: deg(0, 0, 0), handL: point,
      shoulderR: deg(-40, -10, 25), elbowR: deg(50, 0, 0), wristR: deg(0, 0, 0), handR: point,
    }),
    frame(0.7, {
      shoulderL: deg(-25, 30, -40), elbowL: deg(20, 0, 0), wristL: deg(0, 0, 0), handL: point,
      shoulderR: deg(-25, -30, 40), elbowR: deg(20, 0, 0), wristR: deg(0, 0, 0), handR: point,
    }),
    frame(1, rest),
  ]),

  name: clip(1.6, [
    frame(0, rest),
    frame(0.3, {
      shoulderL: deg(-35, 20, -30), elbowL: deg(90, 0, 0), wristL: deg(0, 0, 20), handL: hHand,
      shoulderR: deg(-35, -20, 30), elbowR: deg(90, 0, 0), wristR: deg(0, 0, -20), handR: hHand,
    }),
    frame(0.55, {
      shoulderL: deg(-38, 15, -28), elbowL: deg(95, 0, 0), wristL: deg(0, 0, 20), handL: hHand,
      shoulderR: deg(-32, -25, 32), elbowR: deg(85, 0, 0), wristR: deg(0, 0, -20), handR: hHand,
    }),
    frame(0.8, {
      shoulderL: deg(-32, 25, -32), elbowL: deg(85, 0, 0), wristL: deg(0, 0, 20), handL: hHand,
      shoulderR: deg(-38, -15, 28), elbowR: deg(95, 0, 0), wristR: deg(0, 0, -20), handR: hHand,
    }),
    frame(1, rest),
  ]),

  home: clip(1.9, [
    frame(0, rest),
    frame(0.3, {shoulderR: deg(-55, 5, 15), elbowR: deg(115, 0, 0), wristR: deg(-10, 20, 0), handR: oHand}),
    frame(0.6, {shoulderR: deg(-50, -5, 25), elbowR: deg(105, 0, 0), wristR: deg(-5, -15, 0), handR: oHand}),
    frame(1, rest),
  ]),

  have: clip(1.5, [
    frame(0, rest),
    frame(0.4, {
      shoulderL: deg(-20, 15, -50), elbowL: deg(100, 0, 0), wristL: deg(0, 0, 30), handL: flat,
      shoulderR: deg(-20, -15, 50), elbowR: deg(100, 0, 0), wristR: deg(0, 0, -30), handR: flat,
    }),
    frame(1, rest),
  ]),

  want: clip(1.7, [
    frame(0, rest),
    frame(0.3, {
      shoulderL: deg(-30, 30, -40), elbowL: deg(50, 0, 0), wristL: deg(0, 0, 20), handL: claw,
      shoulderR: deg(-30, -30, 40), elbowR: deg(50, 0, 0), wristR: deg(0, 0, -20), handR: claw,
    }),
    frame(0.7, {
      shoulderL: deg(-25, 10, -45), elbowL: deg(90, 0, 0), wristL: deg(0, 0, 30), handL: claw,
      shoulderR: deg(-25, -10, 45), elbowR: deg(90, 0, 0), wristR: deg(0, 0, -30), handR: claw,
    }),
    frame(1, rest),
  ]),

  love: clip(2.0, [
    frame(0, rest),
    frame(0.4, {
      shoulderL: deg(-15, 35, -55), elbowL: deg(110, 0, 0), wristL: deg(0, 0, 40), handL: fist,
      shoulderR: deg(-15, -35, 55), elbowR: deg(110, 0, 0), wristR: deg(0, 0, -40), handR: fist,
    }),
    frame(0.75, {
      shoulderL: deg(-15, 35, -55), elbowL: deg(110, 0, 0), wristL: deg(0, 0, 40), handL: fist,
      shoulderR: deg(-15, -35, 55), elbowR: deg(110, 0, 0), wristR: deg(0, 0, -40), handR: fist,
    }),
    frame(1, rest),
  ]),

  baby: clip(2.2, [
    frame(0, rest),
    frame(0.25, {
      shoulderL: deg(-20, 25, -45), elbowL: deg(100, 0, 0), wristL: deg(0, 0, 20), handL: flat,
      shoulderR: deg(-25, -15, 40), elbowR: deg(95, 0, 0), wristR: deg(0, 0, -20), handR: flat,
    }),
    frame(0.5, {
      shoulderL: deg(-25, 15, -40), elbowL: deg(95, 0, 0), wristL: deg(0, 0, 20), handL: flat,
      shoulderR: deg(-20, -25, 45), elbowR: deg(100, 0, 0), wristR: deg(0, 0, -20), handR: flat,
      head: deg(0, 8, 0),
    }),
    frame(0.75, {
      shoulderL: deg(-20, 25, -45), elbowL: deg(100, 0, 0), wristL: deg(0, 0, 20), handL: flat,
      shoulderR: deg(-25, -15, 40), elbowR: deg(95, 0, 0), wristR: deg(0, 0, -20), handR: flat,
      head: deg(0, -8, 0),
    }),
    frame(1, rest),
  ]),

  belt: clip(1.8, [
    frame(0, rest),
    frame(0.3, {
      shoulderL: deg(15, 20, -40), elbowL: deg(70, 0, 0), wristL: deg(0, 0, 20), handL: flat,
      shoulderR: deg(15, -20, 40), elbowR: deg(70, 0, 0), wristR: deg(0, 0, -20), handR: flat,
    }),
    frame(0.7, {
      shoulderL: deg(20, 5, -50), elbowL: deg(60, 0, 0), wristL: deg(0, 0, 20), handL: flat,
      shoulderR: deg(20, -5, 50), elbowR: deg(60, 0, 0), wristR: deg(0, 0, -20), handR: flat,
    }),
    frame(1, rest),
  ]),

  eat: clip(1.8, [
    frame(0, rest),
    frame(0.25, {shoulderR: deg(-50, -5, 20), elbowR: deg(115, 0, 0), wristR: deg(-15, 0, 0), handR: oHand}),
    frame(0.45, {shoulderR: deg(-45, -5, 20), elbowR: deg(100, 0, 0), wristR: deg(0, 0, 0), handR: oHand}),
    frame(0.65, {shoulderR: deg(-50, -5, 20), elbowR: deg(115, 0, 0), wristR: deg(-15, 0, 0), handR: oHand}),
    frame(0.85, {shoulderR: deg(-45, -5, 20), elbowR: deg(100, 0, 0), wristR: deg(0, 0, 0), handR: oHand}),
    frame(1, rest),
  ]),

  empty: clip(1.8, [
    frame(0, rest),
    frame(0.25, {
      shoulderL: deg(-15, 20, -40), elbowL: deg(80, 0, 0), wristL: deg(0, 0, 80), handL: flat,
      shoulderR: deg(-35, -10, 30), elbowR: deg(70, 0, 0), wristR: deg(0, 0, -20), handR: flat,
    }),
    frame(0.7, {
      shoulderL: deg(-15, 20, -40), elbowL: deg(80, 0, 0), wristL: deg(0, 0, 80), handL: flat,
      shoulderR: deg(-20, -35, 45), elbowR: deg(40, 0, 0), wristR: deg(0, 0, -10), handR: flat,
    }),
    frame(1, rest),
  ]),

  peg: clip(1.6, [
    frame(0, rest),
    frame(0.3, {shoulderR: deg(-40, -10, 25), elbowR: deg(90, 0, 0), wristR: deg(0, 0, 0), handR: {...open, curl: 0.2, index: 0.35, thumb: 0.3}}),
    frame(0.55, {shoulderR: deg(-40, -10, 25), elbowR: deg(90, 0, 0), wristR: deg(0, 0, 0), handR: {...open, curl: 0.2, index: 0.75, thumb: 0.7}}),
    frame(0.8, {shoulderR: deg(-40, -10, 25), elbowR: deg(90, 0, 0), wristR: deg(0, 0, 0), handR: {...open, curl: 0.2, index: 0.35, thumb: 0.3}}),
    frame(1, rest),
  ]),

  soccer: clip(1.8, [
    frame(0, rest),
    frame(0.3, {
      shoulderL: deg(5, 15, -35), elbowL: deg(70, 0, 0), wristL: deg(0, 0, 20), handL: flat,
      shoulderR: deg(10, -20, 40), elbowR: deg(40, 0, 0), wristR: deg(0, 0, -20), handR: flat,
    }),
    frame(0.6, {
      shoulderL: deg(10, 20, -40), elbowL: deg(50, 0, 0), wristL: deg(0, 0, 20), handL: flat,
      shoulderR: deg(5, -10, 30), elbowR: deg(80, 0, 0), wristR: deg(0, 0, -20), handR: flat,
    }),
    frame(1, rest),
  ]),

  squeeze: clip(1.6, [
    frame(0, rest),
    frame(0.3, {
      shoulderL: deg(-25, 20, -35), elbowL: deg(85, 0, 0), wristL: deg(0, 0, 30), handL: claw,
      shoulderR: deg(-25, -20, 35), elbowR: deg(85, 0, 0), wristR: deg(0, 0, -30), handR: claw,
    }),
    frame(0.6, {
      shoulderL: deg(-28, 15, -30), elbowL: deg(95, 0, 0), wristL: deg(0, 0, 30), handL: fist,
      shoulderR: deg(-28, -15, 30), elbowR: deg(95, 0, 0), wristR: deg(0, 0, -30), handR: fist,
    }),
    frame(1, rest),
  ]),

  vlog: clip(2.0, [
    frame(0, rest),
    frame(0.35, {shoulderR: deg(-45, -20, 30), elbowR: deg(70, 0, 0), wristR: deg(0, 0, -30), handR: {...open, curl: 0.25}}),
    frame(0.7, {shoulderR: deg(-50, -15, 25), elbowR: deg(80, 0, 0), wristR: deg(10, 0, -20), handR: {...open, curl: 0.25}}),
    frame(1, rest),
  ]),

  lock: clip(1.8, [
    frame(0, rest),
    frame(0.35, {
      shoulderL: deg(-30, 20, -35), elbowL: deg(95, 0, 0), wristL: deg(0, 0, 40), handL: fist,
      shoulderR: deg(-30, -20, 35), elbowR: deg(95, 0, 0), wristR: deg(0, 0, -40), handR: fist,
    }),
    frame(0.7, {
      shoulderL: deg(-30, 20, -35), elbowL: deg(95, 0, 0), wristL: deg(0, 40, 40), handL: fist,
      shoulderR: deg(-30, -20, 35), elbowR: deg(95, 0, 0), wristR: deg(0, -40, -40), handR: fist,
    }),
    frame(1, rest),
  ]),

  duck: clip(1.6, [
    frame(0, rest),
    frame(0.3, {shoulderR: deg(-55, 0, 15), elbowR: deg(115, 0, 0), wristR: deg(-20, 0, 0), handR: beak}),
    frame(0.5, {shoulderR: deg(-55, 0, 15), elbowR: deg(115, 0, 0), wristR: deg(-20, 0, 0), handR: {...beak, curl: 0.75, thumb: 0.65}}),
    frame(0.7, {shoulderR: deg(-55, 0, 15), elbowR: deg(115, 0, 0), wristR: deg(-20, 0, 0), handR: beak}),
    frame(1, rest),
  ]),

  baseballcap: clip(1.7, [
    frame(0, rest),
    frame(0.35, {shoulderR: deg(-70, -5, 10), elbowR: deg(130, 0, 0), wristR: deg(-20, 0, 0), handR: flat}),
    frame(0.65, {shoulderR: deg(-65, -5, 15), elbowR: deg(120, 0, 0), wristR: deg(-10, 0, 0), handR: flat}),
    frame(1, rest),
  ]),

  other: clip(1.5, [
    frame(0, rest),
    frame(0.3, {shoulderR: deg(-35, -10, 30), elbowR: deg(80, 0, 0), wristR: deg(0, 0, -40), handR: {...fist, thumb: 0.05}}),
    frame(0.7, {shoulderR: deg(-35, -10, 30), elbowR: deg(80, 0, 0), wristR: deg(0, 0, 40), handR: {...fist, thumb: 0.05}}),
    frame(1, rest),
  ]),

  whatfor: clip(1.8, [
    frame(0, rest),
    frame(0.3, {
      shoulderL: deg(-20, 25, -45), elbowL: deg(70, 0, 0), wristL: deg(0, 0, 70), handL: open,
      shoulderR: deg(-20, -25, 45), elbowR: deg(70, 0, 0), wristR: deg(0, 0, -70), handR: open,
    }),
    frame(0.5, {
      shoulderL: deg(-25, 20, -40), elbowL: deg(75, 0, 0), wristL: deg(0, 0, 60), handL: open,
      shoulderR: deg(-15, -30, 50), elbowR: deg(65, 0, 0), wristR: deg(0, 0, -80), handR: open,
    }),
    frame(0.7, {
      shoulderL: deg(-15, 30, -50), elbowL: deg(65, 0, 0), wristL: deg(0, 0, 80), handL: open,
      shoulderR: deg(-25, -20, 40), elbowR: deg(75, 0, 0), wristR: deg(0, 0, -60), handR: open,
    }),
    frame(1, rest),
  ]),

  drag: clip(1.8, [
    frame(0, rest),
    frame(0.3, {
      shoulderL: deg(-20, 35, -30), elbowL: deg(40, 0, 0), wristL: deg(0, 0, 10), handL: claw,
      shoulderR: deg(-20, -35, 30), elbowR: deg(40, 0, 0), wristR: deg(0, 0, -10), handR: claw,
    }),
    frame(0.7, {
      shoulderL: deg(-15, 5, -40), elbowL: deg(90, 0, 0), wristL: deg(0, 0, 20), handL: claw,
      shoulderR: deg(-15, -5, 40), elbowR: deg(90, 0, 0), wristR: deg(0, 0, -20), handR: claw,
    }),
    frame(1, rest),
  ]),

  microscope: clip(2.0, [
    frame(0, rest),
    frame(0.35, {
      shoulderL: deg(-45, 15, -25), elbowL: deg(110, 0, 0), wristL: deg(0, 0, 30), handL: cHand,
      shoulderR: deg(-50, -10, 20), elbowR: deg(115, 0, 0), wristR: deg(-20, 0, -20), handR: cHand,
      head: deg(-15, 0, 0),
    }),
    frame(0.7, {
      shoulderL: deg(-45, 15, -25), elbowL: deg(110, 0, 0), wristL: deg(0, 0, 30), handL: cHand,
      shoulderR: deg(-50, -10, 20), elbowR: deg(115, 0, 0), wristR: deg(-20, 0, -20), handR: cHand,
      head: deg(-15, 5, 0),
    }),
    frame(1, rest),
  ]),

  party: clip(2.2, [
    frame(0, rest),
    frame(0.25, {
      shoulderL: deg(-40, 20, -35), elbowL: deg(60, 0, 0), wristL: deg(0, 0, 20), handL: yHand,
      shoulderR: deg(-40, -20, 35), elbowR: deg(60, 0, 0), wristR: deg(0, 0, -20), handR: yHand,
    }),
    frame(0.5, {
      shoulderL: deg(-50, 10, -30), elbowL: deg(80, 0, 0), wristL: deg(0, 0, 20), handL: yHand,
      shoulderR: deg(-30, -30, 40), elbowR: deg(40, 0, 0), wristR: deg(0, 0, -20), handR: yHand,
    }),
    frame(0.75, {
      shoulderL: deg(-30, 30, -40), elbowL: deg(40, 0, 0), wristL: deg(0, 0, 20), handL: yHand,
      shoulderR: deg(-50, -10, 30), elbowR: deg(80, 0, 0), wristR: deg(0, 0, -20), handR: yHand,
    }),
    frame(1, rest),
  ]),

  demand: clip(1.5, [
    frame(0, rest),
    frame(0.35, {shoulderR: deg(-45, -15, 25), elbowR: deg(70, 0, 0), wristR: deg(30, 0, 0), handR: point}),
    frame(0.7, {shoulderR: deg(-20, -10, 30), elbowR: deg(40, 0, 0), wristR: deg(40, 0, 0), handR: point}),
    frame(1, rest),
  ]),

  edit: clip(1.8, [
    frame(0, rest),
    frame(0.25, {
      shoulderL: deg(-25, 20, -35), elbowL: deg(85, 0, 0), wristL: deg(0, 0, 40), handL: flat,
      shoulderR: deg(-35, -15, 30), elbowR: deg(90, 0, 0), wristR: deg(0, 0, -20), handR: point,
    }),
    frame(0.5, {
      shoulderL: deg(-25, 20, -35), elbowL: deg(85, 0, 0), wristL: deg(0, 0, 40), handL: flat,
      shoulderR: deg(-30, -20, 35), elbowR: deg(80, 0, 0), wristR: deg(0, 0, -20), handR: point,
    }),
    frame(0.75, {
      shoulderL: deg(-25, 20, -35), elbowL: deg(85, 0, 0), wristL: deg(0, 0, 40), handL: flat,
      shoulderR: deg(-35, -10, 25), elbowR: deg(95, 0, 0), wristR: deg(0, 0, -20), handR: point,
    }),
    frame(1, rest),
  ]),

  mechanic: clip(1.9, [
    frame(0, rest),
    frame(0.3, {
      shoulderL: deg(-20, 15, -40), elbowL: deg(80, 0, 0), wristL: deg(0, 0, 30), handL: fist,
      shoulderR: deg(-35, -20, 30), elbowR: deg(90, 0, 0), wristR: deg(0, 0, -20), handR: fist,
    }),
    frame(0.55, {
      shoulderL: deg(-20, 15, -40), elbowL: deg(80, 0, 0), wristL: deg(0, 0, 30), handL: fist,
      shoulderR: deg(-35, -20, 30), elbowR: deg(90, 0, 0), wristR: deg(0, 50, -20), handR: fist,
    }),
    frame(0.8, {
      shoulderL: deg(-20, 15, -40), elbowL: deg(80, 0, 0), wristL: deg(0, 0, 30), handL: fist,
      shoulderR: deg(-35, -20, 30), elbowR: deg(90, 0, 0), wristR: deg(0, -50, -20), handR: fist,
    }),
    frame(1, rest),
  ]),

  deaf: clip(1.8, [
    frame(0, rest),
    frame(0.3, {shoulderR: deg(-55, 10, 15), elbowR: deg(120, 0, 0), wristR: deg(0, 20, 0), handR: point}),
    frame(0.7, {shoulderR: deg(-50, -5, 25), elbowR: deg(110, 0, 0), wristR: deg(-10, -10, 0), handR: point}),
    frame(1, rest),
  ]),
};

export const REST_POSE = rest;

export function hasSignAnimation(id) {
  return Boolean(SIGN_ANIMATIONS[id]);
}
