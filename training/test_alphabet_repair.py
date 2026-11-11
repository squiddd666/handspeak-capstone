"""Geometry/temporal correctness tests, not independent ASL accuracy."""
import json
from pathlib import Path
import unittest
import quickjs

ROOT=Path(__file__).resolve().parents[1]

class AlphabetRepairTests(unittest.TestCase):
    def setUp(self):
        self.js=quickjs.Context()
        for name in ['gesture-model.js','letter-recognition.js','motion-letters.js']:
            code='\n'.join(line for line in (ROOT/name).read_text(encoding='utf-8').splitlines() if not line.startswith('import '))
            self.js.eval(code.replace('export {letterSequence};','').replace('export ',''))
        self.js.eval('''
          const palm=Array.from({length:21},(_,i)=>({x:.5+i*.005,y:.7-i*.01,z:i*.001}));
          const consensus=createLetterConsensus();
          function observed(letter,t){return consensus.push(letter?{letter,confidence:1}:null,t);}
        ''')

    def test_rectangular_camera_geometry_is_isotropic(self):
        self.assertTrue(self.js.eval('''(()=>{
          const square=letterFeatures(palm,1);
          const rectangular=letterFeatures(palm.map(p=>({...p,y:p.y/.75})),.75);
          return square.every((v,i)=>Math.abs(v-rectangular[i])<1e-10);
        })()'''))

    def test_translation_and_scale_invariance(self):
        self.assertTrue(self.js.eval('''(()=>{
          const a=letterFeatures(palm,.75);
          const b=letterFeatures(palm.map(p=>({x:.1+p.x*.5,y:.2+p.y*.5,z:p.z*.5})),.75);
          return a.every((v,i)=>Math.abs(v-b[i])<1e-10);
        })()'''))

    def test_edge_on_comparison_scale_is_finite_and_scale_invariant(self):
        self.assertTrue(self.js.eval('''(()=>{
          const f=letterFeatures(palm,.75);f[51]=f[15]+1e-5;f[52]=f[16]+1e-5;
          const a=stablePalmFeatures(f),b=stablePalmFeatures(f.map(v=>v*100));
          return a.every((v,i)=>Number.isFinite(v)&&Math.abs(v-b[i])<1e-10);
        })()'''))

    def test_degenerate_comparison_does_not_accept_ambiguous_evidence(self):
        self.assertIsNone(self.js.eval('''(()=>{
          const f=letterFeatures(palm,.75);
          const samples=Array.from({length:20},(_,i)=>({label:i<10?'A':'B',features:f.slice()}));
          return classifyLetter(palm,samples,DEFAULT_PARAMETERS,.75);
        })()'''))

    def test_reject_invalid_tiny_and_clipped_hands(self):
        for expression in ['null','[]','palm.map(p=>({...p,x:NaN}))','palm.map(p=>({...p,x:1.1}))','palm.map(p=>({x:.5+p.x*.001,y:.5+p.y*.001,z:0}))']:
            self.assertFalse(self.js.eval(f'isUsableLetterHand({expression},.75)'))

    def test_side_on_palm_not_mistaken_for_small_hand(self):
        self.assertTrue(self.js.eval('''(()=>{const p=palm.map(p=>({...p}));p[5]={x:.5,y:.5,z:0};p[17]={x:.501,y:.501,z:0};p[0]={x:.5,y:.8,z:0};p[9]={x:.5,y:.5,z:0};return isUsableLetterHand(p,.75);})()'''))

    def test_no_evidence_never_commits(self):
        self.assertTrue(self.js.eval('Array.from({length:30},(_,i)=>observed(null,i*70)).every(v=>v===null)'))

    def test_single_flash_cannot_commit(self):
        self.js.eval("observed('A',0)")
        self.assertIsNone(self.js.eval('observed(null,1000)'))
        self.assertIsNone(self.js.eval("observed('A',1100)"))

    def test_short_abstention_preserves_but_does_not_create_evidence(self):
        self.assertIsNone(self.js.eval("observed('K',0)"))
        self.js.eval("for(let t=100;t<=800;t+=100)observed(t===400?null:'K',t)")
        self.assertEqual(self.js.eval("observed('K',900).letter"),'K')

    def test_competing_letter_resets_hold(self):
        self.js.eval("for(let t=0;t<=800;t+=100)observed('U',t)")
        self.assertIsNone(self.js.eval("observed('V',900)"))

    def test_long_gap_or_reversed_clock_resets_hold(self):
        self.js.eval("for(let t=0;t<=800;t+=100)observed('A',t)")
        self.assertIsNone(self.js.eval("observed('A',1400)"))
        self.assertIsNone(self.js.eval("observed('A',100)"))

    def test_sparse_positive_evidence_cannot_commit(self):
        self.js.eval("for(let t=0;t<1000;t+=100)observed(t%200===0?'Q':null,t)")
        self.assertIsNone(self.js.eval("observed('Q',1000)"))

    def test_motion_stationary_pose_never_produces_j_or_z(self):
        model=json.loads((ROOT/'models/motion-letters.json').read_text(encoding='utf-8'))
        self.js.eval('const motion=createMotionLetters();motion.setModel('+json.dumps(model)+');')
        self.assertTrue(self.js.eval('Array.from({length:90},(_,i)=>motion.frame(palm,i*67)).every(r=>r.result===null)'))

    def test_complete_motion_template_in_both_mirrors(self):
        model=json.loads((ROOT/'models/motion-letters.json').read_text(encoding='utf-8'))
        self.js.eval('const motionModel='+json.dumps(model)+';')
        result=json.loads(self.js.eval('''JSON.stringify(motionModel.templates.flatMap(template=>[1,-1].map(mirror=>{
          const matcher=createMotionLetters();matcher.setModel(motionModel);let recognized=[];
          template.sequence.forEach((row,i)=>{
            const active=template.tip===20?4:1;
            const wx=row[0]-row[2+active*2],wy=row[1]-row[3+active*2];
            const p=Array.from({length:21},()=>({x:wx*mirror,y:wy,z:0}));
            p[5]={x:(wx+.5)*mirror,y:wy-.5,z:0};p[17]={x:(wx-.5)*mirror,y:wy-.5,z:0};
            [4,8,12,16,20].forEach((tip,k)=>p[tip]={x:(wx+row[2+k*2])*mirror,y:wy+row[3+k*2],z:0});
            const r=matcher.frame(p,i*67);if(r.result)recognized.push(r.result.letter);
          });
          return {expected:template.letter,mirror,recognized};
        })))'''))
        for row in result:self.assertIn(row['expected'],row['recognized'],row)

    def test_incomplete_motion_and_lost_tracking_do_not_complete_letters(self):
        model=json.loads((ROOT/'models/motion-letters.json').read_text(encoding='utf-8'))
        self.js.eval('const partialModel='+json.dumps(model)+';')
        result=json.loads(self.js.eval('''JSON.stringify(partialModel.templates.flatMap(template=>[false,true].map(gap=>{
          const matcher=createMotionLetters();matcher.setModel(partialModel);let recognized=[];
          const rows=gap?template.sequence:template.sequence.slice(0,12);
          rows.forEach((row,i)=>{
            const active=template.tip===20?4:1;
            const wx=row[0]-row[2+active*2],wy=row[1]-row[3+active*2];
            const p=Array.from({length:21},()=>({x:wx,y:wy,z:0}));
            p[5]={x:wx+.5,y:wy-.5,z:0};p[17]={x:wx-.5,y:wy-.5,z:0};
            [4,8,12,16,20].forEach((tip,k)=>p[tip]={x:wx+row[2+k*2],y:wy+row[3+k*2],z:0});
            const r=matcher.frame(p,i*67+(gap&&i>=12?700:0));if(r.result)recognized.push(r.result.letter);
          });return {letter:template.letter,gap,recognized};
        })))'''))
        for row in result:self.assertEqual(row['recognized'],[],row)

if __name__=='__main__':unittest.main()
