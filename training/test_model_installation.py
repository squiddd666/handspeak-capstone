"""Research model discovery and runtime readiness (no ML dependencies needed)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import beginner_asl as model

class ModelInstallation(unittest.TestCase):
    def test_bundled_checkpoint_is_discovered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'app'
            (root / 'models').mkdir(parents=True)
            bundled = root / 'models' / 'essential-candidate.pt'
            bundled.touch()
            with patch.object(model, 'REPO', root), patch.dict(os.environ, {}, clear=True):
                self.assertEqual(model._research_checkpoint('TEST_MODEL', bundled.name), bundled)

    def test_explicit_override_is_not_silently_replaced(self):
        with patch.dict(os.environ, {'TEST_MODEL': 'missing.pt'}):
            self.assertEqual(model._research_checkpoint('TEST_MODEL', 'other.pt'), Path('missing.pt'))

    def test_missing_runtime_disables_beginner(self):
        with patch.object(model, '_checkpoint_path', return_value=Path('present.pt')), patch.object(model, '_runtime_available', return_value=False):
            self.assertFalse(model.available())

    def test_missing_artifacts_give_installation_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            absent = Path(directory) / 'missing.pt'
            with patch.object(model, 'ESSENTIAL_REPORT', absent), patch.object(model, 'TARGET20_PATH', absent):
                self.assertIn('Install', model.essential_status()['reason'])
                self.assertIn('Install', model.target20_status()['reason'])

if __name__ == '__main__':
    unittest.main()
