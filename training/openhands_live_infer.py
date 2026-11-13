"""Isolated subprocess: original OpenHands preprocessing and weights."""
import sys,json
from pathlib import Path
import cv2
ROOT=Path(__file__).resolve().parents[1]
path=Path(sys.argv[1])
sys.path.insert(0,str(ROOT))
from video_capture_validation import inspect_capture
video_info=inspect_capture(path)
sys.path.insert(0,str(ROOT/'openhands-test'))
from runtime import predict
print(json.dumps(predict(path)),flush=True)
