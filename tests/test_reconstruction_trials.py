import copy
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts/reconstruction_trials.py'
spec = importlib.util.spec_from_file_location('reconstruction_trials', path)
trials = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trials)


def packet():
    runs = []
    for strategy, seconds in [('baseline', 3), ('candidate', 1)]:
        runs.append({'case': 'reopen', 'repeat': 0, 'strategy': strategy,
                     'properties': {'visible': 'pass', 'persistent': 'pass'}, 'evidence': 'private/receipt.json',
                     'phases': {p: {'seconds': seconds, 'dollars': 0, 'tokens': 0} for p in trials.PHASES}})
    return {'cases': {'reopen': ['visible', 'persistent']}, 'runs': runs}


class TrialTests(unittest.TestCase):
    def test_known_costs_sum_all_phases(self):
        report = trials.summarize(packet(), 'baseline', 'candidate')
        self.assertEqual(report['pairs'][0]['cost_delta']['seconds'], -14)
        self.assertTrue(report['candidate_all_required_properties_passed'])

    def test_fast_candidate_cannot_hide_skip(self):
        data = packet()
        data['runs'][1]['properties']['persistent'] = 'skipped'
        report = trials.summarize(data, 'baseline', 'candidate')
        self.assertEqual(report['pairs'][0]['regressions'], ['persistent'])
        self.assertFalse(report['candidate_all_required_properties_passed'])
        self.assertEqual(report['strategies']['candidate']['fully_qualified_runs'], 0)

    def test_unknown_cost_does_not_become_zero(self):
        data = packet()
        data['runs'][1]['phases']['setup']['dollars'] = None
        report = trials.summarize(data, 'baseline', 'candidate')
        self.assertIsNone(report['pairs'][0]['cost_delta']['dollars'])
        self.assertIsNone(report['strategies']['candidate']['total_all_attempt_cost']['dollars'])

    def test_failed_attempt_remains_in_cost_and_coverage(self):
        data = packet()
        extra = copy.deepcopy(data['runs'])
        for run in extra:
            run['repeat'] = 1
        extra[1]['properties']['visible'] = 'fail'
        extra[1]['phases']['repair']['seconds'] = 100
        data['runs'] += extra
        report = trials.summarize(data, 'baseline', 'candidate')
        self.assertEqual(report['strategies']['candidate']['attempts'], 2)
        self.assertEqual(report['strategies']['candidate']['fully_qualified_runs'], 1)
        self.assertEqual(report['strategies']['candidate']['total_all_attempt_cost']['seconds'], 113)

    def test_unchanged_failures_are_not_equivalence(self):
        data = packet()
        for run in data['runs']:
            run['properties']['persistent'] = 'not_tested'
        report = trials.summarize(data, 'baseline', 'candidate')
        self.assertTrue(report['no_observed_regression'])
        self.assertFalse(report['candidate_all_required_properties_passed'])

    def test_denominator_and_pairing_are_fixed(self):
        data = packet()
        del data['runs'][1]['properties']['persistent']
        with self.assertRaises(ValueError):
            trials.summarize(data, 'baseline', 'candidate')
        data = packet()
        data['runs'].pop()
        with self.assertRaises(ValueError):
            trials.summarize(data, 'baseline', 'candidate')
        data = packet()
        data['cases']['missing'] = ['property']
        with self.assertRaises(ValueError):
            trials.summarize(data, 'baseline', 'candidate')

    def test_bad_costs_and_duplicate_runs_rejected(self):
        for value in [True, -1, float('nan'), float('inf')]:
            data = packet()
            data['runs'][0]['phases']['setup']['seconds'] = value
            with self.assertRaises(ValueError):
                trials.summarize(data, 'baseline', 'candidate')
        data = packet()
        data['runs'].append(data['runs'][0])
        with self.assertRaises(ValueError):
            trials.summarize(data, 'baseline', 'candidate')


if __name__ == '__main__':
    unittest.main()
