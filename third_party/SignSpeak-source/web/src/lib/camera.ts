export async function startCamera(videoEl: HTMLVideoElement): Promise<MediaStream> {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 640, height: 480, facingMode: "user" },
    audio: false,
  });
  videoEl.srcObject = stream;
  if (videoEl.readyState < 1) {
    await new Promise<void>((resolve) => {
      videoEl.onloadedmetadata = () => resolve();
    });
  }
  await videoEl.play();
  return stream;
}

/**
 * Throttled loop that hands the video element straight to the on-device
 * detector — no intermediate canvas copy (that copy + wasm readback was a
 * major mobile bottleneck). Training-time mirroring (cv2.flip) is reproduced
 * in the engine by flipping landmark x after detection.
 */
export function startDetectLoop({
  video,
  fps = 30,
  onFrame,
  onFps,
}: {
  video: HTMLVideoElement;
  fps?: number;
  onFrame: (video: HTMLVideoElement) => void;
  onFps?: (fps: number) => void;
}): () => void {
  const interval = 1000 / fps;
  let last = 0;
  let frames = 0;
  let fpsTick = performance.now();
  let running = true;

  function loop(now: number) {
    if (!running) return;
    if (now - last >= interval && video.readyState >= 2) {
      onFrame(video);
      last = now;
      frames++;
    }
    if (now - fpsTick >= 1000) {
      onFps?.(frames);
      frames = 0;
      fpsTick = now;
    }
    requestAnimationFrame(loop);
  }

  requestAnimationFrame(loop);
  return () => {
    running = false;
  };
}

export function startFrameLoop({
  video,
  fps = 30,
  onFrame,
  onFps,
}: {
  video: HTMLVideoElement;
  fps?: number;
  onFrame: (blob: Blob) => void;
  onFps?: (fps: number) => void;
}): () => void {
  const captureCanvas = document.createElement("canvas");
  captureCanvas.width = 320;
  captureCanvas.height = 240;
  const ctx = captureCanvas.getContext("2d");
  if (!ctx) return () => {};

  const interval = 1000 / fps;
  let last = 0;
  let frames = 0;
  let fpsTick = performance.now();
  let running = true;

  function loop(now: number) {
    if (!running) return;
    if (now - last >= interval) {
      ctx.save();
      ctx.translate(captureCanvas.width, 0);
      ctx.scale(-1, 1);
      ctx.drawImage(video, 0, 0, captureCanvas.width, captureCanvas.height);
      ctx.restore();
      captureCanvas.toBlob(
        (blob) => blob && onFrame(blob),
        "image/jpeg",
        0.7,
      );
      last = now;
      frames++;
    }
    if (now - fpsTick >= 1000) {
      onFps?.(frames);
      frames = 0;
      fpsTick = now;
    }
    requestAnimationFrame(loop);
  }

  requestAnimationFrame(loop);
  return () => {
    running = false;
  };
}
