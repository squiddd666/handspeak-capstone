"""Validate decoded video, not unreliable MediaRecorder container frame counts."""
import math
import cv2

def inspect_capture(path, max_seconds=8, max_frames=480):
    cap=cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():raise ValueError('Video recording could not be opened.')
        fps=float(cap.get(cv2.CAP_PROP_FPS))
        reported_count=float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        count=0;times=[]
        while True:
            ok,frame=cap.read()
            if not ok:break
            count+=1
            if count>max_frames:raise ValueError('Recording has too many frames; record a single short sign.')
            stamp=float(cap.get(cv2.CAP_PROP_POS_MSEC))/1000
            if math.isfinite(stamp) and stamp>=0:times.append(stamp)
        if count<1:raise ValueError('No decodable video frames were received.')
        fps_ok=math.isfinite(fps) and 1<=fps<=120
        step=1/fps if fps_ok else 1/30
        timed=len(times)==count and all(b>=a for a,b in zip(times,times[1:])) and times[-1]>times[0]
        duration=(times[-1]-times[0]+step) if timed else count/fps if fps_ok else 0
        if not .3<=duration<=max_seconds+.25:raise ValueError('Record one complete sign in 0.3 to 8 seconds.')
        return {'decodedFrames':count,'durationSeconds':duration,'fps':fps if fps_ok else None,'reportedFrameCount':reported_count if math.isfinite(reported_count) else None,'usedDecodedTimestamps':timed}
    finally:cap.release()
