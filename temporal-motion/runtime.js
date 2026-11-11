import {temporalFeatures} from './temporal-features.js';
// Frozen classifier for the limited camera validation preview.
export function bodyTipFeatures(row) {
  const frames = row.rawFrames, aspect = row.imageAspect;
  const wrists = frames.flatMap(f => f.filter(Boolean).map(h => [h[0].x, h[0].y * aspect]));
  const center = wrists.length ? [0,1].map(c => wrists.reduce((s,w) => s + w[c],0) / wrists.length) : [0,0];
  const vectors = frames.map((frame,t) => {
    const pose = row.body?.[t], good = Boolean(pose && Math.min(pose[1].visibility,pose[2].visibility) > .5);
    const origin = good ? [(pose[1].x+pose[2].x)/2,(pose[1].y+pose[2].y)*aspect/2] : center;
    const scale = good ? Math.max(.08,Math.hypot(pose[1].x-pose[2].x,(pose[1].y-pose[2].y)*aspect)) : .2;
    return frame.flatMap(h => h ? [
      ...[4,8,12,16,20].flatMap(tip => [(h[tip].x-origin[0])/scale,(h[tip].y*aspect-origin[1])/scale]),
      Math.hypot(h[5].x-h[17].x,(h[5].y-h[17].y)*aspect)/scale
    ] : Array(11).fill(0)).map(v => Number.isFinite(v) ? Math.max(-10,Math.min(10,v)) : 0);
  });
  const extra = Array.from({length:22},(_,c) => Array.from({length:32},(_,i) => {
    if (!vectors.length) return 0;
    const t = i*(vectors.length-1)/31, a = Math.floor(t), b = Math.min(a+1,vectors.length-1);
    return vectors[a][c]+(vectors[b][c]-vectors[a][c])*(t-a);
  }));
  return [...temporalFeatures(row),...extra];
}

export function residualMotionLogits(input, w) {
  function conv(x, weight, bias, dilation = 1) {
    const length = x[0].length, kernel = weight[0][0].length;
    const pad = Math.floor(kernel / 2) * dilation;
    return weight.map((row, out) => Array.from({length}, (_, t) => {
      let sum = bias[out];
      for (let c = 0; c < x.length; c++) for (let k = 0; k < kernel; k++) {
        const at = t + k * dilation - pad;
        if (at >= 0 && at < length) sum += x[c][at] * row[c][k];
      }
      return sum;
    }));
  }
  function gelu(x) {
    // erf approximation: maximum absolute erf error approximately 1.5e-7.
    const z = Math.abs(x) / Math.SQRT2, t = 1 / (1 + .3275911 * z);
    const erf = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t
      - .284496736) * t + .254829592) * t * Math.exp(-z * z);
    return .5 * x * (1 + (x < 0 ? -erf : erf));
  }
  function groupNorm(x, weight, bias) {
    const result = x.map(row => row.slice()), groupSize = x.length / 8;
    for (let group = 0; group < 8; group++) {
      const start = group * groupSize, count = groupSize * x[0].length;
      let mean = 0, variance = 0;
      for (let c = start; c < start + groupSize; c++) for (const v of x[c]) mean += v / count;
      for (let c = start; c < start + groupSize; c++) for (const v of x[c]) variance += (v - mean) ** 2 / count;
      const scale = Math.sqrt(variance + 1e-5);
      for (let c = start; c < start + groupSize; c++)
        result[c] = x[c].map(v => (v - mean) / scale * weight[c] + bias[c]);
    }
    return result;
  }
  const normalized = input.map((row, c) => row.map(v =>
    Math.max(-8, Math.min(8, (v - w.mean[0][c][0]) / w.scale[0][c][0]))));
  const delta = normalized.map(row => row.map((v, t) => t ? v - row[t - 1] : 0));
  let x = conv([...normalized, ...delta], w['project.weight'], w['project.bias']);
  for (let b = 0; b < 3; b++) {
    let branch = conv(x, w[`blocks.${b}.0.weight`], w[`blocks.${b}.0.bias`], 2 ** b);
    branch = groupNorm(branch, w[`blocks.${b}.1.weight`], w[`blocks.${b}.1.bias`]);
    branch = branch.map(row => row.map(gelu));
    branch = conv(branch, w[`blocks.${b}.4.weight`], w[`blocks.${b}.4.bias`], 2 ** b);
    x = x.map((row, c) => row.map((v, t) => gelu(v + branch[c][t])));
  }
  const pooled = [...x.map(row => row.reduce((a, b) => a + b, 0) / row.length),
    ...x.map(row => Math.max(...row))];
  return w['head.1.weight'].map((row, i) =>
    row.reduce((sum, v, c) => sum + v * pooled[c], w['head.1.bias'][i]));
}
