"""Real capture-controller code with deterministic clocks/trackers, not webcam evidence."""
import json
from pathlib import Path
import unittest
import quickjs

ROOT = Path(__file__).resolve().parents[1]


class CaptureController(unittest.TestCase):
    def setUp(self):
        self.js = quickjs.Context()
        self.js.eval('''
          let clock=0,timerId=0,posts=[],timers={},statuses=[];
          const elements={};
          const document={querySelector:s=>elements[s]||=( {value:'target20',checked:false,disabled:false,dataset:{},addEventListener(n,f){this[n]=f}}),dispatchEvent(){}};
          const window={addEventListener(){}};const performance={now:()=>clock};
          function setTimeout(f){timers[++timerId]=f;return timerId}function clearTimeout(i){delete timers[i]}
          class AbortController{constructor(){this.signal={}}abort(){this.signal.aborted=true}}
          class CustomEvent{constructor(n,o){this.detail=o.detail}}
          const pose=[[.5,.2,0],[.5,.2,0],[.5,.2,0],[.3,.4,0],[.7,.4,0],[.3,.6,0],[.7,.6,0]];
          class FakeHolistic{
            setOptions(){} onResults(f){this.callback=f} async initialize(){} close(){}
            send(){
              const body=Array.from({length:33},()=>({x:.5,y:.3,z:0}));
              [0,2,5,11,12,13,14].forEach((k,i)=>body[k]={x:pose[i][0],y:pose[i][1],z:0});
              this.callback({poseLandmarks:body,leftHandLandmarks:Array.from({length:21},()=>({x:.3,y:.5,z:0}))});
              return {then:f=>{f();return {catch(){}}}};
            }
          }
          window.Holistic=FakeHolistic;
          async function fetch(url,options){if(options){posts.push(JSON.parse(options.body));return {ok:true,json:async()=>({predictions:[],state:'unknown',vocabulary:'target20'})}}return {ok:true,json:async()=>({available:true,labels:['HELLO']})}}
        ''')
        code = '\n'.join(l for l in (ROOT/'beginner-recognition.js').read_text(encoding='utf-8').splitlines() if not l.startswith('import '))
        self.js.eval(code.replace('export ', ''))
        self.js.eval("const controller=createBeginnerRecognition({isRunning:()=>true,startCamera:async()=>{},onWord(){},onStatus(){},prepare(){}});")
        self.drain()

    def drain(self):
        while self.js.execute_pending_job(): pass

    def start(self):
        self.js.eval("document.querySelector('#beginnerConsent').checked=true;elements['#beginnerRecord'].click();")
        self.drain()
        self.js.eval('clock=1500;const startTimer=Object.keys(timers)[0];timers[startTimer]();delete timers[startTimer];')

    def test_no_consent_never_records(self):
        self.js.eval("elements['#beginnerRecord'].click();")
        self.drain()
        self.assertFalse(self.js.eval('controller.isCapturing()'))
        self.assertEqual(self.js.eval('posts.length'),0)

    def test_complete_capture_submits_once_with_metadata(self):
        self.start()
        self.js.eval('for(let i=1;i<=65;i++){clock=1500+i*67;controller.frame({},clock,{currentTime:i/15})}')
        self.drain()
        self.assertEqual(self.js.eval('posts.length'),1)
        body=json.loads(self.js.eval('JSON.stringify(posts[0])'))
        self.assertTrue(body['capture']['complete'])
        self.assertGreaterEqual(body['capture']['durationMs'],4000)
        self.assertTrue(all('timestampMs' in f for f in body['frames']))

    def test_duplicate_video_frames_do_not_fill_capture(self):
        self.start()
        self.js.eval('for(let i=1;i<=70;i++){clock=1500+i*67;controller.frame({},clock,{currentTime:1})}')
        self.drain()
        self.assertEqual(self.js.eval('posts.length'),0)

    def test_source_timestamp_gap_blocks_submission(self):
        self.start()
        self.js.eval('for(let i=1;i<=65;i++){clock=1500+i*67;controller.frame({},clock,{currentTime:i/15+(i>=30?1:0)})}')
        self.drain()
        self.assertEqual(self.js.eval('posts.length'),0)
        self.assertIn('Capture quality insufficient',self.js.eval("elements['#beginnerStatus'].textContent"))

    def test_consent_revoked_during_capture_blocks_submission(self):
        self.start()
        self.js.eval("for(let i=1;i<=65;i++){if(i===30)elements['#beginnerConsent'].checked=false;clock=1500+i*67;controller.frame({},clock,{currentTime:i/15})}")
        self.drain()
        self.assertEqual(self.js.eval('posts.length'),0)
        self.assertIn('Consent withdrawn',self.js.eval("elements['#beginnerStatus'].textContent"))

    def test_cancel_discards_partial_recording(self):
        self.start()
        self.js.eval('clock=1600;controller.frame({},clock,{currentTime:1});controller.cancel();clock=6000;controller.frame({},clock,{currentTime:2});')
        self.drain()
        self.assertEqual(self.js.eval('posts.length'),0)
        self.assertFalse(self.js.eval('controller.isCapturing()'))

    def test_timeout_does_not_submit_sparse_capture(self):
        self.start()
        self.js.eval('clock=9500;for(const k of Object.keys(timers))timers[k]();')
        self.drain()
        self.assertEqual(self.js.eval('posts.length'),0)
        self.assertIn('Nothing was submitted',self.js.eval("elements['#beginnerStatus'].textContent"))


if __name__=='__main__': unittest.main()

