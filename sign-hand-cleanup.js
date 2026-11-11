/**
 * Blender-authored PopSign finger/palm cleanup overlays.
 * Preferred over MediaPipe bake for core-sign hand detail.
 */

const CLEAN_BASE = './media/avatar/hand_cleanup';
const CACHE_VER = '20261105-hamer-blender-1';
const cache = new Map();
let indexPromise = null;

async function loadIndex() {
  if (!indexPromise) {
    indexPromise = fetch(`${CLEAN_BASE}/index.json?v=${CACHE_VER}`)
      .then((r) => (r.ok ? r.json() : {signs: {}}))
      .catch(() => ({signs: {}}));
  }
  return indexPromise;
}

export async function loadHandCleanup(id) {
  if (cache.has(id)) return cache.get(id);
  const index = await loadIndex();
  const entry = index?.signs?.[id];
  if (!entry?.file) {
    cache.set(id, null);
    return null;
  }
  const promise = fetch(`${CLEAN_BASE}/${entry.file}?v=${CACHE_VER}`)
    .then((r) => (r.ok ? r.json() : null))
    .then((clip) => {
      if (!clip?.frames?.length) return null;
      return {
        duration: Number(clip.duration) || 2,
        frames: clip.frames,
        cleaned: true,
        id: clip.id || id,
      };
    })
    .catch(() => null);
  cache.set(id, promise);
  return promise;
}

export function prefetchHandCleanup(ids = ['hello', 'thank-you', 'please', 'yes', 'no', 'finish']) {
  return Promise.all(ids.map((id) => loadHandCleanup(id)));
}
