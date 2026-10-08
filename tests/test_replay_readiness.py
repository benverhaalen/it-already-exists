import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'))
from replay_readiness import audit


class ReplayReadinessTests(unittest.TestCase):
    def test_exact_body_bytes_missing_dependency_and_derived_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            body = b'{"query":{"path":"a\\/b"}}'
            url = 'https://example.invalid/query'
            key = hashlib.sha256(url.encode() + body).hexdigest()
            payload = b'[{"document":{"name":"products/a"}}]'
            (root / 'request.body').write_bytes(body)
            (root / (key + '.json')).write_bytes(payload)
            case = {'id': 'slots', 'url': url, 'evidence_mode': 'captured-response',
                    'body': {'path': 'request.body', 'sha256': hashlib.sha256(body).hexdigest()},
                    'response': {'path': key + '.json', 'sha256': hashlib.sha256(payload).hexdigest()}}
            self.assertTrue(audit({'requests': [case]}, root)['ready_for_declared_replay'])
            # Semantically equivalent JSON has a different byte cache identity.
            unescaped = body.replace(b'\\/', b'/')
            (root / 'request.body').write_bytes(unescaped)
            case['body']['sha256'] = hashlib.sha256(unescaped).hexdigest()
            with self.assertRaises(ValueError):
                audit({'requests': [case]}, root)
            (root / 'request.body').write_bytes(body)
            case['body']['sha256'] = hashlib.sha256(body).hexdigest()
            case['evidence_mode'] = 'derived-fixture'
            report = audit({'requests': [case]}, root)
            self.assertFalse(report['ready_for_declared_replay'])
            self.assertTrue(report['requests'][0]['response_verified'])
            missing = {'id': 'detail', 'url': 'https://example.invalid/detail', 'evidence_mode': 'unknown'}
            self.assertFalse(audit({'requests': [case, missing]}, root)['ready_for_declared_replay'])
            self.assertEqual(report['network_calls'], 0)

    def test_response_drift_and_invalid_json_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            url = 'https://example.invalid/document'
            key = hashlib.sha256(url.encode()).hexdigest()
            file = root / (key + '.json')
            case = {'id': 'detail', 'url': url, 'evidence_mode': 'captured-response',
                    'response': {'path': file.name, 'sha256': hashlib.sha256(b'{}').hexdigest()}}
            for payload in (b'{"changed":true}', b'{"duplicate":1,"duplicate":2}'):
                file.write_bytes(payload)
                if payload.startswith(b'{"duplicate'):
                    case['response']['sha256'] = hashlib.sha256(payload).hexdigest()
                self.assertFalse(audit({'requests': [case]}, root)['ready_for_declared_replay'])
            with self.assertRaises(ValueError):
                audit({'requests': [case, case]}, root)


if __name__ == '__main__':
    unittest.main()
