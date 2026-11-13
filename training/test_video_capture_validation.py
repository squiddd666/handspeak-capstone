import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from video_capture_validation import inspect_capture
import cv2
class FakeCapture:
 def __init__(self,count=83,fps=15,reported=9e18):self.count=count;self.fps=fps;self.reported=reported;self.i=0;self.released=False
 def isOpened(self):return True
 def get(self,key):
  return self.fps if key==cv2.CAP_PROP_FPS else self.reported if key==cv2.CAP_PROP_FRAME_COUNT else max(0,self.i-1)*1000/self.fps
 def read(self):
  self.i+=1;return (self.i<=self.count,object() if self.i<=self.count else None)
 def release(self):self.released=True
class ValidationTests(unittest.TestCase):
 def test_streaming_webm_frame_count_is_not_trusted(self):
  cap=FakeCapture()
  with patch('video_capture_validation.cv2.VideoCapture',return_value=cap):r=inspect_capture('recording.webm')
  self.assertEqual(r['decodedFrames'],83);self.assertAlmostEqual(r['durationSeconds'],83/15);self.assertTrue(cap.released)
 def test_variable_frame_rate_timestamps(self):
  cap=FakeCapture();original=cap.get
  cap.get=lambda key:1000 if key==cv2.CAP_PROP_FPS else original(key)
  with patch('video_capture_validation.cv2.VideoCapture',return_value=cap):r=inspect_capture('vfr.webm')
  self.assertTrue(r['usedDecodedTimestamps']);self.assertGreater(r['durationSeconds'],5)
 def test_empty_rejected(self):
  cap=FakeCapture(count=0)
  with patch('video_capture_validation.cv2.VideoCapture',return_value=cap),self.assertRaises(ValueError):inspect_capture('blank')
  self.assertTrue(cap.released)
 def test_too_long_rejected(self):
  with patch('video_capture_validation.cv2.VideoCapture',return_value=FakeCapture(count=150)),self.assertRaises(ValueError):inspect_capture('long')
 def test_decode_bound(self):
  with patch('video_capture_validation.cv2.VideoCapture',return_value=FakeCapture(count=600,fps=120)),self.assertRaises(ValueError):inspect_capture('huge')
if __name__=='__main__':unittest.main()
