const CONNECTIONS = [
  [0, 1], [1, 2], [2, 3], [3, 4],
  [0, 5], [5, 6], [6, 7], [7, 8],
  [0, 9], [9, 10], [10, 11], [11, 12],
  [0, 13], [13, 14], [14, 15], [15, 16],
  [0, 17], [17, 18], [18, 19], [19, 20],
  [5, 9], [9, 13], [13, 17],
];

export function setupOverlay(
  videoEl: HTMLVideoElement,
  canvasEl: HTMLCanvasElement,
): CanvasRenderingContext2D | null {
  const ctx = canvasEl.getContext("2d");
  const sync = () => {
    // Render at device resolution for crisp lines on high-DPI phones; the
    // canvas is CSS-stretched over the video, so draw in CSS pixels via the
    // transform below.
    const dpr = window.devicePixelRatio || 1;
    canvasEl.width = (videoEl.clientWidth || 640) * dpr;
    canvasEl.height = (videoEl.clientHeight || 360) * dpr;
    ctx?.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  sync();
  const ro = new ResizeObserver(sync);
  ro.observe(videoEl);
  return ctx;
}

export function drawLandmarks(
  ctx: CanvasRenderingContext2D | null,
  landmarks: number[][] | null | undefined,
  video: HTMLVideoElement,
) {
  if (!ctx) return;
  const w = video.clientWidth || ctx.canvas.width;
  const h = video.clientHeight || ctx.canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (!landmarks?.length) return;

  // The video uses object-cover: the camera frame is scaled to fill the box
  // and the overflow is cropped. Landmarks are normalized to the *frame*, so
  // apply the same cover transform or the skeleton draws small and offset
  // (exactly what happens on phones, where frame and box aspects differ a lot).
  const vw = video.videoWidth;
  const vh = video.videoHeight;
  if (!vw || !vh) return;
  const s = Math.max(w / vw, h / vh);
  const ox = (vw * s - w) / 2;
  const oy = (vh * s - h) / 2;
  const px = (nx: number) => nx * vw * s - ox;
  const py = (ny: number) => ny * vh * s - oy;

  // No shadowBlur here: canvas shadows force a slow software path on mobile
  // GPUs and this redraws up to 30×/s.
  ctx.strokeStyle = "#3CFF6A";
  ctx.fillStyle = "#3CFF6A";
  ctx.lineWidth = 3;

  ctx.beginPath();
  for (const [a, b] of CONNECTIONS) {
    const la = landmarks[a];
    const lb = landmarks[b];
    if (!la || !lb) continue;
    ctx.moveTo(px(la[0]), py(la[1]));
    ctx.lineTo(px(lb[0]), py(lb[1]));
  }
  ctx.stroke();

  for (const lm of landmarks) {
    ctx.beginPath();
    ctx.arc(px(lm[0]), py(lm[1]), 4, 0, Math.PI * 2);
    ctx.fill();
  }
}
