"""HTTP negative-input/consent contracts using synthetic coordinates, not accuracy."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'training'))
from test_target20_quality import payload


def post(body):
    request=urllib.request.Request('http://127.0.0.1:8000/api/beginner-asl',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=30) as r:return r.status,json.load(r)
    except urllib.error.HTTPError as r:return r.code,json.load(r)


def main():
    tests=[]
    p=payload();p['consent']=False;code,data=post(p);assert code==422;tests.append('consent_required')
    p=payload();p['consent']=True;p['capture']['complete']=False
    code,data=post(p);assert code==200 and data['state']=='incomplete' and not data['predictions'];tests.append('incomplete_not_inferred')
    p=payload();p['consent']=True
    for f in p['frames']:f['left']=None
    code,data=post(p);assert code==200 and data['state']=='tracking_failure' and not data['predictions'];tests.append('no_hands_rejected')
    p=payload();p['consent']=True;p['frames'][0]['left'][0]=[float('nan'),.5]
    code,data=post(p);assert code==422;tests.append('nonfinite_rejected')
    p=payload();p['consent']=True;p['frames'][0]['right']=[[.3,.4]]
    code,data=post(p);assert code==422;tests.append('malformed_hand_rejected')
    result=dict(passed=True,tests=tests,scope='HTTP consent/input contracts only; no physical webcam or recognition accuracy claim')
    (ROOT.parent/'handspeak-training'/'target20-v2-api-checks.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
