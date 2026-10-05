"""Synthetic worker protocol checks; no model or reconstruction is exercised."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts/offline_worker.py'
sys.path.insert(0, str(MODULE.parent))
SPEC = importlib.util.spec_from_file_location('offline_worker', MODULE)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class OfflineWorkerTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.root = Path(self.scratch.name).resolve()
        self.output = self.root / 'work'; self.output.mkdir()
        self.spec = self.root / 'spec.json'
        self.spec.write_text(json.dumps({'goal': 'Synthetic protocol fixture'}))
        self.model = self.root / 'model.gguf'; self.model.write_bytes(b'fixture, not weights')

    def tearDown(self):
        self.scratch.cleanup()

    def backend(self, code):
        return [sys.executable, '-c', code, '{prompt}', '{model}', '{schema}']

    def test_valid_response_is_saved_with_receipt_without_execution(self):
        code = 'import json; print(json.dumps({"files":[{"path":"src/main.py","content":"raise RuntimeError()"}]}))'
        receipt = worker.execute(self.spec, self.output, self.model, self.backend(code))
        self.assertFalse(receipt['generated_code_executed'])
        self.assertTrue((self.output / 'src/main.py').is_file())
        self.assertTrue((self.output / worker.RECEIPT).is_file())

    def test_invalid_later_file_saves_nothing(self):
        code = 'import json; print(json.dumps({"files":[{"path":"ok.txt","content":"ok"},{"path":"../escape","content":"bad"}]}))'
        with self.assertRaisesRegex(ValueError, 'relative path'):
            worker.execute(self.spec, self.output, self.model, self.backend(code))
        self.assertEqual(list(self.output.iterdir()), [])

    def test_duplicates_collisions_reserved_names_and_bounds(self):
        cases = [(['a', 'a'], 'duplicate'), (['a', 'a/b'], 'collision'),
                 ([worker.RECEIPT], 'reserved'), (['/absolute'], 'relative'),
                 (['a/./b'], 'relative'), (['a\\b'], 'relative')]
        for names, reason in cases:
            with self.subTest(names=names), self.assertRaisesRegex(ValueError, reason):
                worker.validate_files({'files': [{'path': name, 'content': 'x'} for name in names]}, 10, 100)
        with self.assertRaisesRegex(ValueError, 'byte limit'):
            worker.validate_files({'files': [{'path': 'a', 'content': 'é'}]}, 1, 1)
        with self.assertRaisesRegex(ValueError, 'duplicate JSON'):
            worker.strict_json('{"files": [], "files": []}')

    def test_timeout_and_output_cap_leave_no_artifact(self):
        for code, timeout, bound, reason in [('import time; time.sleep(5)', 1, 1000, 'timed out'),
                                            ('print("x"*10000)', 5, 100, 'byte limit')]:
            with self.subTest(reason=reason), self.assertRaisesRegex(ValueError, reason):
                worker.execute(self.spec, self.output, self.model, self.backend(code), timeout, bound)
            self.assertEqual(list(self.output.iterdir()), [])

    def test_existing_outputs_and_symlinks_are_rejected(self):
        (self.output / 'existing').write_text('keep')
        with self.assertRaisesRegex(ValueError, 'empty'):
            worker.execute(self.spec, self.output, self.model, self.backend('print("{}")'))
        (self.output / 'existing').unlink()
        link = self.root / 'linked-model'; link.symlink_to(self.model)
        with self.assertRaisesRegex(ValueError, 'ordinary'):
            worker.execute(self.spec, self.output, link, self.backend('print("{}")'))

    def test_environment_does_not_include_host_secrets(self):
        code = 'import json,os; assert "API_KEY" not in os.environ; print(json.dumps({"files":[{"path":"env.txt","content":str(sorted(os.environ))}]}))'
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {'API_KEY': 'synthetic-secret'}):
            worker.execute(self.spec, self.output, self.model, self.backend(code))


if __name__ == '__main__':
    unittest.main()
