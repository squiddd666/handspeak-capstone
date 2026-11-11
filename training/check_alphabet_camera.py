"""Real-browser reference-media regression, not independent ASL accuracy.

Run against the running app with .venv/Scripts/python.exe -X utf8
training/check_alphabet_camera.py --rounds 3 --variations
The expected label is used only by Python when scoring collected UI output.
No landmarks, classifiers, thresholds, or app responses are mocked.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import string
import time
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
CAMERA = """()=>{
 const c=document.createElement('canvas');c.width=640;c.height=480;
 const ctx=c.getContext('2d');
 window.vcam={c,ctx,source:null,samples:[],events:[],scale:1,dx:0,dy:0,mirror:false};
 document.addEventListener('handspeak:letter-committed',event=>vcam.events.push({...event.detail,observedAt:performance.now()}));
 navigator.mediaDevices.getUserMedia=async constraints=>{
   if(constraints.audio)throw Error('Audio was not requested by this test');
   return c.captureStream(15);
 };
 function draw(){
   ctx.resetTransform();ctx.fillStyle='#888';ctx.fillRect(0,0,640,480);
   const s=vcam.source;
   if(s&&((s.tagName==='IMG'&&s.complete)||(s.tagName==='VIDEO'&&s.readyState>=2))){
     const w=s.naturalWidth||s.videoWidth,h=s.naturalHeight||s.videoHeight;
     const k=Math.min(640/w,480/h)*vcam.scale;
     ctx.translate(320+vcam.dx,240+vcam.dy);if(vcam.mirror)ctx.scale(-1,1);
     ctx.drawImage(s,-w*k/2,-h*k/2,w*k,h*k);
   }
   requestAnimationFrame(draw);
 }
 draw();
 setInterval(()=>{
   const visible=!document.querySelector('#liveResult').hidden;
   vcam.samples.push({t:performance.now(),letter:visible?document.querySelector('#liveLetter').textContent.trim():null,
     feedback:document.querySelector('#recognitionFeedback').textContent,
     hands:document.querySelector('#trackingHands').textContent});
 },100);
}"""


def score(samples, expected, motion=False):
    # Include abstentions in the denominator; never count stale hidden text.
    counts = Counter(s['letter'] for s in samples)
    dominant = counts.most_common(1)[0][0] if counts else None
    final = samples[-1] if samples else {}
    wrong = sorted({s['letter'] for s in samples if s['letter'] is not None and s['letter'] in string.ascii_uppercase and s['letter'] != expected})
    committed_wrong = sorted({s['letter'] for s in samples if s['letter'] in wrong and '— recognized.' in s['feedback']})
    recognized = ('motion recognized.' if motion else '— recognized.') in final.get('feedback', '')
    passed = dominant == expected and final.get('letter') == expected and recognized and not committed_wrong
    return dict(passed=passed, dominant=dominant, final=final, counts=dict((k or 'hidden',v) for k,v in counts.items()),
                transientWrong=wrong, committedWrong=committed_wrong,
                noHandSamples=sum(s['hands'].startswith('0') for s in samples), samples=len(samples))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://localhost:8000/')
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--letters', default=string.ascii_uppercase, help='Debug subset; omitted for the full acceptance regression.')
    parser.add_argument('--audit', action='store_true', help='Collect count-only frame audit events; use a URL with letterAudit=1.')
    parser.add_argument('--landmark-audit', action='store_true', help='Retain landmarks of public reference replays only; implies --audit.')
    parser.add_argument('--variations', action='store_true')
    parser.add_argument('--output', type=Path, default=ROOT/'reports/alphabet-repair-20261111/final-camera')
    args = parser.parse_args();args.output.mkdir(parents=True, exist_ok=True)
    sources = json.loads((ROOT/'models/motion-letters-sources.json').read_text())['source']
    report = dict(scope='Reference-media smoke/regression only. Independent browser contexts, not independent signers or images. No expected-label access in the app.',
                  geometry=dict(width=640,height=480,fps=15,fit='contain',crop=False),
                  sourceHashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'media/letters').glob('*.jpg')},
                  codeHashes={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in ['app.js','gesture-model.js','letter-recognition.js','motion-letters.js','letter-camera.js','letter-detection-worker.js','onnx-hand-detector.js','models/hand-landmarks/manifest.json','models/asl-knn.json']},
                  attempts=[], negatives=[], pageErrors=[])
    configs = [(f'repeat-{i+1}',1,0,0) for i in range(args.rounds)]
    if args.variations: configs += [('smaller-left',.8,-45,15), ('smaller-right',.65,45,-15)]
    def save(): (args.output/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',headless=True,args=['--autoplay-policy=no-user-gesture-required','--use-fake-ui-for-media-stream'])
        for name,scale,dx,dy in configs:
            context=browser.new_context(viewport={'width':1280,'height':900});page=context.new_page();page.set_default_timeout(120000)
            page.on('pageerror',lambda e:report['pageErrors'].append(str(e)))
            page.goto(args.url,wait_until='networkidle');page.evaluate(CAMERA)
            if args.audit or args.landmark_audit:
                page.evaluate("""async retain=>{vcam.audit=[];const {isUsableLetterHand}=await import('./letter-recognition.js');
                 document.addEventListener('handspeak:letter-frame',e=>{
                   const {detection:d,temporal:t,timestamp}=e.detail;
                   const aspect=document.querySelector('#webcam').videoHeight/document.querySelector('#webcam').videoWidth;
                   vcam.audit.push({timestamp,observedAt:performance.now(),raw:d.landmarks?.length||0,
                     usable:(d.landmarks||[]).filter(p=>isUsableLetterHand(p,aspect)).length,
                     tracked:d.trackedLandmarks?.length||0,motionHands:d.motionHands?.length??null,
                     moving:!!t.moving,motion:t.result?.letter??null,handIds:t.presentIds??null,
                     motionHandId:t.result?.handId??null,timings:d.timings??null,
                     ...(retain?{aspect,points:d.landmarks,trackedPoints:d.trackedLandmarks,handedness:d.handedness,
                       workerCandidate:d.staticResult??null,arrivalLagMs:d.capturedAt==null?null:performance.now()-d.capturedAt}: {})});
                });}""",args.landmark_audit)
            # Preserve the original app settings, including default face tracking.
            page.locator('#cameraButton').click(force=True)
            page.wait_for_function("document.querySelector('#cameraButton').textContent.includes('Stop camera')")
            page.evaluate('vcam.samples=[]');page.wait_for_timeout(2500)
            samples=page.evaluate('vcam.samples')
            report['negatives'].append(dict(round=name,case='initial-no-hand',
                passed=not any(s['letter'] in string.ascii_uppercase for s in samples if s['letter']),samples=samples))
            for letter in args.letters:
                page.evaluate('vcam.source=null;vcam.samples=[];vcam.events=[]');page.wait_for_timeout(1300)
                motion=letter in 'JZ'
                src=sources[letter.lower()]['video'] if motion else '/media/letters/'+letter.lower()+'.jpg'
                try:
                    page.evaluate("""async({src,motion,scale,dx,dy})=>{
                      const s=document.createElement(motion?'video':'img');s.crossOrigin='anonymous';
                      if(motion){s.muted=true;s.playbackRate=.67;s.playsInline=true;}
                      await new Promise((ok,fail)=>{s[motion?'onloadeddata':'onload']=ok;s.onerror=()=>fail(Error('Reference load failed'));s.src=src});
                      vcam.samples=[];vcam.events=[];if(vcam.audit)vcam.audit=[];vcam.scale=scale;vcam.dx=dx;vcam.dy=dy;vcam.source=s;
                      if(motion)await s.play();
                    }""",dict(src=src,motion=motion,scale=scale,dx=dx,dy=dy))
                    page.wait_for_timeout(9000 if motion else 4500)
                    samples=page.evaluate('vcam.samples');result=score(samples,letter,motion)
                    result.update(round=name,letter=letter,source=src,scale=scale,dx=dx,dy=dy,trace=samples,commits=page.evaluate('vcam.events'),draft=page.locator('#captureTranscript').inner_text(),diagnostics=page.locator('#cameraDiagnostics').inner_text())
                    if args.audit or args.landmark_audit:result['frames']=page.evaluate('vcam.audit')
                    page.screenshot(path=str(args.output/f'{name}-{letter}.png'))
                except Exception as e: result=dict(round=name,letter=letter,passed=False,error=str(e))
                report['attempts'].append(result);save()
                print(json.dumps({k:v for k,v in result.items() if k not in ['trace','source','diagnostics','frames']}),flush=True)
            page.evaluate('vcam.source=null;vcam.samples=[];vcam.events=[]');page.wait_for_timeout(2500)
            samples=page.evaluate('vcam.samples')
            # Allow the first 500 ms to drain the preceding captured frame.
            tail=samples[5:]
            report['negatives'].append(dict(round=name,case='withdrawal-no-hand',passed=bool(tail) and all(s['hands'].startswith('0') and s['letter'] is None for s in tail),samples=samples))
            page.locator('#cameraButton').click(force=True);context.close();save()
        browser.close()
    report['summary']={letter:dict(passed=sum(r['passed'] for r in report['attempts'] if r['letter']==letter),
                                  attempts=sum(r['letter']==letter for r in report['attempts'])) for letter in string.ascii_uppercase}
    save();print(json.dumps(report['summary']),flush=True)


if __name__=='__main__': main()
