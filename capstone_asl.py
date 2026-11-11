"""In-memory adapter for Microsoft's MIT-licensed ASL Citizen ST-GCN."""
from __future__ import annotations
import csv,sys,threading
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent/"third_party/microsoft_asl_citizen";LOCK=threading.Lock();_runtime=None
with (Path(__file__).resolve().parent/"third_party/capstone_asl/data/recognition_label_map_with_split_counts.csv").open() as f:
 TARGETS=[r["gloss"] for r in csv.DictReader(f)]
HAND_POINTS=[0,4,5,8,9,12,13,16,17,20]
EDGES=[[2,0],[1,0],[0,3],[0,4],[3,5],[4,6],[5,7],[6,17],[7,8],[7,9],[9,10],[7,11],[11,12],[7,13],[13,14],[7,15],[15,16],[17,18],[17,19],[19,20],[17,21],[21,22],[17,23],[23,24],[17,25],[25,26]]
class CapstoneASLError(ValueError):pass
def labels():return TARGETS
def _load():
 global _runtime
 if _runtime:return _runtime
 with LOCK:
  if _runtime:return _runtime
  import torch
  sys.path.insert(0,str(ROOT))
  from architecture.st_gcn import STGCN
  from architecture.fc import FC
  from architecture.network import Network
  names=(ROOT/"labels.txt").read_text().splitlines()
  model=Network(STGCN(2,dict(num_nodes=27,center=0,inward_edges=EDGES),True),FC(256,len(names),dropout_ratio=.05)).double().eval()
  model.load_state_dict(torch.load(ROOT/"model.pt",map_location="cpu",weights_only=True))
  _runtime=(torch,model,np.asarray([names.index(x) for x in TARGETS]))
 return _runtime
def _points(value,count,name):
 if not isinstance(value,list) or len(value)!=count:raise CapstoneASLError(f"{name} must contain {count} landmarks")
 out=np.asarray(value,dtype=np.float64)
 if out.ndim!=2 or out.shape[1]<2 or not np.isfinite(out).all() or np.abs(out).max()>20:raise CapstoneASLError(f"Invalid {name} landmarks")
 return out[:,:2]
def recognize(payload):
 frames=payload.get("frames") if isinstance(payload,dict) else None
 if not isinstance(frames,list) or not 12<=len(frames)<=90:raise CapstoneASLError("Capture must contain 12 to 90 landmark frames")
 sequence=[]
 for frame in frames:
  pose=_points(frame.get("pose"),7,"pose");left=_points(frame.get("left"),21,"left hand");right=_points(frame.get("right"),21,"right hand")
  sequence.append(np.concatenate((pose,left[HAND_POINTS],right[HAND_POINTS])))
 data=np.asarray(sequence);original=len(data)
 if original>128:data=data[np.linspace(0,original-1,128).round().astype(int)]
 if len(data)<128:data=np.pad(data,((0,128-len(data)),(0,0),(0,0)))
 center=((data[:,3]+data[:,4])/2).mean(0);distance=np.sqrt(((data[:,3]-data[:,4])**2).sum(-1)).mean()
 if distance>1e-8:data=(data-center)/distance
 torch,model,indices=_load()
 with LOCK,torch.no_grad():logits=model(torch.tensor(data.transpose(2,0,1)[None]))[0].numpy()[indices]
 probabilities=np.exp(logits-logits.max());probabilities/=probabilities.sum();ranking=np.argsort(probabilities)[::-1][:5]
 return {"predictions":[{"label":TARGETS[int(i)],"score":round(float(probabilities[i]),6)} for i in ranking],
  "segment":"full-clip","activeFrames":[0,original-1],"frames":original,"model":"Microsoft ASL Citizen ST-GCN"}
