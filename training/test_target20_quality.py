import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import beginner_asl
from target20_quality import capture_quality
from target20_candidate import temporal_features, TemporalCandidate


def payload():
    pose = [[.5,.2,0]] * 3 + [[.3,.4,0],[.7,.4,0],[.3,.6,0],[.7,.6,0]]
    frames = [dict(pose=copy.deepcopy(pose), left=[[.3,.5,0]]*21, right=None, timestampMs=i*4000/59) for i in range(60)]
    return dict(vocabulary='target20', frames=frames, capture=dict(complete=True, durationMs=4000))


class CaptureQuality(unittest.TestCase):
    def test_complete_capture(self):
        self.assertEqual(capture_quality(payload()), (None, None))

    def test_missing_consent_is_not_fabricated_in_frontend(self):
        code = (Path(__file__).resolve().parents[1]/'guided-experience.js').read_text(encoding='utf-8')
        self.assertNotIn('consent.checked=true', code)

    def test_explicit_incomplete_capture(self):
        p = payload(); p['capture']['complete'] = False
        self.assertEqual(capture_quality(p)[0], 'incomplete')

    def test_no_hand_capture(self):
        p = payload()
        for f in p['frames']: f['left'] = None
        self.assertEqual(capture_quality(p)[0], 'tracking_failure')

    def test_short_complete_sign_with_idle_lead_and_tail(self):
        p=payload()
        for i,f in enumerate(p['frames']):
            if not 15<=i<30:f['left']=None
        self.assertEqual(capture_quality(p),(None,None))

    def test_scattered_hand_glimpses_do_not_form_a_complete_sign(self):
        p=payload()
        for i,f in enumerate(p['frames']):
            if i%6:f['left']=None
        self.assertEqual(capture_quality(p)[0],'tracking_failure')

    def test_gap_and_stale_capture(self):
        p = payload(); p['frames'][20]['timestampMs'] = 0
        self.assertEqual(capture_quality(p)[0], 'tracking_failure')

    def test_sparse_window(self):
        p = payload()
        for f in p['frames']: f['timestampMs'] *= .2
        self.assertEqual(capture_quality(p)[0], 'tracking_failure')

    def test_nonfinite_and_malformed_coordinates(self):
        for value in (float('nan'), float('inf'), True, 'bad'):
            p = payload(); p['frames'][0]['left'][0] = [value, .4]
            with self.assertRaises(ValueError): capture_quality(p)

    def test_degenerate_shoulders(self):
        p = payload(); p['frames'][0]['pose'][4] = p['frames'][0]['pose'][3]
        self.assertEqual(capture_quality(p)[0], 'tracking_failure')

    def test_quality_failure_never_loads_model(self):
        p = payload(); p['capture']['complete'] = False
        with patch.object(beginner_asl, '_load_target20') as load:
            r = beginner_asl.recognize(p)
        self.assertEqual(r['state'], 'incomplete'); load.assert_not_called()

    def test_unknown_uncertain_and_recognized_states(self):
        for logits, expected in [([0.,9.], 'unknown'), ([.1,0.], 'uncertain'), ([9.,0.], 'recognized')]:
            with patch.object(beginner_asl, '_load_target20', return_value=(torch,lambda x:torch.tensor([logits]),['HELLO','UNKNOWN'],32)), \
                 patch.object(beginner_asl,'target20_status',return_value=dict(labels=['HELLO'],gate=.9)):
                r = beginner_asl.recognize(payload())
            self.assertEqual(r['state'], expected)

    def test_masked_coordinates_cannot_create_motion(self):
        x = torch.zeros(2,4,32,27); x[1,:2,:,7:] = torch.randn(2,32,20)*100
        f = temporal_features(x)
        torch.testing.assert_close(f[0], f[1])

    def test_model_shape_and_reload(self):
        model = TemporalCandidate(); other = TemporalCandidate(); other.load_state_dict(model.state_dict())
        model.eval(); other.eval(); x = torch.randn(2,4,32,27); x[:,2:] = 1
        self.assertEqual(model(x).shape, (2,21)); torch.testing.assert_close(model(x), other(x))


if __name__ == '__main__': unittest.main()
