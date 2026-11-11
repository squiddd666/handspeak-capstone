"""Strict target-20 capture contract. No inference or private data persistence."""
import math

TARGET_WORDS = ('HELLO','THANK YOU','PLEASE','SORRY','YES','NO','HELP','LOVE',
                'I / ME','YOU','WANT','NEED','LIKE','GOOD','BAD','WHAT','WHERE','WHO','EAT','WATER')


def capture_quality(payload):
    frames = payload.get('frames')
    if not isinstance(frames, list) or not 3 <= len(frames) <= 90:
        raise ValueError('Capture must contain 3 to 90 landmark frames')
    hand_frames = 0
    visible_indices = []
    times = []
    for index, frame in enumerate(frames):
        if not isinstance(frame, dict):
            raise ValueError('Each frame must be a landmark object')
        for name, count in [('pose', 7), ('left', 21), ('right', 21)]:
            points = frame.get(name)
            if name != 'pose' and points is None:
                continue
            if not isinstance(points, list) or len(points) != count:
                raise ValueError(f'{name} must contain {count} landmarks')
            for point in points:
                if not isinstance(point, (list, tuple)) or len(point) not in (2, 3):
                    raise ValueError('Landmarks must contain XY or XYZ coordinates')
                if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or abs(v) > 10 for v in point):
                    raise ValueError('Landmarks must be finite bounded numbers')
        if frame.get('left') is not None or frame.get('right') is not None:
            hand_frames += 1
            visible_indices.append(index)
        a, b = frame['pose'][3:5]
        if math.hypot(a[0] - b[0], a[1] - b[1]) < .02:
            return 'tracking_failure', 'Shoulders could not be tracked reliably.'
        if 'timestampMs' in frame:
            t = frame['timestampMs']
            if isinstance(t, bool) or not isinstance(t, (int, float)) or not math.isfinite(t):
                raise ValueError('Frame timestamps must be finite numbers')
            times.append(t)
    # A complete short sign can occupy a fraction of a four-second window.
    # Judge continuity within its observed hand interval, not idle lead/tail.
    active_coverage = hand_frames / (visible_indices[-1]-visible_indices[0]+1) if visible_indices else 0
    if len(frames) < 12 or hand_frames < 8 or active_coverage < .6:
        return 'tracking_failure', 'Not enough visible-hand frames; record again.'
    if times and (len(times) != len(frames) or any(b <= a or b - a > 600 for a, b in zip(times, times[1:]))):
        return 'tracking_failure', 'Tracking timestamps are incomplete, stale, or interrupted.'
    capture = payload.get('capture')
    if not isinstance(capture, dict) or capture.get('complete') is not True or capture.get('interrupted') is True:
        return 'incomplete', 'A complete, uninterrupted recording is required.'
    duration = capture.get('durationMs')
    if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 3500 <= duration <= 8500:
        return 'incomplete', 'Record a complete sign using the four-second capture.'
    if times and times[-1] - times[0] < .7 * duration:
        return 'tracking_failure', 'Tracked frames do not cover enough of the recording window.'
    # Capture metadata only proves a full recording window, not linguistic completeness.
    return None, None
