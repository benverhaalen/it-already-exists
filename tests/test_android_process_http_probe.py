import hashlib
from pathlib import Path
import sys
import threading
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
import android_process_http_probe as probe
sys.path.pop(0)

BODY = b'\x00reference\xff'
DIGEST = hashlib.sha256(BODY).hexdigest()
RESPONSE = b'HTTP/1.0 200 OK\r\nContent-Length: 11\r\n\r\n' + BODY


class Script:
    def __init__(self, raw=RESPONSE, failure=None):
        self.raw, self.failure = raw, failure
        self.exports_sync = self
        self.unloaded = False
        self.release = threading.Event()

    def on(self, name, callback):
        self.callback = callback

    def load(self):
        if self.failure == 'load':
            raise RuntimeError('load failed')

    def readfixture(self):
        if self.failure == 'timeout':
            self.release.wait(2)
            raise RuntimeError('unloaded')
        if self.failure == 'rpc':
            raise RuntimeError('read failed')
        if self.failure == 'script':
            self.callback({'type': 'error'}, None)
        self.callback({'type': 'send', 'payload': {'kind': 'fixture-bytes'}}, self.raw)
        return {'total': len(self.raw) + (1 if self.failure == 'length' else 0)}

    def unload(self):
        self.unloaded = True
        self.release.set()
        if self.failure == 'unload':
            raise RuntimeError('unload failed')


class Device:
    def __init__(self, script, create_failure=False):
        self.script, self.create_failure = script, create_failure
        self.detached = False

    def attach(self, pid):
        return self

    def create_script(self, source):
        if self.create_failure:
            raise RuntimeError('create failed')
        return self.script

    def detach(self):
        self.detached = True


class ProcessHTTPTests(unittest.TestCase):
    def test_binary_integrity_and_cleanup(self):
        script = Script()
        device = Device(script)
        result = probe.collect(device, 123, 'source', len(BODY), DIGEST, 1)
        self.assertEqual(result['sha256'], DIGEST)
        self.assertFalse(result['route_mutation'])
        self.assertTrue(script.unloaded and device.detached)

    def test_failures_clean_up_and_cannot_pass(self):
        cases = [(RESPONSE, stage) for stage in ('load', 'rpc', 'script', 'length', 'unload', 'timeout')]
        cases += [(RESPONSE[:-1] + b'z', None), (b'x' * (probe.HEADER_LIMIT + len(BODY) + 1), None)]
        for raw, stage in cases:
            with self.subTest(stage=stage, size=len(raw)):
                script, device = Script(raw, stage), None
                device = Device(script)
                with self.assertRaises((ValueError, RuntimeError)):
                    probe.collect(device, 123, 'source', len(BODY), DIGEST, .02)
                self.assertTrue(script.unloaded and device.detached)
        device = Device(Script(), create_failure=True)
        with self.assertRaises(RuntimeError):
            probe.collect(device, 123, 'source', len(BODY), DIGEST, 1)
        self.assertTrue(device.detached)

    def test_rejects_remote_or_ambiguous_targets(self):
        good = ['emulator-5560', 'org.example.fixture', '127.0.0.1', 8089, '/fixture', len(BODY), DIGEST, 15]
        probe.validate(*good)
        for index, value in [(0, 'phone'), (1, 'package;cmd'), (2, 'example.com'),
                             (3, True), (4, '/fixture?token=x'), (5, -1), (6, 'not-a-digest'), (7, 61)]:
            args = good.copy()
            args[index] = value
            with self.subTest(index=index), self.assertRaises(ValueError):
                probe.validate(*args)


if __name__ == '__main__':
    unittest.main()
