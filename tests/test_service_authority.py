"""Authored lifecycle counterexamples; no captured target or request contents."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts/service_authority.py'
SPEC = importlib.util.spec_from_file_location('service_authority', SCRIPT)
authority = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(authority)

EXPECTED = {'scheme': 'http', 'host': '127.0.0.1', 'port': 8041}
OTHER = {'scheme': 'http', 'host': '127.0.0.2', 'port': 8041}


def configuration(phase, endpoint=EXPECTED):
    return {'phase': phase, 'kind': 'configuration', 'authority': copy.deepcopy(endpoint)}


def request(phase, endpoint=EXPECTED, guard='allowed', transport='succeeded'):
    return {'phase': phase, 'kind': 'request', 'authority': copy.deepcopy(endpoint),
            'guard': guard, 'transport': transport}


def trace(observations=None, phases=None):
    return {'schema_version': 1, 'expected_authority': copy.deepcopy(EXPECTED),
            'phases': copy.deepcopy(phases if phases is not None else [
                {'name': 'initial', 'identity_state': 'fresh'},
                {'name': 'reopen', 'identity_state': 'stored'}]),
            'observations': copy.deepcopy(observations if observations is not None else [
                configuration('initial'), request('initial'),
                configuration('reopen'), request('reopen')])}


def codes(result):
    return [finding['code'] for finding in result['findings']]


class AuthorityTraceTests(unittest.TestCase):
    def test_normal_stored_identity_reopen_matches_without_mutating_input(self):
        supplied = trace()
        original = copy.deepcopy(supplied)
        result = authority.check_trace(supplied)
        self.assertEqual((result['status'], result['authority_status'], result['request_status'], result['guard_status']),
                         ('matched', 'matched', 'succeeded', 'known'))
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['phases'][1]['identity_state'], 'stored')
        self.assertEqual(supplied, original)
        supplied['observations'][0]['authority']['port'] = 10
        self.assertEqual(result['observations'][0]['authority'], EXPECTED)

    def test_initial_success_then_configuration_drift_and_local_denial(self):
        supplied = trace([configuration('initial'), request('initial'),
                          configuration('reopen', OTHER),
                          request('reopen', OTHER, 'denied', 'not_attempted')])
        result = authority.check_trace(supplied)
        self.assertEqual((result['status'], result['authority_status'], result['request_status']),
                         ('failed', 'failed', 'failed'))
        self.assertEqual(result['observations'][3]['classification'], 'local_denial_before_transport')
        self.assertEqual(codes(result), ['authority_mismatch', 'configuration_authority_drift',
                                       'authority_mismatch', 'request_authority_drift',
                                       'local_denial_before_transport'])
        drift = next(item for item in result['findings'] if item['code'] == 'configuration_authority_drift')
        self.assertEqual((drift['observation'], drift['previous_observation']), (2, 0))
        self.assertNotIn('transport_failure', codes(result))

    def test_request_difference_does_not_invent_configuration_mutation(self):
        result = authority.check_trace(trace([configuration('initial'), request('initial'), request('reopen', OTHER)]))
        self.assertIn('request_authority_drift', codes(result))
        self.assertIn('request_configuration_mismatch', codes(result))
        self.assertNotIn('configuration_authority_drift', codes(result))
        self.assertEqual(result['findings'][-1]['configuration_observation'], 0)

    def test_changed_authority_then_return_stays_a_failed_trace(self):
        result = authority.check_trace(trace([request('initial'), request('initial', OTHER), request('reopen')]))
        self.assertEqual(result['authority_status'], 'failed')
        self.assertEqual(codes(result).count('request_authority_drift'), 2)
        self.assertEqual(result['observations'][-1]['authority'], EXPECTED)

    def test_host_scheme_and_port_all_participate_in_authority_identity(self):
        for changed in (dict(EXPECTED, host='localhost'), dict(EXPECTED, scheme='https'), dict(EXPECTED, port=8042)):
            with self.subTest(endpoint=changed):
                result = authority.check_trace(trace([request('initial'), request('reopen', changed)]))
                self.assertEqual(result['status'], 'failed')
                self.assertIn('authority_mismatch', codes(result))

    def test_observed_transport_failure_preserves_unknown_guard_boundary(self):
        supplied = trace([request('initial'), request('reopen', guard='unknown', transport='failed')])
        result = authority.check_trace(supplied)
        self.assertEqual((result['status'], result['authority_status'], result['request_status'], result['guard_status']),
                         ('failed', 'matched', 'failed', 'unresolved'))
        self.assertEqual(result['observations'][-1]['classification'], 'transport_failure')
        self.assertIn('unknown_guard_fact', codes(result))
        self.assertNotIn('local_denial_before_transport', codes(result))
        self.assertNotIn('remote', json.dumps(result['findings']))
        supplied['observations'][-1]['guard'] = 'allowed'
        self.assertEqual(authority.check_trace(supplied)['guard_status'], 'known')

    def test_missing_and_unknown_guard_or_transport_never_qualify_as_success(self):
        for key in ('guard', 'transport'):
            for missing in (False, True):
                supplied = trace()
                if missing:
                    del supplied['observations'][-1][key]
                else:
                    supplied['observations'][-1][key] = 'unknown'
                with self.subTest(key=key, missing=missing):
                    result = authority.check_trace(supplied)
                    self.assertEqual(result['status'], 'unresolved')
                    self.assertIn(('missing_' if missing else 'unknown_') + key + '_fact', codes(result))
        supplied = trace([request('initial'), request('reopen', guard='denied', transport='unknown')])
        result = authority.check_trace(supplied)
        self.assertEqual(result['status'], 'unresolved')
        self.assertNotIn('local_denial_before_transport', codes(result))

    def test_no_transport_without_known_denial_remains_unresolved(self):
        for guard in ('allowed', 'unknown'):
            result = authority.check_trace(trace([request('initial'),
                request('reopen', guard=guard, transport='not_attempted')]))
            self.assertEqual(result['status'], 'unresolved')
            self.assertIn('transport_not_attempted_without_known_denial', codes(result))
            self.assertNotIn('local_denial_before_transport', codes(result))

    def test_missing_observations_or_phase_coverage_never_default_to_match(self):
        for observations in ([], [request('initial')], [configuration('initial'), configuration('reopen')]):
            with self.subTest(observations=observations):
                result = authority.check_trace(trace(observations))
                self.assertEqual(result['status'], 'unresolved')
                self.assertEqual(result['guard_status'], 'unresolved')
        empty = authority.check_trace(trace([]))
        self.assertEqual(codes(empty).count('missing_phase_observations'), 2)
        self.assertIn('missing_request_observations', codes(empty))

    def test_reopen_configuration_without_request_remains_unresolved(self):
        supplied = trace([configuration('initial'), request('initial'), configuration('reopen')])
        result = authority.check_trace(supplied)
        self.assertEqual((result['status'], result['authority_status'], result['request_status'], result['guard_status']),
                         ('unresolved', 'matched', 'unresolved', 'unresolved'))
        self.assertEqual(result['findings'], [{'code': 'missing_phase_request_observations', 'phase': 'reopen'}])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_text(json.dumps(supplied))
            with mock.patch('sys.stdout', new_callable=io.StringIO) as output:
                self.assertEqual(authority.main(['--input', str(path)]), 2)
                self.assertEqual(json.loads(output.getvalue())['status'], 'unresolved')

    def test_denied_guard_with_attempted_transport_is_contradictory(self):
        for transport in ('failed', 'succeeded'):
            with self.subTest(transport=transport), self.assertRaisesRegex(ValueError, 'contradicts'):
                authority.check_trace(trace([request('initial'),
                    request('reopen', guard='denied', transport=transport)]))

    def test_undeclared_duplicate_or_backwards_phases_are_refused(self):
        supplied = trace()
        cases = [trace([request('reopen'), request('initial')]),
                 trace([request('unlisted')]), trace(phases=supplied['phases'] * 2),
                 trace(phases=[]), trace(phases=[{'name': 'bad label', 'identity_state': 'stored'}]),
                 trace(phases=[{'name': 'initial', 'identity_state': 'private-account-value'}])]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                authority.check_trace(case)

    def test_malformed_endpoint_components_are_refused_without_echoing_values(self):
        bad_fields = [('scheme', 'http?token=private-token'), ('scheme', 'HTTP'), ('scheme', None),
                      ('host', 'user:private-token@host.example'), ('host', 'host.example/path'),
                      ('host', 'host.example?token=private-token'), ('host', 'host.example#private-token'),
                      ('host', 'host.example:8041'), ('host', 'host.example.'), ('host', '127.000.0.1'),
                      ('host', '127.1'), ('host', '0x7f000001'), ('host', '0x7f.0.0.1'),
                      ('host', '[::1]'), ('host', 'fe80::1%en0'), ('host', 'é.example'),
                      ('host', 'x' * 64 + '.example'), ('host', ''), ('host', None),
                      ('port', True), ('port', 0), ('port', 65536), ('port', '8041'), ('port', 8041.0)]
        for key, value in bad_fields:
            supplied = trace()
            supplied['observations'][-1]['authority'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError) as error:
                authority.check_trace(supplied)
            self.assertNotIn('private-token', str(error.exception))

    def test_endpoint_dns_case_and_bare_ipv6_normalization_are_pure(self):
        for expected, observed in (({'scheme': 'https', 'host': 'Service.Example', 'port': 443},
                                   {'scheme': 'https', 'host': 'service.example', 'port': 443}),
                                  ({'scheme': 'http', 'host': '2001:db8:0:0::1', 'port': 8041},
                                   {'scheme': 'http', 'host': '2001:db8::1', 'port': 8041})):
            supplied = trace([request('initial', observed), request('reopen', observed)])
            supplied['expected_authority'] = expected
            original = copy.deepcopy(supplied)
            self.assertEqual(authority.check_trace(supplied)['status'], 'matched')
            self.assertEqual(supplied, original)

    def test_unknown_secret_bearing_fields_and_wrong_fact_types_are_refused(self):
        for location in ('root', 'phase', 'configuration', 'request', 'authority'):
            supplied = trace()
            container = {'root': supplied, 'phase': supplied['phases'][0],
                         'configuration': supplied['observations'][0], 'request': supplied['observations'][1],
                         'authority': supplied['expected_authority']}[location]
            container['authorization-private-token'] = {'url': 'https://host.example?token=private-token'}
            with self.subTest(location=location), self.assertRaises(ValueError) as error:
                authority.check_trace(supplied)
            self.assertNotIn('private-token', str(error.exception))
        for key, value in (('guard', True), ('guard', ['allowed']), ('transport', 'Network error'),
                           ('transport', None)):
            supplied = trace()
            supplied['observations'][1][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                authority.check_trace(supplied)
        supplied = trace()
        supplied['observations'][0]['guard'] = 'allowed'
        with self.assertRaises(ValueError):
            authority.check_trace(supplied)

    def test_schema_and_collection_bounds_are_enforced(self):
        for key, value in (('schema_version', True), ('schema_version', 2), ('observations', None),
                           ('observations', [request('initial')] * (authority.MAX_OBSERVATIONS + 1)),
                           ('phases', [{}] * (authority.MAX_PHASES + 1)), ('expected_authority', {})):
            supplied = trace()
            supplied[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                authority.check_trace(supplied)

    def test_checker_never_opens_network_transport(self):
        with mock.patch('socket.socket', side_effect=AssertionError('unexpected network call')):
            self.assertEqual(authority.check_trace(trace())['status'], 'matched')
            self.assertEqual(authority.check_trace(trace([request('initial'),
                request('reopen', OTHER, 'denied', 'not_attempted')]))['status'], 'failed')


class AuthorityFileTests(unittest.TestCase):
    def test_duplicate_json_constants_encoding_and_input_bound_are_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            for raw in (b'{"schema_version":1,"schema_version":1}', b'{"x":NaN}', b'{"x":Infinity}',
                        b'{not JSON private-token}', b'\xff', b' ' * (authority.MAX_INPUT + 1)):
                path.write_bytes(raw)
                with self.subTest(prefix=raw[:30]), self.assertRaises(ValueError) as error:
                    authority.load_trace(path)
                self.assertNotIn('private-token', str(error.exception))

    def test_cli_exit_codes_and_private_output_without_overwriting_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / 'input.json', Path(directory) / 'output.json'
            source.write_text(json.dumps(trace()))
            success = subprocess.run([sys.executable, str(SCRIPT), '--input', str(source), '--output', str(target)],
                                     capture_output=True, text=True)
            self.assertEqual(success.returncode, 0, success.stderr + success.stdout)
            self.assertEqual(json.loads(target.read_text())['status'], 'matched')
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o600)
            original = target.read_bytes()
            with mock.patch('sys.stdout', new_callable=io.StringIO) as output:
                self.assertEqual(authority.main(['--input', str(source), '--output', str(target)]), 1)
                self.assertEqual(json.loads(output.getvalue())['status'], 'invalid')
            self.assertEqual(target.read_bytes(), original)
            for supplied, code, status in ((trace([]), 2, 'unresolved'),
                    (trace([request('initial'), request('reopen', OTHER, 'denied', 'not_attempted')]), 2, 'failed'),
                    (dict(trace(), token='private-token'), 1, 'invalid')):
                source.write_text(json.dumps(supplied))
                with mock.patch('sys.stdout', new_callable=io.StringIO) as output:
                    self.assertEqual(authority.main(['--input', str(source)]), code)
                    self.assertEqual(json.loads(output.getvalue())['status'], status)
                    self.assertNotIn('private-token', output.getvalue())


if __name__ == '__main__':
    unittest.main()
