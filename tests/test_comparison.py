"""Independent, seeded defects and evidence failures, not implementation mirrors."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]/'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
import comparison as c
try:
    from PIL import Image
except ImportError:
    Image = None


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.contract = dict(properties=[dict(id='persistent_count', kind='state', observation='reopened', path=['count']),
                                         dict(id='journey', kind='trajectory'),
                                         dict(id='latency', kind='duration', observation='reopened', start='initial', tolerance=.1)])
        self.reference = self.packet('original', 'a'*64)
        self.candidate = self.packet('candidate', 'b'*64)

    def packet(self, run_id, artifact):
        return dict(run_id=run_id, artifact_sha256=artifact, contract_sha256=c.canonical(self.contract),
                    fixture='empty account', journey='increment then reopen', timestamp_basis='host_monotonic_seconds',
                    observations=[dict(id='initial', run_id=run_id, time=100, state={'count': 0}),
                                  dict(id='reopened', run_id=run_id, time=101, state={'count': 1})])

    def compare(self):
        for p in (self.reference, self.candidate):
            p['contract_sha256'] = c.canonical(self.contract)
        return c.compare(self.contract, self.reference, self.candidate, self.root, self.root)

    def image(self, name, color=(0, 0, 0, 255), size=(10, 10), edit=None):
        image = Image.new('RGBA', size, color)
        if edit:
            for position, value in edit:
                image.putpixel(position, value)
        path = self.root/name
        image.save(path)
        return dict(path=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest())

    def visual(self, **rule):
        self.contract = dict(properties=[dict(id='critical_button', kind='pixels', observation='reopened', **rule)])
        self.reference['observations'][-1]['image'] = self.image('original.png')
        self.candidate['observations'][-1]['image'] = self.image('candidate.png')

    def test_complete_case_and_seeded_persistence_defect(self):
        # The source and candidate use unrelated absolute clock origins.
        for f in self.candidate['observations']:
            f['time'] += 4000
        self.assertEqual(self.compare()['status'], 'passed')
        self.candidate['observations'][-1]['state']['count'] = 0
        report = self.compare()
        self.assertEqual(report['status'], 'failed')
        self.assertEqual([p['id'] for p in report['properties'] if p['status'] == 'failed'], ['persistent_count'])

    def test_missing_field_is_not_tested_and_boolean_is_not_count(self):
        self.candidate['observations'][-1]['state'] = {}
        self.assertEqual(self.compare()['status'], 'not_tested')
        self.candidate['observations'][-1]['state'] = {'count': True}
        self.assertEqual(self.compare()['status'], 'failed')

    def test_mixed_branch_cannot_pass_as_complete_alternative(self):
        self.contract = dict(properties=[dict(id='route', kind='trajectory', allowed=[['initial', 'left', 'done'], ['initial', 'right', 'done']])])
        self.candidate['observations'] = [dict(id=v, run_id='candidate', time=i) for i, v in enumerate(['initial', 'left', 'right', 'done'])]
        self.assertEqual(self.compare()['status'], 'failed')

    def test_wrong_clock_basis_is_not_tested(self):
        self.candidate['timestamp_basis'] = 'device_pts_seconds'
        self.assertEqual(self.compare()['properties'][-1]['status'], 'not_tested')

    def test_timing_uncertainty_cannot_be_hidden_by_equal_midpoints(self):
        self.reference['observations'][0]['time_bounds'] = [99.995, 100.005]
        self.reference['observations'][1]['time_bounds'] = [100.995, 101.005]
        self.candidate['observations'][0]['time_bounds'] = [99.995, 100.005]
        self.candidate['observations'][1]['time_bounds'] = [100.995, 101.005]
        self.assertEqual(self.compare()['properties'][-1]['status'], 'passed')
        self.candidate['observations'][1]['time_bounds'] = [100.8, 101.2]
        self.assertEqual(self.compare()['properties'][-1]['status'], 'not_tested')
        self.candidate['observations'][1].update(time=100.2, time_bounds=[100.19, 100.21])
        prop = self.compare()['properties'][-1]
        self.assertEqual(prop['status'], 'failed')
        self.assertLess(prop['difference_bounds'][1], -.7)

    def test_overlapping_event_order_and_invalid_time_bounds(self):
        self.candidate['observations'][0]['time_bounds'] = [99, 101]
        self.candidate['observations'][1]['time_bounds'] = [100, 102]
        self.assertEqual(self.compare()['properties'][-1]['reason'], 'uncertain_event_order')
        for bounds in ([102, 100], [100, float('inf')], [True, 102], [99], 'uncertain'):
            self.candidate['observations'][0]['time_bounds'] = bounds
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                self.compare()

    @unittest.skipUnless(Image, 'install requirements-comparison.txt for visual checks')
    def test_small_critical_region_and_alpha_only_defects(self):
        self.visual(region=[1, 1, 2, 2], max_changed_ratio=.1)
        self.candidate['observations'][-1]['image'] = self.image('candidate.png', edit=[((1, 1), (0, 0, 0, 254))])
        report = self.compare()
        self.assertEqual(report['status'], 'failed')
        self.assertEqual(report['properties'][0]['changed'], 1)
        self.assertEqual(report['properties'][0]['compared'], 1)

    @unittest.skipUnless(Image, 'install requirements-comparison.txt for visual checks')
    def test_masks_union_is_local_and_requires_reason(self):
        self.visual(region=[0, 0, 3, 3], masks=[dict(rect=[0, 0, 2, 2], reason='reviewed variable avatar'),
                                              dict(rect=[1, 1, 3, 3], reason='reviewed clock'),
                                              dict(rect=[5, 5, 9, 9], reason='outside ROI')])
        self.candidate['observations'][-1]['image'] = self.image('candidate.png', edit=[((1, 1), (255, 0, 0, 255))])
        prop = self.compare()['properties'][0]
        self.assertEqual((prop['status'], prop['ignored'], prop['compared']), ('passed', 7, 2))
        self.contract['properties'][0]['masks'][0]['reason'] = ''
        with self.assertRaises(ValueError):
            self.compare()

    @unittest.skipUnless(Image, 'install requirements-comparison.txt for visual checks')
    def test_changed_image_and_geometry_cannot_pass(self):
        self.visual()
        stale = self.candidate['observations'][-1]['image']
        self.image('candidate.png', color=(255, 0, 0, 255))
        self.assertEqual(self.compare()['status'], 'not_tested')
        self.candidate['observations'][-1]['image'] = self.image('candidate.png', size=(9, 10))
        self.assertEqual(self.compare()['properties'][0]['reason'], 'geometry_mismatch')
        self.assertEqual(self.compare()['status'], 'failed')

    @unittest.skipUnless(Image, 'install requirements-comparison.txt for visual checks')
    def test_evidence_link_and_complete_mask_cannot_pass(self):
        self.visual()
        image = self.candidate['observations'][-1]['image']
        (self.root/'linked.png').symlink_to(self.root/image['path'])
        self.candidate['observations'][-1]['image'] = dict(image, path='linked.png')
        self.assertEqual(self.compare()['status'], 'not_tested')
        self.candidate['observations'][-1]['image'] = image
        self.contract['properties'][0]['masks'] = [dict(rect=[0, 0, 10, 10], reason='invalid attempt to ignore everything')]
        self.assertEqual(self.compare()['status'], 'not_tested')

    def test_contract_fixture_and_run_identity_are_not_interchangeable(self):
        for mutation in ('fixture', 'run', 'time', 'contract'):
            candidate = copy.deepcopy(self.candidate)
            if mutation == 'fixture':
                candidate['fixture'] = 'different account'
            elif mutation == 'run':
                candidate['observations'][0]['run_id'] = 'stale'
            elif mutation == 'time':
                candidate['observations'][-1]['time'] = 99
            else:
                candidate['contract_sha256'] = '0'*64
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                c.compare(self.contract, self.reference, candidate, self.root, self.root)

    def test_invalid_rule_cannot_hide_behind_absent_evidence(self):
        self.candidate['observations'] = []
        for rule in (dict(id='x', kind='imaginary'), dict(id='x', kind='pixels', observation='absent', channel_tolerance=-1),
                     dict(id='x', kind='duration', observation='absent', start='initial', tolerance=float('inf'))):
            self.contract = dict(properties=[rule])
            with self.assertRaises(ValueError):
                self.compare()

    def test_review_bound_repair_preserves_failure_without_waiving_unknowns(self):
        self.candidate['observations'][-1]['state']['count'] = 0
        self.candidate.pop('timestamp_basis')
        report = self.compare()
        review = dict(approved=True, reviewer='independent fixture evaluator', report_sha256=c.canonical(report))
        export = c.repair_export(report, review)
        self.assertEqual(export['contract_sha256'], c.canonical(self.contract))
        self.assertEqual(export['counterexamples'][0]['actual'], 0)
        self.assertEqual(export['unresolved'], ['latency'])
        report['properties'][0]['actual'] = 9
        with self.assertRaises(ValueError):
            c.repair_export(report, review)

    def test_cli_reports_failure_and_refuses_overwrite(self):
        self.candidate['observations'][-1]['state']['count'] = 0
        for name, value in [('contract', self.contract), ('reference', self.reference), ('candidate', self.candidate)]:
            (self.root/(name+'.json')).write_text(json.dumps(value))
        argv = [sys.executable, str(SCRIPTS/'comparison.py')]
        for name in ('contract', 'reference', 'candidate', 'output'):
            argv += ['--'+name, str(self.root/(name+'.json'))]
        first = subprocess.run(argv, capture_output=True, text=True)
        self.assertEqual(first.returncode, 2, first.stderr)
        before = (self.root/'output.json').read_bytes()
        self.assertEqual(subprocess.run(argv, capture_output=True).returncode, 1)
        self.assertEqual((self.root/'output.json').read_bytes(), before)

        report = json.loads(before)
        review = dict(approved=True, reviewer='fixture reviewer', report_sha256=c.canonical(report))
        (self.root/'review.json').write_text(json.dumps(review))
        export = self.root/'repair.json'
        repair_argv = [sys.executable, str(SCRIPTS/'comparison.py'), '--repair-report', str(self.root/'output.json'),
                       '--review', str(self.root/'review.json'), '--output', str(export)]
        completed = subprocess.run(repair_argv, capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(export.read_text())['counterexamples'][0]['property'], 'persistent_count')
        review['report_sha256'] = '0'*64
        (self.root/'review.json').write_text(json.dumps(review))
        export.unlink()
        self.assertEqual(subprocess.run(repair_argv, capture_output=True).returncode, 1)
        self.assertFalse(export.exists())


if __name__ == '__main__':
    unittest.main()
