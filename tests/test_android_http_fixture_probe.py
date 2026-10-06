import hashlib
from pathlib import Path
import subprocess
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
import android_http_fixture_probe as probe
sys.path.pop(0)

BODY = b'\x00reference\xff'
DIGEST = hashlib.sha256(BODY).hexdigest()
RESPONSE = b'HTTP/1.0 200 OK\r\nContent-Length: 11\r\n\r\n' + BODY


class HTTPFixtureTests(unittest.TestCase):
    def test_exact_binary_response(self):
        self.assertEqual(probe.response_matches(RESPONSE, len(BODY), DIGEST)['bytes'], len(BODY))

    def test_transport_and_integrity_failures_cannot_pass(self):
        for raw in (b'', RESPONSE[:-1], RESPONSE + b'x',
                    RESPONSE.replace(b'200 OK', b'404 Missing'),
                    RESPONSE.replace(b'11', b'12'),
                    RESPONSE.replace(b'Content-Length: 11', b'Content-Length: 11\r\nContent-Length: 11'),
                    RESPONSE.replace(b'Content-Length: 11', b'Content-Length: 11\r\nTransfer-Encoding: chunked'),
                    RESPONSE[:-1] + b'z', b'x' * (probe.HEADER_LIMIT + len(BODY) + 1)):
            with self.subTest(raw_bytes=len(raw)), self.assertRaises(ValueError):
                probe.response_matches(raw, len(BODY), DIGEST)

    def test_explicit_local_target_bounded_command(self):
        def invoke(argv, **kw):
            self.assertEqual(argv[1:5], ['-s', 'emulator-5560', 'shell', '-T'])
            self.assertIn('head -c 16396', argv[-1])
            self.assertEqual(kw['timeout'], 15)
            self.assertNotIn(b'Authorization:', kw['input'])
            return subprocess.CompletedProcess(argv, 0, RESPONSE, b'')
        r = probe.probe('adb', 'emulator-5560', '10.0.2.2', 8089, '/fixture', len(BODY), DIGEST, invoke=invoke)
        self.assertEqual(r['sha256'], DIGEST)
        for args in [('phone', '10.0.2.2', 8089, '/fixture'),
                     ('emulator-5560', 'example.com', 8089, '/fixture'),
                     ('emulator-5560', '127.0.0.1', 8089, '/a;echo'),
                     ('emulator-5560', '127.0.0.1', 8089, '/a?token=x')]:
            with self.assertRaises(ValueError):
                probe.probe('adb', *args, len(BODY), DIGEST, invoke=invoke)


if __name__ == '__main__':
    unittest.main()
