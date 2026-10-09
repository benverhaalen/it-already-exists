"""Exercise copied helpers outside the checkout; not live harness activation."""
import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('package_rdd', ROOT / 'tools/package_rdd.py')
package = importlib.util.module_from_spec(spec)
spec.loader.exec_module(package)


class PackageTests(unittest.TestCase):
    def test_fresh_extracted_helpers_and_manifest_without_checkout_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            receipt = package.build(package.SOURCE, work / 'first.zip')
            package.build(package.SOURCE, work / 'second.zip')
            self.assertEqual((work / 'first.zip').read_bytes(), (work / 'second.zip').read_bytes())
            self.assertEqual(receipt['sha256'], hashlib.sha256((work / 'first.zip').read_bytes()).hexdigest())
            with zipfile.ZipFile(work / 'first.zip') as archive:
                archive.extractall(work / 'installed')
            skill = work / 'installed' / package.NAME
            manifest = json.loads((skill / 'package-manifest.json').read_text())
            self.assertEqual(manifest['inventory_version'], package.INVENTORY_VERSION)
            self.assertTrue((skill / 'LICENSE').is_file())
            for document in skill.rglob('*.md'):
                for target in re.findall(r'\]\(([^)]+)\)', document.read_text()):
                    path = target.split('#')[0]
                    if path and not re.match(r'[a-zA-Z][\w+.-]*:', path):
                        resolved = (document.parent / path).resolve()
                        self.assertTrue(resolved.is_relative_to(skill.resolve()), str(document))
                        self.assertTrue(resolved.exists(), str(document) + ': ' + target)
            for name, expected in manifest['files'].items():
                data = (skill / name).read_bytes()
                self.assertEqual(len(data), expected['bytes'])
                self.assertEqual(hashlib.sha256(data).hexdigest(), expected['sha256'])
            env = {'PATH': os.environ.get('PATH', ''), 'HOME': str(work / 'home'),
                   'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
            (work / 'home').mkdir()
            for helper in sorted((skill / 'scripts').glob('*.py')):
                if helper.name == 'process.py':  # import-only shared process primitive
                    continue
                result = subprocess.run([sys.executable, str(helper), '--help'], cwd=work,
                                        env=env, capture_output=True, text=True, timeout=15)
                self.assertEqual(result.returncode, 0, helper.name + ': ' + result.stderr)
            fixture = work / 'input.apk'
            with zipfile.ZipFile(fixture, 'w') as archive:
                archive.writestr('classes.dex', b'synthetic metadata fixture')
                archive.writestr('AndroidManifest.xml', b'not a decoded manifest')
            report = work / 'intake.json'
            result = subprocess.run([sys.executable, str(skill / 'scripts/apk_intake.py'),
                                     str(fixture), '--output', str(report)], cwd=work,
                                    env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            observed = json.loads(report.read_text())
            self.assertEqual(observed['input']['sha256'], hashlib.sha256(fixture.read_bytes()).hexdigest())
            for route in observed['next_inspection']:
                self.assertTrue((skill / route['catalog']).is_file())
            self.assertFalse(observed['bounds']['complete_payload_scan'])

    def test_unknown_files_links_and_existing_output_are_not_packaged(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            source = work / 'source'
            shutil.copytree(package.SOURCE, source, ignore=shutil.ignore_patterns('__pycache__'))
            output = work / 'package.zip'
            hidden = source / '.env'
            hidden.write_text('synthetic marker, not credentials')
            with self.assertRaisesRegex(ValueError, 'unreviewed'):
                package.build(source, output)
            self.assertFalse(output.exists())
            hidden.unlink()
            link = source / 'references/external.md'
            link.symlink_to(ROOT / 'README.md')
            with self.assertRaisesRegex(ValueError, 'non-regular'):
                package.build(source, output)
            link.unlink()
            package.build(source, output)
            before = output.read_bytes()
            with self.assertRaises(FileExistsError):
                package.build(source, output)
            self.assertEqual(output.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
