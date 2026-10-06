import hashlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'skills/reference-driven-development/scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

provider = load('reference_provider')
trials = load('research_trials')

class Opener:
    def __init__(self, content):
        self.content = content
        self.headers_seen = None
    def open(self, req, timeout):
        self.headers_seen = dict(req.header_items())
        return io.BytesIO(self.content)

class ProviderTests(unittest.TestCase):
    def ticket(self, content):
        return {'packageName': 'org.example.demo', 'apkId': '123',
                'sha256': hashlib.sha256(content).hexdigest(), 'fileSize': len(content),
                'url': 'https://fixture.r2.cloudflarestorage.com/archive?secret=synthetic', 'format': 'apk'}

    def test_download_verified_before_publish_and_no_api_key_forwarded(self):
        content = b'independent authored archive fixture'
        opener = Opener(content)
        with tempfile.TemporaryDirectory() as root, patch.object(provider.request, 'build_opener', return_value=opener):
            target = Path(root) / 'input.apk'
            result = provider.download(self.ticket(content), 'org.example.demo', '123', target, 100)
            self.assertEqual(target.read_bytes(), content)
            self.assertEqual(result['bytes'], 36)
            self.assertFalse(result['signature_verified_locally'])
            self.assertEqual(opener.headers_seen, {})
            self.assertNotIn('url', result)
            with self.assertRaises(FileExistsError):
                provider.download(self.ticket(content), 'org.example.demo', '123', target, 100)

    def test_mismatch_cleanup_identity_size_and_origin_rejected(self):
        content = b'abcd'
        with tempfile.TemporaryDirectory() as root:
            target = Path(root) / 'input.apk'
            with patch.object(provider.request, 'build_opener', return_value=Opener(b'abce')):
                with self.assertRaisesRegex(ValueError, 'mismatch'):
                    provider.download(self.ticket(content), 'org.example.demo', '123', target, 100)
            self.assertEqual(list(Path(root).iterdir()), [])
            for change in [{'packageName': 'org.other.demo'}, {'apkId': '124'}, {'fileSize': 200},
                           {'sha256': 'bad'}, {'url': 'https://localhost/archive'},
                           {'url': 'http://fixture.r2.cloudflarestorage.com/archive'},
                           {'url': 'https://fixture.r2.cloudflarestorage.com.evil.test/archive'}]:
                with self.assertRaises(ValueError):
                    provider.download(dict(self.ticket(content), **change), 'org.example.demo', '123', target, 100)
            with patch.object(provider.request, 'build_opener', return_value=Opener(b'abcde')):
                with self.assertRaisesRegex(ValueError, 'exceeds'):
                    provider.download(self.ticket(content), 'org.example.demo', '123', target, 100)
            self.assertEqual(list(Path(root).iterdir()), [])

    def test_search_contract_and_credential_redirect_boundary(self):
        self.assertEqual(provider.exa_body('mechanism', domains=['github.com']),
                         {'query': 'mechanism', 'type': 'auto', 'numResults': 10,
                          'contents': {'highlights': True}, 'includeDomains': ['github.com']})
        with self.assertRaises(ValueError):
            provider.package_path('org.example/../../me')
        with self.assertRaises(ValueError):
            provider.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://elsewhere.test')

    def test_api_credentials_scoped_and_not_in_receipt(self):
        class Response(io.BytesIO):
            headers = {'X-Credits-Cost': '1'}
        class ApiOpener:
            def open(self, req, timeout):
                self.req = req
                return Response(b'{"items": []}')
        for url in ['https://elsewhere.test/api/v1/apps', 'http://apkcube.com/api/v1/apps', 'https://apkcube.com/not-api']:
            with self.assertRaisesRegex(ValueError, 'origin'):
                provider.api(url, 'APKCUBE_API_KEY')
        opener = ApiOpener()
        with patch.dict(provider.os.environ, {'APKCUBE_API_KEY': 'synthetic-key'}), patch.object(provider.request, 'build_opener', return_value=opener):
            data, receipt = provider.api('https://apkcube.com/api/v1/apps?q=fixture', 'APKCUBE_API_KEY')
            self.assertEqual(opener.req.get_header('Authorization'), 'Bearer synthetic-key')
            self.assertEqual(receipt['credits_cost'], '1')
            self.assertNotIn('synthetic-key', str((data, receipt)))

    def test_paired_trial_preserves_losses_unknown_cost_and_deduplicates(self):
        rows = [{'case': 'a', 'strategy': 'base', 'verified_contributions': ['x', 'x', 'y'],
                 'seconds': 10, 'tokens': 100, 'judgment_evidence': 'private/review-a'},
                {'case': 'a', 'strategy': 'extra', 'verified_contributions': ['x', 'z', 'w'],
                 'seconds': 20, 'tokens': 150, 'dollars': 0.1, 'judgment_evidence': 'private/review-a'}]
        result = trials.summarize(rows, 'base', 'extra')
        self.assertEqual(result['mean_contribution_delta'], 1)
        self.assertEqual(result['paired_cases'][0]['missed'], ['y'])
        self.assertEqual(result['paired_cases'][0]['added'], ['w', 'z'])
        self.assertEqual(result['cost_delta_totals'], {'seconds': 10, 'dollars': None, 'tokens': 50})
        with self.assertRaisesRegex(ValueError, 'unpaired'):
            trials.summarize(rows[:1], 'base', 'extra')
        for invalid in [dict(rows[0], dollars=float('nan')), dict(rows[0], tokens=-1), dict(rows[0], judgment_evidence='')]:
            with self.assertRaises(ValueError):
                trials.summarize([invalid, rows[1]], 'base', 'extra')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            trials.summarize(rows + rows[:1], 'base', 'extra')

if __name__ == '__main__':
    unittest.main()
