import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('transfer', ROOT / 'skills/reference-driven-development/scripts/firestore_reference_transfer.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
SOURCE = 'projects/reference/databases/(default)/documents/'
TARGET = 'projects/demo-local/databases/(default)/documents/'

class TransferTests(unittest.TestCase):
    def test_typed_nested_references_preserve_literals_and_source(self):
        source = {
            'city': {'referenceValue': SOURCE + 'cities/example'},
            'literal': {'stringValue': SOURCE + 'cities/example'},
            'nested': {'mapValue': {'fields': {'items': {'arrayValue': {'values': [
                {'referenceValue': SOURCE + 'venues/example/items/one'},
                {'integerValue': '9007199254740991'}, {'nullValue': None},
                {'mapValue': {}}, {'arrayValue': {}}]}}}}},
            'other': {'referenceValue': 'projects/other/databases/(default)/documents/cities/example'}}
        baseline = copy.deepcopy(source)
        result, changes = module.transfer(source, SOURCE, TARGET)
        self.assertEqual(source, baseline)
        self.assertEqual(result['city']['referenceValue'], TARGET + 'cities/example')
        self.assertEqual(result['literal'], source['literal'])
        self.assertEqual(result['other'], source['other'])
        values = result['nested']['mapValue']['fields']['items']['arrayValue']['values']
        self.assertEqual(values[0]['referenceValue'], TARGET + 'venues/example/items/one')
        self.assertEqual(values[1:], source['nested']['mapValue']['fields']['items']['arrayValue']['values'][1:])
        self.assertEqual(changes, ['/city', '/nested/items/0'])
        result['literal']['stringValue'] = 'changed'
        self.assertEqual(source, baseline)

    def test_invalid_root_and_document_paths_are_rejected(self):
        for root in ('https://example.invalid/', SOURCE + '../', 'projects/reference/databases/(default)/documents'):
            with self.subTest(root=root), self.assertRaises(ValueError):
                module.transfer({}, root, TARGET)
        for path in ('', 'cities', 'cities//example', 'cities/../items/example'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                module.transfer({'ref': {'referenceValue': SOURCE + path}}, SOURCE, TARGET)

    def test_malformed_values_rejected(self):
        for item in ({}, {'stringValue': 'x', 'referenceValue': SOURCE + 'c/d'},
                     {'mapValue': {'unknown': {}}}, {'arrayValue': {'values': 'x'}},
                     {'referenceValue': 123}):
            with self.subTest(item=item), self.assertRaises(ValueError):
                module.transfer({'field': item}, SOURCE, TARGET)

if __name__ == '__main__':
    unittest.main()
