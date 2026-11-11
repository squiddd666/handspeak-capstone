/**
 * Map MediaPipe Pose + Hand landmarks → Kai VRM-calibrated arm eulers
 * (same joint space as sign-animations.js).
 */
const VISION_VER = '0.10.22-rc.20250304';
const VISION_CDN = `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@${VISION_VER}`;
const WASM = `${VISION_CDN}/wasm`;
const POSE_MODEL = 'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task';
const HAND_MODEL = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task';

const LS = 11, RS = 12, LW = 15, RW = 16, NOSE = 0;
const LI = 19, RI = 20;
const LHIP = 23, RHIP = 24;

const HANG_L = {shoulder: [0.55, 0.35, 0.25], elbow: [0.05, 0, 0.75], wrist: [-0.15, -0.15, 0.15]};
const HANG_R = {shoulder: [0.55, -0.75, -0.35], elbow: [0.05, 0, -0.4], wrist: [-0.25, 0.2, -0.3]};
const TEMPLE_R = {shoulder: [-0.3, 0.2, -0.1], elbow: [0.05, 0.04, -1.3], wrist: [-0.4, 1.6, -1.2]};
const TEMPLE_L = {shoulder: [-0.3, -0.2, 0.1], elbow: [0.05, -0.04, 1.3], wrist: [-0.4, -1.6, 1.2]};
const CHIN_R = {shoulder: [-0.55, 0.28, -0.78], elbow: [0.05, 0, -1.38], wrist: [0.55, 0.35, -0.25]};
const CHIN_L = {shoulder: [-0.55, -0.28, 0.78], elbow: [0.05, 0, 1.38], wrist: [0.55, -0.35, 0.25]};
const CHEST_R = {shoulder: [-1.35, 0.35, -1.15], elbow: [0.05, 0, -1.55], wrist: [0.55, 0.1, -0.35]};
const CHEST_L = {shoulder: [-1.35, -0.35, 1.15], elbow: [0.05, 0, 1.55], wrist: [0.55, -0.1, 0.35]};
const WAVE_IN_R = {shoulder: [-0.3, 0.4, -0.1], elbow: [0.05, 0.08, -1.3], wrist: [-0.4, 1.6, -1.2]};
const WAVE_OUT_R = {shoulder: [-0.3, 0.0, -0.1], elbow: [0.05, 0.0, -1.3], wrist: [-0.4, 1.6, -1.2]};
const WAVE_IN_L = {shoulder: [-0.3, -0.4, 0.1], elbow: [0.05, -0.08, 1.3], wrist: [-0.4, -1.6, 1.2]};
const WAVE_OUT_L = {shoulder: [-0.3, 0.0, 0.1], elbow: [0.05, 0.0, 1.3], wrist: [-0.4, -1.6, 1.2]};
const THANK_OUT_R = {shoulder: [0.05, -0.5, -0.6], elbow: [0.05, 0, -0.9], wrist: [0.35, 0.3, -0.45]};
const THANK_OUT_L = {shoulder: [0.05, 0.5, 0.6], elbow: [0.05, 0, 0.9], wrist: [0.35, -0.3, 0.45]};

const B_HAND = {curl: 0.02, thumb: 0.62, index: 0.02, middle: 0.02, ring: 0.02, pinky: 0.02, spread: 0.02};

function lerp(a, b, t) { return a + (b - a) * t; }
function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }
function lerpVec(a, b, t) { return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)]; }
function lerpArm(a, b, t) {
  return {
    shoulder: lerpVec(a.shoulder, b.shoulder, t),
    elbow: lerpVec(a.elbow, b.elbow, t),
    wrist: lerpVec(a.wrist, b.wrist, t),
  };
}
function visible(lm, min = 0.2) {
  return Boolean(lm) && Number.isFinite(lm.x) && Number.isFinite(lm.y)
    && (lm.visibility == null || lm.visibility >= min);
}

function fingerCurl(landmarks, tip, pip, mcp) {
  if (!landmarks?.[tip] || !landmarks?.[pip] || !landmarks?.[mcp]) return 0.08;
  const a = landmarks[mcp], b = landmarks[pip], c = landmarks[tip];
  const abx = b.x - a.x, aby = b.y - a.y, abz = (b.z || 0) - (a.z || 0);
  const bcx = c.x - b.x, bcy = c.y - b.y, bcz = (c.z || 0) - (b.z || 0);
  const ab = Math.hypot(abx, aby, abz) || 1e-6;
  const bc = Math.hypot(bcx, bcy, bcz) || 1e-6;
  const cos = (abx * bcx + aby * bcy + abz * bcz) / (ab * bc);
  const angle = Math.acos(Math.min(1, Math.max(-1, cos)));
  return clamp(angle / 2.0, 0, 1);
}

function handShapeFromLandmarks(landmarks) {
  if (!landmarks) return {...B_HAND};
  const index = fingerCurl(landmarks, 8, 6, 5);
  const middle = fingerCurl(landmarks, 12, 10, 9);
  const ring = fingerCurl(landmarks, 16, 14, 13);
  const pinky = fingerCurl(landmarks, 20, 18, 17);
  const thumb = fingerCurl(landmarks, 4, 3, 2);
  const curl = (index + middle + ring + pinky) / 4;
  // Flat / open fingers → B-hand (HELLO, THANK YOU, PLEASE)
  if (curl < 0.28) return {...B_HAND, thumb: Math.max(0.55, thumb)};
  return {thumb, index, middle, ring, pinky, curl, spread: 0.3};
}

/**
 * Collect hand candidates. Side is decided by image X later
 * (screen-left = person-right = avatar-right), not MediaPipe labels.
 */
function collectHands(pose, hands) {
  const out = [];
  if (Array.isArray(hands)) {
    for (const hand of hands) {
      const lm = hand.landmarks;
      if (!lm?.[0]) continue;
      const mid = lm[9] || lm[10] || lm[8] || lm[0];
      const tip = lm[8] || lm[12] || mid;
      // Use the higher of mid-hand and fingertip for lift.
      const height = (tip.y <= mid.y) ? tip : mid;
      out.push({
        wrist: lm[0],
        height,
        shapeLm: lm,
        x: mid.x,
        score: 1 - mid.y, // higher in frame = better
      });
    }
  }
  // Pose wrists / index tips as fallbacks
  for (const [wristIdx, tipIdx] of [[RW, RI], [LW, LI]]) {
    if (!visible(pose[wristIdx], 0.15) && !visible(pose[tipIdx], 0.15)) continue;
    const wrist = visible(pose[wristIdx], 0.15) ? pose[wristIdx] : pose[tipIdx];
    const tip = visible(pose[tipIdx], 0.15) ? pose[tipIdx] : wrist;
    const height = tip.y < wrist.y ? tip : wrist;
    out.push({
      wrist,
      height,
      shapeLm: null,
      x: height.x,
      score: 1 - height.y,
    });
  }
  return out;
}

function armFromHand(shoulderLm, hand, noseLm, hipLm, side) {
  const hang = side === 'R' ? HANG_R : HANG_L;
  if (!shoulderLm || !hand?.wrist) return {arm: hang, lift: 0};

  const shY = shoulderLm.y;
  const hY = hand.height?.y ?? hand.wrist.y;
  const noseY = noseLm?.y ?? shY - 0.16;
  const hipY = hipLm?.y ?? shY + 0.35;

  // 0 = hang at hip, 1 = at/above nose (temple)
  const span = Math.max(0.12, hipY - noseY);
  const lift = clamp((hipY - hY) / span, 0, 1.15);

  const chest = side === 'R' ? CHEST_R : CHEST_L;
  const chin = side === 'R' ? CHIN_R : CHIN_L;
  const temple = side === 'R' ? TEMPLE_R : TEMPLE_L;
  const waveIn = side === 'R' ? WAVE_IN_R : WAVE_IN_L;
  const waveOut = side === 'R' ? WAVE_OUT_R : WAVE_OUT_L;
  const thankOut = side === 'R' ? THANK_OUT_R : THANK_OUT_L;

  if (lift < 0.18) return {arm: hang, lift};

  let arm;
  if (lift < 0.42) {
    arm = lerpArm(hang, chest, (lift - 0.18) / 0.24);
  } else if (lift < 0.62) {
    arm = lerpArm(chest, chin, (lift - 0.42) / 0.2);
  } else {
    arm = lerpArm(chin, temple, clamp((lift - 0.62) / 0.28, 0, 1));
  }

  // HELLO wave: hand high and off to the side of the head
  if (lift > 0.7) {
    const dx = hand.wrist.x - shoulderLm.x;
    const waveT = side === 'R'
      ? clamp((-dx) / 0.12, 0, 1)
      : clamp(dx / 0.12, 0, 1);
    const waved = lerpArm(waveIn, waveOut, waveT);
    arm = lerpArm(arm, waved, clamp((lift - 0.7) / 0.2, 0, 1));
  }

  // THANK YOU: hand near face centerline → push forward
  if (lift > 0.4 && lift < 0.85) {
    const midX = (side === 'R' ? 0.42 : 0.58);
    const towardFace = 1 - clamp(Math.abs(hand.wrist.x - midX) / 0.2, 0, 1);
    const nearChin = 1 - clamp(Math.abs(hY - (noseY + 0.08)) / 0.14, 0, 1);
    const reach = towardFace * nearChin;
    if (reach > 0.25) arm = lerpArm(arm, thankOut, reach * 0.85);
  }

  return {arm, lift};
}

/**
 * @returns {{pose: object, confidence: number}|null}
 */
export function poseFromLandmarks(poseNorm, hands) {
  const p = poseNorm;
  if (!p?.length || !visible(p[LS]) || !visible(p[RS])) return null;

  const midShoulderX = (p[LS].x + p[RS].x) / 2;
  const candidates = collectHands(p, hands);
  // Deduplicate roughly overlapping detections; keep highest score.
  candidates.sort((a, b) => b.score - a.score);

  let right = null;
  let left = null;
  for (const c of candidates) {
    // Screen-left of mid-shoulder → person/avatar RIGHT hand.
    const isRight = c.x <= midShoulderX;
    if (isRight && !right) right = c;
    else if (!isRight && !left) left = c;
    if (right && left) break;
  }

  const nose = p[NOSE];
  const mappedR = armFromHand(p[RS], right, nose, p[RHIP], 'R');
  const mappedL = armFromHand(p[LS], left, nose, p[LHIP], 'L');

  // One-handed signs: if one side is clearly the signer, hang the other.
  if (mappedR.lift > 0.28 && mappedR.lift > mappedL.lift + 0.08) {
    mappedL.arm = HANG_L;
    mappedL.lift = 0;
    left = null;
  } else if (mappedL.lift > 0.28 && mappedL.lift > mappedR.lift + 0.08) {
    mappedR.arm = HANG_R;
    mappedR.lift = 0;
    right = null;
  }

  const confidence = Math.max(mappedR.lift, mappedL.lift);
  // Need a clearly raised (or chest-level) hand to trust live tracking.
  if (confidence < 0.22) return null;

  return {
    confidence,
    pose: {
      head: [0, 0, 0],
      shoulderL: mappedL.arm.shoulder,
      elbowL: mappedL.arm.elbow,
      wristL: mappedL.arm.wrist,
      shoulderR: mappedR.arm.shoulder,
      elbowR: mappedR.arm.elbow,
      wristR: mappedR.arm.wrist,
      handL: handShapeFromLandmarks(left?.shapeLm),
      handR: handShapeFromLandmarks(right?.shapeLm),
    },
  };
}

export function blendPoses(base, overlay, t) {
  if (!overlay) return base;
  if (!base) return overlay;
  const keys = ['head', 'shoulderL', 'elbowL', 'wristL', 'shoulderR', 'elbowR', 'wristR'];
  const out = {...base};
  for (const key of keys) {
    if (base[key] && overlay[key]) out[key] = lerpVec(base[key], overlay[key], t);
  }
  if (overlay.handL) out.handL = t > 0.4 ? overlay.handL : base.handL;
  if (overlay.handR) out.handR = t > 0.4 ? overlay.handR : base.handR;
  return out;
}

export async function createVideoRetargeter() {
  const vision = await import(`${VISION_CDN}/+esm`);
  const files = await vision.FilesetResolver.forVisionTasks(WASM);

  async function make(delegate) {
    const pose = await vision.PoseLandmarker.createFromOptions(files, {
      baseOptions: {modelAssetPath: POSE_MODEL, delegate},
      runningMode: 'VIDEO',
      numPoses: 1,
      minPoseDetectionConfidence: 0.3,
      minPosePresenceConfidence: 0.3,
      minTrackingConfidence: 0.3,
    });
    const hands = await vision.HandLandmarker.createFromOptions(files, {
      baseOptions: {modelAssetPath: HAND_MODEL, delegate},
      runningMode: 'VIDEO',
      numHands: 2,
      minHandDetectionConfidence: 0.25,
      minHandPresenceConfidence: 0.25,
      minTrackingConfidence: 0.25,
    });
    return {pose, hands};
  }

  let trackers;
  try {
    trackers = await make('GPU');
  } catch {
    trackers = await make('CPU');
  }

  let frameIndex = 0;
  let lastResult = null;

  return {
    detect(video) {
      if (!video || video.readyState < 2) return null;
      frameIndex += 1;
      try {
        const poseRes = trackers.pose.detectForVideo(video, frameIndex);
        const handRes = trackers.hands.detectForVideo(video, frameIndex);
        const norm = poseRes?.landmarks?.[0] || null;
        const handsOut = [];
        const landmarks = handRes?.landmarks || [];
        const handedness = handRes?.handednesses || handRes?.handedness || [];
        for (let i = 0; i < landmarks.length; i += 1) {
          const h = handedness[i];
          const cat = Array.isArray(h) ? h[0] : h;
          handsOut.push({
            landmarks: landmarks[i],
            handedness: cat?.categoryName || cat?.displayName || '',
          });
        }
        lastResult = {norm, hands: handsOut, ok: Boolean(norm)};
        return lastResult;
      } catch (error) {
        console.warn('sign-video-retarget', error);
        return lastResult;
      }
    },
    dispose() {
      try { trackers.pose?.close?.(); } catch { /* ignore */ }
      try { trackers.hands?.close?.(); } catch { /* ignore */ }
    },
  };
}
