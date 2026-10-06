#!/usr/bin/env python3
"""Loopback-only callable protocol fixture; no app business routes or outbound calls."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import threading
import re

parser=argparse.ArgumentParser()
parser.add_argument('--evidence',type=Path,required=True)
args=parser.parse_args()
evidence=args.evidence.open('x')
lock=threading.Lock()

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):
        pass

    def do_POST(self):
        route=self.path.rsplit('/',1)[-1]
        valid_path=re.fullmatch(r'/demo-rdd-accounts/[a-z0-9]+(?:-[a-z0-9]+)*/[A-Za-z][A-Za-z0-9_-]{0,99}',self.path) is not None
        length=int(self.headers.get('Content-Length','0'))
        if not valid_path or not 0 < length <= 32768 or self.headers.get_content_type() != 'application/json':
            self.send_error(400);return
        try:
            request=json.loads(self.rfile.read(length))
            if not isinstance(request,dict) or set(request) != {'data'}:
                raise ValueError('Expected callable data envelope')
        except (ValueError,json.JSONDecodeError):
            self.send_error(400);return
        row={'route':route,'method':'POST','envelope':True,'parameter_keys':sorted(request['data']) if isinstance(request['data'],dict) else [],'auth_header_present':bool(self.headers.get('Authorization')),
             'appcheck_header_present':bool(self.headers.get('X-Firebase-AppCheck'))}
        with lock:
            evidence.write(json.dumps(row)+'\n');evidence.flush()
        if route == 'rddEcho':
            response={'data':request['data']}
        elif route == 'rddDenied':
            response={'error':{'status':'PERMISSION_DENIED','message':'Deliberate local protocol control','details':{'fixture':True}}}
        elif route == 'rddMalformed':
            response={'unexpected':True}
        else:
            response={'error':{'status':'UNIMPLEMENTED','message':'Local business contract has not been qualified'}}
        payload=json.dumps(response).encode()
        self.send_response(200 if route in {'rddEcho','rddDenied','rddMalformed'} else 501)
        self.send_header('Content-Type','application/json')
        self.send_header('Content-Length',str(len(payload)))
        self.end_headers();self.wfile.write(payload)

server=ThreadingHTTPServer(('127.0.0.1',5006),Handler)
print('RDD_CALLABLE_PROTOCOL_FIXTURE_READY loopback=1 port=5006 businessRoutes=0',flush=True)
try:
    server.serve_forever()
finally:
    server.server_close();evidence.close()
