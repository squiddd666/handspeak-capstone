"""Loopback-only test server. Videos processed in temp files, then deleted."""
import json,tempfile,os
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse,parse_qs
from runtime import LABELS,CHECKPOINT,predict
HERE=Path(__file__).parent
class Handler(BaseHTTPRequestHandler):
    def send(self,obj,status=200):
        body=json.dumps(obj).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=='/health':return self.send(dict(ready=True,labels=LABELS,reported_validation=CHECKPOINT.get('val_acc')))
        if path=='/results':
            report=HERE/'reference-results.json'
            return self.send(json.loads(report.read_text()) if report.exists() else dict(total=0,scope='Evaluation not yet complete'))
        if path!='/':return self.send(dict(error='Not found'),404)
        body=(HERE/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def do_POST(self):
        if self.headers.get('Origin') not in (None,'http://localhost:8001','http://127.0.0.1:8001'):return self.send(dict(error='Origin rejected'),403)
        if urlparse(self.path).path!='/predict':return self.send(dict(error='Not found'),404)
        expected=parse_qs(urlparse(self.path).query).get('expected',[''])[0]
        if expected not in LABELS:return self.send(dict(error='Choose expected word before recording'),400)
        length=int(self.headers.get('Content-Length','0'))
        if not 0<length<=20*1024*1024:return self.send(dict(error='Video limit: 20 MB'),400)
        name=None
        try:
            with tempfile.NamedTemporaryFile(suffix='.webm',delete=False) as f:
                name=f.name;f.write(self.rfile.read(length))
            result=predict(name);result.update(expected=expected,correct=result['predicted']==expected,top5_correct=expected in [r['word'] for r in result['top5']])
            self.send(result)
        except Exception as e:self.send(dict(error=str(e)),400)
        finally:
            if name:os.unlink(name)
print('OpenHands test ready: http://localhost:8001',flush=True)
ThreadingHTTPServer(('127.0.0.1',8001),Handler).serve_forever()
