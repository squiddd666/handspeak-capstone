import json
from pathlib import Path
import unittest
import quickjs


class Association(unittest.TestCase):
    def setUp(self):
        self.js=quickjs.Context()
        source=(Path(__file__).resolve().parents[1]/'target20-tracker.js').read_text(encoding='utf-8')
        self.js.eval(source.split('export async function createTarget20Tracker')[0].replace('export ',''))
        self.js.eval('''
          const pose=Array.from({length:33},()=>({x:.5,y:.4,z:0,visibility:1}));
          pose[11].x=.3;pose[12].x=.7;pose[15].x=.2;pose[16].x=.8;
          const left=Array.from({length:21},()=>({x:.2,y:.4,z:0}));
          const right=Array.from({length:21},()=>({x:.8,y:.4,z:0}));
        ''')

    def test_detection_order_does_not_swap_anatomical_hands(self):
        self.assertTrue(self.js.eval('JSON.stringify(associateHands(pose,[left,right]))===JSON.stringify(associateHands(pose,[right,left]))'))
        self.assertAlmostEqual(self.js.eval('associateHands(pose,[right,left]).left[0][0]'),.2)

    def test_invisible_shoulders_are_not_accepted(self):
        self.assertIsNone(self.js.eval('pose[11].visibility=.1;associateHands(pose,[left])'))

    def test_distant_hand_is_not_forced_into_a_body_slot(self):
        self.assertIsNone(self.js.eval('associateHands(pose,[left.map(p=>({...p,x:2}))]).left'))

    def test_invisible_wrists_do_not_assign_a_single_hand(self):
        self.assertTrue(self.js.eval('pose[15].visibility=.1;pose[16].visibility=.1;const r=associateHands(pose,[left]);r.left===null&&r.right===null'))


if __name__=='__main__':unittest.main()
