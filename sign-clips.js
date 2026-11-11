/**
 * Load Kai-native, animation-only GLB clips, including Studio Galt ASL mocap.
 * Original Kai bind axes are preserved by the offline retargeter.
 */
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

const CLIPS_BASE = './media/avatar/clips';
const CACHE_VER = '20261105-reference-3';
// Keep torso, head, arms, wrists and fingers; never translate the avatar or legs.
const KEEP_QUAT = /^(?:Spine\d*|Neck\d*|Head|(?:Left|Right)(?:Shoulder|Arm|ForeArm\d*|Hand(?:(?:Thumb|Index|Middle|Ring|Pinky)[1-4])?))\.quaternion$/;

const loader = new GLTFLoader();
const clipCache = new Map();
let indexPromise = null;

async function loadIndex() {
  if (!indexPromise) {
    indexPromise = fetch(`${CLIPS_BASE}/index.json?v=${CACHE_VER}`)
      .then((r) => (r.ok ? r.json() : {signs: {}}))
      .catch(() => ({signs: {}}));
  }
  return indexPromise;
}

export async function hasSkeletalClip(id) {
  const index = await loadIndex();
  return Boolean(index?.signs?.[id]?.file);
}

/**
 * @returns {Promise<{id: string, duration: number, animation: THREE.AnimationClip}|null>}
 */
export async function loadSkeletalClip(id) {
  if (clipCache.has(id)) return clipCache.get(id);

  const index = await loadIndex();
  const entry = index?.signs?.[id];
  if (!entry?.file || !/^[a-z0-9][a-z0-9_.-]*\.glb$/i.test(entry.file)) {
    clipCache.set(id, null);
    return null;
  }

  const url = `${CLIPS_BASE}/${entry.file}?v=${CACHE_VER}`;
  const promise = new Promise((resolve) => {
    loader.load(
      url,
      (gltf) => {
        try {
          const raw = pickAnimation(gltf.animations, id);
          if (!raw) {
            console.warn(`sign-clips: no animation in ${entry.file}`);
            resolve(null);
            return;
          }
          const animation = sanitizeUpperBodyClip(raw);
          if (!animation.tracks.length) {
            console.warn(`sign-clips: no usable upper-body tracks in ${entry.file}`);
            resolve(null);
            return;
          }
          const declaredDuration = Number(entry.duration);
          const duration = Number.isFinite(declaredDuration) && declaredDuration > 0
            ? declaredDuration
            : Math.max(0.2, animation.duration || 1);
          resolve({
            id, duration, animation, baked: false, skeletal: true,
            source: entry.source || null,
            approximation: entry.approximation === true,
            retargeted: entry.retargeted === true,
            independentTiming: entry.independentTiming === true,
            includesFingers: entry.includesFingers === true,
            learningOnly: entry.learningOnly === true,
            referenceVideo: entry.referenceVideo || null,
            lessonUrl: entry.lessonUrl || null,
            fps: entry.fps || null,
          });
        } catch (error) {
          console.warn('sign-clips: invalid clip', id, error);
          resolve(null);
        }
      },
      undefined,
      (error) => {
        console.warn('sign-clips', id, error);
        resolve(null);
      },
    );
  });

  clipCache.set(id, promise);
  return promise;
}

function pickAnimation(animations, id) {
  if (!animations?.length) return null;
  const want = ['Sign', 'sign', 'Vid2Anim_Motion', id, id.replace(/-/g, '_'), 'Armature|Sign', 'NlaTrack'];
  for (const name of want) {
    const hit = animations.find((a) => a.name === name || a.name?.endsWith(`|${name}`));
    if (hit) return hit;
  }
  // Prefer the longest clip if names don't match.
  return [...animations].sort((a, b) => (b.duration || 0) - (a.duration || 0))[0];
}

export function sanitizeUpperBodyClip(animation) {
  const tracks = animation.tracks.filter((track) =>
    KEEP_QUAT.test(track.name) && track.times?.length >= 2 &&
    track.values?.length === track.times.length * 4 &&
    track.times.every((time, i) => Number.isFinite(time) && time >= 0 && (i === 0 || time > track.times[i - 1])) &&
    track.values.every(Number.isFinite));
  // Clone so we don't mutate the GLTF cache if the loader reuses data.
  const cleaned = animation.clone();
  cleaned.tracks = tracks;
  cleaned.name = animation.name || 'Sign';
  return cleaned;
}

/** Prefetch known skeletal clips listed in index.json. */
export async function prefetchSkeletalClips() {
  const index = await loadIndex();
  const ids = Object.keys(index?.signs || {});
  await Promise.all(ids.map((id) => loadSkeletalClip(id)));
}
