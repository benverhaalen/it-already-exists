import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/reference-driven-development/scripts/oracle_challenge.py'
spec = importlib.util.spec_from_file_location('oracle_challenge', SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

# Authored fixture: clamp(x, lo, hi). The evaluator never probes x above hi.
EVALUATOR = textwrap.dedent('''
    import importlib.util, json, sys
    candidate, out = sys.argv[1], sys.argv[2]
    cases = {}
    try:
        spec = importlib.util.spec_from_file_location('clamp', candidate + '/clamp.py')
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    except Exception:
        mod = None
    for name, args, want in (('inside', (5, 0, 9), 5), ('below', (-3, 0, 9), 0)EXTRA):
        if mod is None:
            cases[name] = 'error'; continue
        try:
            cases[name] = 'pass' if mod.clamp(*args) == want else 'fail'
        except Exception:
            cases[name] = 'error'
    DROP
    json.dump({'cases': cases}, open(out, 'w'))
''')
GOOD = 'def clamp(x, lo, hi):\n    return max(lo, min(x, hi))\n'
NO_LOWER = 'def clamp(x, lo, hi):\n    return min(x, hi)\n'
NO_UPPER = 'def clamp(x, lo, hi):\n    return max(lo, x)\n'
RAISES = 'def clamp(x, lo, hi):\n    raise RuntimeError("no")\n'


class Fixture:
    live = []

    def __init__(self, extra='', drop=''):
        self.tmp = tempfile.TemporaryDirectory()
        self.live.append(self.tmp)
        self.root = Path(self.tmp.name)
        (self.root / 'evaluate.py').write_text(EVALUATOR.replace('EXTRA', extra).replace('DROP', drop))
        self.candidates = []
        self.add('control', GOOD, register=False)

    def add(self, name, source, author='seeder', register=True, **extra):
        (self.root / name).mkdir()
        (self.root / name / 'clamp.py').write_text(source)
        if register:
            self.candidates.append(dict({'id': name, 'path': name, 'author': author, 'intent': name}, **extra))

    def manifest(self, minimum=1):
        return {'evaluator': {'command': [sys.executable, 'evaluate.py', '{candidate}', '{ledger}'],
                              'author': 'builder', 'files': ['evaluate.py']},
                'control': 'control', 'minimum_independent': minimum, 'candidates': self.candidates}

    def run(self, minimum=1):
        return m.run(self.manifest(minimum), self.root, timeout=60)


class OracleChallengeTests(unittest.TestCase):
    def tearDown(self):
        while Fixture.live:
            Fixture.live.pop().cleanup()

    def test_killed_candidate_names_witness(self):
        f = Fixture()
        f.add('no_lower', NO_LOWER)
        report = f.run()
        self.assertEqual(report['status'], 'qualified')
        self.assertEqual(report['rows'][0]['witnesses'], {'below': 'fail'})
        self.assertTrue(report['rows'][0]['precise'])

    def test_independent_survivor_blocks_even_when_builder_defects_all_die(self):
        f = Fixture()
        f.add('no_lower', NO_LOWER, author='builder')
        f.add('no_upper', NO_UPPER)
        report = f.run()
        self.assertEqual(report['status'], 'unqualified')
        self.assertEqual(report['strata']['evaluator_author'], dict(report['strata']['evaluator_author'], killed=1, survived=0))
        self.assertEqual(report['strata']['independent']['survived'], 1)
        self.assertIn('no_upper survived without a disposition', report['blockers'])

    def test_builder_only_candidates_do_not_qualify(self):
        f = Fixture()
        f.add('no_lower', NO_LOWER, author='builder')
        self.assertEqual(f.run()['status'], 'unqualified')

    def test_closing_the_gap_kills_the_survivor(self):
        f = Fixture(extra=", ('above', (12, 0, 9), 9)")
        f.add('no_upper', NO_UPPER)
        report = f.run()
        self.assertEqual(report['status'], 'qualified')
        self.assertEqual(report['rows'][0]['witnesses'], {'above': 'fail'})

    def test_unverifiable_survivor_becomes_claim_limit(self):
        f = Fixture()
        f.add('no_lower', NO_LOWER)
        f.add('no_upper', NO_UPPER, disposition={'state': 'unverifiable', 'reason': 'no reference observation above hi',
                                                 'claim_limit': 'behavior above hi is not established'})
        report = f.run()
        self.assertEqual(report['status'], 'qualified_with_limits')
        self.assertEqual(report['claim_limits'][0]['limit'], 'behavior above hi is not established')

    def test_disposition_without_reason_or_limit_is_rejected(self):
        f = Fixture()
        f.add('no_upper', NO_UPPER, disposition={'state': 'unverifiable', 'reason': 'x'})
        with self.assertRaises(ValueError):
            f.run()

    def test_disposition_cannot_relabel_a_killed_candidate(self):
        f = Fixture()
        f.add('no_lower', NO_LOWER, disposition={'state': 'equivalent', 'evidence': 'claimed'})
        self.assertEqual(f.run()['rows'][0]['state'], 'killed')

    def test_copy_of_control_is_invalid_and_not_counted(self):
        f = Fixture()
        f.add('copy', GOOD)
        report = f.run()
        self.assertEqual(report['rows'][0]['state'], 'invalid')
        self.assertEqual(report['strata']['independent']['valid'], 0)
        self.assertEqual(report['status'], 'unqualified')

    def test_error_only_detection_is_marked_imprecise(self):
        f = Fixture()
        f.add('raises', RAISES)
        row = f.run()['rows'][0]
        self.assertEqual(row['state'], 'killed')
        self.assertFalse(row['precise'])

    def test_evaluator_that_rejects_control_is_reported(self):
        f = Fixture(extra=", ('wrong', (1, 0, 9), 2)")
        f.add('no_lower', NO_LOWER)
        self.assertEqual(f.run()['status'], 'evaluator_rejects_control')

    def test_evaluator_without_ledger_is_not_a_kill(self):
        f = Fixture()
        f.add('no_lower', NO_LOWER)
        manifest = f.manifest()
        (f.root / 'evaluate.py').write_text(
            "import sys, json\nif 'control' not in sys.argv[1]: sys.exit(3)\njson.dump({'cases': {'a': 'pass'}}, open(sys.argv[2], 'w'))\n")
        report = m.run(manifest, f.root, timeout=60)
        self.assertEqual(report['rows'][0]['state'], 'evaluator_error')
        self.assertEqual(report['status'], 'unqualified')

    def test_dropped_case_blocks_qualification(self):
        f = Fixture(drop="\nif 'no_lower' in candidate: cases.pop('inside')")
        f.add('no_lower', NO_LOWER)
        report = f.run()
        self.assertEqual(report['rows'][0]['dropped_cases'], ['inside'])
        self.assertEqual(report['status'], 'unqualified')

    def test_minimum_independent_candidates(self):
        f = Fixture()
        f.add('no_lower', NO_LOWER)
        self.assertEqual(f.run(minimum=2)['status'], 'unqualified')

    def test_check_detects_evaluator_drift_and_edited_totals(self):
        f = Fixture()
        f.add('no_lower', NO_LOWER)
        report = f.run()
        self.assertEqual(m.check(report, f.root)['status'], 'qualified')
        edited = json.loads(json.dumps(report))
        edited['rows'][0]['state'] = 'survived'
        self.assertEqual(m.check(edited, f.root)['status'], 'stale')
        (f.root / 'evaluate.py').write_text((f.root / 'evaluate.py').read_text() + '\n# changed\n')
        self.assertIn('evaluator changed: evaluate.py', m.check(report, f.root)['problems'])

    def test_paths_must_stay_inside_root(self):
        f = Fixture()
        f.candidates.append({'id': 'x', 'path': '../x', 'author': 'seeder', 'intent': 'escape'})
        with self.assertRaises(ValueError):
            f.run()

    def test_cli_exit_codes(self):
        f = Fixture()
        f.add('no_upper', NO_UPPER)
        (f.root / 'manifest.json').write_text(json.dumps(f.manifest()))
        argv = [sys.executable, str(SCRIPT), 'run', str(f.root / 'manifest.json'), '--root', str(f.root),
                '--output', str(f.root / 'ledger.json')]
        self.assertEqual(subprocess.run(argv, capture_output=True).returncode, 1)
        f.candidates[0]['disposition'] = {'state': 'unverifiable', 'reason': 'r', 'claim_limit': 'l'}
        (f.root / 'manifest.json').write_text(json.dumps(f.manifest()))
        self.assertEqual(subprocess.run(argv, capture_output=True).returncode, 0)
        check = [sys.executable, str(SCRIPT), 'check', str(f.root / 'ledger.json'), '--root', str(f.root)]
        self.assertEqual(subprocess.run(check, capture_output=True).returncode, 0)
        (f.root / 'manifest.json').write_text('{}')
        self.assertEqual(subprocess.run(argv, capture_output=True).returncode, 2)


if __name__ == '__main__':
    unittest.main()
