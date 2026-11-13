"""Isolated audit harness: upstream weights/preprocessing, no alphabet model."""
import os, sys, json, types, time, threading
from pathlib import Path
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
UPSTREAM=ROOT/'third_party'/'OpenHands-source'/'api'
os.environ['MODEL_PATH_POSE']=str(UPSTREAM/'model'/'pose_landmarker_lite.task')
os.environ['MODEL_PATH_HAND']=str(UPSTREAM/'model'/'hand_landmarker.task')
sys.path.insert(0,str(UPSTREAM))
# Upstream keypoints imports these constants from config, whose other side
# effects load models. Supply constants only and load weights safely ourselves.
config=types.ModuleType('config')
config.NUM_FRAMES=50;config.NUM_JOINTS=55;config.IN_CHANNELS=4
sys.modules['config']=config
from models import ASLClassifier
from keypoints import prepare_input, tta_augment
from extract_keypoints import extract_keypoints_from_video

torch.set_num_threads(2)
LABELS=json.loads((UPSTREAM/'data'/'labels'/'word_labels_100.json').read_text())
CHECKPOINT=torch.load(UPSTREAM/'lstm_model_v7.pth',map_location='cpu',weights_only=True)
MODEL=ASLClassifier(num_classes=len(LABELS))
MODEL.load_state_dict(CHECKPOINT['model_state_dict']);MODEL.eval()
LOCK=threading.Lock()

def predict(path):
    started=time.perf_counter()
    with LOCK:
        tensor=extract_keypoints_from_video(str(path))
        if tensor is None: raise ValueError('Video could not be decoded')
        if not torch.isfinite(tensor).all(): raise ValueError('Nonfinite landmarks')
        # Reject blank/no-hand clips in this harness; upstream always guesses.
        if tensor[:,13:,:].abs().sum().item()==0:
            return dict(predicted=None,confidence=None,top5=[],error='No hands detected',seconds=time.perf_counter()-started)
        x=prepare_input(tensor)
        with torch.random.fork_rng(),torch.inference_mode():
            torch.manual_seed(42)
            state=np.random.get_state();np.random.seed(42)
            try:
                probs=torch.softmax(MODEL(x),dim=1)
                for _ in range(8): probs+=torch.softmax(MODEL(tta_augment(x)),dim=1)
                probs=(probs/9).squeeze(0)
            finally: np.random.set_state(state)
        values,indices=probs.topk(5)
        top=[dict(word=LABELS[int(i)],confidence=float(v)) for v,i in zip(values,indices)]
    return dict(predicted=top[0]['word'],confidence=top[0]['confidence'],top5=top,seconds=round(time.perf_counter()-started,3))

if __name__=='__main__':
    with torch.inference_mode(): y=MODEL(torch.zeros(1,50,220))
    print(json.dumps(dict(labels=len(LABELS),output_shape=list(y.shape),finite=bool(torch.isfinite(y).all()),checkpoint_metadata={k:v for k,v in CHECKPOINT.items() if k!='model_state_dict'}),indent=2))
