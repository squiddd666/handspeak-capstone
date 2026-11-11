"""20-word dataset and rejection contracts, not recognition-accuracy tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import torch

from target20_data import LABELS, NEGATIVES, TARGETS
import beginner_asl


class Target20Contracts(unittest.TestCase):
    def test_exact_requested_vocabulary(self):
        expected = {'HELLO', 'THANK YOU', 'PLEASE', 'SORRY', 'YES', 'NO',
                    'HELP', 'LOVE', 'I / ME', 'YOU', 'WANT', 'NEED', 'LIKE',
                    'GOOD', 'BAD', 'WHAT', 'WHERE', 'WHO', 'EAT', 'WATER'}
        self.assertEqual(set(LABELS), expected | {'UNKNOWN'})
        self.assertEqual(len(LABELS), 21)
        self.assertEqual(TARGETS['ME'], 'I / ME')
        self.assertTrue(all(set(values).isdisjoint(TARGETS) for values in NEGATIVES.values()))

    def test_missing_checkpoint_does_not_enable_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'target20-candidate.pt'
            (path.parent / 'target20-report.json').write_text(json.dumps(
                {'selected_gate': .9, 'labels': LABELS}))
            with patch.object(beginner_asl, 'TARGET20_PATH', path):
                self.assertFalse(beginner_asl.target20_status()['available'])

    def test_client_cannot_lower_target20_rejection_threshold(self):
        frames = [dict(pose=[[.2,.3,0]]*3+[[.3,.4,0],[.7,.4,0]]+[[.2,.3,0]]*2,
                       left=[[.3, .4, 0]] * 21, right=None)] * 12

        def model(batch):
            return torch.tensor([[.1, 0.]])

        with patch.object(beginner_asl, '_load_target20', return_value=(torch, model, ['HELLO', 'UNKNOWN'], 32)), \
             patch.object(beginner_asl, 'target20_status', return_value={'available': True, 'labels': ['HELLO'], 'gate': .9}):
            result = beginner_asl.recognize(dict(frames=frames, vocabulary='target20',capture={'complete':True,'durationMs':4000}, minScore=.01))
        self.assertEqual(result['predictions'], [])
        self.assertEqual(result['minScore'], .9)
        self.assertTrue(result['lowConfidence'])


if __name__ == '__main__':
    unittest.main()
