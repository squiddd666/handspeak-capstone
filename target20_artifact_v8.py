"""Versioned private Target-20 browser landmark artifact, never a V3 input."""
import hashlib
import json
import math
from target20_encoder_v6 import VERSION as ENCODER_VERSION, encode

SCHEMA='handspeak-target20-browser-landmarks-v1'
TRACKER={'build':'@mediapipe/holistic@0.5.1675471629','modelComplexity':1,
         'smoothLandmarks':True,'minDetectionConfidence':.5,'minTrackingConfidence':.5,
         'pose_indices':[0,2,5,11,12,13,14],'hand_points':21}

def canonical_bytes(obj):
    return json.dumps(obj,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')

def digest(obj):return hashlib.sha256(canonical_bytes(obj)).hexdigest()

def hex_hash(value):
    return isinstance(value,str) and len(value)==64 and all(x in '0123456789abcdef' for x in value)

def seal(body):
    return {**body,'artifact_sha256':digest(body)}

def validate(artifact):
    if not isinstance(artifact,dict) or artifact.get('schema')!=SCHEMA:
        raise ValueError('Incompatible artifact schema')
    body={k:v for k,v in artifact.items() if k!='artifact_sha256'}
    if artifact.get('artifact_sha256')!=digest(body):raise ValueError('Artifact hash mismatch')
    if artifact.get('encoder')!=ENCODER_VERSION:raise ValueError('Incompatible encoder')
    source=artifact.get('source')
    if not isinstance(source,dict):raise ValueError('Missing source provenance')
    if not hex_hash(source.get('sha256')):raise ValueError('Missing source hash')
    if any(not isinstance(source.get(k),str) or not source[k].strip() for k in ('id','license_ref','permission_ref','label','gloss','variant')):
        raise ValueError('Missing source provenance')
    if artifact.get('split') not in ('train','val'):raise ValueError('Not a development artifact')
    extraction=artifact.get('extraction')
    if (not isinstance(extraction,dict) or extraction.get('tracker')!=TRACKER or extraction.get('resolution')!=[640,480]
        or extraction.get('fps')!=15 or not hex_hash(extraction.get('frontend_sha256'))
        or not hex_hash(extraction.get('harness_sha256')) or not extraction.get('browser')):
        raise ValueError('Incompatible extraction profile')
    capture=artifact.get('capture')
    if not isinstance(capture,dict):raise ValueError('Missing capture provenance')
    status=artifact.get('status')
    if status not in ('usable_development','excluded'):raise ValueError('Invalid status')
    if status=='excluded' and not artifact.get('reason'):raise ValueError('Exclusion reason required')
    frames=artifact.get('frames')
    if not isinstance(frames,list):raise ValueError('Missing frame array')
    previous=-math.inf
    for frame in frames:
        if not isinstance(frame,dict) or any(k not in frame for k in ('left','right','pose','timestampMs')):
            raise ValueError('Malformed frame')
        t=frame['timestampMs']
        if type(t) not in (float,int) or not math.isfinite(t) or t<=previous:
            raise ValueError('Invalid source timestamp order')
        previous=t
        for side,size in (('pose',7),('left',21),('right',21)):
            points=frame[side]
            if points is None and side!='pose':continue
            if not isinstance(points,list) or len(points)!=size or any(
                not isinstance(point,list) or len(point)!=3 or any(
                    type(v) not in (float,int) or not math.isfinite(v) or abs(v)>10 for v in point)
                for point in points):
                raise ValueError('Malformed landmark coordinates')
        if (frame.get('left_visible') is not (frame['left'] is not None)
            or frame.get('right_visible') is not (frame['right'] is not None)):
            raise ValueError('Visibility masks disagree with observations')
    if status=='excluded':return None  # Preserve rejected evidence, never supply training tensors.
    duration=capture.get('durationMs')
    if (capture.get('complete') is not True or capture.get('interrupted') is not False
        or capture.get('qa_verified_window') is not True or type(duration) not in (int,float)
        or not math.isfinite(duration) or not 3500<=duration<=8500):
        raise ValueError('Incomplete capture')
    encoded=encode(frames)
    span=float(encoded.source_ms[-1]-encoded.source_ms[0])
    if span<.7*duration or span>duration+600:
        raise ValueError('Source and capture durations disagree')
    return encoded

def validate_batch(artifacts):
    seen=set()
    for a in artifacts:
        validate(a)
        h=a['source']['sha256']
        if h in seen:raise ValueError('Duplicate source in extraction batch')
        seen.add(h)
