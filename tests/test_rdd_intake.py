"""Focused synthetic intake mechanics; no target scenarios or live acquisition."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
import intake
import rdd


class IntakeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()

    def test_regular_inventory_hashes_and_reference_record_is_compatible(self):
        (self.root / 'a.py').write_bytes(b'example')
        result = intake.intake(str(self.root), capabilities=['source-analysis'])
        inventory = result['reference']['inventory']
        self.assertTrue(inventory['complete_content_inventory'])
        self.assertEqual(inventory['entries'][1]['sha256'], hashlib.sha256(b'example').hexdigest())
        self.assertEqual(result['surface']['selected'], 'source')
        self.assertEqual(result['capabilities']['missing'], ['project-inspection'])
        self.assertFalse(result['readiness']['ready_for_behavioral_observation'])
        rdd.validate(result['reference_record'], {}, self.root / 'journal.jsonl')

    def test_no_symlink_or_fifo_reads(self):
        target = self.root / 'file'; target.write_text('bytes')
        (self.root / 'alias').symlink_to(target)
        os.mkfifo(self.root / 'fifo')
        result = intake.inventory(self.root)
        kinds = {e['path']: e['type'] for e in result['entries']}
        self.assertEqual(kinds['alias'], 'symlink')
        self.assertEqual(kinds['fifo'], 'special')
        self.assertFalse(result['complete_content_inventory'])
        with self.assertRaises(ValueError):
            intake.inventory(self.root / 'alias')

    def test_budgets_report_incomplete_without_absence_claim(self):
        (self.root / 'a').write_bytes(b'large')
        (self.root / 'nested').mkdir()
        (self.root / 'nested' / 'b').write_text('b')
        result = intake.inventory(self.root, max_file_bytes=2, max_depth=1)
        self.assertFalse(result['complete_content_inventory'])
        self.assertTrue(result['omissions'])
        bounded = intake.inventory(self.root, max_entries=1)
        self.assertEqual(len(bounded['entries']), 1)
        self.assertTrue(bounded['omissions'])

    def test_url_and_opaque_identity_do_not_fetch_and_surface_stays_uncertain(self):
        result = intake.intake('https://example.invalid/app', capabilities=['capture'])
        self.assertFalse(result['reference']['content_acquired'])
        self.assertEqual(result['surface']['basis'], 'locator hint')
        self.assertFalse(result['capabilities']['verified'])
        opaque = intake.intake('physical device on desk', identity=True, surface='physical')
        self.assertEqual(opaque['surface']['basis'], 'explicit')
        unknown = intake.intake('opaque target', identity=True)
        self.assertIsNone(unknown['surface']['selected'])
        with self.assertRaises(ValueError):
            intake.intake('https://user:secret@example.invalid')

    def test_all_declared_surfaces_route_without_claiming_observation(self):
        for surface in intake.SURFACES:
            result = intake.intake('fixture', identity=True, surface=surface)
            self.assertTrue(result['next_action'])
            self.assertFalse(result['readiness']['ready_for_behavioral_observation'])
        android = intake.intake('fixture.apk', identity=True)
        self.assertEqual(android['surface']['selected'], 'android')
        self.assertIn('scripts/apk_intake.py', android['next_action'])
        self.assertTrue((SCRIPTS / 'apk_intake.py').is_file())
        desktop = intake.intake('fixture.ipa', identity=True, surface='desktop')
        self.assertIn('iOS', ' '.join(desktop['platform_limits']))

    def test_cli_never_overwrites_existing_output(self):
        out = self.root / 'output.json'
        args = [sys.executable, str(SCRIPTS / 'intake.py'), 'reference', '--identity', '--surface', 'web', '--output', str(out)]
        first = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(json.loads(out.read_text())['surface']['selected'], 'web')
        second = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(second.returncode, 2)


if __name__ == '__main__':
    unittest.main()
