import unittest
from pathlib import Path
import quickjs
ROOT=Path(__file__).resolve().parents[1]
class FaceTests(unittest.TestCase):
    def setUp(self):
        self.js=quickjs.Context();self.js.eval((ROOT/'face-tracker.js').read_text(encoding='utf-8').replace('export ',''))
        self.js.eval('''
          const states=[],calls=[],draws=[],expressions=[],delegates=[];let fail=false,gpuFail=false,noFace=false,blendshapes=true;
          let coefficients={mouthSmileLeft:.9,mouthSmileRight:.9,jawOpen:.1,browInnerUp:.1,browDownLeft:.1,browDownRight:.1};
          const console={warn(){}};
          const model={detectForVideo(v,t){calls.push(t);if(fail)throw Error('inference');return {faceLandmarks:noFace?[]:[[{x:.2,y:.2},{x:.5,y:.6}]],faceBlendshapes:blendshapes?[{categories:Object.entries(coefficients).map(([categoryName,score])=>({categoryName,score}))}]:[]}},close(){}};
          const api={FaceLandmarker:{FACE_LANDMARKS_FACE_OVAL:[{start:0,end:1}],async createFromOptions(f,o){delegates.push(o.baseOptions.delegate);if(!o.outputFaceBlendshapes)throw Error('Blendshapes must be enabled');if(gpuFail && o.baseOptions.delegate==='GPU')throw Error('GPU');return model}}};
          const ctx={save(){},restore(){},beginPath(){},moveTo(){},lineTo(){},stroke(){},arc(){},fill(){},strokeRect(){draws.push(1)}};
          const tracker=createFaceTracker(s=>states.push(s),s=>expressions.push(s));
        ''')
    def drain(self):
        while self.js.execute_pending_job():pass
    def test_load_throttle_toggle_and_reset(self):
        self.js.eval('tracker.load(api,{});');self.drain()
        self.js.eval('tracker.draw({},0,ctx,640,480);tracker.draw({},50,ctx,640,480);tracker.draw({},100,ctx,640,480);')
        self.assertEqual(self.js.eval('calls.length'),2)
        self.assertEqual(self.js.eval('states[states.length-1]'),'Face tracked')
        self.js.eval('tracker.setEnabled(false);tracker.draw({},200,ctx,640,480);')
        self.assertEqual(self.js.eval('calls.length'),2)
        self.assertEqual(self.js.eval('states[states.length-1]'),'Off')
        self.js.eval('tracker.setEnabled(true);tracker.reset();tracker.draw({},300,ctx,640,480);');self.drain()
        self.assertEqual(self.js.eval('calls.length'),3)
    def test_gpu_fallback_and_runtime_failure(self):
        self.js.eval('gpuFail=true;tracker.load(api,{});');self.drain()
        self.assertEqual(self.js.eval('states[states.length-1]'),'Ready')
        self.js.eval('fail=true;tracker.draw({},0,ctx,640,480);')
        self.assertEqual(self.js.eval('states[states.length-1]'),'Unavailable')
        self.js.eval('tracker.draw({},200,ctx,640,480);')
        self.assertEqual(self.js.eval('calls.length'),1)
    def test_failed_download_is_contained(self):
        self.js.eval("api.FaceLandmarker.createFromOptions=async()=>{throw Error('download')};tracker.load(api,{});");self.drain()
        self.assertEqual(self.js.eval('states[states.length-1]'),'Unavailable')
        self.js.eval('tracker.draw({},100,ctx,640,480);')
        self.assertEqual(self.js.eval('calls.length'),0)
    def test_expression_rules_describe_movements(self):
        self.assertEqual(self.js.eval('facialExpression(coefficients)'),'Smiling')
        self.assertEqual(self.js.eval('facialExpression({...coefficients,mouthSmileLeft:0,mouthSmileRight:0,jawOpen:.8,browInnerUp:.8})'),'Mouth open · Brows raised')
        self.assertEqual(self.js.eval('facialExpression({...coefficients,mouthSmileLeft:0,mouthSmileRight:0,browDownLeft:.8,browDownRight:.8})'),'Brows lowered')
        self.assertIsNone(self.js.eval('facialExpression({})'))
        self.assertIsNone(self.js.eval('facialExpression({...coefficients,jawOpen:NaN})'))
    def test_expression_stability_and_face_loss(self):
        self.js.eval('tracker.load(api,{});');self.drain()
        self.js.eval('tracker.draw({},0,ctx,640,480);tracker.draw({},100,ctx,640,480);')
        self.assertNotEqual(self.js.eval('expressions[expressions.length-1]'),'Smiling')
        self.js.eval('tracker.draw({},200,ctx,640,480);tracker.draw({},300,ctx,640,480);')
        self.assertEqual(self.js.eval('expressions[expressions.length-1]'),'Smiling')
        self.js.eval('noFace=true;tracker.draw({},400,ctx,640,480);')
        self.assertEqual(self.js.eval('expressions[expressions.length-1]'),'No face')
        self.js.eval('tracker.setEnabled(false);')
        self.assertEqual(self.js.eval('expressions[expressions.length-1]'),'Off')
    def test_missing_blendshapes_clear_previous_expression(self):
        self.js.eval('tracker.load(api,{});');self.drain()
        self.js.eval('for(let t=0;t<=300;t+=100)tracker.draw({},t,ctx,640,480);blendshapes=false;tracker.draw({},400,ctx,640,480);')
        self.assertEqual(self.js.eval('expressions[expressions.length-1]'),'Unavailable')
        self.assertEqual(self.js.eval('states[states.length-1]'),'Face tracked')
    def test_slow_camera_still_produces_expression(self):
        self.js.eval('tracker.load(api,{});');self.drain()
        self.js.eval('tracker.draw({},0,ctx,640,480);tracker.draw({},1200,ctx,640,480);')
        self.assertEqual(self.js.eval('expressions[expressions.length-1]'),'Smiling')
    def test_runtime_gpu_error_recovers_on_cpu(self):
        self.js.eval('tracker.load(api,{});');self.drain()
        self.js.eval('fail=true;tracker.draw({},0,ctx,640,480);');self.drain()
        self.assertEqual(self.js.eval('JSON.stringify(delegates)'), '["GPU","CPU"]')
        self.js.eval('fail=false;tracker.draw({},200,ctx,640,480);')
        self.assertEqual(self.js.eval('states[states.length-1]'),'Face tracked')
        self.assertGreater(self.js.eval('draws.length'),0)
    def test_failed_load_can_be_retried(self):
        self.js.eval("const factory=api.FaceLandmarker.createFromOptions;api.FaceLandmarker.createFromOptions=async()=>{throw Error('offline')};tracker.load(api,{});");self.drain()
        self.assertEqual(self.js.eval('states[states.length-1]'),'Unavailable')
        self.js.eval('api.FaceLandmarker.createFromOptions=factory;tracker.load();');self.drain()
        self.js.eval('tracker.draw({},200,ctx,640,480);')
        self.assertEqual(self.js.eval('states[states.length-1]'),'Face tracked')
    def test_word_recording_pauses_and_resumes_face_inference(self):
        self.js.eval('tracker.load(api,{});');self.drain()
        self.js.eval('tracker.draw({},0,ctx,640,480,true);tracker.draw({},100,ctx,640,480,true);')
        self.assertEqual(self.js.eval('calls.length'),0)
        self.assertEqual(self.js.eval('states[states.length-1]'),'Paused for word recording')
        self.js.eval('tracker.draw({},200,ctx,640,480,false);')
        self.assertEqual(self.js.eval('calls.length'),1)
        self.assertEqual(self.js.eval('states[states.length-1]'),'Face tracked')
if __name__=='__main__':unittest.main()
