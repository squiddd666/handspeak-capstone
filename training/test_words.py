"""Verify exported word references and Python/browser prediction parity."""
import json
from pathlib import Path
import unittest
import quickjs
from reference_classifiers import motion_prediction

ROOT=Path(__file__).resolve().parents[1]

class PretrainedWordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.model=json.loads((ROOT/'models/asl-words.json').read_text(encoding='utf-8'))
        cls.report=json.loads((ROOT/'models/asl-words-evaluation.json').read_text(encoding='utf-8'))
        cls.fixture=json.loads((ROOT/'models/asl-words-test.json').read_text(encoding='utf-8'))
        cls.sources=json.loads((ROOT/'models/asl-words-sources.json').read_text(encoding='utf-8'))
        cls.js=quickjs.Context()
        cls.js.eval((ROOT/'motion-model.js').read_text(encoding='utf-8').replace('export ',''))
        cls.js.eval('const model='+json.dumps(cls.model)+';')

    def test_references_and_split_integrity(self):
        self.assertEqual(set(self.model['labels']),{'HELLO','THANK YOU','PLEASE','YES','NO','FINISH'})
        self.assertTrue(self.js.eval('model.samples.every(e=>validMotion(e.sequence))&&validMotionParameters(model.parameters)'))
        self.assertEqual(len(self.model['samples']),sum(self.report['trainingPerWord'].values()))
        signers={s:{r['participant'] for r in self.sources if r['split']==s} for s in ['train','val','test']}
        for a,b in [('train','val'),('train','test'),('val','test')]:self.assertFalse(signers[a]&signers[b])
        self.assertEqual(len({r['sha256'] for r in self.sources}),len(self.sources))
        self.assertFalse(any(r['split']=='train' and r['label']=='DRINK' for r in self.sources))

    def test_legacy_sequences_current_classifier_python_parity(self):
        counts={'correct':0,'wrong':0,'rejected':0}
        for i,row in enumerate(self.fixture):
            self.js.eval('var input='+json.dumps(row['sequence'])+';')
            predicted=self.js.eval('recognizeMotion(input,model.samples,model.parameters)?.label||null')
            expected=motion_prediction(row['sequence'],self.model['samples'],self.model['parameters'])
            self.assertEqual(predicted,expected,f'Legacy numeric parity vector {i}')
            counts['rejected' if predicted is None else 'correct' if predicted==row['label'] else 'wrong']+=1
        self.assertEqual(sum(counts.values()),len(self.fixture))
        # Do not compare legacy fixture counts to a different current video report.

if __name__=='__main__':unittest.main()
