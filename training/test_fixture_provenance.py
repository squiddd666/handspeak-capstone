"""Prevent archived vectors from being mislabeled as current accuracy evidence."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]


class FixtureProvenance(unittest.TestCase):
    def test_archived_labels_and_expected_outputs_remain_unchanged(self):
        provenance=json.loads((ROOT/'models/fixture-provenance.json').read_text(encoding='utf-8'))
        for key in ('letter','motion'):
            meta=provenance[key]
            self.assertEqual(hashlib.sha256((ROOT/meta['file']).read_bytes()).hexdigest(),meta['sha256'])
            self.assertFalse(meta['current_accuracy_eligible'])

    def test_legacy_letter_fixture_cannot_validate_current_normalization(self):
        provenance=json.loads((ROOT/'models/fixture-provenance.json').read_text(encoding='utf-8'))
        model=json.loads((ROOT/'models/asl-knn.json').read_text(encoding='utf-8'))
        self.assertNotEqual(provenance['letter']['normalization'],model['normalization'])

    def test_legacy_motion_fixture_is_not_the_current_test_report(self):
        provenance=json.loads((ROOT/'models/fixture-provenance.json').read_text(encoding='utf-8'))
        report=json.loads((ROOT/'models/asl-words-evaluation.json').read_text(encoding='utf-8'))
        self.assertNotEqual(provenance['motion']['samples'],report['test']['total'])


if __name__=='__main__':unittest.main()
