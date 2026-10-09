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


def relationship_contract_cases():
    """Authored record joins and caller expectations; no helper-derived oracle."""
    item = ROOT + 'items/item-a'
    child = ROOT + 'sessions/session-b'
    owner = ROOT + 'owners/owner-c'
    other = ROOT + 'owners/owner-z'
    base = [
        {'name': item, 'fields': {'session': {'referenceValue': child}, 'owner': {'referenceValue': owner}}},
        {'name': child, 'fields': {'owner': {'referenceValue': owner}, 'parent': {'stringValue': 'owners/owner-c'}}},
        {'name': owner, 'fields': {}}, {'name': other, 'fields': {}},
        {'name': ROOT + 'owners/session-b', 'fields': {}}]
    two_steps = [{'field': 'session', 'collection': 'sessions'}, {'field': 'owner', 'collection': 'owners'}]

    def case(label, status, reason, documents=None, steps=None, expected=owner, start=item):
        return {'label': label, 'status': status, 'reason': reason,
                'arguments': (copy.deepcopy(base if documents is None else documents), ROOT, start,
                              copy.deepcopy(two_steps if steps is None else steps), expected)}

    cases = [
        case('direct-owner', 'matched', 'endpoint_match', steps=[{'field': 'owner', 'collection': 'owners'}]),
        case('distinct-child-owner', 'matched', 'endpoint_match'),
        case('declared-relative-owner', 'matched', 'endpoint_match', steps=[two_steps[0],
             {'field': 'parent', 'collection': 'owners', 'encoding': 'relative_path'}]),
        case('caller-child-role', 'failed', 'endpoint_mismatch', expected=child),
        case('unrelated-existing-owner', 'failed', 'endpoint_mismatch', expected=other),
        case('child-tail-owner-alias', 'failed', 'endpoint_mismatch', expected=ROOT + 'owners/session-b'),
        case('missing-start', 'unresolved', 'missing_start_document', documents=base[1:]),
        case('missing-child', 'unresolved', 'missing_reference_document', documents=[base[0]] + base[2:]),
        case('missing-owner', 'unresolved', 'missing_reference_document', documents=base[:2] + base[3:]),
        case('undeclared-string', 'failed', 'wrong_encoding', steps=[two_steps[0],
             {'field': 'parent', 'collection': 'owners'}])]

    missing_field = copy.deepcopy(base)
    del missing_field[1]['fields']['owner']
    cases.append(case('missing-declared-field', 'unresolved', 'missing_field', documents=missing_field))
    integer_field = copy.deepcopy(base)
    integer_field[1]['fields']['owner'] = {'integerValue': '7'}
    cases.append(case('nonreference-value', 'failed', 'wrong_encoding', documents=integer_field))
    typed_relative = copy.deepcopy(base)
    typed_relative[1]['fields']['parent'] = {'referenceValue': owner}
    cases.append(case('typed-value-for-relative-encoding', 'failed', 'wrong_encoding', documents=typed_relative,
                      steps=[two_steps[0], {'field': 'parent', 'collection': 'owners', 'encoding': 'relative_path'}]))
    for label, reference, collection, reason in (
            ('foreign-namespace', 'projects/elsewhere/databases/(default)/documents/owners/owner-c', 'owners', 'foreign_namespace'),
            ('foreign-database', 'projects/reference/databases/alternate/documents/owners/owner-c', 'owners', 'foreign_namespace'),
            ('wrong-collection', ROOT + 'teams/owner-c', 'owners', 'wrong_collection'),
            ('nested-collection-prefix', ROOT + 'owners/owner-c/records/record-d', 'owners', 'wrong_collection')):
        changed = copy.deepcopy(base)
        changed[1]['fields']['owner'] = {'referenceValue': reference}
        if reference.startswith(ROOT):
            changed.append({'name': reference, 'fields': {}})
        cases.append(case(label, 'failed', reason, documents=changed,
                          steps=[two_steps[0], {'field': 'owner', 'collection': collection}]))
    for label, relative, reason in (
            ('relative-empty', '', 'invalid_reference'),
            ('relative-double-slash', 'owners//owner-c', 'invalid_reference'),
            ('relative-leading-slash', '/owners/owner-c', 'invalid_reference'),
            ('relative-dot', 'owners/..', 'invalid_reference'),
            ('relative-collection-only', 'owners', 'invalid_reference'),
            ('relative-full-namespace', 'projects/elsewhere/databases/(default)/documents/owners/owner-c', 'invalid_reference'),
            ('relative-wrong-collection', 'teams/owner-c', 'wrong_collection')):
        changed = copy.deepcopy(base)
        changed[1]['fields']['parent'] = {'stringValue': relative}
        cases.append(case(label, 'failed', reason, documents=changed, steps=[two_steps[0],
                          {'field': 'parent', 'collection': 'owners', 'encoding': 'relative_path'}]))
    shared_owner = ROOT + 'owners/shared'
    shared_session = ROOT + 'sessions/shared'
    shared = [{'name': item, 'fields': {'owner': {'referenceValue': shared_owner}}},
              {'name': shared_owner, 'fields': {}}, {'name': shared_session, 'fields': {}}]
    cases.extend([
        case('same-tail-other-endpoint', 'failed', 'endpoint_mismatch', documents=shared,
             steps=[{'field': 'owner', 'collection': 'owners'}], expected=shared_session),
        case('same-tail-wrong-step-collection', 'failed', 'wrong_collection', documents=shared,
             steps=[{'field': 'owner', 'collection': 'sessions'}], expected=shared_session)])
    cycle = copy.deepcopy(base)
    cycle[1]['fields']['owner'] = {'referenceValue': item}
    cases.append(case('declared-cycle', 'failed', 'cycle', documents=cycle,
                      steps=[two_steps[0], {'field': 'owner', 'collection': 'items'}], expected=item))
    return cases


def evaluate_relationship_acceptance(candidate):
    """Use the authored caller/record contract to evaluate any predicate."""
    disagreements = []
    for case in relationship_contract_cases():
        accepted = candidate(*case['arguments'])
        if accepted is not (case['status'] == 'matched'):
            disagreements.append(case['label'])
    return disagreements


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


class RelationshipTests(unittest.TestCase):
    def test_independent_contract_cases_preserve_failure_and_missing_data(self):
        for case in relationship_contract_cases():
            with self.subTest(case=case['label']):
                original = copy.deepcopy(case['arguments'])
                result = module.check_relationship(*case['arguments'])
                self.assertEqual((result['status'], result['reason']), (case['status'], case['reason']))
                self.assertEqual(case['arguments'], original)
                if result['status'] == 'matched':
                    self.assertEqual(result['endpoint'], case['arguments'][-1])

    def test_trace_preserves_full_names_field_and_declared_encoding(self):
        case = next(case for case in relationship_contract_cases() if case['label'] == 'declared-relative-owner')
        result = module.check_relationship(*case['arguments'])
        self.assertEqual(result['trace'], [
            {'document': ROOT + 'items/item-a', 'field': '/session', 'collection': 'sessions',
             'encoding': 'reference', 'target': ROOT + 'sessions/session-b', 'status': 'resolved'},
            {'document': ROOT + 'sessions/session-b', 'field': '/parent', 'collection': 'owners',
             'encoding': 'relative_path', 'target': ROOT + 'owners/owner-c', 'status': 'resolved'}])
        case['arguments'][0][1]['fields']['parent']['stringValue'] = 'owners/changed'
        self.assertEqual(result['endpoint'], ROOT + 'owners/owner-c')
        self.assertEqual(result['trace'][1]['target'], ROOT + 'owners/owner-c')

    def test_failed_and_unresolved_attempts_do_not_advance_the_endpoint(self):
        expected_endpoints = {'missing-start': None, 'missing-child': ROOT + 'items/item-a',
                              'missing-owner': ROOT + 'sessions/session-b',
                              'foreign-namespace': ROOT + 'sessions/session-b',
                              'relative-double-slash': ROOT + 'sessions/session-b'}
        for case in relationship_contract_cases():
            if case['label'] in expected_endpoints:
                with self.subTest(case=case['label']):
                    result = module.check_relationship(*case['arguments'])
                    self.assertEqual(result['endpoint'], expected_endpoints[case['label']])
                    if result['trace']:
                        self.assertEqual(result['trace'][-1]['status'], case['reason'])
                        if case['label'] in ('foreign-namespace', 'relative-double-slash'):
                            self.assertIsNotNone(result['trace'][-1]['target'])

    def test_exact_nested_collection_and_literal_top_level_field(self):
        start, owner = ROOT + 'items/item-a', ROOT + 'groups/group-q/owners/owner-c'
        documents = [{'name': start, 'fields': {'owner/~': {'referenceValue': owner}}},
                     {'name': owner, 'fields': {}}]
        result = module.check_relationship(documents, ROOT, start,
                   [{'field': 'owner/~', 'collection': 'groups/group-q/owners'}], owner)
        self.assertEqual(result['status'], 'matched')
        self.assertEqual(result['trace'][0]['field'], '/owner~1~0')

    def test_empty_chain_compares_existing_full_endpoint_and_duplicate_capture_is_allowed(self):
        first, second = ROOT + 'owners/first', ROOT + 'owners/second'
        documents = [{'name': first, 'fields': {}}, {'name': first, 'fields': {}},
                     {'name': second, 'fields': {}}]
        self.assertEqual(module.check_relationship(documents, ROOT, first, [], first)['status'], 'matched')
        self.assertEqual(module.check_relationship(documents, ROOT, first, [], second)['status'], 'failed')
        self.assertEqual(module.check_relationship(documents, ROOT, first, [], first)['trace'], [])

    def test_invalid_contracts_are_rejected_before_traversal(self):
        name = ROOT + 'items/item-a'
        documents = [{'name': name, 'fields': {}}]
        invalid_steps = [None, (), [{}], [{'field': 'x'}], [{'field': '', 'collection': 'owners'}],
                         [{'field': 1, 'collection': 'owners'}], [{'field': 'x', 'collection': None}],
                         [{'field': 'x', 'collection': 'owners/id'}],
                         [{'field': 'x', 'collection': 'owners//nested'}],
                         [{'field': 'x', 'collection': '/owners'}],
                         [{'field': 'x', 'collection': '..'}],
                         [{'field': 'x', 'collection': 'owners', 'encoding': 'infer'}],
                         [{'field': 'x', 'collection': 'owners', 'role': 'owner'}],
                         [{'field': 'x', 'collection': 'owners'}] * 17]
        for steps in invalid_steps:
            with self.subTest(steps=steps), self.assertRaises(ValueError):
                module.check_relationship(documents, ROOT, name, steps, name)
        for root, start, expected in ((None, name, name), (ROOT, 'item-a', name),
                (ROOT, name, 'projects/elsewhere/databases/(default)/documents/items/item-a')):
            with self.subTest(root=root, start=start, expected=expected), self.assertRaises(ValueError):
                module.check_relationship(documents, root, start, [], expected)

    def test_malformed_or_conflicting_captures_cannot_report_a_match(self):
        name = ROOT + 'items/item-a'
        first = {'name': name, 'fields': {}}
        captures = [None, [None], [{'name': ROOT + 'items'}],
                    [{'name': 'projects/elsewhere/databases/(default)/documents/items/item-a'}],
                    [{'name': name, 'fields': {'bad': {}}}],
                    [{'name': name, 'fields': {'bad': {'referenceValue': ROOT + 'owners/..'}}}],
                    [{'name': name, 'fields': {'bad': {'referenceValue': 'projects/elsewhere/databases/(default)/documents/owners'}}}],
                    [{'name': name, 'fields': {'bad': {'referenceValue': 3}}}],
                    [{'name': name, 'fields': {'bad': {'stringValue': 3}}}],
                    [{'name': name, 'fields': {'bad': {'unknownValue': 'anything'}}}],
                    [{'name': name, 'fields': {'bad': {'booleanValue': 'true'}}}],
                    [{'name': name, 'fields': {'bad': {'integerValue': 'not-an-integer'}}}],
                    [{'name': name, 'fields': {1: {'stringValue': 'bad-field-name'}}}],
                    [{'name': name, 'fields': {'bad': {'mapValue': {'fields': []}}}}],
                    [first, {'name': name, 'fields': {'changed': {'integerValue': '1'}}}]]
        for documents in captures:
            with self.subTest(documents=documents), self.assertRaises(ValueError):
                module.check_relationship(documents, ROOT, name, [], name)

    def test_independent_acceptance_evaluator_rejects_seeded_mutants(self):
        def checker(*arguments):
            return module.check_relationship(*arguments)['status'] == 'matched'

        def raw_first_reference_tail(documents, source_root, start_name, steps, expected_name):
            by_name = {document['name']: document for document in documents}
            item = by_name.get(start_name, {}).get('fields', {}).get(steps[0]['field'], {})
            raw = item.get('referenceValue', item.get('stringValue', ''))
            return isinstance(raw, str) and raw.rsplit('/', 1)[-1] == expected_name.rsplit('/', 1)[-1]

        self.assertEqual(evaluate_relationship_acceptance(checker), [])
        raw_tail_failures = evaluate_relationship_acceptance(raw_first_reference_tail)
        self.assertIn('distinct-child-owner', raw_tail_failures)
        self.assertIn('caller-child-role', raw_tail_failures)
        self.assertIn('same-tail-other-endpoint', raw_tail_failures)
        always_accept_failures = evaluate_relationship_acceptance(lambda *arguments: True)
        self.assertIn('unrelated-existing-owner', always_accept_failures)
        self.assertIn('missing-owner', always_accept_failures)
        self.assertEqual(len(always_accept_failures), len(relationship_contract_cases()) - 3)


if __name__ == '__main__':
    unittest.main()
