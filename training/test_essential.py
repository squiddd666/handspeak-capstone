"""Check that candidate training normalization matches serving normalization."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
import torch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import beginner_asl
from train_essential import encode

class EncodingParity(unittest.TestCase):
    def test_target20_unknown_is_rejected(self):
        frames=[dict(pose=[[.2,.3,0]]*3+[[.3,.4,0],[.7,.4,0]]+[[.2,.3,0]]*2,left=[[.3,.4,0]]*21,right=None)]*12
        def network(batch):return torch.tensor([[0.,8.]])
        with patch.object(beginner_asl,'_load_target20',return_value=(torch,network,['HELLO','UNKNOWN'],32)),patch.object(beginner_asl,'target20_status',return_value={'available':True,'labels':['HELLO'],'gate':.5}):
            result=beginner_asl.recognize(dict(frames=frames,vocabulary='target20',capture={'complete':True,'durationMs':4000}))
        self.assertEqual(result['predictions'],[])
        self.assertEqual(result['vocabulary'],'target20')

    def test_other_sign_is_not_renormalized_into_target(self):
        frames=[dict(pose=[[.2,.3,0]]*3+[[.3,.4,0],[.7,.4,0]]+[[.2,.3,0]]*2,left=[[.3,.4,0]]*21,right=None)]*12
        def network(batch):return torch.tensor([[0.,8.]])
        with patch.object(beginner_asl,'_load_essential',return_value=(torch,network,['HELP','OTHER'],32)),patch.object(beginner_asl,'essential_status',return_value={'available':True,'gate':.5}):
            result=beginner_asl.recognize(dict(frames=frames,vocabulary='essential',minScore=.01))
        self.assertEqual(result['predictions'],[])

    def test_essential_rejection_gate_cannot_be_lowered_by_client(self):
        frames=[dict(pose=[[.2,.3,0]]*3+[[.3,.4,0],[.7,.4,0]]+[[.2,.3,0]]*2,left=[[.3,.4,0]]*21,right=None)]*12
        def network(batch):return torch.tensor([[.1,0.]])
        with patch.object(beginner_asl,'_load_essential',return_value=(torch,network,['HELP','OTHER'],32)),patch.object(beginner_asl,'essential_status',return_value={'available':True,'gate':.9}):
            result=beginner_asl.recognize(dict(frames=frames,vocabulary='essential',minScore=.01))
        self.assertTrue(result['lowConfidence'])
        self.assertEqual(result['predictions'],[])

    def test_training_tensor_matches_server_tensor(self):
        rng=np.random.default_rng(12)
        frames=[];extracted=[];captured=[]
        for _ in range(19):
            pose=rng.uniform(.2,.8,(7,3)).astype(np.float32)
            left=rng.uniform(.2,.8,(21,3)).astype(np.float32)
            right=rng.uniform(.2,.8,(21,3)).astype(np.float32)
            frames.append(dict(pose=pose.tolist(),left=left.tolist(),right=right.tolist()))
            extracted.append((pose[:,:2],left[beginner_asl.HAND_POINTS,:2],right[beginner_asl.HAND_POINTS,:2]))
        def network(batch):
            captured.append(batch.numpy()[0]);return torch.tensor([[8.,0.]])
        with patch.object(beginner_asl,'_load',return_value=(torch,network,['HELP','OTHER'],32)),patch.object(beginner_asl,'ready_labels',return_value=['HELP']),patch.object(beginner_asl,'status',return_value={'model':'test'}):
            result=beginner_asl.recognize({'frames':frames})
        self.assertEqual(result['predictions'][0]['label'],'HELP')
        np.testing.assert_allclose(encode(extracted,32),captured[0],rtol=1e-5,atol=1e-6)

if __name__=='__main__': unittest.main()
