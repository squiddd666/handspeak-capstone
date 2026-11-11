"""Benchmark frozen classifiers and verify temporal Python/JS parity in Chromium."""
import json
import numpy as np,torch
from pathlib import Path
from playwright.sync_api import sync_playwright
from temporal import ROOT,features,Temporal
SITE=Path(__file__).resolve().parents[2]
if __name__=='__main__':
 saved=torch.load(ROOT/'temporal-candidate.pt',map_location='cpu',weights_only=True);net=Temporal(saved['config']['width']);net.load_state_dict(saved['state']);net.eval();rows=json.loads((ROOT/'development-features.json').read_text());sample=next(r for r in rows if r['sequence']);x=features(sample)
 with torch.no_grad():expected=net(torch.tensor(x[None])).numpy()[0].tolist()
 data=dict(row=sample,weights={k:v.tolist() for k,v in saved['state'].items()},input=x.tolist(),expected=expected,sequence=sample['sequence'],candidate=json.loads((ROOT/'dtw-candidate.json').read_text()))
 with sync_playwright() as p:
  b=p.chromium.launch(args=['--no-sandbox']);page=b.new_page();page.goto('https://handspeak.cvsu.dev',wait_until='domcontentloaded');page.set_default_timeout(120000)
  result=page.evaluate('''async data=>{
   const {temporalLogits,temporalFeatures}=await import('./training/accuracy/temporal-browser.js');const {recognizeMotion}=await import('./motion-model.js');
   const baseline=await(await fetch('./models/asl-words.json')).json();let latency={};
   const computed=temporalFeatures(data.row);const featureError=Math.max(...computed.flatMap((r,i)=>r.map((v,j)=>Math.abs(v-data.input[i][j]))));const logits=temporalLogits(computed,data.weights);const error=Math.max(...logits.map((x,i)=>Math.abs(x-data.expected[i])));
   for(const [name,fn] of Object.entries({temporal:()=>temporalLogits(data.input,data.weights),dtw:()=>recognizeMotion(data.sequence,data.candidate.samples,data.candidate.parameters),baseline:()=>recognizeMotion(data.sequence,baseline.samples,baseline.parameters)})){
    fn();const times=[];for(let i=0;i<20;i++){const start=performance.now();fn();times.push(performance.now()-start);}times.sort((a,b)=>a-b);latency[name]={medianMs:times[10],p95Ms:times[18]};
   }
   return {maxLogitError:error,maxFeatureError:featureError,latency};
  }''',data)
  assert result['maxLogitError']<1e-4 and result['maxFeatureError']<1e-5,result
  result['scope']='Classifier only, one development clip, 20 timed runs after warmup. Excludes hand/pose tracking and does not establish phone or physical webcam performance.'
  (ROOT/'browser-classifier-benchmark.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));b.close()
