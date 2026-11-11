"""Phase 3 manifest checks; fixtures are synthetic metadata, not signing data."""
import unittest
from alphabet_dataset import validate

class CaptureManifestTests(unittest.TestCase):
    def test_session_leakage_with_different_signers_and_media(self):
        def record(split, suffix):
            return dict(id=suffix,split=split,label='A',session_id='shared',recording_id=suffix,
                        signer_id=suffix,signer_verified=True,identity_evidence='registry',
                        review_status='accepted',reviewer_id='reviewer',license='CC0-1.0',
                        rights_evidence='publisher',sha256=suffix*64,parent_media_sha256=suffix*64)
        result=validate(dict(schema='handspeak-alphabet-recordings-v1',
                             recordings=[record('train','a'),record('test','b')]))
        self.assertFalse(result['valid'])
        self.assertTrue(any('session_id shared crosses' in error for error in result['errors']))

    def test_strict_rejects_empty_protocol(self):
        result=validate(dict(schema='handspeak-alphabet-recordings-v1',recordings=[]),strict_coverage=True)
        self.assertFalse(result['valid'])
        self.assertTrue(any('NO_HAND' in error and 'UNKNOWN' in error for error in result['errors']))
        self.assertTrue(any('fewer than two verified signers' in error for error in result['errors']))
