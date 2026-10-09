import copy
import hashlib
import importlib.util
import json
import tempfile
import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('behavior', ROOT / 'skills/reference-driven-development/scripts/behavioral_evidence.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def trace():
    return {'case': 'reopen', 'environment': 'controlled-v1', 'inputs_sha256': 'fixture-inputs',
            'events': [{'boundary': 'load', 'state': {'ready': False}}, {'boundary': 'display', 'state': {'ready': True}}],
            'final_state': {'ready': True}}


class BehaviorTests(unittest.TestCase):
    def test_equal_traces_pass(self):
        self.assertEqual(m.compare(trace(), trace())['status'], 'pass')

    def test_same_final_state_wrong_order_fails(self):
        candidate = trace()
        candidate['events'].reverse()
        report = m.compare(trace(), candidate)
        self.assertEqual(report['status'], 'fail')
        self.assertTrue(report['final_state_equal'])
        self.assertEqual(report['first_difference'], 0)

    def test_phase_state_missing_event_and_final_drift_fail(self):
        for mutate in (lambda t: t['events'][0]['state'].update(ready=True),
                       lambda t: t['events'].pop(),
                       lambda t: t['final_state'].update(ready=False)):
            candidate = trace()
            mutate(candidate)
            self.assertEqual(m.compare(trace(), candidate)['status'], 'fail')

    def test_context_mismatch_and_empty_trace_refused(self):
        for key in ('case', 'environment', 'inputs_sha256'):
            candidate = trace()
            candidate[key] = 'different'
            with self.assertRaises(ValueError):
                m.compare(trace(), candidate)
        candidate = trace()
        candidate['events'] = []
        with self.assertRaises(ValueError):
            m.compare(trace(), candidate)

    def setup_receipt(self, root, **changes):
        result = m.compare(trace(), trace())
        result.update(obligation='persist', original_basis='observed', verifier_executed=True)
        result.update(changes)
        path = root / 'result.json'
        path.write_text(json.dumps(result))
        packet = {'obligations': [{'id': 'persist', 'environment': 'controlled-v1', 'required_cases': ['reopen'],
                                  'receipts': [{'case': 'reopen', 'file': 'result.json', 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}]}]}
        return packet

    def test_closure_requires_observed_executed_exact_case(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(m.closure(self.setup_receipt(root), root)['status'], 'qualified')
            for changes in ({'original_basis': 'inferred'}, {'verifier_executed': False},
                            {'case': 'different'}, {'environment': 'different'}, {'status': 'fail'},
                            {'obligation': 'different'}, {'events_equal': False}):
                packet = self.setup_receipt(root, **changes)
                self.assertEqual(m.closure(packet, root)['status'], 'unresolved')

    def test_missing_case_and_stale_receipt_cannot_close(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = self.setup_receipt(root)
            packet['obligations'][0]['required_cases'].append('cancel')
            self.assertEqual(m.closure(packet, root)['unresolved'][0]['case'], 'cancel')
            packet = self.setup_receipt(root)
            (root / 'result.json').write_text('{}')
            self.assertEqual(m.closure(packet, root)['status'], 'unresolved')

    def test_empty_denominator_duplicate_and_path_escape_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(ValueError):
                m.closure({'obligations': []}, root)
            packet = self.setup_receipt(root)
            packet['obligations'].append(copy.deepcopy(packet['obligations'][0]))
            with self.assertRaises(ValueError):
                m.closure(packet, root)
            packet = self.setup_receipt(root)
            packet['obligations'][0]['receipts'][0]['file'] = '../outside'
            with self.assertRaises(ValueError):
                m.closure(packet, root)

    def test_cli_failing_trace_and_unresolved_closure_exit_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / 'original.json'
            candidate = root / 'candidate.json'
            original.write_text(json.dumps(trace()))
            wrong = trace()
            wrong['events'].reverse()
            candidate.write_text(json.dumps(wrong))
            output = root / 'comparison.json'
            helper = ROOT / 'skills/reference-driven-development/scripts/behavioral_evidence.py'
            run = subprocess.run([sys.executable, str(helper), 'compare', str(original), str(candidate), '--output', str(output)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 1, run.stderr)
            self.assertTrue(json.loads(output.read_text())['final_state_equal'])
            packet = self.setup_receipt(root, verifier_executed=False)
            path = root / 'obligations.json'
            path.write_text(json.dumps(packet))
            run = subprocess.run([sys.executable, str(helper), 'closure', str(path), '--root', str(root)], capture_output=True, text=True)
            self.assertEqual(run.returncode, 1, run.stderr)
            self.assertEqual(json.loads(run.stdout)['status'], 'unresolved')
