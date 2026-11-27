from http.server import ThreadingHTTPServer
import http.client
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from pypdf import PdfReader
from local_review.store import Store
from local_review.demo import seed
from local_review.server import handler_for

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'db');self.pid=seed(self.store)['id'];self.server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.store));self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,method,path,body=None,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',self.server.server_port);c.request(method,path,json.dumps(body) if body is not None else None,headers or {'Content-Type':'application/json'});r=c.getresponse();out=r.status,r.read();c.close();return out
    def test_pages_exports_and_source_download(self):
        for path in ['/','/app.js','/style.css','/api/projects',f'/api/state?project={self.pid}']:
            self.assertEqual(self.request('GET',path)[0],200,path)
        doc=self.store.state(self.pid)['documents'][0]
        status,raw=self.request('GET',f'/api/page?project={self.pid}&document={doc["id"]}&page=2');self.assertEqual(status,200);self.assertIn('roof height',json.loads(raw)['text'])
        status,raw=self.request('GET',f'/api/export?project={self.pid}&format=pdf');self.assertEqual(status,200);self.assertGreater(len(PdfReader(io.BytesIO(raw)).pages),0)
        self.assertTrue(self.request('GET',f'/api/original?project={self.pid}&document={doc["id"]}')[1].startswith(b'%PDF-'))
    def test_invalid_requests_and_cross_origin_writes(self):
        self.assertEqual(self.request('GET','/../../etc/passwd')[0],404)
        self.assertEqual(self.request('GET','/',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.request('POST','/api/demo',{}, {'Content-Type':'application/json','Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.request('POST','/api/demo',{}, {'Content-Type':'text/plain'})[0],415)
        self.assertEqual(self.request('POST','/api/demo',[])[0],400)
        self.assertEqual(self.request('POST','/api/documents',dict(project=self.pid,name='bad.pdf',kind='plans',format='pdf',base64='invalid!!'))[0],400)
    def test_http_upload_is_local_and_source_labeled(self):
        status,raw=self.request('POST','/api/documents',dict(project=self.pid,name='notes.txt',kind='reference',format='text',content='Unverified user-supplied notes.'))
        self.assertEqual(status,200);self.assertEqual(json.loads(raw)['result']['source'],'manual_text')
        status,_=self.request('POST','/api/item/new',dict(project='missing',label='x',text='No project exists'))
        self.assertEqual(status,400)
if __name__=='__main__':unittest.main()
