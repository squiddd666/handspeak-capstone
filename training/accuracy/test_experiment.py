import copy,unittest
import numpy as np
from temporal import features,metrics,outputs,Temporal,mirrored
import torch
class ExperimentTests(unittest.TestCase):
 def row(self):
  h=[dict(x=.3+i*.006,y=.4,z=0) for i in range(21)];p=[dict(x=x,y=y,z=0,visibility=1) for x,y in [(.5,.2),(.3,.4),(.7,.4),(.2,.6),(.8,.6)]]
  return dict(rawFrames=[[h,None] for _ in range(30)],body=[p for _ in range(30)],imageAspect=1)
 def test_translation_invariance_and_missing_body(self):
  a=self.row();b=copy.deepcopy(a)
  for f in b['rawFrames']:
   for h in f:
    if h:
     for p in h:p['x']+=.1;p['y']+=.1
  for pose in b['body']:
   for p in pose:p['x']+=.1;p['y']+=.1
  np.testing.assert_allclose(features(a),features(b),atol=1e-6)
  b['body']=[None]*30;self.assertTrue(np.isfinite(features(b)).all());self.assertEqual(features(b).shape,(153,32))
 def test_mirroring_twice_preserves_features(self):
  r=self.row();np.testing.assert_allclose(features(r),features(mirrored(mirrored(r))),atol=1e-6)
 def test_model_and_unknown_output(self):
  net=Temporal(16);self.assertEqual(tuple(net(torch.zeros(2,153,32)).shape),(2,7))
  p=np.array([[.01]*6+[.94],[.94]+[.01]*6]);self.assertEqual(outputs(p,.7,.2),[None,'HELLO'])
 def test_rejections_and_negative_counts(self):
  rows=[dict(kind='supported',label='HELLO'),dict(kind='supported',label='NO'),dict(kind='unsupported',label='DRINK'),dict(kind='synthetic-still',label='UNKNOWN')]
  m=metrics(rows,['HELLO',None,'NO',None]);self.assertEqual((m['correct'],m['wrong'],m['missed'],m['unsupportedFalse'],m['syntheticFalse']),(1,0,1,1,0))
if __name__=='__main__':unittest.main()
