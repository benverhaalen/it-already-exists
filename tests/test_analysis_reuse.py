import json
import subprocess
import sys
import importlib.util
import tempfile
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('reuse', ROOT / 'skills/reference-driven-development/scripts/analysis_reuse.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def query():
    return {'provider_profile': {'provider': 'fixture', 'version': '1', 'settings': {'mode': 'strict'}},
            'operation': 'xrefs', 'parameters': {'document': 'target', 'address': '0x10'},
            'effects': {'immutable': True, 'mutates_artifact': False, 'depends_on_live_state': False, 'depends_on_implicit_cursor': False}}


class ReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifact = self.root / 'target'
        self.artifact.write_bytes(b'authored fixture')
        self.store = self.root / 'retained'
        self.evidence = {'basis': 'observed', 'source': 'fixture tool receipt', 'conditions': 'fixture settings', 'limitations': ['synthetic only']}

    def test_reuse_and_small_view_keep_complete_parent_and_limits(self):
        result = {'rows': list(range(200))}
        receipt = m.retain(self.store, self.artifact, query(), result, self.evidence)
        self.assertEqual(m.lookup(self.store, self.artifact, query())['status'], 'hit')
        page = m.view(self.store, receipt['evidence_id'], self.artifact, query(), '/rows', 10, 3)
        self.assertEqual(page['value'], [10, 11, 12])
        self.assertEqual(page['total'], 200)
        self.assertEqual(page['evidence'], self.evidence)
        self.assertEqual(m.read_parent(self.store, receipt['evidence_id'])['result'], result)

    def test_artifact_and_profile_drift_miss_and_reject_old_view(self):
        receipt = m.retain(self.store, self.artifact, query(), [1], self.evidence)
        changed = query()
        changed['provider_profile']['settings']['mode'] = 'loose'
        self.assertEqual(m.lookup(self.store, self.artifact, changed)['status'], 'miss')
        with self.assertRaisesRegex(ValueError, 'another artifact or provider'):
            m.view(self.store, receipt['evidence_id'], self.artifact, changed)
        self.artifact.write_bytes(b'changed')
        self.assertEqual(m.lookup(self.store, self.artifact, query())['status'], 'miss')
        with self.assertRaises(ValueError):
            m.view(self.store, receipt['evidence_id'], self.artifact, query())

    def test_live_mutable_cursor_and_unqualified_are_refused(self):
        for field in query()['effects']:
            q = query()
            q['effects'][field] = not q['effects'][field]
            with self.assertRaises(ValueError):
                m.retain(self.store, self.artifact, q, [], self.evidence)
        q = query()
        del q['effects']['immutable']
        with self.assertRaises(ValueError):
            m.binding(self.artifact, q)

    def test_retained_tampering_and_path_ids_rejected(self):
        receipt = m.retain(self.store, self.artifact, query(), [1], self.evidence)
        (self.store / (receipt['evidence_id'] + '.json')).write_text('{}')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            m.lookup(self.store, self.artifact, query())
        with self.assertRaises(ValueError):
            m.read_parent(self.store, '../outside')

    def test_reanalysis_retains_both_parents(self):
        first = m.retain(self.store, self.artifact, query(), [1], self.evidence)
        second = m.retain(self.store, self.artifact, query(), [2], self.evidence)
        self.assertNotEqual(first['evidence_id'], second['evidence_id'])
        self.assertEqual(m.read_parent(self.store, first['evidence_id'])['result'], [1])
        self.assertEqual(m.lookup(self.store, self.artifact, query())['evidence_id'], second['evidence_id'])

    def test_invalid_page_and_changed_parameters_rejected(self):
        receipt = m.retain(self.store, self.artifact, query(), [1], self.evidence)
        with self.assertRaises(ValueError):
            m.view(self.store, receipt['evidence_id'], self.artifact, query(), limit=101)
        q = query()
        q['parameters']['address'] = '0x20'
        self.assertEqual(m.lookup(self.store, self.artifact, q)['status'], 'miss')

    def test_cli_complete_retention_journey(self):
        q = self.root / 'query.json'
        q.write_text(json.dumps(query()))
        result = self.root / 'result.json'
        result.write_text(json.dumps({'rows': list(range(100))}))
        evidence = self.root / 'evidence.json'
        evidence.write_text(json.dumps(self.evidence))
        base = [sys.executable, str(ROOT / 'skills/reference-driven-development/scripts/analysis_reuse.py')]
        common = ['--store', str(self.store), '--artifact', str(self.artifact), '--query', str(q)]
        def run(action, extra=()):
            out = subprocess.run(base + [action] + common + list(extra), capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr)
            return json.loads(out.stdout)
        self.assertEqual(run('lookup')['status'], 'miss')
        receipt = run('retain', ['--result', str(result), '--evidence', str(evidence)])
        self.assertEqual(run('lookup')['evidence_id'], receipt['evidence_id'])
        page = run('view', ['--id', receipt['evidence_id'], '--pointer', '/rows', '--limit', '2'])
        self.assertEqual(page['value'], [0, 1])
        self.assertEqual(page['next_offset'], 2)
        self.artifact.write_bytes(b'new revision')
        self.assertEqual(run('lookup')['status'], 'miss')

    def test_oversized_item_refuses_without_losing_parent(self):
        receipt = m.retain(self.store, self.artifact, query(), ['x' * 70000], self.evidence)
        with self.assertRaisesRegex(ValueError, 'byte budget'):
            m.view(self.store, receipt['evidence_id'], self.artifact, query())
        self.assertEqual(len(m.read_parent(self.store, receipt['evidence_id'])['result'][0]), 70000)
