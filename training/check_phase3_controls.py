"""Extra unsupported-pose replay without modifying the A-Z scoring harness."""
import json
import argparse
from pathlib import Path
from playwright.sync_api import sync_playwright
from check_alphabet_camera import CAMERA,ROOT

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'reports/alphabet-phase3')
    parser.add_argument('--url',default='http://localhost:8000/')
    args=parser.parse_args()
    out=args.output
    out.mkdir(parents=True,exist_ok=True)
    with sync_playwright() as p:
        b=p.chromium.launch(channel='chrome',headless=True)
        page=b.new_page()
        page.goto(args.url,wait_until='networkidle')
        page.evaluate(CAMERA)
        page.locator('#cameraButton').click(force=True)
        page.wait_for_function("document.querySelector('#cameraButton').textContent.includes('Stop camera')",timeout=120000)
        rows=[]
        for kind in ('blank','unsupported-five'):
            page.evaluate('vcam.source=null;vcam.events=[];vcam.samples=[]')
            page.wait_for_timeout(1300)
            if kind!='blank':
                page.evaluate("""async()=>{const img=new Image();await new Promise((ok,fail)=>{img.onload=ok;img.onerror=fail;img.src='/media/letters/5.jpg'});vcam.source=img}""")
            page.wait_for_timeout(4500)
            events=page.evaluate('vcam.events')
            rows.append(dict(case=kind,commits=events,passed=not events))
        page.locator('#cameraButton').click(force=True)
        b.close()
    (out/'controls.json').write_text(json.dumps(rows,indent=2))
    print(rows)

if __name__=='__main__':main()
