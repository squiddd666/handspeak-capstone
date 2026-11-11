import hashlib,json
from pathlib import Path
import unittest
import quickjs
from alphabet_dataset import validate,signer_split
ROOT=Path(__file__).resolve().parents[1]

class ArchitectureTests(unittest.TestCase):
 def test_model_asset_manifest(self):
  folder=ROOT/'models/hand-landmarks'
  manifest=json.loads((folder/'manifest.json').read_text())
  self.assertEqual(manifest['license'],'Apache-2.0')
  self.assertEqual(len(manifest['models']),2)
  for name,record in manifest['models'].items():
   data=(folder/name).read_bytes()
   self.assertEqual(len(data),record['bytes'])
   self.assertEqual(hashlib.sha256(data).hexdigest(),record['sha256'])

 def test_palm_decoder_anchor_geometry(self):
  js=quickjs.Context()
  js.eval((ROOT/'onnx-hand-detector.js').read_text().replace('export ',''))
  self.assertEqual(js.eval('palmAnchors().length'),2016)
  self.assertAlmostEqual(js.eval('boxIoU([0,0,2,2],[1,0,3,2])'),1/3)

 def test_signer_and_media_cannot_cross_splits(self):
  r=dict(signer_id='s1',signer_verified=True,identity_evidence='private registry',review_status='accepted',reviewer_id='r1',license='CC0-1.0',rights_evidence='publisher',recording_id='x',parent_media_sha256='b'*64,sha256='a'*64,label='A')
  result=validate({'schema':'handspeak-alphabet-recordings-v1','recordings':[dict(r,split='train'),dict(r,split='test')]})
  self.assertFalse(result['valid'])
  self.assertTrue(any('Signer s1 crosses' in x for x in result['errors']))
  self.assertTrue(any('identical media crosses' in x for x in result['errors']))
  self.assertEqual(signer_split('unverified',False),'development')

 def test_hands_keep_identity_when_detector_order_changes(self):
  js=quickjs.Context()
  js.eval((ROOT/'motion-letters.js').read_text().replace('export {letterSequence};','').replace('export ',''))
  self.assertTrue(js.eval("""(()=>{
   const t=createMultiHandMotionLetters();
   const p=x=>Array.from({length:21},(_,i)=>({x:x+i*.002,y:.6-i*.003,z:0}));
   const a=t.frame([p(.2),p(.7)],100),b=t.frame([p(.7),p(.2)],180);
   return a.presentIds[0]===b.presentIds[1]&&a.presentIds[1]===b.presentIds[0]&&!b.result;
  })()"""))
