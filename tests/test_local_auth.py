import json
from pathlib import Path
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] /
                     'skills/reference-driven-development/scripts'))
from local_auth import LocalAuth


class LocalAuthTests(unittest.TestCase):
    def test_remote_and_ambiguous_endpoints_rejected(self):
        for endpoint in ['https://127.0.0.1:9099', 'http://localhost:9099',
                         'http://example.org', 'http://127.0.0.1@evil.invalid',
                         'http://127.0.0.1/path', 'http://127.0.0.1?x=1',
                         'http://user:password@127.0.0.1', 'http://127.0.0.1#x']:
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                LocalAuth(endpoint)

    def test_non_synthetic_identity_rejected_before_request(self):
        auth = LocalAuth()
        auth.call = lambda *args: self.fail('must not contact service')
        for email in ['person@example.com', 'missing.invalid', 'a@b@c.invalid']:
            with self.assertRaises(ValueError):
                auth.create(email, 'Synthetic Person', 'synthetic-password')

    def test_original_http_adapter_and_redirect_failure(self):
        seen = []
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass
            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                seen.append((self.path, body))
                if 'accounts:signUp' in self.path:
                    response = {'idToken': 'local-session', 'localId': 'synthetic-uid'}
                elif 'accounts:update' in self.path:
                    response = {'localId': 'synthetic-uid', 'displayName': body['displayName']}
                else:
                    self.send_response(302)
                    self.send_header('Location', '/must-not-follow')
                    self.end_headers()
                    return
                data = json.dumps(response).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            auth = LocalAuth('http://127.0.0.1:' + str(server.server_port))
            result = auth.create('synthetic@example.invalid', 'Synthetic Person', 'test-password')
            self.assertEqual(result['uid'], 'synthetic-uid')
            self.assertNotIn('idToken', result)
            self.assertEqual(seen[1][1]['idToken'], 'local-session')
            with self.assertRaisesRegex(RuntimeError, 'HTTP 302'):
                auth.call('accounts:lookup', {})
            self.assertEqual(len(seen), 3)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_fast_persona_setup_is_scoped_and_no_tokens_returned(self):
        auth = LocalAuth()
        calls = []
        def call(operation, payload):
            calls.append((operation, payload))
            return {'idToken': 'test-only', 'localId': 'rdd-test-one'}
        auth.call = call
        with self.assertRaises(ValueError):
            auth.fast_account('production-id', 'one@example.invalid', 'One')
        self.assertEqual(calls, [])
        result = auth.fast_account('rdd-test-one', 'one@example.invalid', 'One')
        self.assertEqual(json.loads(calls[0][1]['token']), {'uid': 'rdd-test-one'})
        self.assertEqual(calls[1][1]['displayName'], 'One')
        self.assertNotIn('idToken', result)


if __name__ == '__main__':
    unittest.main()
