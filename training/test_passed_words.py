import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import beginner_asl as b


class PassedWordContracts(unittest.TestCase):
    def recognize(self, logits):
        frames = [dict(pose=[[.2,.3,0]]*3+[[.3,.4,0],[.7,.4,0]]+[[.2,.3,0]]*2,
                       left=[[.3,.4,0]]*21, right=None)]*12
        with patch.object(b, '_load_target20', return_value=(torch, lambda _: torch.tensor([logits]), ['HELLO','GOOD','UNKNOWN'], 32)), patch.object(b, 'passed_target20_status', return_value={'available':True,'labels':['HELLO']}), patch.object(b, 'target20_status', return_value={'gate':.9}), patch('target20_quality.capture_quality', return_value=(None,None)):
            return b.recognize(dict(frames=frames, vocabulary='target20-passed', minScore=.01))

    def test_unqualified_top_label_is_rejected(self):
        self.assertEqual(self.recognize([0.,8.,0.])['predictions'], [])

    def test_probabilities_not_renormalized(self):
        self.assertEqual(self.recognize([.1,0.,0.])['predictions'], [])

    def test_passed_word_can_be_recognized(self):
        result = self.recognize([8.,0.,0.])
        self.assertEqual(result['predictions'][0]['label'], 'HELLO')
        self.assertEqual(result['vocabulary'], 'target20-passed')


if __name__ == '__main__':
    unittest.main()
