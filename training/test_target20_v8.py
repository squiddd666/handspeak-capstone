"""Schema regressions using mathematical fixtures; no simulated recognition data."""
from copy import deepcopy
import unittest
from target20_artifact_v8 import SCHEMA,TRACKER,ENCODER_VERSION,seal,validate,validate_batch
from target20_virtual_camera import assess_outcome

def body():
    pose=[[.5,.2,0]]*3+[[.3,.4,0],[.7,.4,0],[.3,.6,0],[.7,.6,0]]
    frames=[dict(timestampMs=5000+i*100,pose=pose,left=[[.4,.5,0]]*21,right=None,left_visible=True,right_visible=False) for i in range(41)]
    return dict(schema=SCHEMA,encoder=ENCODER_VERSION,split='val',status='usable_development',
                source=dict(id='test fixture',sha256='a'*64,label='HELLO',gloss='HELLO',variant='fixture',license_ref='fixture',permission_ref='fixture'),
                extraction=dict(tracker=TRACKER,resolution=[640,480],fps=15,frontend_sha256='b'*64,harness_sha256='c'*64,browser='fixture'),
                capture=dict(complete=True,interrupted=False,qa_verified_window=True,durationMs=4000),frames=frames)

class ArtifactTests(unittest.TestCase):
    def test_valid_preserves_source_times_and_hands(self):
        x=validate(seal(body()))
        self.assertEqual((x.source_ms[0],x.source_ms[-1]),(5000,9000))
        self.assertTrue(x.visible[:,7].all())
        self.assertFalse(x.visible[:,17].any())

    def test_integrity_duplicate_and_profile(self):
        a=seal(body());a['source']={**a['source'],'label':'NO'}
        with self.assertRaisesRegex(ValueError,'hash'):validate(a)
        with self.assertRaisesRegex(ValueError,'Duplicate'):validate_batch([seal(body()),seal(body())])
        b=body();b['extraction']['fps']=30
        with self.assertRaisesRegex(ValueError,'profile'):validate(seal(b))

    def test_invalid_masks_and_order(self):
        b=body();b['frames'][0]['right_visible']=True
        with self.assertRaisesRegex(ValueError,'masks'):validate(seal(b))
        b=body();b['frames'][1]['timestampMs']=b['frames'][0]['timestampMs']
        with self.assertRaisesRegex(ValueError,'timestamp'):validate(seal(b))

    def test_incomplete_and_excluded_never_encode(self):
        b=body();b['capture']['qa_verified_window']=False
        with self.assertRaisesRegex(ValueError,'Incomplete'):validate(seal(b))
        b.update(status='excluded',reason='source window')
        self.assertIsNone(validate(seal(b)))
        b['frames'][0]['pose']=[]
        with self.assertRaisesRegex(ValueError,'Malformed'):validate(seal(b))

    def test_exposed_split_cannot_be_packaged(self):
        b=body();b['split']='test'
        with self.assertRaisesRegex(ValueError,'development'):validate(seal(b))

    def test_need_like_failed_window_cannot_earn_capture_or_unknown_credit(self):
        r=dict(label='UNKNOWN',scenario='normal',camera_configuration_ok=True,http_status=200,
               full_source_window_captured=False,backend_response={'state':'uncertain','experimentalEncoder':{'state':'encoded'}})
        outcome=assess_outcome(r)
        self.assertEqual(outcome['capture_outcome'],'capture_failure')
        self.assertEqual(outcome['encoder_outcome'],'encoded')
        self.assertEqual(outcome['v3_outcome'],'not_scored')
        self.assertFalse(outcome['unknown_rejected'])

if __name__=='__main__':unittest.main()
