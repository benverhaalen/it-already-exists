"""Reviewed binary transport faults across persistent actions and resume.

Scripted inference tests the lifecycle, not a model's design judgment.
"""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/reference-driven-development/scripts'))
import assets
import coding_loop as loop
import repair


class AssetLoopTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.worker = self.root/'worker'
        self.spec = self.root/'spec.json'
        self.spec.write_text(json.dumps(dict(scope='owned', goal='Use the supplied logo and preserve its bytes')))
        self.originals = self.root/'originals'; self.originals.mkdir()
        self.data = b'\x89PNG\r\n\x1a\ntransport fixture, not a decoded-image fidelity claim'
        (self.originals/'logo.png').write_bytes(self.data)
        self.manifest = dict(scope='owned', reviewer='fixture asset reviewer', rights='Owned transport fixture',
            limits='Header/hash transport test, no visual quality claim', files=[dict(path='logo.png', kind='image',
                sha256=hashlib.sha256(self.data).hexdigest())])
        self.model = self.root/'model'; self.model.write_bytes(b'scripted inference')
        self.backend = ['/fake', '{model}', '{prompt}']
        self.settings = dict(commands={'read': [sys.executable, '-c',
            'from pathlib import Path; import hashlib; print(hashlib.sha256(Path("assets/logo.png").read_bytes()).hexdigest())']},
            max_steps=10, total_seconds=30, step_seconds=3, max_output_bytes=65536,
            max_context_bytes=1048576, max_files=5, max_content_bytes=65536)
        self.edit = dict(action='edit', files=[dict(path='index.html', content='<img src="assets/logo.png">')])

    def execute(self, actions, resume=False, repair_request=None):
        remaining, prompts = iter(actions), []
        def generate(argv, *args):
            prompts.append(Path(argv[-1]).read_text())
            return json.dumps(next(remaining))
        with patch.object(loop, 'run_backend', side_effect=generate) as backend:
            state = loop.execute(self.worker, self.spec, self.model, self.backend, self.settings, resume,
                asset_manifest=self.manifest, asset_root=None if resume else self.originals, repair=repair_request)
            backend.prompts = prompts
            return state, backend

    def test_whole_bytes_read_by_real_command_and_resume_without_originals(self):
        state, backend = self.execute([self.edit, dict(action='command', command='read'), dict(action='submit')])
        self.assertEqual(state['status'], 'submitted')
        self.assertEqual(state['messages'][1]['observation']['stdout'].strip(), self.manifest['files'][0]['sha256'])
        self.assertEqual((self.worker/'project/assets/logo.png').read_bytes(), self.data)
        context = backend.prompts[0]
        self.assertIn('assets/logo.png', context)
        self.assertNotIn(str(self.originals), context)
        self.assertNotIn('transport fixture, not a decoded', context)
        shutil.rmtree(self.originals)
        resumed, backend = self.execute([], True)
        self.assertEqual(resumed['steps'], 3)
        backend.assert_not_called()

    def test_reserved_namespace_rejects_edit_delete_and_case_alias(self):
        for action in [dict(action='edit', files=[dict(path='assets', content='replace directory')]),
                       dict(action='edit', files=[dict(path='Assets/new.css', content='bad')]),
                       dict(action='edit', delete=['assets/logo.png'])]:
            with self.subTest(action=action):
                if self.worker.exists(): shutil.rmtree(self.worker)
                with self.assertRaisesRegex(ValueError, 'namespace is reserved'):
                    self.execute([action])
                self.assertEqual((self.worker/'project/assets/logo.png').read_bytes(), self.data)

    def test_submitted_resume_rejects_missing_extra_changed_and_linked_assets(self):
        self.execute([self.edit, dict(action='submit')])
        path = self.worker/'project/assets/logo.png'
        for fault in ('missing', 'extra', 'changed', 'link', 'directory'):
            with self.subTest(fault=fault):
                path.chmod(0o644)
                if fault == 'missing': path.unlink()
                if fault == 'extra': (path.parent/'unreviewed.png').write_bytes(self.data)
                if fault == 'changed': path.write_bytes(self.data+b'drift')
                if fault == 'link': path.unlink(); path.symlink_to(self.originals/'logo.png')
                if fault == 'directory': (path.parent/'extra').mkdir()
                with self.assertRaises((ValueError, OSError)):
                    self.execute([], True)
                if path.is_symlink(): path.unlink()
                path.write_bytes(self.data)
                (path.parent/'unreviewed.png').unlink(missing_ok=True)
                if (path.parent/'extra').exists(): (path.parent/'extra').rmdir()

    def test_command_asset_mutation_remains_uncertain_and_is_not_replayed(self):
        self.settings['commands']['mutate'] = [sys.executable, '-c',
            'from pathlib import Path; p=Path("assets/logo.png"); p.chmod(0o644); p.write_bytes(b"drift")']
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            self.execute([self.edit, dict(action='command', command='mutate')])
        state = loop.load(self.worker/'loop.json')
        self.assertEqual(state['status'], 'uncertain_operation')
        self.assertEqual(state['pending']['kind'], 'command')
        with self.assertRaisesRegex(ValueError, 'uncertain'):
            self.execute([], True)

    def test_inference_drift_prevents_accepting_edit(self):
        def mutate(*args):
            path = self.worker/'project/assets/logo.png'
            path.chmod(0o644); path.write_bytes(self.data+b'drift')
            return json.dumps(self.edit)
        with patch.object(loop, 'run_backend', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'hash differs'):
                loop.execute(self.worker, self.spec, self.model, self.backend, self.settings,
                    asset_manifest=self.manifest, asset_root=self.originals)
        self.assertFalse((self.worker/'project/index.html').exists())
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            self.execute([], True)

    def test_preparation_scope_hash_and_combined_budget_reject_before_inference(self):
        for fault in ('scope', 'hash', 'files', 'bytes'):
            with self.subTest(fault=fault), patch.object(loop, 'run_backend') as backend:
                original_scope, original_hash = self.manifest['scope'], self.manifest['files'][0]['sha256']
                settings = self.settings.copy()
                if fault == 'scope': self.manifest['scope'] = 'wrong'
                if fault == 'hash': self.manifest['files'][0]['sha256'] = 'a'*64
                if fault == 'files': self.settings['max_files'] = 1
                if fault == 'bytes': self.settings['max_content_bytes'] = len(self.data)-1
                with self.assertRaises(ValueError): self.execute([])
                backend.assert_not_called()
                self.assertFalse(self.worker.exists())
                self.manifest['scope'], self.manifest['files'][0]['sha256'] = original_scope, original_hash
                self.settings = settings
        self.settings['max_files'] = 2
        self.settings['max_content_bytes'] = len(self.data)+2
        with self.assertRaisesRegex(ValueError, 'byte'):
            self.execute([self.edit])

    def test_manifest_drift_requires_new_handoff_and_directory_case_is_portable(self):
        self.execute([self.edit, dict(action='submit')])
        self.manifest['rights'] = 'Changed review'
        with self.assertRaisesRegex(ValueError, 'inputs changed'): self.execute([], True)
        self.manifest['files'] = [dict(path=path, kind='image', sha256='a'*64)
                                  for path in ('logos/a.png', 'Logos/b.png')]
        with self.assertRaisesRegex(ValueError, 'casing'): assets.review(self.manifest, 'owned')

    def test_external_repair_preserves_assets_and_drift_blocks_review_acceptance(self):
        state, _ = self.execute([self.edit, dict(action='submit')])
        artifact = self.worker/'project/index.html'
        report = dict(status='failed', contract_sha256='a'*64,
            candidate_artifact=hashlib.sha256(artifact.read_bytes()).hexdigest(),
            properties=[dict(id='alt', status='failed', reason='state_assertion', expected='Logo', actual='')])
        review = dict(approved=True, reviewer='independent evaluator', report_sha256=loop.digest(report))
        guidance = dict(scope='owned', behaviors=['Supply accessible Logo alternative text.'], review=dict(
            reviewer='behavior reviewer', implementation_independent=True, source_free=True,
            asset_rights=True, limits='Owned fixture only'))
        request = repair.prepare(report, review, guidance, 'index.html')
        (self.worker/'project/assets/extra.png').write_bytes(self.data)
        with self.assertRaisesRegex(ValueError, 'unexpected'): self.execute([], True, request)
        self.assertNotIn('repairs', loop.load(self.worker/'loop.json'))
        (self.worker/'project/assets/extra.png').unlink()
        repaired, _ = self.execute([dict(action='edit', files=[dict(path='index.html',
            content='<img src="assets/logo.png" alt="Logo">')]), dict(action='submit')], True, request)
        self.assertEqual(repaired['approved_assets'], state['approved_assets'])
        self.assertEqual(repaired['steps'], 4)
        self.assertEqual((self.worker/'project/assets/logo.png').read_bytes(), self.data)


if __name__ == '__main__':
    unittest.main()
