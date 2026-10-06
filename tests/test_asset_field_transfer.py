import copy
import unittest
import json
import subprocess
import sys
import tempfile
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('asset_field_transfer', ROOT / 'skills/reference-driven-development/scripts/asset_field_transfer.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
transfer = module.transfer


class AssetFieldTransferTests(unittest.TestCase):
    def test_cli_hashes_inputs_and_refuses_existing_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, bindings, output = (root / name for name in ('source.json', 'bindings.json', 'output.json'))
            source.write_text('{"image": "https://assets.example/a"}')
            bindings.write_text(json.dumps([{'pointer': '/image', 'expected': 'https://assets.example/a', 'replacement': 'http://127.0.0.1/a'}]))
            command = [sys.executable, str(ROOT / 'skills/reference-driven-development/scripts/asset_field_transfer.py'), '--input', str(source), '--bindings', str(bindings), '--output', str(output)]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            receipt = json.loads(output.read_text())
            self.assertEqual(receipt['document']['image'], 'http://127.0.0.1/a')
            self.assertEqual(len(receipt['source_sha256']), 64)
            before = output.read_bytes()
            again = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(output.read_bytes(), before)

    def test_nested_exact_leaf_preserves_other_occurrences_and_input(self):
        url = 'https://assets.example/image?token=opaque%2Fvalue'
        source = {'cover': url, 'gallery': [{'url': url, 'type': 'IMAGE'}], 'other': {'url': url}, 'amount': 0, 'enabled': False}
        before = copy.deepcopy(source)
        result, changes = transfer(source, [{'pointer': '/gallery/0/url', 'expected': url, 'replacement': 'http://127.0.0.1:8089/image'}])
        self.assertEqual(source, before)
        self.assertEqual(result['cover'], url)
        self.assertEqual(result['other'], source['other'])
        self.assertEqual(result['gallery'][0]['type'], 'IMAGE')
        self.assertEqual(result['gallery'][0]['url'], 'http://127.0.0.1:8089/image')
        self.assertEqual(result['amount'], 0)
        self.assertFalse(result['enabled'])
        self.assertEqual(changes[0]['pointer'], '/gallery/0/url')
        self.assertNotIn(url, str(changes))

    def test_pointer_escapes_and_typed_rest_leaf(self):
        source = {'a/b~c': {'arrayValue': {'values': [{'mapValue': {'fields': {'image': {'stringValue': 'https://assets.example/a'}}}}]}}}
        pointer = '/a~1b~0c/arrayValue/values/0/mapValue/fields/image/stringValue'
        result, _ = transfer(source, [{'pointer': pointer, 'expected': 'https://assets.example/a', 'replacement': 'http://127.0.0.1/a'}])
        self.assertEqual(result['a/b~c']['arrayValue']['values'][0]['mapValue']['fields']['image']['stringValue'], 'http://127.0.0.1/a')

    def test_missing_stale_duplicate_and_invalid_addresses_fail_without_mutation(self):
        source = {'items': [{'url': 'https://assets.example/a'}]}
        before = copy.deepcopy(source)
        binding = {'pointer': '/items/0/url', 'expected': 'https://assets.example/a', 'replacement': 'http://127.0.0.1/a'}
        cases = [
            [dict(binding, pointer='/missing')], [dict(binding, expected='https://assets.example/b')],
            [binding, binding], [dict(binding, pointer='/items/00/url')],
            [dict(binding, pointer='/items/-1/url')], [dict(binding, pointer='/items/1/url')],
            [dict(binding, pointer='/bad~2escape')], [dict(binding, pointer='')],
            [dict(binding, pointer='/items/0')], [dict(binding, replacement='https://user@assets.example/a')],
            [dict(binding, replacement='http://127.0.0.1/a\n')],
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                transfer(source, case)
            self.assertEqual(source, before)


if __name__ == '__main__':
    unittest.main()
