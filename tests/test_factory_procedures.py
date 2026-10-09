"""Exercise source admission, native class distinctions and cold resolution.

These are material/selection checks, not product or live procedure qualification.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/reference-driven-development/scripts/factory_procedures.py'
spec = importlib.util.spec_from_file_location('factory_procedures', SCRIPT)
procedures = importlib.util.module_from_spec(spec)
spec.loader.exec_module(procedures)


class ProcedureTests(unittest.TestCase):
    def test_exact_original_material_and_inactive_discovery(self):
        manifest, entries, _ = procedures.load()
        self.assertEqual(manifest['source']['revision'], 'ccb5507cec1546dc88135c1139c811e6c59115ba')
        self.assertEqual(len(entries), 132)
        self.assertEqual(sum(item['bytes'] for item in entries.values()), 666023)
        self.assertEqual(entries['pstack/LICENSE']['sha256'],
                         'bc957ca6bee02792566a1a028d105e02e247c6e77cf057061674273da77b200e')
        self.assertEqual(entries['pstack/skills/poteto-mode/playbooks/feature.md']['sha256'],
                         '3a62cc4a8cbcf144bb9dd05f05420a15be0d38b784d3b141bb730a5852f50a62')
        self.assertEqual(list(procedures.VENDOR.rglob('SKILL.md')), [])
        for item in entries.values():
            data = (procedures.VENDOR / item['installed_path']).read_bytes()
            self.assertEqual(item['git_blob_sha1'],
                             hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest())

    def test_selected_classes_preserve_output_and_authority_differences(self):
        creation = procedures.select('verification-create', ['control-examples'])
        upkeep = procedures.select('verification-maintain')
        diagnosis = procedures.select('trace-diagnosis')
        feature = procedures.select('feature')
        self.assertTrue(any('one mapped feature' in item for item in creation['required_outputs']))
        self.assertTrue(any('all-feature' in item for item in upkeep['required_outputs']))
        self.assertIn('verification control directory only', upkeep['write_scope'])
        self.assertTrue(any('unpaired' in item for item in diagnosis['required_outputs']))
        self.assertTrue(any('four-part throughput' in item for item in feature['required_outputs']))
        self.assertIn('pstack/skills/architect/references/runner-prompt.md',
                      [item['original_path'] for item in feature['ordered_reads']])
        self.assertNotEqual(creation['source_closure_sha256'], upkeep['source_closure_sha256'])
        self.assertFalse(feature['limits']['procedure_applied'])
        self.assertFalse(feature['limits']['upstream_commands_executed'])
        self.assertIn('native-authority', [item['id'] for item in feature['adaptations']])
        self.assertIn('native-models', [item['id'] for item in feature['adaptations']])
        self.assertLess(sum(item['bytes'] for item in feature['ordered_reads']), 666023)
        with self.assertRaisesRegex(ValueError, 'unknown task class'):
            procedures.select('implicit-shipping')
        with self.assertRaisesRegex(ValueError, 'unknown conditional'):
            procedures.select('feature', ['automatically-install-global-rules'])

    def test_original_relative_names_resolve_to_exact_inert_bytes(self):
        origin = 'pstack/skills/architect/SKILL.md'
        resolved = procedures.resolve(origin, 'references/runner-prompt.md')
        self.assertTrue(resolved['installed_path'].endswith('runner-prompt.md.source'))
        self.assertTrue(Path(resolved['file']).is_file())
        self.assertEqual(resolved['sha256'], hashlib.sha256(Path(resolved['file']).read_bytes()).hexdigest())
        missing = procedures.resolve(origin, 'https://example.org/uninspected')
        self.assertFalse(missing['fetched'])
        self.assertFalse(missing['qualified'])
        with self.assertRaisesRegex(ValueError, 'not retained'):
            procedures.resolve(origin, 'references/nonexistent.md')
        with self.assertRaisesRegex(ValueError, 'unsafe'):
            procedures.resolve(origin, '../../../../../../outside')

    def test_changed_missing_extra_active_and_linked_sources_reject(self):
        for defect in ('changed', 'missing', 'extra', 'active', 'symlink'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory:
                vendor = Path(directory) / 'pstack'
                shutil.copytree(procedures.VENDOR, vendor)
                original = vendor / 'sources/pstack/skills/poteto-mode/playbooks/feature.md.source'
                if defect == 'changed':
                    original.write_bytes(original.read_bytes() + b'changed')
                elif defect == 'missing':
                    original.unlink()
                elif defect == 'extra':
                    (vendor / 'unreviewed.py').write_text('print("not authorized")')
                elif defect == 'active':
                    (original.parent / 'SKILL.md').write_text('---\nname: accidental\n---\n')
                else:
                    original.unlink()
                    original.symlink_to(procedures.VENDOR / 'sources/pstack/LICENSE')
                with self.assertRaises((ValueError, OSError)):
                    procedures.select('feature', vendor=vendor)

    def test_unretained_conditional_dependency_rejects_before_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            vendor = Path(directory) / 'pstack'
            shutil.copytree(procedures.VENDOR, vendor)
            path = vendor / 'manifest.json'
            manifest = json.loads(path.read_text())
            manifest['conditional_modules']['grounding']['read_paths'].append('pstack/skills/missing/SKILL.md')
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'unretained procedure dependency'):
                procedures.select('feature', vendor=vendor)

    def test_cold_copied_helper_resolves_without_checkout_imports_or_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            installed = Path(directory) / 'skill'
            (installed / 'scripts').mkdir(parents=True)
            shutil.copy2(SCRIPT, installed / 'scripts/factory_procedures.py')
            shutil.copytree(procedures.VENDOR, installed / 'upstream/pstack')
            before = sorted(str(path.relative_to(installed)) for path in installed.rglob('*'))
            result = subprocess.run([sys.executable, str(installed / 'scripts/factory_procedures.py'),
                                     'select', 'bug-fix', '--include', 'grounding'], cwd=directory,
                                    capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            selection = json.loads(result.stdout)
            self.assertFalse(selection['limits']['procedure_applied'])
            for item in selection['ordered_reads']:
                self.assertTrue(Path(item['file']).resolve().is_relative_to(installed.resolve()))
                self.assertTrue(Path(item['file']).is_file())
            self.assertEqual(before, sorted(str(path.relative_to(installed)) for path in installed.rglob('*')))
            read = subprocess.run([sys.executable, str(installed / 'scripts/factory_procedures.py'),
                                   'read', 'pstack/skills/poteto-mode/playbooks/bug-fix.md'], cwd=directory,
                                  capture_output=True, timeout=10)
            self.assertEqual(read.returncode, 0, read.stderr)
            self.assertEqual(read.stdout, (installed / 'upstream/pstack/sources/pstack/skills/poteto-mode/playbooks/bug-fix.md.source').read_bytes())


if __name__ == '__main__':
    unittest.main()
