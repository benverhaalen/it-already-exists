"""Real loopback backend invariants; frontend journey has separate browser evidence."""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SERVER = Path(__file__).resolve().parents[1] / 'examples/ui-reference-mesh/server.py'


class LibraryBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        self.url = f'http://127.0.0.1:{port}/api/items'
        self.server = subprocess.Popen(
            [sys.executable, str(SERVER), '--database', str(Path(self.temp.name) / 'library.sqlite'),
             '--port', str(port), '--fail-first-save'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        self.addCleanup(self.stop)
        deadline = time.monotonic() + 5
        while True:
            try:
                self.items = self.request()[1]['items']
                break
            except URLError:
                if self.server.poll() is not None or time.monotonic() >= deadline:
                    self.fail('owned test server did not start')
                time.sleep(.02)

    def stop(self):
        self.server.terminate()
        try:
            self.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.server.kill()
            self.server.wait(timeout=5)

    def request(self, data=None):
        request = Request(self.url, data=json.dumps(data).encode() if data is not None else None,
                          headers={'Content-Type': 'application/json'})
        try:
            response = urlopen(request, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            return response.code, json.load(response)

    def test_invalid_and_failed_requests_preserve_committed_snapshot(self):
        original = next(item for item in self.items if item['id'] == 'drafts')
        changed = dict(original, notes='new snapshot')
        self.assertEqual(self.request(dict(changed, url='ftp://example.test/a'))[0], 400)
        self.assertEqual(self.request(changed)[0], 503)
        current = next(item for item in self.request()[1]['items'] if item['id'] == 'drafts')
        self.assertEqual(current, original)
        code, result = self.request(changed)
        self.assertEqual(code, 200)
        self.assertEqual(result['item']['revision'], original['revision'] + 1)
        self.assertEqual(result['item']['notes'], 'new snapshot')

    def test_concurrent_old_revisions_cannot_overwrite_a_new_commit(self):
        original = next(item for item in self.items if item['id'] == 'drafts')
        self.assertEqual(self.request(original)[0], 503)  # consume the explicit fault
        contenders = [dict(original, notes='candidate A'), dict(original, notes='candidate B')]
        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(self.request, contenders))
        self.assertEqual(sorted(code for code, _ in results), [200, 409])
        winner = next(result['item'] for code, result in results if code == 200)
        current = next(item for item in self.request()[1]['items'] if item['id'] == 'drafts')
        self.assertEqual(current, winner)
        self.assertEqual(current['revision'], original['revision'] + 1)


if __name__ == '__main__':
    unittest.main()
