"""Deterministic mathematical fixtures, not recordings or accuracy evidence."""
import copy
import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from target20_encoder_v6 import encode

def fixture(times,missing=(),delay=0):
    return [dict(timestampMs=float(t),callbackMs=float(t+delay+i*5),
                 pose=[[.5,.2]]*3+[[.3,.4],[.7,.4],[.3,.6],[.7,.6]],
                 left=None if i in missing else [[.3+t*.00008,.5]]*21,
                 right=[[.7,.6]]*21) for i,t in enumerate(times)]

class MaskTimeEncoder(unittest.TestCase):
    def test_irregular_intervals_and_physical_velocity(self):
        t=np.cumsum([0]+[40,80,100]*9)
        e=encode(fixture(t))
        np.testing.assert_array_equal(e.source_ms,t)
        np.testing.assert_allclose(e.velocity[1:,7,0],.2,atol=1e-12)
        np.testing.assert_allclose(e.velocity[:,17],0)

    def test_variable_sampling_rates(self):
        a=encode(fixture(np.arange(0,2001,50)))
        b=encode(fixture(np.arange(0,2001,100)))
        np.testing.assert_allclose(a.xy,b.xy,atol=1e-12)

    def test_duplicate_and_backward_timestamps_rejected(self):
        for second in (100,80):
            f=fixture(np.arange(0,2000,100))
            f[2]['timestampMs']=second
            with self.assertRaisesRegex(ValueError,'strictly increasing'):encode(f)

    def test_tracker_delay_does_not_shift_motion(self):
        t=np.arange(0,2000,100)
        a=encode(fixture(t));b=encode(fixture(t,delay=900))
        np.testing.assert_array_equal(a.sample_ms,b.sample_ms)
        np.testing.assert_array_equal(a.velocity,b.velocity)

    def test_temporary_hand_loss_does_not_bridge_or_change_other_hand(self):
        e=encode(fixture(np.arange(0,2000,100),missing=range(5,9)))
        gap=(e.sample_ms>400)&(e.sample_ms<900)
        self.assertFalse(e.visible[gap,7].any())
        self.assertTrue(e.visible[gap,17].all())
        self.assertTrue((e.xy[gap,7]==0).all())
        self.assertTrue((e.velocity[~e.velocity_valid[:,7],7]==0).all())
        np.testing.assert_allclose(e.velocity[e.velocity_valid[:,7],7,0],.2)

    def test_dropped_interval_masks_both_hands(self):
        e=encode(fixture(np.r_[np.arange(0,800,100),np.arange(1100,2200,100)]))
        gap=(e.sample_ms>700)&(e.sample_ms<1100)
        self.assertFalse(e.visible[gap].any())
        self.assertFalse(e.velocity_valid[gap].any())

    def test_velocity_cannot_cross_gap_between_grid_points(self):
        e=encode(fixture(np.arange(0,2000,100),missing=[7]),samples=8)
        self.assertTrue(e.visible[:,7].all())
        self.assertFalse(e.velocity_valid[3,7])
        self.assertTrue(e.velocity_valid[3,17])

    def test_missing_timestamp_rejected(self):
        f=fixture(np.arange(0,2000,100));del f[1]['timestampMs']
        with self.assertRaisesRegex(ValueError,'timestamps required'):encode(f)

    def test_insufficient_sequence_and_invalid_landmarks_rejected(self):
        f=fixture(np.arange(0,2000,100))
        for r in f:r['left']=r['right']=None
        with self.assertRaisesRegex(ValueError,'visible-hand support'):encode(f)
        f=fixture(np.arange(0,2000,100));f[2]['pose'][0]=[float('nan'),.5]
        with self.assertRaisesRegex(ValueError,'Invalid pose'):encode(f)

    def test_body_relative_translation_invariance(self):
        f=fixture(np.arange(0,2000,100))
        shifted=copy.deepcopy(f)
        for frame in shifted:
            for key in ('pose','left','right'):
                frame[key]=(np.array(frame[key])+[.1,.05]).tolist()
        np.testing.assert_allclose(encode(f).xy,encode(shifted).xy,atol=1e-12)

if __name__=='__main__':unittest.main()

