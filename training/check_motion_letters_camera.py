"""Supplementary framing/control checks. NOT the original A-Z acceptance test.

Uses a disclosed common upper-body crop for J/Z and static I/D source videos,
with face tracking off to measure the hand/motion pipeline separately. Cropped
successes must never replace failures in the uncropped 640x480 A-Z regression.
"""
import argparse
from pathlib import Path
import json
from playwright.sync_api import sync_playwright
from check_alphabet_camera import CAMERA, ROOT, score


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--rounds',type=int,default=3)
    parser.add_argument('--output',type=Path,default=ROOT/'reports/alphabet-repair-20261111/motion-supplement')
    parser.add_argument('--url',default='http://localhost:8000/')
    args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    sources=json.loads((ROOT/'models/motion-letters-sources.json').read_text())['source']
    camera=CAMERA.replace('const w=s.naturalWidth||s.videoWidth,h=s.naturalHeight||s.videoHeight;',
        'const w=720,h=550;').replace('ctx.drawImage(s,-w*k/2,-h*k/2,w*k,h*k);',
        'ctx.drawImage(s,0,350,720,550,-w*k/2,-h*k/2,w*k,h*k);')
    report=dict(scope='Supplement only; altered framing and disabled face tracking. Does not count toward original acceptance.',
        crop=dict(x=0,y=350,width=720,height=550),geometry=dict(width=640,height=480,fps=15),attempts=[],errors=[])
    with sync_playwright() as p:
        b=p.chromium.launch(channel='chrome',headless=True,args=['--autoplay-policy=no-user-gesture-required'])
        for attempt in range(args.rounds):
            context=b.new_context(viewport={'width':1280,'height':900});page=context.new_page();page.set_default_timeout(120000)
            page.on('pageerror',lambda e:report['errors'].append(str(e)))
            page.goto(args.url,wait_until='networkidle');page.evaluate(camera)
            if page.locator('#simpleViewButton').get_attribute('aria-pressed')=='true':page.locator('#simpleViewButton').click()
            page.locator('.camera-settings > summary').click()
            page.locator('#faceTrackingToggle').uncheck();page.locator('#cameraButton').click(force=True)
            page.wait_for_function("document.querySelector('#cameraButton').textContent.includes('Stop camera')")
            for label in 'JZID':
                page.evaluate('vcam.source=null');page.wait_for_timeout(1500)
                before=page.locator('#captureTranscript').inner_text()
                page.evaluate('''async src=>{
                    const v=document.createElement('video');v.crossOrigin='anonymous';v.muted=true;v.playbackRate=.67;
                    await new Promise((ok,fail)=>{v.onloadeddata=ok;v.onerror=fail;v.src=src});
                    vcam.samples=[];vcam.source=v;await v.play();
                }''',sources[label.lower()]['video'])
                page.wait_for_timeout(9000);samples=page.evaluate('vcam.samples')
                r=score(samples,label,label in 'JZ');r.update(letter=label,attempt=attempt+1,trace=samples,
                    draftBefore=before,draftAfter=page.locator('#captureTranscript').inner_text())
                if label in 'ID':
                    r['falseMotion']=any('motion recognized.' in s['feedback'] for s in samples)
                    r['staticMotionNegativePassed']=not r['falseMotion']
                report['attempts'].append(r)
                page.screenshot(path=str(out/f'{attempt+1}-{label}.png'))
                (out/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
                print(json.dumps({k:v for k,v in r.items() if k!='trace'}),flush=True)
            page.locator('#cameraButton').click(force=True);context.close()
        b.close()

if __name__=='__main__':main()
