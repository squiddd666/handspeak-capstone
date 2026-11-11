# Target-20 V6 timestamp audit

Browser capture uses the video source clock, not callback completion time. V6 accepts strictly increasing finite numeric milliseconds and retains original times; it produces a uniform 32-step grid within the observed hand span. Velocities are normalized coordinate units per second. Source gaps over 200 ms are not interpolated; timestamps are not fabricated. Dropped frames up to the gap bound are interpolated only within a contiguous visible run. Processing delay can still reduce frame coverage even when timestamps are correct.

Validation browser encodings: 19. Median of the maximum gap per encoded clip: 120.9 ms. Largest observed source gap among those encodings: 159.7 ms. Input stream FPS does not equal tracker throughput.

Deterministic mathematical tests cover irregular intervals and physical velocity, variable frame rates, repeated/backward/missing times, callback delay, dropped intervals, temporary single-hand loss, gaps between adjacent grid points, malformed input, and body-relative translation. These fixtures are not recordings or accuracy evidence.
