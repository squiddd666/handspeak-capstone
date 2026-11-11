import {recognizeMotion} from './motion-model.js?v=20261109-vm-sync-1';

// The expanded vocabulary competes only when the user enables the preview.
const compatibilityMatch=(sequence,profile)=>profile&&recognizeMotion(sequence,profile.samples,profile.parameters);

export function recognizeExpandedMotion(sequence, examples, parameters, expansion, baseCompatibility=null) {
  const basePractice = compatibilityMatch(sequence,baseCompatibility);
  const existing = recognizeMotion(sequence, examples, parameters);
  if (!expansion) return existing || basePractice;
  const extraPractice=compatibilityMatch(sequence,expansion.cameraCompatibility);
  if(extraPractice)return extraPractice;
  if (expansion.baselineExtra) {
    // Score default-six and extra-seven separately. When both pass their gates,
    // take the closer distance so PLEASE/YES are not stolen by looser extra
    // cutoffs (HUNGRY 1.5). When default has no match under its tighter gate,
    // accept extra-only so HUNGRY still works if PLEASE is a nearer joint
    // neighbor but above maxDistance 0.8.
    const extraLabels = new Set(expansion.labels || expansion.samples.map(s => s.label));
    const extraOnly = recognizeMotion(sequence, expansion.samples, expansion.parameters);
    if (existing && extraOnly) {
      return extraOnly.distance < existing.distance ? extraOnly : existing;
    }
    if (existing) return existing;
    if (extraOnly) return extraOnly;
    const joint = recognizeMotion(sequence, examples.concat(expansion.samples), expansion.parameters);
    if (joint && extraLabels.has(joint.label)) return joint;
    const prior = expansion.baselineExtra;
    const priorOnly = recognizeMotion(sequence, prior.samples, prior.parameters);
    if (priorOnly) return priorOnly;
    return null;
  }
  const match = recognizeMotion(sequence, examples.concat(expansion.samples), expansion.parameters);
  return match || existing || basePractice;
}
