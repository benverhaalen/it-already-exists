"""External repair bindings, durable feedback and unchanged budgets."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/reference-driven-development/scripts'))
import coding_loop as loop
import repair


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve(); self.worker = self.root/'worker'
        self.spec = self.root/'spec.json'; self.spec.write_text(json.dumps(dict(scope='owned-counter', goal='Display zero')))
        self.model = self.root/'model'; self.model.write_bytes(b'test double')
        self.backend = ['/fake', '{model}', '{prompt}']
        self.policy = dict(commands={'check': [sys.executable, 'counter.py']}, max_steps=10,
            total_seconds=30, step_seconds=3, max_output_bytes=65536,
            max_context_bytes=1048576, max_files=10, max_content_bytes=65536)
        self.actions([dict(action='edit', files=[dict(path='counter.py', content='print(1)\n')]), dict(action='submit')])
        self.artifact = self.worker/'project/counter.py'
        actual = int(subprocess.check_output([sys.executable, str(self.artifact)], text=True))
        self.report = dict(status='failed', contract_sha256='a'*64,
            candidate_artifact=hashlib.sha256(self.artifact.read_bytes()).hexdigest(),
            properties=[dict(id='count', status='failed', reason='state_assertion', expected=0, actual=actual)])
        self.review = dict(approved=True, reviewer='independent fixture evaluator', report_sha256=loop.digest(self.report))
        self.guidance = dict(scope='owned-counter', behaviors=['The independently observed output was one; display zero.'],
            review=dict(reviewer='behavior-only fixture reviewer', implementation_independent=True,
                        source_free=True, asset_rights=True, limits='Owned behavioral fixture, no original source.'))

    def actions(self, actions, request=None, resume=False):
        with patch.object(loop, 'run_backend', side_effect=[json.dumps(a) for a in actions]):
            return loop.execute(self.worker, self.spec, self.model, self.backend, self.policy,
                                resume=resume, repair=request)

    def request(self):
        return repair.prepare(self.report, self.review, self.guidance, 'counter.py')

    def test_external_feedback_repairs_actual_output_without_erasing_history(self):
        state = self.actions([dict(action='edit', files=[dict(path='counter.py', content='print(0)\n')]),
            dict(action='command', command='check'), dict(action='submit')], self.request(), True)
        self.assertEqual(state['steps'], 5)
        self.assertEqual(len(state['repairs']), 1)
        self.assertEqual(state['messages'][2]['kind'], 'external_review')
        self.assertEqual(state['messages'][2]['feedback']['counterexamples'][0]['actual'], 1)
        self.assertEqual(subprocess.check_output([sys.executable, str(self.artifact)], text=True).strip(), '0')
        self.assertEqual(state['messages'][4]['observation']['stdout'].strip(), '0')
        repeated = self.actions([], self.request(), True)
        self.assertEqual(repeated['steps'], 5)
        self.assertEqual(len(repeated['repairs']), 1)

    def test_stale_report_and_changed_artifact_are_rejected_before_inference(self):
        self.report['properties'][0]['actual'] = 2
        with self.assertRaisesRegex(ValueError, 'current report hash'):
            self.request()
        self.report['properties'][0]['actual'] = 1
        request = self.request(); request['feedback']['candidate_artifact'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'differs'):
            self.actions([], request, True)
        request = self.request(); request['artifact'] = 'delivered.bin'
        (self.worker/'project/delivered.bin').write_bytes(b'changed delivered build')
        with self.assertRaisesRegex(ValueError, 'different delivered'):
            self.actions([], request, True)
        self.assertEqual(loop.load(self.worker/'loop.json')['steps'], 2)

    def test_later_repair_cannot_change_contract_or_scope(self):
        self.actions([dict(action='edit', files=[dict(path='counter.py', content='print(0)\n')]),
                      dict(action='submit')], self.request(), True)
        self.report['candidate_artifact'] = hashlib.sha256(self.artifact.read_bytes()).hexdigest()
        self.report['contract_sha256'] = 'b'*64
        self.review['report_sha256'] = loop.digest(self.report)
        with self.assertRaisesRegex(ValueError, 'change the external contract'):
            self.actions([], self.request(), True)
        self.report['contract_sha256'] = 'a'*64
        self.review['report_sha256'] = loop.digest(self.report)
        self.guidance['scope'] = 'different-project'
        with self.assertRaisesRegex(ValueError, 'scope differs'):
            self.actions([], self.request(), True)
        state = loop.load(self.worker/'loop.json')
        self.assertEqual(state['steps'], 4)
        self.assertEqual(len(state['repairs']), 1)
        self.assertEqual(state['status'], 'submitted')

    def test_failed_inference_reuses_accepted_review_without_resetting_steps(self):
        request = self.request()
        with patch.object(loop, 'run_backend', side_effect=ValueError('inference interrupted before action')):
            with self.assertRaisesRegex(ValueError, 'interrupted'):
                loop.execute(self.worker, self.spec, self.model, self.backend, self.policy,
                             resume=True, repair=request)
        state = loop.load(self.worker/'loop.json')
        self.assertEqual(state['steps'], 3)
        self.assertEqual(len(state['repairs']), 1)
        state = self.actions([dict(action='submit')], request, True)
        self.assertEqual(state['steps'], 4)
        self.assertEqual(len(state['repairs']), 1)
        self.assertEqual(sum(m.get('kind') == 'external_review' for m in state['messages']), 1)


if __name__ == '__main__':
    unittest.main()
