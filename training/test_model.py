"""Run: python -m unittest discover -s training -v (requires quickjs)."""
import json
from pathlib import Path
import unittest

import numpy as np
import quickjs
from train_asl import normalize
from reference_classifiers import static_prediction

ROOT = Path(__file__).resolve().parents[1]


class ModelTests(unittest.TestCase):
    def setUp(self):
        self.js = quickjs.Context()
        self.js.eval((ROOT/'gesture-model.js').read_text(encoding='utf-8').replace('export ', ''))
        self.model = json.loads((ROOT/'models/asl-knn.json').read_text(encoding='utf-8'))
        self.js.eval('const model = '+json.dumps(self.model)+';')

    def test_export_is_valid(self):
        self.assertTrue(self.js.eval('model.samples.every(s=>validSample(s, model.labels))'))
        self.assertEqual(set(self.model['labels']), set('ABCDEFGHIKLMNOPQRSTUVWXY'))
        self.assertFalse(self.js.eval("validSample({label:'A',features:[1]}, ['A'])"))

    def test_normalization_matches_training(self):
        points = np.random.default_rng(9).random((21, 3))
        objects = [dict(zip(['x', 'y', 'z'], p)) for p in points]
        actual = json.loads(self.js.eval('JSON.stringify(normalizeLandmarks('+json.dumps(objects)+'))'))
        np.testing.assert_allclose(actual, normalize(points), atol=0.000001)

    def test_legacy_vectors_current_classifier_python_parity(self):
        fixtures = json.loads((ROOT/'models/asl-test-fixture.json').read_text(encoding='utf-8'))
        for row in fixtures:
            result = self.js.eval('(classifyFeatures('+json.dumps(row['features'])+',model.samples,model.parameters)||{}).letter || null')
            expected=static_prediction(row['features'],self.model['samples'],self.model['parameters'])
            self.assertEqual(result,expected,row['label'])
            mirrored = [(-v if i%3==0 else v) for i,v in enumerate(row['features'])]
            mirror_result = self.js.eval('(classifyFeatures('+json.dumps(mirrored)+',model.samples,model.parameters)||{}).letter || null')
            self.assertEqual(mirror_result,expected)
        self.assertIsNone(self.js.eval('classifyFeatures(Array(63).fill(0),[])'))

    def boot_app(self, failure=False):
        self.js.eval("""
          const elements={};
          function element(){return {value:'',textContent:'',hidden:false,disabled:false,checked:false,videoWidth:640,videoHeight:480,style:{},dataset:{},listeners:{},
            classList:{add(){},remove(){},toggle(){},contains(){return false}},
            addEventListener(name,fn){this.listeners[name]=fn},setAttribute(){},getAttribute(){return null},
            getContext(){return {clearRect(){},beginPath(){},moveTo(){},lineTo(){},stroke(){},arc(){},fill(){}}},
            querySelectorAll(){return []},querySelector(){return element()},replaceChildren(){},append(){},scrollIntoView(){}}}
          const document={documentElement:{dataset:{}},querySelector:key=>elements[key]||=element(),querySelectorAll:()=>[],addEventListener(){},dispatchEvent(){},createElement:()=>element()};
          const window={addEventListener(){}},location={search:''};
          const localStorage={getItem:()=>null,setItem(){},removeItem(){}};
          const console={warn(){},error(){}},AbortSignal={timeout(){}};
          function CustomEvent(name,options){this.type=name;this.detail=options?.detail;}
          function setTimeout(){} function clearTimeout(){} function clearInterval(){} function cancelAnimationFrame(){}
          const stub=()=>({cancel(){},disable(){},frame(){},active:()=>false,isCapturing:()=>false,needsHandDetection:()=>true,showCameraAccuracy(){},finish:()=>false});
          const createExperienceUI=stub,createResearchWords=stub,createVocabularyLibrary=stub,createCapstoneRecognition=stub,createBeginnerRecognition=stub,createInterpreter=stub;
        """)
        self.js.eval('const fetch=async path=>'+(
            '({ok:false,json:async()=>({})});' if failure else
            "path.includes('asl-knn')?({ok:true,json:async()=>model}):({ok:false,json:async()=>({})});"))
        for name in ['letter-recognition.js','motion-letters.js','camera-performance.js','sentence-builder.js','vocabulary-settings.js','motion-model.js','automatic-motion.js','temporal-word-model.js','expanded-motion.js','hello-binary.js','motion-studio.js','face-tracker.js']:
            code='\n'.join(line for line in (ROOT/name).read_text(encoding='utf-8').splitlines()if not line.startswith('import '))
            self.js.eval(code.replace('export {letterSequence};','').replace('export ',''))
        app='\n'.join(line for line in (ROOT/'app.js').read_text(encoding='utf-8').splitlines()if not line.startswith('import '))
        self.js.eval(app)
        while self.js.execute_pending_job():pass

    def test_auto_load_and_personal_reset(self):
        self.boot_app()
        self.assertEqual(self.js.eval('baseSamples.length'), len(self.model['samples']))
        self.assertIn(f"{len(self.model['labels'])} pretrained letters", self.js.eval("elements['#aiModelStatus'].textContent"))
        self.js.eval("aiSamples.push(model.samples[0]); elements['#resetModelButton'].listeners.click();")
        self.assertEqual(self.js.eval('aiSamples.length'), 0)
        self.assertEqual(self.js.eval('baseSamples.length'), len(self.model['samples']))

    def test_download_failure_reports_unavailable(self):
        self.boot_app(failure=True)
        self.assertEqual(self.js.eval('baseSamples.length'), 0)
        self.assertIn('unavailable', self.js.eval("elements['#aiModelStatus'].textContent"))

    def test_unfamiliar_and_ambiguous_poses_are_rejected(self):
        self.assertIsNone(self.js.eval('classifyFeatures(Array(63).fill(100),model.samples)'))
        self.assertIsNone(self.js.eval('classifyFeatures([NaN],model.samples)'))
        self.js.eval("const ambiguous=Array.from({length:20},(_,i)=>({label:i<10?'A':'B',features:Array(63).fill(0)}));")
        self.assertIsNone(self.js.eval('classifyFeatures(Array(63).fill(0),ambiguous)'))

    def test_training_locks_label_and_saves_complete_batch(self):
        self.boot_app()
        self.js.eval("""
          running=true; elements['#trainingLabel'].value='A';
          elements['#captureSamplesButton'].listeners.click();
          elements['#trainingLabel'].value='B';
          const sample=model.samples[0].features;
          const points=Array.from({length:21},(_,i)=>({x:.5+sample[i*3]*.05,y:.5+sample[i*3+1]*.05,z:sample[i*3+2]*.05}));
          captureTrainingSample(points,200);
        """)
        self.assertEqual(self.js.eval('aiSamples.length'), 0)
        self.assertTrue(self.js.eval("elements['#trainingLabel'].disabled"))
        self.js.eval('for(let i=2;i<=30;i++)captureTrainingSample(points,i*200);')
        self.assertEqual(self.js.eval('aiSamples.length'), 30)
        self.assertTrue(self.js.eval("aiSamples.every(s=>s.label==='A')"))
        self.assertFalse(self.js.eval('trainingActive'))

    def test_camera_stop_discards_partial_capture_and_stale_candidate(self):
        self.boot_app()
        self.js.eval("""
          running=true; elements['#trainingLabel'].value='A';
          elements['#captureSamplesButton'].listeners.click();
          pendingSamples.push(model.samples[0]);candidate='A';candidateSince=100;committed='A';
          stopCamera();
        """)
        self.assertEqual(self.js.eval('pendingSamples.length'), 0)
        self.assertEqual(self.js.eval('aiSamples.length'), 0)
        self.assertEqual(self.js.eval('candidate'), '')
        self.assertFalse(self.js.eval('trainingActive'))


    def test_camera_processes_new_frames_only_and_never_types_during_training(self):
        self.boot_app()
        self.js.eval("""
          const sample=model.samples[0].features;
          const points=Array.from({length:21},(_,i)=>({x:.5+sample[i*3]*.05,y:.5+sample[i*3+1]*.05,z:sample[i*3+2]*.05}));
          const performance={now:()=>1000};
          function requestAnimationFrame(){}
          let calls=0,stabilized=0;
          handLandmarker={detectForVideo(){calls++;return {landmarks:[points]}}};
          drawHand=()=>{};stabilize=()=>{stabilized++};
          video.readyState=2;video.currentTime=1;video.videoWidth=640;video.videoHeight=480;
          running=true; elements['#trainingLabel'].value='A';
          elements['#captureSamplesButton'].listeners.click();
          detect();detect();
        """)
        self.assertEqual(self.js.eval('calls'), 1)
        self.assertEqual(self.js.eval('stabilized'), 0)
        self.assertEqual(self.js.eval('pendingSamples.length'), 1)
        self.js.eval('endTraining();video.currentTime=2;detect();')
        self.assertEqual(self.js.eval('stabilized'), 1)

    def test_hand_error_does_not_stop_face_loop(self):
        self.boot_app()
        self.js.eval('''
          const performance={now:()=>1000};let faceFrames=0,scheduled=0;
          function requestAnimationFrame(){scheduled++}
          faceTracker.draw=()=>{faceFrames++};
          handLandmarker={detectForVideo(){throw Error('GPU lost')},close(){}};
          video.readyState=2;video.currentTime=1;video.videoWidth=640;video.videoHeight=480;running=true;
          detect();video.currentTime=2;detect();
        ''')
        self.assertEqual(self.js.eval('faceFrames'),2)
        self.assertEqual(self.js.eval('scheduled'),2)
        self.assertIsNone(self.js.eval('handLandmarker'))

    def test_camera_restart_retries_face_model(self):
        self.boot_app()
        self.js.eval('let faceLoads=0;faceTracker.load=()=>{faceLoads++};handLandmarker={};handMaxHands=1;letterImageLandmarker={};loadRecognizer();')
        while self.js.execute_pending_job():pass
        self.assertEqual(self.js.eval('faceLoads'),1)
    def test_camera_word_button_selects_word_mode(self):
        self.boot_app()
        self.js.eval("let started=0;running=true;motionStudio.recognize=()=>{started++};motionStudio.isCapturing=()=>true;motionStudio.isRecording=()=>true;elements['#wordCaptureButton'].listeners.click();")
        while self.js.execute_pending_job():pass
        self.assertEqual(self.js.eval('recognitionMode'),'words')
        self.assertEqual(self.js.eval('started'),1)
        self.assertTrue(self.js.eval("elements['#wordCaptureButton'].disabled"))



if __name__ == '__main__':
    unittest.main()

