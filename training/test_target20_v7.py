"""QA classification contract and V6 limit regressions."""
import unittest
from target20_virtual_camera import assess_outcome, associated_response, blank_control_verified
from types import SimpleNamespace
from test_target20_v6 import fixture,encode
import numpy as np

class OutcomeContract(unittest.TestCase):
    def test_blank_control_requires_observed_uniform_frames(self):
        self.assertFalse(blank_control_verified([0,0,0]))
        self.assertFalse(blank_control_verified([0,0,37,0]))
        self.assertTrue(blank_control_verified([0,1,2,0]))
        r=self.case(scenario='no-hands',blank_control_verified=False)
        self.assertEqual(assess_outcome(r)['capture_outcome'],'capture_failure')
        self.assertFalse(assess_outcome(r)['unknown_rejected'])

    def test_stale_response_ignored_and_duplicates_fail(self):
        old,new=object(),object()
        stale=SimpleNamespace(request=old)
        current=SimpleNamespace(request=new)
        self.assertIsNone(associated_response([new],[stale]))
        self.assertIs(associated_response([new],[stale,current]),current)
        with self.assertRaises(RuntimeError):associated_response([new],[current,current])
        with self.assertRaises(RuntimeError):associated_response([old,new],[current])

    def case(self,**fields):
        return dict(dict(label='UNKNOWN',scenario='normal',camera_configuration_ok=True,
            full_source_window_captured=True,http_status=200,backend_response={'state':'unknown'}),**fields)

    def test_transport_or_window_failure_never_credits_unknown(self):
        for changes in ({'http_status':422},{'full_source_window_captured':False},{'page_errors':['error']},
                        {'backend_response':{'state':'tracking_failure'}},{'backend_response':{'state':'incomplete'}}):
            self.assertFalse(assess_outcome(self.case(**changes))['unknown_rejected'])

    def test_valid_unknown_and_distinct_encoder_failure(self):
        result=assess_outcome(self.case(backend_response={'state':'unknown','experimentalEncoder':{'state':'encoder_rejected'}}))
        self.assertTrue(result['unknown_rejected'])
        self.assertEqual(result['encoder_outcome'],'encoder_rejected')

    def test_wrong_and_correct_recognition_not_conflated(self):
        for label,out in [('YES','correct'),('YOU','incorrect')]:
            self.assertEqual(assess_outcome(self.case(label=label,predicted='YES',backend_response={'state':'recognized'}))['v3_outcome'],out)
        r=self.case(label='YES',scenario='incomplete',predicted='YES',backend_response={'state':'recognized'})
        self.assertEqual(assess_outcome(r)['v3_outcome'],'incorrect')

    def test_200ms_limit_cannot_be_overridden(self):
        with self.assertRaises(ValueError):encode(fixture(np.arange(0,2000,100)),max_gap_ms=201)

    def test_finite_endpoints_with_overflowing_gap_rejected(self):
        times=[-1e308]+list(np.linspace(1e308,1.2e308,12))
        with self.assertRaisesRegex(ValueError,'timestamps'):encode(fixture(times))

if __name__=='__main__':unittest.main()
