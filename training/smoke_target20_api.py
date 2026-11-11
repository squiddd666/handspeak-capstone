"""Test the installed HTTP model using real video landmarks, not a webcam.

This checks API wiring. It is not a new accuracy or browser-camera benchmark.
"""
import argparse
import json
import sys
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CACHE = ROOT.parent / 'handspeak-training'
POSE = [0, 2, 5, 11, 12, 13, 14]


def frames_from_video(path):
    frames = []
    cap = cv2.VideoCapture(path)
    try:
        with mp.solutions.holistic.Holistic(model_complexity=1) as tracker:
            stride = max(1, round((cap.get(cv2.CAP_PROP_FPS) or 30) / 15))
            index = 0
            while True:
                ok, image = cap.read()
                if not ok:
                    break
                index += 1
                if (index - 1) % stride:
                    continue
                result = tracker.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
                if not result.pose_landmarks:
                    continue
                def points(hand):
                    return [[p.x, p.y, p.z] for p in hand.landmark] if hand else None
                frames.append(dict(pose=[[result.pose_landmarks.landmark[i].x,
                                          result.pose_landmarks.landmark[i].y,
                                          result.pose_landmarks.landmark[i].z] for i in POSE],
                                   left=points(result.left_hand_landmarks),
                                   right=points(result.right_hand_landmarks)))
    finally:
        cap.release()
    return frames


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--direct', action='store_true', help='Test Python inference without starting or contacting a server')
    args = parser.parse_args()
    if args.direct:
        import beginner_asl
        status = beginner_asl.target20_status()
    else:
        with urllib.request.urlopen(args.url + '/api/beginner-asl/status') as response:
            status = json.load(response)['target20']
    assert status['available'] and len(status['labels']) == 20 and not status['ready']
    manifest = json.loads((CACHE / 'target20-manifest.json').read_text())
    results = []
    for label in ('HELLO', 'UNKNOWN'):
        row = next(r for r in manifest['samples'] if r['split'] == 'val' and r['label'] == label)
        frames = frames_from_video(row['file'])
        payload = dict(consent=True, vocabulary='target20', frames=frames)
        if args.direct:
            result = beginner_asl.recognize(payload)
        else:
            request = urllib.request.Request(args.url + '/api/beginner-asl', data=json.dumps(payload).encode(),
                                             headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.load(response)
        assert result['vocabulary'] == 'target20' and result['vocabularySize'] == 20
        assert result['experimental'] and result['minScore'] == status['gate']
        results.append(dict(source_label=label, frames=len(frames), response=result))
    scope = 'Direct Python inference' if args.direct else 'HTTP wiring'
    report = dict(scope=scope + ' using real validation-video landmarks; not webcam accuracy',
                  status=status, results=results, passed=True)
    filename = 'target20-inference-smoke.json' if args.direct else 'target20-api-smoke.json'
    (CACHE / filename).write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
