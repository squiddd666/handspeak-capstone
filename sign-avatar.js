import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {SIGN_ANIMATIONS, REST_POSE} from './sign-animations.js?v=20261105-reference-3';
import {loadBakedAnimation, prefetchBaked} from './sign-baked.js?v=20261105-reference-3';
import {loadSkeletalClip, prefetchSkeletalClips} from './sign-clips.js?v=20261105-reference-3';
import {loadHandCleanup, prefetchHandCleanup} from './sign-hand-cleanup.js?v=20261105-reference-3';
import {loadReferenceClip, prefetchReferenceClips, sameReference} from './sign-reference.js?v=20261105-reference-3';

const JOINT_KEYS = ['head', 'shoulderL', 'elbowL', 'wristL', 'shoulderR', 'elbowR', 'wristR'];
const MODEL_URL = './media/avatar/signer.glb?v=20261105-reference-3';

function lerp(a, b, t) { return a + (b - a) * t; }
function lerpVec3(a, b, t) { return [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t)]; }

function handDefaults(shape = {}) {
  return {
    curl: shape.curl ?? 0.08,
    thumb: shape.thumb ?? 0.2,
    index: shape.index ?? shape.curl ?? 0.08,
    middle: shape.middle ?? shape.curl ?? 0.08,
    ring: shape.ring ?? shape.curl ?? 0.08,
    pinky: shape.pinky ?? shape.curl ?? 0.08,
    spread: shape.spread ?? 0.08,
  };
}

function lerpHand(a, b, t) {
  const A = handDefaults(a), B = handDefaults(b);
  return {
    curl: lerp(A.curl, B.curl, t), thumb: lerp(A.thumb, B.thumb, t),
    index: lerp(A.index, B.index, t), middle: lerp(A.middle, B.middle, t),
    ring: lerp(A.ring, B.ring, t), pinky: lerp(A.pinky, B.pinky, t),
    spread: lerp(A.spread, B.spread, t),
  };
}

function faceDefaults(face = {}) {
  return {blink: face.blink ?? 0, smile: face.smile ?? 0.2, brow: face.brow ?? 0};
}

function lerpFace(a, b, t) {
  const A = faceDefaults(a), B = faceDefaults(b);
  return {blink: lerp(A.blink, B.blink, t), smile: lerp(A.smile, B.smile, t), brow: lerp(A.brow, B.brow, t)};
}

function mergePose(base, overlay = {}) {
  return {
    head: overlay.head || base.head,
    shoulderL: overlay.shoulderL || base.shoulderL,
    elbowL: overlay.elbowL || base.elbowL,
    wristL: overlay.wristL || base.wristL,
    shoulderR: overlay.shoulderR || base.shoulderR,
    elbowR: overlay.elbowR || base.elbowR,
    wristR: overlay.wristR || base.wristR,
    handL: overlay.handL ? {...handDefaults(base.handL), ...overlay.handL} : handDefaults(base.handL),
    handR: overlay.handR ? {...handDefaults(base.handR), ...overlay.handR} : handDefaults(base.handR),
    handDetailL: overlay.handDetailL || base.handDetailL || null,
    handDetailR: overlay.handDetailR || base.handDetailR || null,
    handTrackedL: overlay.handTrackedL ?? base.handTrackedL ?? false,
    handTrackedR: overlay.handTrackedR ?? base.handTrackedR ?? false,
    face: faceDefaults(overlay.face || base.face),
  };
}

function sampleClip(clip, u) {
  const frames = clip.frames;
  if (!frames.length) return mergePose(REST_POSE);
  if (u <= frames[0].t) return mergePose(REST_POSE, frames[0]);
  if (u >= frames[frames.length - 1].t) return mergePose(REST_POSE, frames[frames.length - 1]);
  let i = 0;
  while (i < frames.length - 1 && frames[i + 1].t < u) i += 1;
  const a = frames[i], b = frames[i + 1];
  const t = (u - a.t) / Math.max(1e-6, b.t - a.t);
  const poseA = mergePose(REST_POSE, a), poseB = mergePose(REST_POSE, b);
  const out = {};
  for (const key of JOINT_KEYS) out[key] = lerpVec3(poseA[key], poseB[key], t);
  out.handL = lerpHand(poseA.handL, poseB.handL, t);
  out.handR = lerpHand(poseA.handR, poseB.handR, t);
  out.face = lerpFace(poseA.face, poseB.face, t);
  // Prefer the nearer keyframe's landmark-accurate hand detail (don't lerp quats poorly).
  const near = t < 0.5 ? a : b;
  out.handDetailL = near.handDetailL || null;
  out.handDetailR = near.handDetailR || null;
  out.handTrackedL = Boolean(near.handTrackedL);
  out.handTrackedR = Boolean(near.handTrackedR);
  return out;
}

function friendlyFaceFor(id) {
  if (['hello', 'thank-you', 'please', 'love', 'like', 'party'].includes(id)) return {smile: 0.55, brow: 0.12, blink: 0};
  if (['yes', 'finish', 'go'].includes(id)) return {smile: 0.35, brow: 0.05, blink: 0};
  if (['no', 'demand', 'hungry', 'pain', 'sick'].includes(id)) return {smile: 0.05, brow: 0.3, blink: 0};
  return {smile: 0.2, brow: 0, blink: 0};
}

function findBone(root, name) {
  // Supports Mixamo ("mixamorig:LeftArm" → "mixamorigLeftArm") and VRM/humanoid ("LeftArm") names.
  const bare = name.replace(/^mixamorig:/, 'mixamorig');
  return root.getObjectByName(bare) || root.getObjectByName(name) || null;
}

function firstBone(root, names) {
  for (const name of names) {
    const bone = findBone(root, name);
    if (bone) return bone;
  }
  return null;
}

function fingerChain(root, side, digit) {
  // Prefer VRM/humanoid names, then Mixamo.
  return [1, 2, 3].map((i) => firstBone(root, [
    `${side}Hand${digit}${i}`,
    `mixamorig${side}Hand${digit}${i}`,
    `mixamorig:${side}Hand${digit}${i}`,
  ])).filter(Boolean);
}

function boneMap(root) {
  const n = (...names) => firstBone(root, names);
  return {
    hips: n('Hips', 'mixamorigHips', 'mixamorig:Hips'),
    spine: n('Spine', 'mixamorigSpine', 'mixamorig:Spine'),
    spine2: n('Spine2', 'Spine1', 'mixamorigSpine2', 'mixamorigSpine1'),
    neck: n('Neck', 'Neck1', 'mixamorigNeck'),
    head: n('Head', 'mixamorigHead'),
    shoulderL: n('LeftArm', 'mixamorigLeftArm'),
    elbowL: n('LeftForeArm', 'mixamorigLeftForeArm'),
    wristL: n('LeftHand', 'mixamorigLeftHand'),
    shoulderR: n('RightArm', 'mixamorigRightArm'),
    elbowR: n('RightForeArm', 'mixamorigRightForeArm'),
    wristR: n('RightHand', 'mixamorigRightHand'),
    clavicleL: n('LeftShoulder', 'mixamorigLeftShoulder'),
    clavicleR: n('RightShoulder', 'mixamorigRightShoulder'),
    eyeL: n('LeftEye'),
    eyeR: n('RightEye'),
    fingersL: {
      thumb: fingerChain(root, 'Left', 'Thumb'),
      index: fingerChain(root, 'Left', 'Index'),
      middle: fingerChain(root, 'Left', 'Middle'),
      ring: fingerChain(root, 'Left', 'Ring'),
      pinky: fingerChain(root, 'Left', 'Pinky'),
    },
    fingersR: {
      thumb: fingerChain(root, 'Right', 'Thumb'),
      index: fingerChain(root, 'Right', 'Index'),
      middle: fingerChain(root, 'Right', 'Middle'),
      ring: fingerChain(root, 'Right', 'Ring'),
      pinky: fingerChain(root, 'Right', 'Pinky'),
    },
  };
}

function cacheBind(bones) {
  const walk = (obj) => {
    if (obj.isBone || obj.type === 'Bone') {
      obj.userData.bindQuat = obj.quaternion.clone();
      obj.userData.bindPos = obj.position.clone();
    }
    obj.children.forEach(walk);
  };
  Object.values(bones).forEach((b) => {
    if (!b) return;
    if (b.isBone || b.type === 'Bone') {
      b.userData.bindQuat = b.quaternion.clone();
      b.userData.bindPos = b.position.clone();
    }
  });
  // Also cache all finger bones
  for (const side of [bones.fingersL, bones.fingersR]) {
    if (!side) continue;
    for (const list of Object.values(side)) list.forEach((b) => {
      b.userData.bindQuat = b.quaternion.clone();
    });
  }
  if (bones.hips) walk(bones.hips);
}

function setBoneEuler(bone, x, y, z) {
  if (!bone || !bone.userData.bindQuat) return;
  const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(x, y, z, 'XYZ'));
  bone.quaternion.copy(bone.userData.bindQuat).multiply(q);
}

/**
 * Apply clip joint angles directly as Kai VRM local euler offsets.
 * Lifeprint-matched clips author values in this calibrated space
 * (hang / temple / chin / chest measured on signer.glb).
 */
function applyArmPose(bones, pose) {
  const rest = REST_POSE;
  const d = (key, i) => pose[key][i] - rest[key][i];

  setBoneEuler(bones.shoulderL, pose.shoulderL[0], pose.shoulderL[1], pose.shoulderL[2]);
  setBoneEuler(bones.elbowL, pose.elbowL[0], pose.elbowL[1], pose.elbowL[2]);
  setBoneEuler(bones.wristL, pose.wristL[0], pose.wristL[1], pose.wristL[2]);

  setBoneEuler(bones.shoulderR, pose.shoulderR[0], pose.shoulderR[1], pose.shoulderR[2]);
  setBoneEuler(bones.elbowR, pose.elbowR[0], pose.elbowR[1], pose.elbowR[2]);
  setBoneEuler(bones.wristR, pose.wristR[0], pose.wristR[1], pose.wristR[2]);

  setBoneEuler(bones.clavicleL, 0.03 + d('shoulderL', 0) * 0.05, 0.02, 0.08 + d('shoulderL', 2) * 0.06);
  setBoneEuler(bones.clavicleR, 0.03 + d('shoulderR', 0) * 0.05, -0.02, -0.08 + d('shoulderR', 2) * 0.06);

  setBoneEuler(bones.head, pose.head[0], pose.head[1], pose.head[2]);
  setBoneEuler(bones.neck, pose.head[0] * 0.28, pose.head[1] * 0.22, pose.head[2] * 0.22);
}

function applyHandShape(fingers, shape, sideSign) {
  if (!fingers) return;
  const s = handDefaults(shape);
  const amounts = {thumb: s.thumb, index: s.index, middle: s.middle, ring: s.ring, pinky: s.pinky};
  const spread = {
    index: 0.18 * s.spread * sideSign,
    middle: 0.04 * s.spread * sideSign,
    ring: -0.1 * s.spread * sideSign,
    pinky: -0.22 * s.spread * sideSign,
  };

  for (const [name, amount] of Object.entries(amounts)) {
    const bones = fingers[name];
    if (!bones?.length) continue;
    if (name === 'thumb') {
      // Higher thumb → across the palm (B-hand); low → beside.
      const oppose = Math.max(0, amount - 0.2);
      setBoneEuler(bones[0], amount * 0.4 + oppose * 0.3, -oppose * 0.95 * sideSign, amount * 0.25);
      if (bones[1]) setBoneEuler(bones[1], amount * 0.75, 0, 0);
      if (bones[2]) setBoneEuler(bones[2], amount * 0.6, 0, 0);
    } else {
      // Near-zero curl straightens Kai's bind; tiny adduction keeps fingers together.
      const bend = amount < 0.1 ? (amount - 0.1) * 1.1 : amount * 1.2;
      const adduct = (spread[name] || 0) - 0.04 * sideSign * (amount < 0.15 ? 1 : 0);
      setBoneEuler(bones[0], bend * 0.95, adduct, 0);
      if (bones[1]) setBoneEuler(bones[1], bend * 1.0, 0, 0);
      if (bones[2]) setBoneEuler(bones[2], bend * 0.85, 0, 0);
    }
  }
}

function applyFace(model, face, time) {
  const f = faceDefaults(face);
  const pulse = Math.sin(time * 1.7) * 0.5 + Math.sin(time * 0.33) * 0.5;
  const autoBlink = pulse > 0.93 ? Math.min(1, (pulse - 0.93) / 0.07) : 0;
  const blink = Math.min(1, Math.max(f.blink, autoBlink));
  const smile = f.smile;
  const brow = f.brow;

  model.traverse((obj) => {
    if (!obj.isMesh || !obj.morphTargetDictionary || !obj.morphTargetInfluences) return;
    const dict = obj.morphTargetDictionary;
    const infl = obj.morphTargetInfluences;
    const set = (keys, value) => {
      for (const key of keys) {
        if (dict[key] != null) infl[dict[key]] = value;
      }
    };
    // ARKit / VRM / generic morph names
    set(['eyeBlinkLeft', 'blink', 'Blink', 'eyesClosed'], blink);
    set(['eyeBlinkRight'], blink);
    set(['mouthSmileLeft', 'mouthSmile', 'smile', 'Smile', 'mouthSmileRight'], smile * 0.85);
    set(['mouthSmileRight'], smile * 0.85);
    set(['browInnerUp', 'browOuterUpLeft', 'browOuterUpRight', 'browUp', 'BrowsUp'], brow * 0.7);
    set(['cheekSquintLeft', 'cheekSquintRight'], smile * 0.25);
  });
}

function applyIdle(bones, time, signing) {
  if (!bones?.spine2 && !bones?.spine) return;
  const breathe = Math.sin(time * 1.35) * (signing ? 0.008 : 0.018);
  const sway = Math.sin(time * 0.55) * (signing ? 0.01 : 0.03);
  setBoneEuler(bones.spine2 || bones.spine, breathe, sway * 0.35, 0);
  if (!signing) {
    setBoneEuler(bones.neck, breathe * 0.4, sway * 0.5, 0);
    setBoneEuler(bones.head, breathe * 0.2, sway * 0.25, 0);
  }
}

function prepareModel(gltf, camera, controls) {
  const root = gltf.scene;
  root.name = 'signer';

  root.traverse((obj) => {
    if (!obj.isMesh) return;
    obj.castShadow = true;
    obj.receiveShadow = true;
    obj.frustumCulled = false;
    if (!obj.material) return;
    const mats = Array.isArray(obj.material) ? obj.material : [obj.material];
    const fixed = mats.map((m) => {
      if (m.map) m.map.colorSpace = THREE.SRGBColorSpace;
      // Keep standard/physical mats; rebuild unknown/custom (e.g. MToon) so Kai is visible.
      const type = m.type || m.constructor?.name || '';
      if (type === 'MeshStandardMaterial' || type === 'MeshPhysicalMaterial' || type === 'MeshBasicMaterial') {
        m.side = THREE.DoubleSide;
        // Ensure textures are ready; force a visible albedo if map missing/unusable.
        if (!m.map) m.color = new THREE.Color(0xd4a574);
        else m.color = new THREE.Color(0xffffff);
        m.roughness = Math.min(m.roughness ?? 0.7, 0.85);
        m.metalness = 0;
        m.envMapIntensity = 1;
        m.needsUpdate = true;
        return m;
      }
      const map = m.map || null;
      const std = new THREE.MeshStandardMaterial({
        name: m.name,
        map,
        color: map ? 0xffffff : (m.color?.clone?.() || new THREE.Color(0xc4a484)),
        roughness: 0.65,
        metalness: 0.05,
        side: THREE.DoubleSide,
        transparent: Boolean(m.transparent),
        opacity: m.opacity ?? 1,
      });
      if (obj.isSkinnedMesh) std.skinning = true;
      if (obj.morphTargetInfluences?.length) {
        std.morphTargets = true;
        std.morphNormals = true;
      }
      if (m.normalMap) std.normalMap = m.normalMap;
      std.needsUpdate = true;
      return std;
    });
    obj.material = Array.isArray(obj.material) ? fixed : fixed[0];
  });

  // Normalize to ~1.7 m tall, feet on ground, centered
  root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(root);
  const size = new THREE.Vector3();
  box.getSize(size);
  const scale = 1.7 / Math.max(size.y, 0.001);
  root.scale.setScalar(scale);
  root.updateMatrixWorld(true);

  const box2 = new THREE.Box3().setFromObject(root);
  const center = new THREE.Vector3();
  box2.getCenter(center);
  root.position.x += -center.x;
  root.position.z += -center.z;
  root.position.y += -box2.min.y;
  root.updateMatrixWorld(true);

  const bones = boneMap(root);
  cacheBind(bones);

  // Frame upper body from the head bone so hands stay in view
  const focus = new THREE.Vector3();
  if (bones.head) bones.head.getWorldPosition(focus);
  else box2.getCenter(focus);
  focus.y -= 0.18; // upper chest ? keeps head + both signing hands in frame
  controls.target.copy(focus);
  camera.position.set(focus.x, focus.y + 0.05, focus.z + 2.25);
  camera.fov = 30;
  camera.near = 0.05;
  camera.far = 40;
  camera.updateProjectionMatrix();
  controls.minDistance = 1.3;
  controls.maxDistance = 4.0;
  controls.update();

  return {root, bones, animations: gltf.animations || [], focus: focus.clone()};
}

export function createSignAvatar(canvas) {
  const stage = canvas.parentElement;
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: true,
    preserveDrawingBuffer: true,
    powerPreference: 'high-performance',
  });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setClearColor(0x000000, 0);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.outputColorSpace = THREE.SRGBColorSpace;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(28, 3 / 4, 0.05, 40);
  // Upper-body framing: head + torso + both hands
  camera.position.set(0, 1.28, 2.55);

  const controls = new OrbitControls(camera, canvas);
  controls.target.set(0, 1.12, 0);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.minDistance = 1.4;
  controls.maxDistance = 4.2;
  controls.minPolarAngle = 0.7;
  controls.maxPolarAngle = 1.75;
  controls.enablePan = false;
  controls.update();

  scene.add(new THREE.AmbientLight(0xffffff, 0.85));
  scene.add(new THREE.HemisphereLight(0xffffff, 0x445566, 0.9));
  const key = new THREE.DirectionalLight(0xfff3e8, 1.6);
  key.position.set(1.6, 3.2, 2.4);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.radius = 3;
  scene.add(key);
  const fill = new THREE.DirectionalLight(0xb5ddd4, 0.9);
  fill.position.set(-2.0, 1.4, 1.2);
  scene.add(fill);
  const rim = new THREE.DirectionalLight(0xdde8ff, 0.7);
  rim.position.set(-0.6, 2.0, -2.4);
  scene.add(rim);

  const ground = new THREE.Mesh(
    new THREE.CircleGeometry(1.4, 48),
    new THREE.MeshStandardMaterial({color: 0x152420, roughness: 0.95, transparent: true, opacity: 0.45}),
  );
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = 0;
  ground.receiveShadow = true;
  scene.add(ground);

  let avatar = null;
  let ready = false;
  let loadError = null;
  let speed = 1, loop = false, playing = false, elapsed = 0;
  let currentId = 'hello', clip = SIGN_ANIMATIONS.hello;
  let usingBaked = false;
  let usingSkeletal = false;
  let handOverlay = null; // authored/baked clip used for ASL fingers + wrists on skeletal body
  let mixer = null;
  let mixerAction = null;
  let raf = 0, last = 0, clock = 0;
  let onStatus = () => {};
  let syncVideo = null;
  let endedNotified = false;
  let retargetMode = false;
  let clipRevision = 0;
  let disposed = false;

  // Prefetch skeletal GLBs + baked/cleanup JSON (non-blocking).
  prefetchHandCleanup().catch(() => {});
  prefetchSkeletalClips().catch(() => {});
  prefetchBaked().catch(() => {});
  prefetchReferenceClips().catch(() => {});

  function stopMixer() {
    if (mixerAction) {
      mixerAction.stop();
      mixerAction = null;
    }
    if (mixer) mixer.stopAllAction();
  }

  function resetBonesToBind() {
    if (!avatar?.root) return;
    // Mocap also drives Spine1 and other joints outside the procedural bone map.
    avatar.root.traverse((bone) => {
      if (!bone.isBone || !bone.userData?.bindQuat) return;
      bone.quaternion.copy(bone.userData.bindQuat);
      if (bone.userData.bindPos) bone.position.copy(bone.userData.bindPos);
    });
  }

  function startMixerClip(skeletal) {
    if (!avatar?.root || !skeletal?.animation) return false;
    if (!mixer) mixer = new THREE.AnimationMixer(avatar.root);
    stopMixer();
    resetBonesToBind();
    mixerAction = mixer.clipAction(skeletal.animation);
    mixerAction.enabled = true;
    mixerAction.setLoop(THREE.LoopOnce, 0);
    mixerAction.clampWhenFinished = true;
    mixerAction.paused = true; // scrub manually from mocap time or a matched video
    mixerAction.play();
    return true;
  }

  /**
   * Prefer Kai-native reconstruction of the actual displayed reference first.
   * Without that reference, retain captured/authored/baked fallback. Resolution is side-effect
   * free so a late response cannot change the currently selected sign's flags.
   */
  async function resolveClip(id, referenceURL = null) {
    if (referenceURL) {
      const reference = await loadReferenceClip(id, referenceURL);
      if (reference?.referenceMatched && reference?.animation) {
        return {clip: reference, skeletal: true, baked: false, overlay: null};
      }
    }
    const authored = SIGN_ANIMATIONS[id] || null;
    const skeletal = await loadSkeletalClip(id);
    // When the UI asked for the displayed reference, never substitute a
    // different-performance Studio Galt clip (independentTiming) — that is what
    // made Kai's hands disagree with the video. Prefer authored/baked instead.
    const allowIndependentMocap = !referenceURL;
    if (skeletal?.retargeted && skeletal?.animation && (allowIndependentMocap || !skeletal.independentTiming)) {
      return {clip: skeletal, skeletal: true, baked: false, overlay: null};
    }
    if (authored?.frames?.length) {
      return {clip: authored, skeletal: false, baked: false, overlay: null};
    }
    const [baked, cleaned] = await Promise.all([loadBakedAnimation(id), loadHandCleanup(id)]);
    if (baked?.frames?.length) {
      return {clip: baked, skeletal: false, baked: true, overlay: cleaned?.frames?.length ? cleaned : null};
    }
    if (skeletal?.animation && (allowIndependentMocap || !skeletal.independentTiming)) {
      return {clip: skeletal, skeletal: true, baked: false, overlay: cleaned?.frames?.length ? cleaned : null};
    }
    return null;
  }

  function currentPose(u) {
    const pose = sampleClip(clip, u);
    pose.face = {...faceDefaults(pose.face), ...friendlyFaceFor(currentId), ...pose.face};
    return pose;
  }

  function apply(pose, signing = false) {
    if (!avatar) return;
    applyArmPose(avatar.bones, pose);
    applyHandShape(avatar.bones.fingersL, pose.handL, -1);
    applyHandShape(avatar.bones.fingersR, pose.handR, 1);
    applyFace(avatar.root, pose.face, clock);
    applyIdle(avatar.bones, clock, signing);
  }

  function applyHandOverlay(u) {
    // Kai-native captured/authored clips own their fingers; never overwrite them.
    if (!avatar || clip?.retargeted || clip?.includesFingers || !handOverlay?.frames?.length) return false;
    const pose = sampleClip(handOverlay, u);
    for (const side of ['L', 'R']) {
      const handKey = `hand${side}`, wristKey = `wrist${side}`;
      const fingers = avatar.bones[`fingers${side}`];
      if (handOverlay.frames.some((frame) => frame[handKey])) {
        applyHandShape(fingers, pose[handKey], side === 'L' ? -1 : 1);
      }
      if (handOverlay.frames.some((frame) => Array.isArray(frame[wristKey]))) {
        setBoneEuler(avatar.bones[wristKey], ...pose[wristKey]);
      }
      // Optional cleanup uses Kai-local XYZ Euler offsets, not world rotations.
      const detail = pose[`handDetail${side}`];
      if (detail && typeof detail === 'object') {
        for (const name of ['thumb', 'index', 'middle', 'ring', 'pinky']) {
          for (const [i, angles] of (Array.isArray(detail[name]) ? detail[name] : []).entries()) {
            if (Array.isArray(angles) && angles.length === 3 && angles.every(Number.isFinite)) {
              setBoneEuler(fingers?.[name]?.[i], ...angles);
            }
          }
        }
      }
    }
    return true;
  }

  /** Lock motion to the reference video timeline (skeletal scrub or euler sample). */
  function applySyncedToVideo() {
    // A different publisher's reference video is not this mocap's time source.
    if (!avatar || !syncVideo || clip?.independentTiming) return false;
    if (clip?.referenceMatched && !sameReference(clip.referenceVideo,
        syncVideo.getAttribute?.('src') || syncVideo.currentSrc)) return false;
    const videoU = progressFromVideo();
    if (videoU == null) return false;
    const u = Math.min(1, Math.max(0, videoU));

    if (usingSkeletal && mixer && mixerAction && clip?.animation) {
      const duration = Math.max(0.2, clip.duration || clip.animation.duration || 1);
      mixerAction.time = u * duration;
      mixer.update(0);
      applyHandOverlay(u);
      applyFace(avatar.root, friendlyFaceFor(currentId), clock);
      retargetMode = true;
      return true;
    }

    if (!clip?.frames) return false;
    apply(currentPose(u), true);
    // Video / ASL finger overlay (always for flat B-hand signs).
    applyHandOverlay(u);
    retargetMode = true;
    return true;
  }

  function resize() {
    const width = stage.clientWidth || 300;
    const height = stage.clientHeight || Math.round(width * 4 / 3);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
  }

  function progressFromVideo() {
    const el = syncVideo;
    if (!el || !Number.isFinite(el.duration) || el.duration <= 0) return null;
    if (el.ended && !el.loop) return 1;
    // Reconstructed tracks use the reference's original seconds. Do not stretch
    // a different performance to fit it, or advance a second independent clock.
    const duration = clip?.referenceMatched ? clip.duration : el.duration;
    return Math.min(1, Math.max(0, el.currentTime / duration));
  }

  function tick(now) {
    raf = requestAnimationFrame(tick);
    const dt = Math.min(0.05, (now - last) / 1000 || 0);
    last = now;
    clock += dt;
    controls.update();

    let pose = mergePose(REST_POSE, {face: friendlyFaceFor(currentId)});
    let usedVideo = false;

    // Scrub 3D to the reference video timeline even while paused (seeking).
    if (ready && syncVideo && syncVideo.readyState >= 2 && clip && !clip.independentTiming) {
      usedVideo = applySyncedToVideo();
      const videoU = progressFromVideo();
      if (videoU != null) {
        elapsed = videoU * Math.max(0.2, clip?.duration || 1);
        if (playing && videoU >= 0.999 && !syncVideo.loop && !endedNotified) {
          endedNotified = true;
          playing = false;
          onStatus('ended');
        } else if (videoU < 0.05) {
          endedNotified = false;
        }
      }
    }

    if (playing && clip && ready && !usedVideo) {
      retargetMode = false;
      elapsed += dt * speed;
      const duration = Math.max(0.2, clip.duration || clip.animation?.duration || 1);
      let u = elapsed / duration;
      if (u >= 1) {
        if (loop) { elapsed = 0; u = 0; }
        else {
          elapsed = duration;
          playing = false;
          if (usingSkeletal && mixerAction) {
            mixerAction.time = duration;
            mixer.update(0);
          } else {
            apply(currentPose(1), false);
          }
          onStatus('ended');
          renderer.render(scene, camera);
          return;
        }
      }
      if (usingSkeletal && mixer && mixerAction && clip?.animation) {
        mixerAction.time = Math.min(1, u) * duration;
        mixer.update(0);
        applyHandOverlay(Math.min(1, u));
        applyFace(avatar.root, friendlyFaceFor(currentId), clock);
      } else if (clip?.frames) {
        apply(currentPose(Math.min(1, u)), true);
        if (handOverlay) applyHandOverlay(Math.min(1, u));
      }
    } else if (ready && !usedVideo) {
      retargetMode = false;
      // Hold the current pose when paused/finished instead of snapping to rest.
      if (usingSkeletal && mixer && mixerAction && clip?.animation) {
        mixerAction.time = Math.min(elapsed, Math.max(0.2, clip.duration || 1));
        mixer.update(0);
        applyFace(avatar.root, friendlyFaceFor(currentId), clock);
      } else if (clip?.frames && elapsed > 0) {
        apply(currentPose(Math.min(1, elapsed / Math.max(0.2, clip.duration || 1))), false);
        if (handOverlay) applyHandOverlay(Math.min(1, elapsed / Math.max(0.2, clip.duration || 1)));
      } else {
        apply(pose, false);
      }
    } else if (ready && usedVideo && !playing) {
      applyFace(avatar.root, friendlyFaceFor(currentId), clock);
    }

    renderer.render(scene, camera);
  }

  const ro = new ResizeObserver(resize);
  ro.observe(stage);
  resize();
  raf = requestAnimationFrame(tick);

  const loader = new GLTFLoader();
  loader.load(
    MODEL_URL,
    (gltf) => {
      if (disposed) return;
      try {
        avatar = prepareModel(gltf, camera, controls);
        scene.add(avatar.root);
        ready = true;
        if (usingSkeletal && clip?.animation) startMixerClip(clip);
        else apply(mergePose(REST_POSE, {face: friendlyFaceFor(currentId)}));
        if (playing) onStatus('playing');
        else onStatus('ready');
      } catch (error) {
        console.warn(error);
        loadError = error;
        onStatus('missing');
      }
    },
    undefined,
    (error) => {
      console.warn(error);
      loadError = error;
      onStatus('missing');
    },
  );

  const api = {
    get ready() { return ready; },
    get currentId() { return currentId; },
    get playing() { return playing; },
    measureHandSpread() {
      if (!avatar?.bones) return null;
      const fr = avatar.bones.fingersR || {};
      avatar.root.updateMatrixWorld(true);
      const tip = (chain) => {
        const b = chain?.[chain.length - 1];
        if (!b) return null;
        const v = new THREE.Vector3();
        b.getWorldPosition(v);
        return new THREE.Vector3(0, 0.03, 0).applyQuaternion(b.getWorldQuaternion(new THREE.Quaternion())).add(v);
      };
      const i = tip(fr.index);
      const p = tip(fr.pinky);
      return i && p ? i.distanceTo(p) : null;
    },
    /** Debug: force B-hand; optional flipZ; returns world tip spread. */
    debugHands({flipZ = false} = {}) {
      if (!avatar?.bones) return null;
      const fr = avatar.bones.fingersR || {};
      const counts = Object.fromEntries(Object.entries(fr).map(([k, v]) => [k, v?.length || 0]));
      applyHandShape(fr, {curl: 0.02, thumb: 0.88, spread: 0}, 1);
      if (flipZ) {
        for (const chain of Object.values(fr)) {
          for (const bone of chain || []) {
            const offset = bone.userData.bindQuat.clone().invert().multiply(bone.quaternion);
            const angles = new THREE.Euler().setFromQuaternion(offset, 'XYZ');
            setBoneEuler(bone, angles.x, angles.y, -angles.z);
          }
        }
      }
      return {counts, spread: api.measureHandSpread(), flipZ, usingBaked, usingSkeletal, hasOverlay: Boolean(handOverlay)};
    },
    setStatusHandler(fn) { onStatus = typeof fn === 'function' ? fn : () => {}; },
    play(id, options = {}) {
      if (loadError || disposed) { onStatus('missing'); return false; }
      if (typeof id !== 'string' || !/^[a-z0-9-]+$/.test(id)) { onStatus('missing'); return false; }
      const revision = ++clipRevision;
      const referenceURL = typeof options.reference === 'string' ? options.reference : null;
      const cached = clip?.id === id && clip.retargeted &&
        (referenceURL ? clip.referenceMatched && clip.referenceVideo === referenceURL : !clip.referenceMatched) ? clip : null;
      currentId = id;
      // Do not flash the old, mismatched gesture while its reference loads.
      clip = cached || (referenceURL ? null : SIGN_ANIMATIONS[id]) || null;
      usingBaked = false;
      usingSkeletal = Boolean(cached);
      handOverlay = null;
      retargetMode = false;
      stopMixer();
      if (usingSkeletal && avatar) startMixerClip(clip);
      elapsed = 0;
      endedNotified = false;
      playing = true;
      canvas.setAttribute('aria-label', `${id.replace(/-/g, ' ').toUpperCase()} ASL 3D gesture example`);
      onStatus(ready && clip ? 'playing' : 'loading');
      resolveClip(id, referenceURL).then((next) => {
        if (disposed || currentId !== id || clipRevision !== revision) return;
        if (!next) { playing = false; onStatus('missing'); return; }
        const changed = clip !== next.clip;
        clip = next.clip;
        usingSkeletal = next.skeletal;
        usingBaked = next.baked;
        handOverlay = next.overlay;
        retargetMode = false;
        if (changed) elapsed = 0;
        if (usingSkeletal && clip.animation) {
          if (avatar && (changed || !mixerAction)) startMixerClip(clip);
        } else {
          stopMixer();
          if (avatar && changed) resetBonesToBind();
        }
        if (ready && playing) onStatus('playing');
      }).catch((error) => {
        if (disposed || clipRevision !== revision) return;
        console.warn('sign-avatar: motion could not load', id, error);
        // Network failure preserves an existing authored fallback.
        if (!clip) { playing = false; onStatus('missing'); }
      });
      return true;
    },
    replay() {
      if (!clip) return false;
      elapsed = 0;
      endedNotified = false;
      playing = true;
      if (usingSkeletal && clip?.animation && avatar) startMixerClip(clip);
      onStatus(ready ? 'playing' : 'loading');
      return true;
    },
    pause() { playing = false; onStatus('paused'); },
    setSpeed(value) { speed = Number(value) || 1; },
    setLoop(value) { loop = Boolean(value); },
    /** Keep 3D motion locked to a reference <video>. */
    setSyncVideo(el) { syncVideo = el || null; },
    get retargeting() { return (usingBaked || usingSkeletal) && retargetMode; },
    get videoSynced() { return retargetMode; },
    get usingBaked() { return usingBaked && !usingSkeletal; },
    get usingSkeletal() { return usingSkeletal; },
    get mocap() { return usingSkeletal && clip?.source?.kind === 'studio-galt'; },
    get referenceMatched() { return usingSkeletal && clip?.referenceMatched === true; },
    get reconstructionQuality() { return clip?.referenceMatched ? clip.quality : null; },
    get approximate() {
      return usingSkeletal
        ? clip?.reconstructed === true || clip?.approximation === true || clip?.source?.kind === 'authored'
        : !usingBaked && Boolean(clip?.frames?.length);
    },
    get motionSource() { return clip?.source?.name || (usingBaked ? 'Baked reference' : 'Hand-authored'); },
    dispose() {
      disposed = true;
      clipRevision++;
      cancelAnimationFrame(raf);
      stopMixer();
      mixer = null;
      ro.disconnect();
      controls.dispose();
      renderer.dispose();
    },
  };
  if (typeof window !== 'undefined') window.__hsAvatar = api;
  return api;
}
