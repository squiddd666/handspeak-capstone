/**
 * Load offline-baked PopSign→Kai animation clips (media/avatar/baked/*.json).
 * Prefer these over hand-authored SIGN_ANIMATIONS when available.
 */

const BAKED_BASE = './media/avatar/baked';
const cache = new Map();
let indexPromise = null;

async function loadIndex() {
  if (!indexPromise) {
    indexPromise = fetch(`${BAKED_BASE}/index.json?v=20261104-bake-3`)
      .then((r) => (r.ok ? r.json() : {signs: {}}))
      .catch(() => ({signs: {}}));
  }
  return indexPromise;
}

export async function hasBakedAnimation(id) {
  const index = await loadIndex();
  return Boolean(index?.signs?.[id]);
}

export async function loadBakedAnimation(id) {
  if (cache.has(id)) return cache.get(id);
  const index = await loadIndex();
  const entry = index?.signs?.[id];
  if (!entry?.file) {
    cache.set(id, null);
    return null;
  }
  const url = `${BAKED_BASE}/${entry.file}?v=20261104-bake-3`;
  const promise = fetch(url)
    .then((r) => (r.ok ? r.json() : null))
    .then((clip) => {
      if (!clip?.frames?.length) return null;
      // Ensure duration is present for the avatar player.
      return {
        duration: Number(clip.duration) || 2,
        frames: clip.frames,
        baked: true,
        id: clip.id || id,
      };
    })
    .catch(() => null);
  cache.set(id, promise);
  return promise;
}

/** Prefetch core baked clips so the first play is instant. */
export function prefetchBaked(ids = ['hello', 'thank-you', 'please', 'yes', 'no', 'finish']) {
  return Promise.all(ids.map((id) => loadBakedAnimation(id)));
}
