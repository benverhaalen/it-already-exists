import copy
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('dependency_audit', SCRIPTS / 'firestore_dependency_audit.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
ROOT = 'projects/reference/databases/(default)/documents/'


class DependencyAuditTests(unittest.TestCase):
    def test_filtered_listing_can_omit_nested_item_and_preserves_every_occurrence(self):
        missing = ROOT + 'products/child'
        foreign = 'projects/other/databases/(default)/documents/products/child'
        fields = {'items/~': {'arrayValue': {'values': [
            {'mapValue': {'fields': {'reference': {'referenceValue': missing}}}},
            {'referenceValue': missing},
            {'referenceValue': ROOT + 'products/known'},
            {'referenceValue': foreign},
            {'stringValue': ROOT + 'products/string-only'}]}}}
        documents = [{'name': ROOT + 'products/bundle', 'fields': fields},
                     {'name': ROOT + 'products/known', 'fields': {}},
                     {'name': ROOT + 'products/known', 'fields': {}}]
        original = copy.deepcopy(documents)
        result = module.audit(documents, ROOT)
        self.assertEqual(documents, original)
        self.assertEqual(result['captured_documents'], 2)
        self.assertEqual(list(result['missing']), [missing])
        self.assertEqual([x['field'] for x in result['missing'][missing]],
                         ['/items~1~0/0/reference', '/items~1~0/1'])
        self.assertEqual(list(result['external']), [foreign])

    def test_conflicting_or_malformed_captures_do_not_report_false_completeness(self):
        first = {'name': ROOT + 'products/x', 'fields': {}}
        for documents in ([first, {'name': first['name'], 'fields': {'v': {'integerValue': '1'}}}],
                          [{'name': ROOT + 'products'}],
                          [{'name': first['name'], 'fields': {'ref': {'referenceValue': ROOT + '../x'}}}],
                          [{'name': 'projects/other/databases/(default)/documents/products/x'}],
                          [{'name': first['name'], 'fields': {'bad': {}}}]):
            with self.subTest(documents=documents), self.assertRaises(ValueError):
                module.audit(documents, ROOT)


if __name__ == '__main__':
    unittest.main()
