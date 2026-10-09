import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
from firestore_query_scenario import project

ROOT = 'projects/reference/databases/(default)/documents'
PARENT = ROOT + '/groups/example'
URL = 'https://firestore.googleapis.com/v1/' + ROOT + ':runQuery'
BOUND = '2025-04-03T05:00:00.000000001Z'


def encode(value):
    return json.dumps(value, separators=(',', ':')).encode()


def field_filter(name, op, value):
    return {'fieldFilter': {'field': {'fieldPath': name}, 'op': op, 'value': value}}


def source_manifest():
    return {'url': URL, 'method': 'POST', 'responseFile': 'a' * 64 + '.json', 'body': {
        'structuredQuery': {'from': [{'collectionId': 'records', 'allDescendants': True}],
                            'where': field_filter('parent', 'EQUAL', {'referenceValue': PARENT}), 'limit': 100}}}


def target_manifest():
    return {'url': URL, 'method': 'POST', 'responseFile': 'b' * 64 + '.json', 'body': {
        'structuredQuery': {'from': [{'collectionId': 'records', 'allDescendants': False}],
                            'where': {'compositeFilter': {'op': 'AND', 'filters': [
                                field_filter('`scheduled`', 'GREATER_THAN_OR_EQUAL', {'timestampValue': BOUND}),
                                field_filter('`disabled`', 'EQUAL', {'booleanValue': False})]}}}}}


def document(identifier, stamp=BOUND, disabled=False):
    return {'name': ROOT + '/records/' + identifier, 'fields': {
        'parent': {'referenceValue': PARENT}, 'scheduled': {'timestampValue': stamp},
        'disabled': {'booleanValue': disabled},
        'related': {'arrayValue': {'values': [{'referenceValue': ROOT + '/other/one'},
                                           {'integerValue': '9007199254740993'}]}},
        'literal': {'stringValue': PARENT}},
        'createTime': '2025-01-01T00:00:00Z', 'updateTime': '2025-03-01T00:00:00.123456000Z'}


def derive(documents, source=None, target=None):
    return project(encode(documents), encode(source or source_manifest()), encode(target or target_manifest()))


class QueryScenarioTests(unittest.TestCase):
    def test_nanosecond_boundary_and_timezone_instants(self):
        rows = [document('late', '2025-04-03T05:00:00.000000002Z'),
                document('before', '2025-04-03T05:00:00.000000000Z'),
                document('offset', '2025-04-02T23:00:00.000000001-06:00'),
                document('equal', BOUND),
                document('day-after', '2025-04-03T00:00:00-06:00')]
        # Independent expected UTC instants: 05:00:00+1ns inclusive, not string order or microsecond truncation.
        result = derive([{'document': row} for row in rows])
        self.assertEqual([r['document']['name'].split('/')[-1] for r in result['response']],
                         ['equal', 'offset', 'late', 'day-after'])
        self.assertEqual(result['provenance']['excluded_documents']['timestamp_filter'], 1)
        self.assertEqual(derive(list(reversed(rows)))['response'], result['response'])

    def test_preserves_original_document_data_and_separates_read_time(self):
        doc = document('one')
        baseline = copy.deepcopy(doc)
        result = derive([{'document': doc, 'readTime': '2025-04-04T10:00:00Z'},
                         {'done': True, 'readTime': '2025-04-04T10:01:00Z'}])
        self.assertEqual(result['response'], [{'document': baseline}])
        self.assertNotIn('readTime', result['response'][0])
        self.assertEqual(result['provenance']['source_observations'][0]['readTime'], '2025-04-04T10:00:00Z')
        result['response'][0]['document']['fields']['literal']['stringValue'] = 'changed'
        self.assertEqual(doc, baseline)

    def test_collection_group_source_does_not_supply_nested_target_records(self):
        direct = document('direct')
        nested = document('nested')
        nested['name'] = ROOT + '/groups/example/records/nested'
        similar = document('other')
        similar['name'] = ROOT + '/groups/elsewhere/records/other'
        result = derive([direct, nested, similar])
        self.assertEqual(result['response'], [{'document': direct}])
        self.assertEqual(result['provenance']['excluded_documents']['collection_scope'], 2)
        target = target_manifest()
        target['url'] = 'https://firestore.googleapis.com/v1/' + PARENT + ':runQuery'
        self.assertEqual(derive([direct, nested, similar], target=target)['response'], [{'document': nested}])

    def test_valid_type_mismatches_and_missing_fields_are_not_coerced(self):
        text_date = document('text-date')
        text_date['fields']['scheduled'] = {'stringValue': BOUND}
        zero_flag = document('zero-flag')
        zero_flag['fields']['disabled'] = {'integerValue': '0'}
        missing = document('missing')
        del missing['fields']['disabled']
        disabled = document('disabled', disabled=True)
        self.assertEqual(derive([text_date, zero_flag, missing, disabled])['response'], [])
        target = target_manifest()
        target['body']['structuredQuery']['where']['compositeFilter']['filters'][1]['fieldFilter']['value'] = {'booleanValue': True}
        self.assertEqual(derive([disabled], target=target)['response'], [{'document': disabled}])

    def test_malformed_relevant_values_fail_even_after_an_earlier_nonmatch(self):
        invalid = [None, {}, {'timestampValue': BOUND, 'stringValue': BOUND},
                   {'timestampValue': '2025-04-03T05:00:00'}, {'booleanValue': 0},
                   {'integerValue': 'not-a-number'}, {'integerValue': '١'},
                   {'bytesValue': 'invalid@base64'}, {'geoPointValue': {'latitude': 91, 'longitude': 0}},
                   {'unknownValue': 'x'}]
        for value in invalid:
            doc = document('one', stamp='2025-04-02T00:00:00Z')
            doc['fields']['disabled'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                derive([doc])

    def test_invalid_timestamps_fail_for_rows_and_thresholds(self):
        for stamp in ('2025-04-03', '2025-04-03T05:00:00', '2025-04-03T05:00:00-00:00',
                      '2025-04-03T05:00:00+24:00', '2025-04-03T05:00:00+01:60',
                      '2025-02-30T05:00:00Z', '2025-04-03T05:00:60Z',
                      '2025-04-03T05:00:00.0000000001Z', '0001-01-01T00:00:00+01:00',
                      '２０２５-04-03T05:00:00Z', '2025-04-03T05:00:00.١Z'):
            with self.subTest(stamp=stamp), self.assertRaises(ValueError):
                derive([document('one', stamp)])
            target = target_manifest()
            target['body']['structuredQuery']['where']['compositeFilter']['filters'][0]['fieldFilter']['value'] = {'timestampValue': stamp}
            with self.subTest(threshold=stamp), self.assertRaises(ValueError):
                derive([], target=target)

    def test_duplicate_inconsistent_and_noncanonical_source_documents_fail(self):
        one = document('one')
        conflicting = document('one', disabled=True)
        for rows in ([one, copy.deepcopy(one)], [one, conflicting]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                derive(rows)
        for name in (ROOT + '/records', ROOT + '/records/../records/one', ROOT + '/records//one',
                     ROOT + '/records/a%2Fb', ROOT + '/records/one/children',
                     ROOT + '/recordset/one', 'projects/other/databases/(default)/documents/records/one'):
            doc = document('one')
            doc['name'] = name
            with self.subTest(name=name), self.assertRaises(ValueError):
                derive([doc])
        one['fields']['parent'] = {'referenceValue': ROOT + '/groups/different'}
        with self.assertRaises(ValueError):
            derive([one])

    def test_unsupported_target_grammar_is_refused_instead_of_ignored(self):
        variants = []
        for key, value in (('orderBy', []), ('limit', 1), ('offset', 0), ('select', {}),
                           ('startAt', {}), ('endAt', {}), ('findNearest', {})):
            target = target_manifest()
            target['body']['structuredQuery'][key] = value
            variants.append(target)
        for edit in ('descendants', 'or', 'extra-filter', 'nested-field', 'wrong-type', 'same-field', 'transaction'):
            target = target_manifest()
            query = target['body']['structuredQuery']
            filters = query['where']['compositeFilter']['filters']
            if edit == 'descendants': query['from'][0]['allDescendants'] = True
            elif edit == 'or': query['where']['compositeFilter']['op'] = 'OR'
            elif edit == 'extra-filter': filters.append(copy.deepcopy(filters[0]))
            elif edit == 'nested-field': filters[0]['fieldFilter']['field']['fieldPath'] = 'nested.scheduled'
            elif edit == 'wrong-type': filters[1]['fieldFilter']['value'] = {'booleanValue': 'false'}
            elif edit == 'same-field': filters[1]['fieldFilter']['field']['fieldPath'] = '`scheduled`'
            elif edit == 'transaction': target['body']['transaction'] = 'opaque'
            variants.append(target)
        for target in variants:
            with self.subTest(target=target), self.assertRaises(ValueError):
                derive([], target=target)

    def test_source_scope_limit_response_and_manifest_safety(self):
        source = source_manifest()
        source['body']['structuredQuery']['limit'] = 0
        with self.assertRaises(ValueError): derive([document('one')], source=source)
        source = source_manifest()
        source['body']['structuredQuery']['select'] = {'fields': []}
        with self.assertRaises(ValueError): derive([], source=source)
        for response in ([{'error': {'status': 'DENIED'}}], [{'document': None}],
                         [{'readTime': '2025-04-03T05:00:00'}], [{'skippedResults': 1}],
                         [{'done': True}, {'document': document('one')}],
                         [document('one'), {'document': document('two')}]):
            with self.subTest(response=response), self.assertRaises(ValueError): derive(response)
        for url in (URL + '?x=1', URL + '#fragment', URL.replace('https:', 'http:'),
                    ' ' + URL, URL.replace('/documents:', '/documents/records:'),
                    URL.replace('/documents:', '/documents/../x:')):
            target = target_manifest(); target['url'] = url
            with self.subTest(url=url), self.assertRaises(ValueError): derive([], target=target)
        target = target_manifest(); target['responseFile'] = '../' + target['responseFile']
        with self.assertRaises(ValueError): derive([], target=target)
        target = target_manifest(); target['url'] = URL.replace('projects/reference/', 'projects/elsewhere/')
        with self.assertRaises(ValueError): derive([], target=target)

    def test_hashes_partial_provenance_and_no_reconstructed_cache_identity(self):
        row = document('one')
        response = encode([{'document': row}])
        source = encode(source_manifest())
        target = encode(target_manifest())
        report = project(response, source, target)
        p = report['provenance']
        self.assertEqual(p['source_response_sha256'], hashlib.sha256(response).hexdigest())
        self.assertEqual(p['source_manifest_sha256'], hashlib.sha256(source).hexdigest())
        self.assertEqual(p['target_manifest_sha256'], hashlib.sha256(target).hexdigest())
        self.assertEqual(p['evidence_mode'], 'derived-fixture')
        self.assertEqual(p['coverage'], 'observed-subset-only')
        self.assertEqual(p['current_state'], 'unknown')
        self.assertFalse(p['complete']); self.assertFalse(p['ready_for_fidelity'])
        self.assertFalse(p['request_cache_keys_verified']); self.assertFalse(p['request_body_bytes_available'])
        self.assertFalse(p['coverage_difference']['source_scope_implies_target_completeness'])
        self.assertNotIn('cache_key', p)
        pretty = json.dumps(target_manifest(), indent=2).encode()
        altered = project(response, source, pretty)
        self.assertEqual(altered['response'], report['response'])
        self.assertNotEqual(altered['provenance']['target_manifest_sha256'], p['target_manifest_sha256'])
        empty = derive([])
        self.assertEqual(empty['response'], [])
        self.assertFalse(empty['provenance']['complete'])

    def test_duplicate_json_keys_nonfinite_and_existing_cli_output_fail(self):
        with self.assertRaises(ValueError):
            project(b'[]', encode(source_manifest()), b'{"url":"x","url":"y"}')
        with self.assertRaises(ValueError):
            project(b'[{"value":NaN}]', encode(source_manifest()), encode(target_manifest()))
        with self.assertRaises(ValueError):
            project(b'[{"value":1e309}]', encode(source_manifest()), encode(target_manifest()))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / 'rows.json', root / 'source.request', root / 'target.request']
            for path, payload in zip(paths, (encode([document('one')]), encode(source_manifest()), encode(target_manifest()))):
                path.write_bytes(payload)
            output = root / 'derived.json'
            command = [sys.executable, str(SCRIPTS / 'firestore_query_scenario.py'), '--input', str(paths[0]),
                       '--source-manifest', str(paths[1]), '--target-manifest', str(paths[2]), '--output', str(output)]
            first = subprocess.run(command, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr.decode())
            original = output.read_bytes()
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(original)['response'], [{'document': document('one')}])
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(output.read_bytes(), original)
            command[-1] = str(root / '..' / 'unsafe-derived.json')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            paths[0].unlink(); paths[0].symlink_to(output)
            command[-1] = str(root / 'another.json')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse((root / 'another.json').exists())
            paths[0].unlink(); paths[0].write_bytes(encode([document('one')]))
            nested = root / 'real' / 'nested'; nested.mkdir(parents=True)
            (root / 'linked').symlink_to(root / 'real', target_is_directory=True)
            command[-1] = str(root / 'linked' / 'nested' / 'derived.json')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse((nested / 'derived.json').exists())
            (nested / 'rows.json').write_bytes(encode([document('one')]))
            command[3] = str(root / 'linked' / 'nested' / 'rows.json')
            command[-1] = str(root / 'another.json')
            self.assertNotEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertFalse((root / 'another.json').exists())


if __name__ == '__main__':
    unittest.main()
