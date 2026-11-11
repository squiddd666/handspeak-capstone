/** Exact source-video pairing for estimated Kai-native body/finger reconstructions.
 * Never substitute a different signer's mocap or guess anatomical sides by screen X.
 */
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {sanitizeUpperBodyClip} from './sign-clips.js?v=20261105-reference-3';

const BASE = './media/avatar/reference';
const VERSION = '20261105-reference-3';
const loader = new GLTFLoader();
const cache = new Map();
let indexPromise = null;

async function loadIndex() {
  if (!indexPromise) indexPromise = fetch(`${BASE}/index.json?v=${VERSION}`)
    .then(response => response.ok ? response.json() : {signs: {}})
    .catch(() => ({signs: {}}));
  return indexPromise;
}

export function sameReference(expected, actual, base = globalThis.document?.baseURI || 'https://handspeak.invalid/') {
  if (typeof expected !== 'string' || typeof actual !== 'string') return false;
  try {
    const a = new URL(expected, base), b = new URL(actual, base), origin = new URL(base).origin;
    return a.origin === origin && b.origin === origin && a.pathname === b.pathname;
  } catch { return false; }
}

function validEntry(id, entry, referenceURL) {
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id) &&
    entry?.id === id && /^[a-z0-9][a-z0-9_.-]*\.glb$/i.test(entry.file || '') &&
    entry.source?.kind === 'reference-video' && entry.referenceMatched === true &&
    entry.includesFingers === true && entry.retargeted === true && entry.independentTiming === false &&
    /^[a-f0-9]{64}$/.test(entry.reference?.sha256 || '') &&
    sameReference(entry.reference?.file, referenceURL);
}

export async function hasReferenceClip(id, referenceURL = `./media/signs/${id}.mp4`) {
  const index = await loadIndex();
  return validEntry(id, index?.signs?.[id], referenceURL);
}

export async function loadReferenceClip(id, referenceURL) {
  if (!referenceURL) return null;
  const index = await loadIndex(), entry = index?.signs?.[id];
  if (!validEntry(id, entry, referenceURL) || entry.targetModelSha256 !== index.targetModelSha256) return null;
  const key = `${id}|${referenceURL}`;
  if (cache.has(key)) return cache.get(key);
  const promise = new Promise(resolve => loader.load(`${BASE}/${entry.file}?v=${VERSION}`, gltf => {
    try {
      const metadata = gltf.parser?.json?.extras;
      if (metadata?.id !== id || metadata?.reference?.sha256 !== entry.reference.sha256 ||
          metadata?.targetModelSha256 !== index.targetModelSha256 ||
          !sameReference(metadata?.reference?.file, referenceURL)) { resolve(null); return; }
      const raw = gltf.animations?.find(clip => clip.name === 'Sign');
      if (!raw) { resolve(null); return; }
      const animation = sanitizeUpperBodyClip(raw);
      // Both wrists and all 30 weighted finger joints must be present; partial
      // animations must not be advertised as reference-matched hand motion.
      const names = new Set(animation.tracks.map(track => track.name));
      for (const side of ['Left', 'Right']) {
        for (const part of ['Shoulder', 'Arm', 'ForeArm', 'Hand']) {
          if (!names.has(`${side}${part}.quaternion`)) { resolve(null); return; }
        }
        for (const digit of ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']) {
          for (const joint of [1, 2, 3]) {
            if (!names.has(`${side}Hand${digit}${joint}.quaternion`)) { resolve(null); return; }
          }
        }
      }
      const duration = Number(entry.duration);
      if (!Number.isFinite(duration) || duration <= 0 || Math.abs(animation.duration - duration) > .01) {
        resolve(null); return;
      }
      resolve({id, duration, animation, skeletal: true, baked: false,
        source: entry.source, retargeted: true, includesFingers: true,
        referenceMatched: true, reconstructed: true, independentTiming: false,
        referenceVideo: referenceURL, reference: entry.reference, quality: entry.quality});
    } catch (error) {
      console.warn('sign-reference: invalid reconstruction', id, error);
      resolve(null);
    }
  }, undefined, () => resolve(null)));
  cache.set(key, promise);
  return promise;
}

export async function prefetchReferenceClips(ids = ['hello', 'please', 'thank-you', 'yes', 'no', 'finish']) {
  await Promise.all(ids.map(id => loadReferenceClip(id, `./media/signs/${id}.mp4`)));
}
