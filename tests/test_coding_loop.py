"""Real command feedback and lifecycle faults; scripted inference is not model QA."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/reference-driven-development/scripts'))
import coding_loop as loop


class LoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.spec = self.root/'spec.json'
        self.spec.write_text(json.dumps(dict(goal='Create a counter with persistence')))
        self.model = self.root/'model'
        self.model.write_bytes(b'test double, not actual inference weights')
        self.settings = dict(commands={'check': [sys.executable, '-m', 'py_compile', 'counter.py']},
                             max_steps=10, total_seconds=30, step_seconds=3,
                             max_output_bytes=65536, max_context_bytes=1048576,
                             max_files=10, max_content_bytes=65536)
        self.backend = ['/fake/inference', '{model}', '{prompt}']

    def execute(self, actions, resume=False):
        with patch.object(loop, 'run_backend', side_effect=[json.dumps(a) for a in actions]):
            return loop.execute(self.root/'worker', self.spec, self.model, self.backend, self.settings, resume)

    def edit(self, content):
        return dict(action='edit', files=[dict(path='counter.py', content=content)])

    def test_actual_compile_failure_then_repair_then_submission(self):
        result = self.execute([self.edit('def broken('), dict(action='command', command='check'),
                               self.edit('count = 0\n'), dict(action='command', command='check'), dict(action='submit')])
        self.assertEqual(result['status'], 'submitted')
        observations = [m['observation'] for m in result['messages']]
        self.assertNotEqual(observations[1]['exit_code'], 0)
        self.assertEqual(observations[3]['exit_code'], 0)
        self.assertIn('external_evaluation', observations[4]['status'])
        self.assertEqual((self.root/'worker/project/counter.py').read_text(), 'count = 0\n')

    def test_resume_preserves_sources_history_and_spent_calls(self):
        self.settings['max_steps'] = 3
        with self.assertRaises(ValueError):
            self.execute([self.edit('count = 0\n'), dict(action='unknown')])
        result = self.execute([dict(action='submit')], resume=True)
        self.assertEqual(result['steps'], 3)
        self.assertEqual(len(result['messages']), 3)
        self.assertEqual(result['status'], 'submitted')

    def test_interrupted_command_cannot_be_replayed_on_resume(self):
        with self.assertRaises(ValueError):
            self.execute([self.edit('count = 0\n'), dict(action='unknown')])
        path = self.root/'worker/loop.json'
        state = json.loads(path.read_text())
        state['pending'] = dict(kind='command', name='check', step=2)
        path.write_text(json.dumps(state))
        with self.assertRaisesRegex(ValueError, 'uncertain'):
            self.execute([], resume=True)

    def test_unreviewed_command_and_traversal_do_not_execute(self):
        for action in [dict(action='command', command='arbitrary shell'),
                       dict(action='edit', files=[dict(path='../escape', content='bad')])]:
            worker = self.root/'worker'
            if worker.exists():
                import shutil
                shutil.rmtree(worker)
            with self.assertRaises(ValueError):
                self.execute([action])
        self.assertFalse((self.root/'escape').exists())

    def test_input_drift_and_step_budget_do_not_reset_on_resume(self):
        self.settings['max_steps'] = 1
        result = self.execute([self.edit('count = 0\n')])
        self.assertEqual(result['status'], 'step_limit')
        self.assertEqual(self.execute([], resume=True)['steps'], 1)
        self.spec.write_text(json.dumps(dict(goal='Changed behavior')))
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.execute([], resume=True)

    def test_command_output_limit_is_retained_in_feedback(self):
        self.settings['commands']['noisy'] = [sys.executable, '-c', 'print("x"*100000)']
        result = self.execute([self.edit('count = 0\n'), dict(action='command', command='noisy'), dict(action='submit')])
        self.assertEqual(result['messages'][1]['observation']['status'], 'output_limit')
        self.assertLessEqual(len(result['messages'][1]['observation']['stdout']), 65536)

    def test_submitted_resume_detects_managed_source_drift(self):
        self.execute([self.edit('count = 0\n'), dict(action='submit')])
        (self.root/'worker/project/counter.py').write_text('count = 1\n')
        with self.assertRaisesRegex(ValueError, 'sources changed before return'):
            self.execute([], resume=True)


if __name__ == '__main__':
    unittest.main()
