"""Native skill release lifecycle in isolated homes; no models or live globals."""
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('factory_install', ROOT / 'tools/install_factory.py')
factory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(factory)


def source_fixture(root):
    shutil.copytree(factory.package.SOURCE, root, ignore=shutil.ignore_patterns('__pycache__'))
    return root


class InstallationTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.work = Path(self.scratch.name)
        self.home = self.work / 'home'
        self.home.mkdir()
        self.store = factory.default_store(self.home)
        self.source = source_fixture(self.work / 'source')
        self.addCleanup(self.make_releases_writable)

    def make_releases_writable(self):
        if self.store.exists():
            for path in self.store.rglob('*'):
                if not path.is_symlink():
                    os.chmod(path, 0o755 if path.is_dir() else 0o644)

    def cli(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(ROOT / 'tools/install_factory.py'),
                                 '--home', str(self.home), *args], cwd=self.work,
                                env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                                text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return json.loads(result.stdout) if result.stdout else result.stderr

    def stage(self):
        return factory.stage(self.store, self.source)['release']

    def source_pointers(self):
        for path in factory.roots(self.home).values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(self.source)

    def rewrite_archive(self, archive, omit=(), edition='unchanged', amend=None):
        with zipfile.ZipFile(archive) as original:
            files = {entry.filename: original.read(entry) for entry in original.infolist()}
        prefix = factory.NAME + '/'
        manifest_path = prefix + 'package-manifest.json'
        manifest = json.loads(files[manifest_path])
        for name in omit:
            files.pop(prefix + name)
            manifest['files'].pop(name)
        if edition == 'legacy':
            manifest.pop('inventory_version')
        elif edition != 'unchanged':
            manifest['inventory_version'] = edition
        if amend:
            amend(manifest)
        files[manifest_path] = json.dumps(manifest).encode()
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w') as zipped:
            for name, data in files.items():
                zipped.writestr(name, data)
        return payload.getvalue()

    def test_legacy_inventory_survives_current_source_update_and_rollback(self):
        archive = self.work / 'current.zip'
        factory.package.build(self.source, archive)
        legacy = self.work / 'legacy.zip'
        legacy.write_bytes(self.rewrite_archive(
            archive, omit=['scripts/firestore_query_scenario.py'], edition='legacy'))
        with self.assertRaisesRegex(ValueError, 'requires current factory inventory'):
            factory.stage(self.store, archive=legacy)
        # Stage under the original admission edition, then inspect/update using
        # today's edition. Retained inspection must not reset initial admission.
        with mock.patch.object(factory.package, 'INVENTORY_VERSION', 1):
            first = factory.stage(self.store, archive=legacy)['release']
        receipt_path = self.store / 'releases' / first / 'receipt.json'
        # Early receipts also predate the edition field; retain that input case.
        receipt = json.loads(receipt_path.read_text())
        receipt.pop('inventory_version')
        os.chmod(receipt_path, 0o644)
        receipt_path.write_text(json.dumps(receipt))
        factory.activate(self.home, self.store, first, self.source)
        observed = factory.doctor(self.home, self.store)
        self.assertEqual(observed['errors'], [])
        self.assertEqual(observed['content'], 'verified_complete_inventory')
        self.assertEqual(observed['inventory_version'], 1)
        self.assertEqual(observed['current_inventory_version'], 2)
        second = self.stage()
        factory.activate(self.home, self.store, second, self.source)
        self.assertEqual(factory.doctor(self.home, self.store)['inventory_version'], 2)
        factory.rollback(self.store)
        self.assertEqual(factory.doctor(self.home, self.store)['active_release'], first)
        self.assertEqual(factory.doctor(self.home, self.store)['errors'], [])
        self.assertEqual(legacy.read_bytes(), (self.store / 'releases' / first / 'capsule.zip').read_bytes())
        self.assertNotIn('inventory_version', json.loads(receipt_path.read_text()))

    def test_editions_reject_self_consistent_incomplete_and_unknown_archives(self):
        archive = self.work / 'current.zip'
        factory.package.build(self.source, archive)
        missing_helper = ['scripts/firestore_query_scenario.py']
        cases = [
            ([], 999), ([], True), ([], None), ([], 1),
            (missing_helper, 2),
            (missing_helper + ['scripts/fixtures/flutter_abi/TONIC-LICENSE'], 'legacy'),
            (['scripts/workflow.py'], 'legacy'),
        ]
        for omit, edition in cases:
            with self.subTest(omit=omit, edition=edition):
                payload = self.rewrite_archive(archive, omit=omit, edition=edition)
                with self.assertRaisesRegex(ValueError, 'inventory'):
                    factory.archive_inventory(payload)
        # The untagged complete current capsule is also a retained early input.
        _, manifest = factory.archive_inventory(self.rewrite_archive(archive, edition='legacy'))
        self.assertEqual(factory.package.reviewed_inventory(manifest)[0], 2)

    def test_current_source_requires_current_helper_and_receipt_edition_agrees(self):
        helper = self.source / 'scripts/firestore_query_scenario.py'
        data = helper.read_bytes()
        helper.unlink()
        with self.assertRaisesRegex(ValueError, 'incomplete portable skill'):
            self.stage()
        helper.write_bytes(data)
        release = self.stage()
        receipt_path = self.store / 'releases' / release / 'receipt.json'
        receipt = json.loads(receipt_path.read_text())
        receipt['inventory_version'] = 1
        os.chmod(receipt_path, 0o644)
        receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'receipt inventory mismatch'):
            factory.inspect_release(self.store, release)

    def test_malformed_metadata_reports_drift_instead_of_crashing(self):
        release = self.stage()
        factory.activate(self.home, self.store, release, self.source)
        receipt_path = self.store / 'releases' / release / 'receipt.json'
        receipt = json.loads(receipt_path.read_text())
        os.chmod(receipt_path, 0o644)
        for invalid in (None, [], {**receipt, 'files': float(receipt['files'])},
                        {**receipt, 'schema_version': True}):
            with self.subTest(receipt=invalid):
                receipt_path.write_text(json.dumps(invalid))
                observed = factory.doctor(self.home, self.store)
                self.assertEqual(observed['content'], 'drift_or_missing')
                self.assertIn('release receipt mismatch', observed['errors'])
                self.assertEqual(factory.load_state(self.store)['active_release'], release)
        receipt_path.write_text(json.dumps(receipt))
        archive = self.store / 'releases' / release / 'capsule.zip'
        changes = (
            lambda m: m.update(schema_version=True),
            lambda m: m['files']['SKILL.md'].update(bytes=float(m['files']['SKILL.md']['bytes'])),
            lambda m: m['files'].update({'SKILL.md': None}),
        )
        for amend in changes:
            with self.assertRaises(ValueError):
                factory.archive_inventory(self.rewrite_archive(archive, amend=amend))

    def test_staging_is_deterministic_complete_and_does_not_activate(self):
        first = self.stage()
        second = self.stage()
        self.assertEqual(first, second)
        self.assertFalse(any(path.exists() for path in factory.roots(self.home).values()))
        root = self.store / 'releases' / first
        self.assertEqual(factory.digest((root / 'capsule.zip').read_bytes()), first)
        self.assertTrue((root / factory.NAME / 'scripts/factory.py').is_file())
        self.assertTrue((root / factory.NAME / 'references/factory.md').is_file())
        self.assertEqual(factory.inspect_release(self.store, first)['activation'].split(';')[0], 'staged_only')

    def test_normal_cli_install_update_rollback_and_remove_preserve_source_and_overlay(self):
        self.source_pointers()
        originals = {}
        for host, path in factory.policy_roots(self.home).items():
            path.parent.mkdir(parents=True, exist_ok=True)
            originals[host] = b'Personal instructions\n\nKeep native settings.\n'
            path.write_bytes(originals[host])
            os.chmod(path, 0o640)
        overlay = self.home / '.config/it-already-exists/factory/personal.md'
        overlay.parent.mkdir(parents=True)
        overlay.write_text('Personal overlay stays private.\n')
        installed = self.cli('install', '--source', str(self.source), '--enable-policy')
        first = installed['active_release']
        self.assertEqual(installed['model_calls'], 0)
        self.assertEqual(installed['content'], 'verified_complete_inventory')
        for host, details in installed['hosts'].items():
            self.assertEqual(details['installation'], 'owned_pointer_installed')
            self.assertEqual(details['policy'], 'owned_block_enabled')
            self.assertEqual(details['current_session_activation'], 'not_demonstrated')
            self.assertEqual(factory.policy_roots(self.home)[host].read_bytes().count(factory.START), 1)
            self.assertEqual(factory.policy_roots(self.home)[host].stat().st_mode & 0o777, 0o640)
        (self.source / 'SKILL.md').write_text((self.source / 'SKILL.md').read_text() + '\nRevision two.\n')
        updated = self.cli('install', '--source', str(self.source), '--enable-policy')
        second = updated['active_release']
        self.assertNotEqual(first, second)
        self.assertTrue((self.store / 'releases' / first).is_dir())
        rolled = self.cli('rollback')
        self.assertEqual(rolled['active_release'], first)
        self.cli('remove')
        for path in factory.roots(self.home).values():
            self.assertEqual(os.readlink(path), str(self.source))
        for host, path in factory.policy_roots(self.home).items():
            self.assertEqual(path.read_bytes(), originals[host])
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
        self.assertEqual(overlay.read_text(), 'Personal overlay stays private.\n')
        self.assertTrue((self.store / 'releases' / second).is_dir())

    def test_exact_source_link_only_arbitrary_links_and_directories_are_untouched(self):
        first = self.stage()
        paths = factory.roots(self.home)
        paths['codex'].parent.mkdir(parents=True)
        unowned = self.work / 'unowned'
        unowned.mkdir()
        paths['codex'].symlink_to(unowned)
        with self.assertRaisesRegex(ValueError, 'unowned skill symlink'):
            factory.activate(self.home, self.store, first, self.source)
        self.assertFalse(paths['claude'].exists())
        self.assertEqual(os.readlink(paths['codex']), str(unowned))
        paths['codex'].unlink()
        paths['codex'].mkdir()
        (paths['codex'] / 'user.md').write_text('Keep me')
        with self.assertRaisesRegex(ValueError, 'unowned skill collision'):
            factory.activate(self.home, self.store, first, self.source)
        self.assertEqual((paths['codex'] / 'user.md').read_text(), 'Keep me')

    def test_release_added_file_or_directory_drift_blocks_update_and_doctor(self):
        first = self.stage()
        factory.activate(self.home, self.store, first, self.source)
        skill = self.store / 'releases' / first / factory.NAME
        os.chmod(skill, 0o755)
        added = skill / 'unexpected.md'
        added.write_text('New discovery surface')
        self.assertTrue(factory.doctor(self.home, self.store)['errors'])
        (self.source / 'SKILL.md').write_text('Second')
        second = self.stage()
        with self.assertRaisesRegex(ValueError, 'content/discovery drift'):
            factory.activate(self.home, self.store, second, self.source)
        self.assertEqual(factory.load_state(self.store)['active_release'], first)
        added.unlink()
        (skill / 'unexpected-directory').mkdir()
        with self.assertRaisesRegex(ValueError, 'content/discovery drift'):
            factory.inspect_release(self.store, first)

    def test_remove_preserves_new_global_content_but_refuses_owned_block_drift(self):
        self.cli('install', '--source', str(self.source), '--enable-policy')
        policies = factory.policy_roots(self.home)
        for path in policies.values():
            path.write_bytes(path.read_bytes() + b'\nNew user instruction.\n')
        factory.remove(self.store)
        for path in policies.values():
            self.assertIn(b'New user instruction.', path.read_bytes())
            self.assertNotIn(factory.START, path.read_bytes())
        self.cli('install', '--source', str(self.source), '--enable-policy')
        path = policies['codex']
        path.write_bytes(path.read_bytes().replace(b'Keep simple tasks direct.', b'Changed owned text.'))
        pointers = {host: os.readlink(path) for host, path in factory.roots(self.home).items()}
        with self.assertRaisesRegex(ValueError, 'managed policy drift'):
            factory.remove(self.store)
        self.assertEqual(pointers, {host: os.readlink(path) for host, path in factory.roots(self.home).items()})

    def test_owned_pointer_drift_refuses_remove_and_preserves_user_link(self):
        first = self.stage()
        factory.activate(self.home, self.store, first, self.source)
        path = factory.roots(self.home)['claude']
        path.unlink()
        path.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, 'owned skill pointer drift'):
            factory.remove(self.store)
        self.assertEqual(os.readlink(path), str(self.source))

    def test_interrupted_multi_target_activation_can_complete_or_rollback(self):
        for action in ('complete', 'rollback'):
            with self.subTest(action=action):
                first = self.stage()
                real_apply = factory.apply_change
                count = 0

                def interrupted(change, reverse=False):
                    nonlocal count
                    count += 1
                    if count == 2:
                        raise OSError('Synthetic interruption before second target')
                    real_apply(change, reverse)

                with mock.patch.object(factory, 'apply_change', interrupted):
                    with self.assertRaisesRegex(OSError, 'Synthetic interruption'):
                        factory.activate(self.home, self.store, first, self.source, True)
                self.assertEqual(factory.doctor(self.home, self.store)['maintenance'], 'pending_recovery')
                with self.assertRaisesRegex(ValueError, 'pending maintenance'):
                    factory.activate(self.home, self.store, first, self.source)
                factory.recover(self.store, action)
                self.assertEqual(factory.doctor(self.home, self.store)['maintenance'], 'idle')
                if action == 'complete':
                    self.assertEqual(factory.load_state(self.store)['active_release'], first)
                    self.assertTrue(all(path.is_symlink() for path in factory.roots(self.home).values()))
                    factory.remove(self.store)
                else:
                    self.assertFalse(any(path.exists() for path in factory.roots(self.home).values()))
                self.assertTrue((self.store / 'releases' / first).is_dir())

    def test_unknown_state_version_is_not_rewritten(self):
        self.store.mkdir(parents=True)
        path = self.store / 'installation.json'
        text = '{"schema_version": 999, "package": "reference-driven-development"}\n'
        path.write_text(text)
        with self.assertRaisesRegex(ValueError, 'unsupported installation state'):
            factory.load_state(self.store)
        self.assertEqual(path.read_text(), text)

    def test_archive_accepts_verified_closure_and_rejects_extra_entry(self):
        archive = self.work / 'skill.zip'
        factory.package.build(self.source, archive)
        receipt = factory.stage(self.store, archive=archive)
        self.assertIsNone(receipt['source'])
        payload = io.BytesIO()
        with zipfile.ZipFile(payload, 'w') as zipped:
            with zipfile.ZipFile(archive) as original:
                for entry in original.infolist():
                    zipped.writestr(entry, original.read(entry))
            zipped.writestr(factory.NAME + '/../outside', 'Synthetic')
        with self.assertRaisesRegex(ValueError, 'unsafe package path'):
            factory.archive_inventory(payload.getvalue())

    def test_vendor_original_bytes_license_and_inventory_are_required(self):
        vendor = self.source / 'upstream/pstack'
        manifest = json.loads((vendor / 'manifest.json').read_text())
        first = self.stage()
        self.assertTrue((self.store / 'releases' / first / factory.NAME / 'upstream/pstack/sources/pstack/LICENSE').is_file())
        (vendor / manifest['source_files'][1]['installed_path']).write_text('Changed procedure')
        with self.assertRaisesRegex(ValueError, 'upstream source digest mismatch'):
            self.stage()

    def test_required_dependency_license_and_unlisted_public_content_block_staging(self):
        for relative in ('scripts/workflow.py', 'scripts/rdd.py', 'scripts/fixtures/flutter_abi/TONIC-LICENSE'):
            with self.subTest(relative=relative):
                path = self.source / relative
                data = path.read_bytes()
                path.unlink()
                with self.assertRaisesRegex(ValueError, 'incomplete portable skill'):
                    self.stage()
                path.write_bytes(data)
        extra = self.source / 'references/private-user-project.md'
        extra.write_text('Synthetic unreviewed export marker; no private data')
        with self.assertRaisesRegex(ValueError, 'unreviewed package entry'):
            self.stage()
        self.assertFalse(any(path.exists() for path in factory.roots(self.home).values()))

    def test_wrong_source_revision_blocks_package_and_recovery_rechecks_destination(self):
        path = self.source / 'upstream/pstack/manifest.json'
        original = path.read_bytes()
        manifest = json.loads(original)
        manifest['source']['revision'] = 'a' * 40
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'unsupported upstream identity'):
            self.stage()
        path.write_bytes(original)
        first = self.stage()
        real_apply = factory.apply_change
        count = 0

        def interrupted(change, reverse=False):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('Synthetic interruption')
            real_apply(change, reverse)

        with mock.patch.object(factory, 'apply_change', interrupted):
            with self.assertRaises(OSError):
                factory.activate(self.home, self.store, first, self.source)
        skill = self.store / 'releases' / first / factory.NAME
        os.chmod(skill, 0o755)
        (skill / 'unexpected.md').write_text('Synthetic added discovery')
        with self.assertRaisesRegex(ValueError, 'content/discovery drift'):
            factory.recover(self.store, 'complete')
        self.assertTrue(factory.load_state(self.store).get('pending'))
        self.assertFalse(factory.roots(self.home)['claude'].exists())
        factory.recover(self.store, 'rollback')
        self.assertFalse(factory.roots(self.home)['codex'].exists())

    def test_concurrent_creation_of_absent_policy_is_preserved_and_blocks_replacement(self):
        first = self.stage()
        path = factory.policy_roots(self.home)['codex']
        real_atomic = factory.atomic_file

        def concurrent(path_arg, data, expected=factory.UNSPECIFIED, mode=0o600):
            if Path(path_arg) == path and not path.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'Concurrent new personal instructions\n')
            return real_atomic(path_arg, data, expected, mode)

        with mock.patch.object(factory, 'atomic_file', concurrent):
            with self.assertRaisesRegex(ValueError, 'concurrent file change'):
                factory.activate(self.home, self.store, first, self.source, True)
        self.assertEqual(path.read_bytes(), b'Concurrent new personal instructions\n')
        factory.recover(self.store, 'rollback')
        self.assertEqual(path.read_bytes(), b'Concurrent new personal instructions\n')


if __name__ == '__main__':
    unittest.main()
