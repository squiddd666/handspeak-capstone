"""Additional-source and negative UI checks; separate from original acceptance.

Requires the external videos listed in additional-reference-sources.json.
No extra frame is added to the recognition model. All static source frames are
sampled at the same 1500 ms and use the same disclosed crop, without selecting
the best-predicting frame for any letter.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import string
import cv2
from playwright.sync_api import sync_playwright
from check_alphabet_camera import ROOT, CAMERA, score


def main():
    base=ROOT/'reports/alphabet-repair-20261111';out=base/'additional-source-camera';out.mkdir(parents=True,exist_ok=True)
    sources=json.loads((base/'additional-reference-sources.json').read_text());frames={}
    for label in string.ascii_uppercase:
        if label in 'JZ' or sources[label].get('error'):continue
        cap=cv2.VideoCapture(sources[label]['local']);cap.set(cv2.CAP_PROP_POS_MSEC,1500);ok,frame=cap.read();cap.release()
        if not ok:continue
        frame=frame[350:900,0:720];ok,data=cv2.imencode('.png',frame)
        if ok:frames[label]=data.tobytes()
    report=dict(scope='Additional source/crop/1500 ms fixed-frame smoke tests, not independent signer accuracy or a replacement for original regression.',
                crop=dict(x=0,y=350,width=720,height=550),sampleTimeMs=1500,faceTracking=False,attempts=[],negatives=[],errors=[])
    with sync_playwright() as p:
        b=p.chromium.launch(channel='chrome',headless=True);context=b.new_context(viewport={'width':1280,'height':900});page=context.new_page();page.set_default_timeout(120000)
        page.route('**/__letter-reference-test__/*.png',lambda route:route.fulfill(content_type='image/png',body=frames[route.request.url.split('/')[-1].split('.')[0]]))
        page.on('pageerror',lambda e:report['errors'].append(str(e)))
        page.goto('http://localhost:8000/',wait_until='networkidle');page.evaluate(CAMERA)
        if page.locator('#simpleViewButton').get_attribute('aria-pressed')=='true':page.locator('#simpleViewButton').click()
        page.locator('.camera-settings > summary').click()
        page.locator('#faceTrackingToggle').uncheck();page.locator('#cameraButton').click(force=True)
        page.wait_for_function("document.querySelector('#cameraButton').textContent.includes('Stop camera')")
        def save(): (out/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        for label,data in frames.items():
            page.evaluate('vcam.source=null');page.wait_for_timeout(1300)
            page.evaluate('''async src=>{const img=new Image();await new Promise((ok,fail)=>{img.onload=ok;img.onerror=fail;img.src=src});vcam.samples=[];vcam.source=img;}''','/__letter-reference-test__/'+label+'.png')
            page.wait_for_timeout(4500);samples=page.evaluate('vcam.samples')
            r=score(samples,label);r.update(letter=label,source=sources[label]['page'],frameSha256=hashlib.sha256(data).hexdigest(),trace=samples)
            report['attempts'].append(r);page.screenshot(path=str(out/(label+'.png')));save()
            print(json.dumps({k:v for k,v in r.items() if k!='trace'}),flush=True)
        for kind in ['blank','text-shapes','unsupported-digit-five']:
            page.evaluate('vcam.source=null');page.wait_for_timeout(1300)
            page.evaluate('''async kind=>{
                const img=new Image();let src='/media/letters/5.jpg';
                if(kind!=='unsupported-digit-five'){
                  const c=document.createElement('canvas');c.width=640;c.height=480;const x=c.getContext('2d');
                  x.fillStyle='#777';x.fillRect(0,0,640,480);
                  if(kind==='text-shapes'){
                    for(let i=0;i<15;i++){x.fillStyle=['#e0a075','#f0d0a0','#442211'][i%3];x.fillRect(i*43,20+(i%4)*90,35,75);}
                    x.font='48px sans-serif';x.fillStyle='white';x.fillText('NO HAND ABC XYZ',45,440);
                  }
                  src=c.toDataURL();
                }
                await new Promise((ok,fail)=>{img.onload=ok;img.onerror=fail;img.src=src});vcam.samples=[];vcam.source=img;
            }''',kind)
            page.wait_for_timeout(5000);samples=page.evaluate('vcam.samples')
            r=dict(case=kind,passed=not any('— recognized.' in s['feedback'] or 'motion recognized.' in s['feedback'] for s in samples),trace=samples)
            report['negatives'].append(r);save();print(kind,r['passed'],flush=True)
        page.evaluate('vcam.source=null');page.wait_for_timeout(1500)
        page.evaluate('''async()=>{const img=new Image();await new Promise(ok=>{img.onload=ok;img.src='/media/letters/a.jpg'});vcam.samples=[];vcam.source=img;}''')
        page.wait_for_timeout(4500);samples=page.evaluate('vcam.samples');r=score(samples,'A');r.update(case='recovery-after-negatives',trace=samples);report['negatives'].append(r);save()
        page.locator('#cameraButton').click(force=True);context.close();b.close()
    print('additional static passes',sum(r['passed'] for r in report['attempts']),'/',len(report['attempts']),flush=True)

if __name__=='__main__':main()
