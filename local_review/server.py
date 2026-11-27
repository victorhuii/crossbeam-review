"""Loopback local workspace. No model calls, cloud services, or submissions."""
import argparse
import base64
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

from local_review.store import Store,ROOT
from local_review.demo import seed
from local_review.export import markdown,pdf

MAX_BODY=12_000_000

def handler_for(store):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*_):pass
        def local(self):return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')
        def send(self,status,data,kind='application/json',filename=None):
            raw=json.dumps(data,allow_nan=False).encode() if kind=='application/json' else data.encode() if isinstance(data,str) else data
            self.send_response(status);self.send_header('Content-Type',kind+('; charset=utf-8' if kind!='application/pdf' else ''));self.send_header('Content-Length',str(len(raw)))
            self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            if filename:self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
            self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            if not self.local():return self.send(403,dict(error='Loopback host required'))
            parsed=urlsplit(self.path);q=parse_qs(parsed.query);path=parsed.path
            try:
                if path=='/api/projects':return self.send(200,dict(projects=store.projects()))
                if path.startswith('/api/'):
                    pid=q.get('project',[''])[0]
                    if path=='/api/state':return self.send(200,store.state(pid))
                    if path=='/api/page':return self.send(200,store.page(pid,q.get('document',[''])[0],int(q.get('page',['0'])[0])))
                    if path=='/api/search':return self.send(200,dict(candidates=store.search(pid,q.get('q',[''])[0])))
                    if path=='/api/original':return self.send(200,store.raw(pid,q.get('document',[''])[0]),'application/pdf','source-document.pdf')
                    if path=='/api/export':
                        state=store.state(pid);fmt=q.get('format',['json'])[0]
                        if fmt=='json':return self.send(200,state,filename='crossbeam-review.json')
                        if fmt=='md':return self.send(200,markdown(state),'text/markdown','crossbeam-response-draft.md')
                        if fmt=='pdf':return self.send(200,pdf(state),'application/pdf','crossbeam-response-draft.pdf')
                        raise ValueError('Select JSON, Markdown, or PDF')
                assets={'/':('index.html','text/html'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
                if path in assets:
                    name,kind=assets[path];return self.send(200,(ROOT/'web'/name).read_bytes(),kind)
                return self.send(404,dict(error='Not found'))
            except (ValueError,KeyError) as exc:return self.send(400,dict(error=str(exc)))
        def do_POST(self):
            if not self.local():return self.send(403,dict(error='Loopback host required'))
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):return self.send(403,dict(error='Same-origin writes required'))
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.send(415,dict(error='JSON required'))
            try:
                size=int(self.headers.get('Content-Length',0))
                if not 0<size<=MAX_BODY:return self.send(413,dict(error='Request limit is 12 MB'))
                body=json.loads(self.rfile.read(size))
                if not isinstance(body,dict):raise ValueError('JSON object required')
                path=urlsplit(self.path).path;pid=body.get('project')
                if path=='/api/projects':result=store.create(body)
                elif path=='/api/demo':result=seed(store)
                elif path=='/api/documents':
                    if body.get('format')=='pdf':
                        value=body.get('base64')
                        if not isinstance(value,str):raise ValueError('PDF data missing')
                        raw=base64.b64decode(value,validate=True);result=store.upload(pid,body.get('name'),body.get('kind'),raw=raw)
                    elif body.get('format')=='text':result=store.upload(pid,body.get('name'),body.get('kind'),content=body.get('content'))
                    else:raise ValueError('Select PDF or text')
                    result={k:v for k,v in result.items() if k!='pages'}
                elif path=='/api/item/update':result=store.update_item(pid,body)
                elif path=='/api/item/new':result=store.manual_item(pid,body)
                elif path=='/api/evidence':result=store.evidence(pid,body)
                elif path=='/api/evidence/remove':result=store.evidence(pid,body,remove=True)
                elif path=='/api/evidence/check':result=store.review_evidence(pid,body)
                elif path=='/api/document/review':result=store.review_document(pid,body);result={k:v for k,v in result.items() if k!='pages'}
                elif path=='/api/checklist':result=store.update_task(pid,body)
                else:raise ValueError('Unknown action')
                return self.send(200,dict(ok=True,result=result))
            except (ValueError,TypeError,KeyError) as exc:return self.send(400,dict(error=str(exc)))
            except OSError:return self.send(503,dict(error='Local storage or file operation failed; existing records retained'))
    return Handler

def main():
    p=argparse.ArgumentParser(description='CrossBeam local evidence review');p.add_argument('--data',type=Path,default=Path('runtime/local-review.db'));p.add_argument('--port',type=int,default=8773);p.add_argument('--demo',action='store_true');args=p.parse_args()
    store=Store(args.data)
    if args.demo:seed(store)
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(store));print(f'CrossBeam Review: http://127.0.0.1:{server.server_port}',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=='__main__':main()
