"""Build the browser's weighted kNN reference set from labeled ASL images.

Run with Python 3.11 and mediapipe 0.10.21, numpy 1.26.4, pyarrow and Pillow.
On headless hosts replace opencv-contrib-python with its headless variant.
Downloads/cache stay outside the website; only landmarks and metrics are exported.
"""
import argparse
from collections import Counter
import hashlib
import io
import json
from pathlib import Path
import urllib.request

import mediapipe as mp
import numpy as np
import pyarrow.parquet as pq
from PIL import Image, ImageOps

SOURCE = 'https://huggingface.co/datasets/Marxulia/asl_sign_languages_alphabets_v03'
REVISION = '1adf43b2d31eb9d7aea5855edaeac0231d8a2757'
MODEL_URL = 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task'
LABELS = list('ABILVWY')


def normalize(points):
    p = np.array(points, dtype=float)
    scale = np.linalg.norm(p[5, :2] - p[17, :2]) or 1
    angle = np.arctan2(p[9, 1]-p[0, 1], p[9, 0]-p[0, 0])-np.pi/2
    p = (p-p[0])/scale
    x, y = p[:, 0].copy(), p[:, 1].copy()
    p[:, 0] = x*np.cos(-angle)-y*np.sin(-angle)
    p[:, 1] = x*np.sin(-angle)+y*np.cos(-angle)
    return np.round(p.reshape(-1), 6).tolist()


def predict(features, samples):
    distances = np.sqrt(np.mean((np.array([s['features'] for s in samples])-features)**2, axis=1))
    nearest = np.argsort(distances)[:5]
    votes = {}
    for i in nearest:
        label = samples[i]['label']
        votes[label] = votes.get(label, 0)+1/(distances[i]+.001)
    label = max(votes, key=votes.get)
    confidence = min(.99, votes[label]/sum(votes.values())*max(.55, 1-distances[nearest[0]]))
    return label if confidence >= .62 else None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, default=Path(__file__).resolve().parents[1]/'models')
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    args.output.mkdir(parents=True, exist_ok=True)
    for name, url in [('asl.parquet', f'{SOURCE}/resolve/{REVISION}/data/train-00000-of-00001.parquet'), ('hand_landmarker.task', MODEL_URL)]:
        if not (args.cache/name).exists():
            urllib.request.urlretrieve(url, args.cache/name)
    extracted_path = args.cache/'extracted-v1.json'
    if extracted_path.exists():
        extraction = json.loads(extracted_path.read_text())
    else:
        records, seen, counts, failed = [], set(), Counter(), Counter()
        options = mp.tasks.vision.HandLandmarkerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(args.cache/'hand_landmarker.task')),
            running_mode=mp.tasks.vision.RunningMode.IMAGE, num_hands=1,
            min_hand_detection_confidence=.65, min_hand_presence_confidence=.65)
        with mp.tasks.vision.HandLandmarker.create_from_options(options) as detector:
            for row in pq.read_table(args.cache/'asl.parquet').to_pylist():
                label = chr(65+row['label'])
                if label not in LABELS:
                    continue
                pil = ImageOps.exif_transpose(Image.open(io.BytesIO(row['image']['bytes']))).convert('RGB')
                digest = hashlib.sha256(str(pil.size).encode()+pil.tobytes()).hexdigest()
                if digest in seen:
                    continue
                seen.add(digest)
                counts[label] += 1
                result = detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.array(pil)))
                if not result.hand_landmarks:
                    failed[label] += 1
                    continue
                points = [[p.x, p.y, p.z] for p in result.hand_landmarks[0]]
                records.append({'label': label, 'features': normalize(points), 'imageHash': digest})
                if len(records) % 200 == 0:
                    print(f'Extracted {len(records)} hands', flush=True)
        extraction = {'records': records, 'uniqueImages': dict(counts), 'undetected': dict(failed)}
        extracted_path.write_text(json.dumps(extraction))
    from tune_model import build_model
    build_model(extraction, args.output)


if __name__ == '__main__':
    main()
