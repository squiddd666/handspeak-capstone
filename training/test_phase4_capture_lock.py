import unittest
from lock_phase4_manifest import capture_errors
class Phase4CaptureTests(unittest.TestCase):
    def test_incomplete_cannot_be_locked(self):
        errors=capture_errors([{'id':'fixture','split':'test','incomplete':True}])
        self.assertTrue(any('incomplete capture' in e for e in errors))
        self.assertTrue(any('both left- and right-handed' in e for e in errors))

    def test_nonfinite_and_visibility_alignment(self):
        errors=capture_errors([dict(id='fixture',split='train',width=640,height=480,
            source_fps=30,start_ms=0,end_ms=1000,timestamps_ms=[0,float('nan')],handedness='right',visible_hand_counts=[1])])
        self.assertTrue(any('finite source times' in e for e in errors))
        self.assertTrue(any('must align' in e for e in errors))
