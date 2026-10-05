"""Hosted-tool drift rejection and separate generated-code execution routing."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/reference-driven-development/scripts'))
import coding_loop
import frontier_worker as frontier


class FrontierTests(unittest.TestCase):
    def test_nested_asset_mount_is_explicit_and_requires_qualification(self):
        from types import SimpleNamespace
        image = 'sha256:'+'a'*64
        with tempfile.TemporaryDirectory() as directory, patch.object(frontier.cleanroom, 'image_id'), \
                patch.object(frontier.cleanroom, 'invoke', return_value=SimpleNamespace(returncode=0)), \
                patch.object(frontier, 'run', return_value=dict(status='completed', exit_code=0,
                    elapsed=.01, stdout=b'checked', stderr=b'')) as execution:
            project = Path(directory).resolve()
            (project/'assets').mkdir()
            runner = frontier.DockerCommands(image, protected_assets=True)
            runner.qualified = True
            with self.assertRaisesRegex(ValueError, 'nested asset boundary'):
                runner.run(['node', '--version'], project, 1, 1024)
            execution.assert_not_called()
            runner.assets_qualified = True
            runner.asset_project = project
            runner.run(['node', '--version'], project, 1, 1024)
            argv = execution.call_args.args[0]
            self.assertIn('type=bind,src='+str(project/'assets')+',dst=/work/assets,readonly,bind-recursive=disabled', argv)
            self.assertNotIn('type=bind,src='+str(project)+',dst=/spec,readonly', argv)
            self.assertTrue(runner.receipts[-1]['approved_assets_readonly'])
            self.assertEqual(runner.identity['asset_boundary'], 'nested-readonly/no-recursive-mounts/v1')
            other = project/'other'; other.mkdir()
            with self.assertRaisesRegex(ValueError, 'another project'):
                runner.run(['node', '--version'], other, 1, 1024)

    def test_failed_asset_requalification_invalidates_old_success(self):
        runner = frontier.DockerCommands.__new__(frontier.DockerCommands)
        runner.protected_assets, runner.assets_qualified = True, True
        runner.asset_project = Path('/prior-project')
        runner.receipts = [dict(kind='command')]
        with patch.object(runner, 'run', return_value=dict(status='completed', exit_code=31)):
            with self.assertRaisesRegex(ValueError, 'qualification failed'):
                runner.qualify_assets(Path('/different-project'), dict(files=[dict(path='logo.png',sha256='a'*64)]))
        self.assertFalse(runner.assets_qualified)
        self.assertIsNone(runner.asset_project)
        self.assertFalse(runner._qualifying_assets)

    def stream(self):
        return [dict(type='system', subtype='init', model='approved', tools=[], mcp_servers=[], skills=[], plugins=[]),
                dict(type='assistant', message=dict(content=[dict(type='text', text='{"action":"submit"}')])),
                dict(type='result', subtype='success', is_error=False, num_turns=1,
                     result='{"action":"submit"}', usage=dict(server_tool_use=dict(web_search_requests=0)))]

    def parse(self, events, max_bytes=1024):
        return frontier.parse_stream('\n'.join(json.dumps(e) for e in events).encode(), 'approved', max_bytes)

    def test_one_tool_free_generation_preserves_usage(self):
        events = self.stream()
        events.insert(1, dict(type='system', subtype='thinking_tokens', thinking_tokens=17))
        raw, receipt = self.parse(events)
        self.assertEqual(json.loads(raw), dict(action='submit'))
        raw, receipt = self.parse(self.stream())
        self.assertEqual(json.loads(raw), dict(action='submit'))
        self.assertEqual(receipt['model'], 'approved')
        self.assertEqual(receipt['tools'], [])

    def test_tool_retrieval_custom_context_and_model_drift_are_rejected(self):
        changes = [('tools', ['Read']), ('mcp_servers', ['reference-retrieval']),
                   ('skills', ['source-bearing-skill']), ('model', 'fallback-model'),
                   ('plugins', [dict(path='/analyst/plugin', name='custom')])]
        for field, value in changes:
            with self.subTest(field=field):
                events = self.stream(); events[0][field] = value
                with self.assertRaises(ValueError): self.parse(events)
        events = self.stream()
        events[1]['message']['content'] = [dict(type='tool_use', name='Read', input=dict(path='/reference'))]
        with self.assertRaisesRegex(ValueError, 'tool'): self.parse(events)
        events = self.stream(); events[-1]['usage']['server_tool_use']['web_search_requests'] = 1
        with self.assertRaisesRegex(ValueError, 'server tools'): self.parse(events)

    def test_failure_truncation_multiple_results_and_oversized_action_are_not_success(self):
        for modify in (lambda e: e.pop(), lambda e: e.append(copy.deepcopy(e[-1])),
                       lambda e: e[-1].update(is_error=True), lambda e: e[-1].update(num_turns=2),
                       lambda e: e[-1].update(result='{"action":"submit","action":"edit"}')):
            events = self.stream(); modify(events)
            with self.assertRaises(ValueError): self.parse(events)
        with self.assertRaisesRegex(ValueError, 'bound'): self.parse(self.stream(), max_bytes=2)
        events = self.stream(); events.insert(1, dict(type='system', subtype='hook_started'))
        with self.assertRaisesRegex(ValueError, 'unexpected'): self.parse(events)

    def test_hosted_loop_needs_no_weights_and_cannot_default_to_host_commands(self):
        class Inference:
            identity = dict(provider='scripted-transport-test')
            def __init__(self): self.prompts = []
            def generate(self, prompt, schema, timeout, max_bytes):
                self.prompts.append(prompt)
                actions = [dict(action='edit', files=[dict(path='counter.js', content='let count = 0;\n')]),
                           dict(action='command', command='check'), dict(action='submit')]
                return json.dumps(actions[len(self.prompts)-1])
        class Boundary:
            identity = dict(image='scripted-boundary-test')
            def __init__(self): self.calls = []
            def run(self, argv, cwd, **kwargs):
                self.calls.append((argv, cwd))
                return dict(status='completed', exit_code=0, stdout=b'checked', stderr=b'', elapsed=.01)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            spec = root/'spec.json'; spec.write_text(json.dumps(dict(goal='Counter behavior')))
            settings = dict(commands={'check': ['node', '--check', 'counter.js']}, max_steps=3,
                total_seconds=10, step_seconds=3, max_output_bytes=4096, max_context_bytes=65536,
                max_files=3, max_content_bytes=4096)
            provider, boundary = Inference(), Boundary()
            with self.assertRaisesRegex(ValueError, 'separate execution'):
                coding_loop.execute(root/'denied', spec, None, None, settings, inference=provider)
            self.assertFalse((root/'denied').exists())
            state = coding_loop.execute(root/'worker', spec, None, None, settings,
                                        inference=provider, command_runner=boundary)
            self.assertEqual(state['status'], 'submitted')
            self.assertEqual(boundary.calls[0][0], settings['commands']['check'])
            self.assertIn('checked', provider.prompts[-1])
            boundary.identity = dict(image='changed-image')
            with self.assertRaisesRegex(ValueError, 'changed'):
                coding_loop.execute(root/'worker', spec, None, None, settings, resume=True,
                                    inference=provider, command_runner=boundary)

    def test_rejected_response_retains_attempt_receipt_without_returning_diagnostics(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory)/'fake-cli'; executable.write_bytes(b'fake cli identity')
            provider = frontier.ClaudeInference.__new__(frontier.ClaudeInference)
            provider.executable, provider.model = executable, 'approved'
            provider.identity = dict(executable_sha256=hashlib.sha256(executable.read_bytes()).hexdigest())
            provider.receipts = []
            persisted = []
            provider.receipt_sink = lambda: persisted.append(copy.deepcopy(provider.receipts))
            events = self.stream(); events[0]['tools'] = ['Read']
            response = dict(status='completed', exit_code=0, elapsed=.1,
                            stdout='\n'.join(json.dumps(e) for e in events).encode(), stderr=b'private account diagnostics')
            with patch.object(frontier, 'run', return_value=response) as call:
                with self.assertRaisesRegex(ValueError, 'exposed tools'):
                    provider.generate('Behavior only', {}, 2, 4096)
            self.assertEqual(persisted[0][0]['status'], 'pending')
            self.assertEqual(persisted[-1][0]['status'], 'response_rejected')
            self.assertNotIn('private account', json.dumps(provider.receipts))
            argv = call.call_args.args[0]
            self.assertEqual(argv[argv.index('--tools')+1], '')
            self.assertIn('--safe-mode', argv)
            self.assertNotIn('--resume', argv)


if __name__ == '__main__':
    unittest.main()
