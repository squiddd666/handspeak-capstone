"""Experimental Target-20 v6 encoder. Not compatible with the v3 checkpoint."""
from dataclasses import dataclass
import numpy as np


VERSION = 'target20-mask-time-v6'
HAND_POINTS = [0, 4, 5, 8, 9, 12, 13, 16, 17, 20]

@dataclass(frozen=True)
class Encoding:
    source_ms: np.ndarray
    sample_ms: np.ndarray
    xy: np.ndarray
    visible: np.ndarray
    velocity: np.ndarray
    velocity_valid: np.ndarray

def encode(frames, *, samples=32, max_gap_ms=200):
    """Use absolute source milliseconds; never bridge missing or stale samples."""
    if not 12 <= len(frames) <= 90 or type(samples) is not int or not 8 <= samples <= 256 or not 0 < max_gap_ms <= 200:
        raise ValueError('Invalid frame count or resampling configuration')
    try:
        t = np.asarray([f['timestampMs'] for f in frames], dtype=np.float64)
    except (TypeError, KeyError, ValueError) as exc:
        raise ValueError('Source timestamps required') from exc
    with np.errstate(over='ignore', invalid='ignore'):
        steps=np.diff(t)
    if not np.isfinite(t).all() or not np.isfinite(steps).all() or np.any(steps <= 0):
        raise ValueError('Source timestamps must be finite and strictly increasing')
    for frame in frames:
        if isinstance(frame['timestampMs'], bool) or not isinstance(frame['timestampMs'], (int,float)):
            raise ValueError('Numeric source timestamps required')
        for key,count in [('pose',7),('left',21),('right',21)]:
            if key not in frame or frame[key] is None:
                if key=='pose': raise ValueError('Body landmarks required')
                continue
            points=np.asarray(frame[key],dtype=float)
            if points.shape not in ((count,2),(count,3)) or not np.isfinite(points).all() or np.abs(points).max()>10:
                raise ValueError(f'Invalid {key} landmarks')
    body = np.asarray([np.asarray(f['pose'],np.float64)[:,:2] for f in frames])
    center = np.median((body[:,3]+body[:,4])/2, axis=0)
    scale = np.median(np.linalg.norm(body[:,3]-body[:,4],axis=1))
    if scale < .02: raise ValueError("Insufficient shoulder scale")
    xy = np.zeros((len(t),27,2))
    valid = np.zeros((len(t),27), dtype=bool)
    xy[:,:7] = (body-center)/scale
    valid[:,:7] = True
    for i,f in enumerate(frames):
        for key,start in [('left',7),('right',17)]:
            if f.get(key) is not None:
                xy[i,start:start+10]=(np.asarray(f[key],np.float64)[HAND_POINTS,:2]-center)/scale
                valid[i,start:start+10]=True
    # Trim idle edges by visibility, not a motion peak computed against zeros.
    hand_frames=np.flatnonzero(valid[:,7:].any(axis=1))
    if len(hand_frames)<8 or t[hand_frames[-1]]-t[hand_frames[0]]<300 or len(hand_frames)/(hand_frames[-1]-hand_frames[0]+1)<.6:
        raise ValueError('Insufficient visible-hand support')
    grid=np.linspace(t[hand_frames[0]],t[hand_frames[-1]],samples)
    out=np.zeros((samples,27,2))
    mask=np.zeros((samples,27),bool)
    seg=np.full((samples,27),-1,dtype=int)
    for joint in range(27):
        indices=np.flatnonzero(valid[:,joint])
        breaks=np.flatnonzero((np.diff(indices)!=1)|(np.diff(t[indices])>max_gap_ms))+1
        for k,run in enumerate(np.split(indices,breaks)):
            if not len(run):continue
            inside=(grid>=t[run[0]])&(grid<=t[run[-1]])
            mask[inside,joint]=True
            seg[inside,joint]=k
            for axis in range(2):
                out[inside,joint,axis]=np.interp(grid[inside],t[run],xy[run,joint,axis])
    if mask[:,7:].any(axis=1).sum()<8 or mask[:,:7].all(axis=1).sum()<samples*.7:
        raise ValueError('Insufficient resampled hand or body support')
    velocity=np.zeros_like(out)
    vm=np.zeros_like(mask)
    vm[1:]=mask[1:]&mask[:-1]&(seg[1:]==seg[:-1])
    np.divide(np.diff(out,axis=0),np.diff(grid)[:,None,None]/1000,out=velocity[1:],where=vm[1:,:,None])
    return Encoding(t,grid,out,mask,velocity,vm)

def summarize(frames):
    e=encode(frames)
    return dict(version=VERSION, input_frames=len(e.source_ms), source_first_ms=float(e.source_ms[0]),
                source_last_ms=float(e.source_ms[-1]), max_source_gap_ms=float(np.diff(e.source_ms).max()),
                samples=len(e.sample_ms), grid_first_ms=float(e.sample_ms[0]),grid_last_ms=float(e.sample_ms[-1]),
                xy_shape=list(e.xy.shape),left_samples=int(e.visible[:,7].sum()),right_samples=int(e.visible[:,17].sum()),
                valid_hand_velocity_samples=[int(e.velocity_valid[:,j].sum()) for j in (7,17)],
                model_compatibility='not a v3 input; no v6 prediction')
