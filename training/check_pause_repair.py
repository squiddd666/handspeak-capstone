import json,subprocess,math
from pathlib import Path
import cv2,numpy as np,imageio_ffmpeg,mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from playwright.sync_api import sync_playwright
ROOT=Path.cwd();PRIVATE=ROOT.parent/'handspeak-training/pause-repair';PRIVATE.mkdir(exist_ok=True)
OUT=ROOT/'website-word-test/pause-repair';OUT.mkdir(exist_ok=True)
source=ROOT/'media/signs/before.mp4';cap=cv2.VideoCapture(str(source));fps=cap.get(cv2.CAP_PROP_FPS);frames=[]
while True:
 ok,frame=cap.read()
 if not ok:break
 frames.append(frame)
cap.release();duration=len(frames)/fps
options=vision.HandLandmarkerOptions(base_options=python.BaseOptions(model_asset_path=str(ROOT/'third_party/OpenHands-source/api/model/hand_landmarker.task')),running_mode=vision.RunningMode.IMAGE,num_hands=2)
held=None
with vision.HandLandmarker.create_from_options(options) as detector:
 for frame in frames[::3]:
  result=detector.detect(mp.Image(image_format=mp.ImageFormat.SRGB,data=cv2.cvtColor(frame,cv2.COLOR_BGR2RGB)))
  if any(all(0<=p.x<=1 and 0<=p.y<=1 for p in hand) for hand in result.hand_landmarks):held=frame.copy()
assert held is not None,'No real full-hand frame for the controlled hold test'
def letterbox(frame):
 h,w=frame.shape[:2];scale=min(640/w,480/h);small=cv2.resize(frame,(round(w*scale),round(h*scale)));canvas=np.full((480,640,3),128,np.uint8);y=(480-small.shape[0])//2;x=(640-small.shape[1])//2;canvas[y:y+small.shape[0],x:x+small.shape[1]]=small;return canvas
video=PRIVATE/'hold-background.avi';writer=cv2.VideoWriter(str(video),cv2.VideoWriter_fourcc(*'MJPG'),15,(640,480))
for i in range(round((4+duration+4+4)*15)):
 t=i/15
 if t<4 or t>=8+duration:frame=np.full((480,640,3),128,np.uint8)
 elif t<4+duration:frame=letterbox(frames[min(len(frames)-1,int((t-4)*fps))])
 else:frame=letterbox(held)
 # Deliberately animated background region, away from the actual signing hands.
 frame[0:80,0:80]=230 if i%2 else 10
 writer.write(frame)
writer.release();camera=PRIVATE/'hold-background.y4m'
subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-y','-v','error','-i',str(video),'-pix_fmt','yuv420p','-f','yuv4mpegpipe',str(camera)],check=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe',headless=True,args=['--use-fake-device-for-media-stream=fps=15','--use-fake-ui-for-media-stream','--use-file-for-fake-video-capture='+str(camera)])
 page=b.new_page(viewport={'width':1440,'height':1000});events=[];errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("window.pauseQA=[];document.addEventListener('handspeak:word-capture-diagnostics',e=>pauseQA.push(e.detail));")
 r={'scope':'Controlled endpoint regression, not recognition accuracy: real reference movement followed by a frozen real hand frame and deliberately moving background. No injected landmarks or model predictions.'}
 try:
  page.goto('http://localhost:8000/#workspace',wait_until='domcontentloaded');page.wait_for_selector('#openhandsEnabled',state='attached');page.select_option('#recognitionMode','words');page.click('#cameraButton')
  with page.expect_response(lambda response:response.url.endswith('/api/openhands/recognize') and response.request.method=='POST',timeout=90000) as pending:
   page.wait_for_function('pauseQA.length>0',timeout=85000)
  response=pending.value;r.update(http=response.status,response=response.json(),captures=page.evaluate('pauseQA'))
  r['stablePoseConfirmed']=any(x.get('boundaryQuality',{}).get('poseWindow') for x in r['captures'])
  r['noForcedTimeout']=all(x.get('reason')!='maximum-duration-without-confirmed-end' for x in r['captures'])
  page.screenshot(path=str(OUT/'held-pose-background.png'))
 except Exception as e:r['error']=str(e);r['status']=page.locator('#openhandsStatus').inner_text() if page.locator('#openhandsStatus').count() else 'Not initialized'
 r['errors']=errors;(OUT/'held-pose-background.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True);b.close()
