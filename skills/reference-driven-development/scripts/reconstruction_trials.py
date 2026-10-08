#!/usr/bin/env python3
"""Compare supplied reconstruction trial receipts with a fixed fidelity denominator.

Does not run apps, inspect evidence, infer costs, or certify equivalence.
"""
import argparse
import json
import math
import statistics
from pathlib import Path

PHASES = ('research', 'setup', 'build', 'exploration', 'replay', 'verification', 'repair')
METRICS = ('seconds', 'dollars', 'tokens')
STATUSES = {'pass', 'fail', 'not_tested', 'skipped'}


def identifier(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('empty identifier')
    return value


def summarize(packet, baseline, candidate):
    identifier(baseline)
    identifier(candidate)
    if baseline == candidate:
        raise ValueError('strategies must differ')
    cases = packet['cases']
    if not isinstance(cases, dict) or not cases:
        raise ValueError('need fixed cases and required properties')
    for case, props in cases.items():
        identifier(case)
        if not isinstance(props, list) or not props or len(set(props)) != len(props):
            raise ValueError('properties must be nonempty and unique')
        for prop in props:
            identifier(prop)
    groups = {}
    for row in packet['runs']:
        case, strategy, repeat = row['case'], row['strategy'], row['repeat']
        if case not in cases or strategy not in {baseline, candidate}:
            raise ValueError('undeclared case or strategy')
        if type(repeat) is not int or repeat < 0:
            raise ValueError('repeat must be a nonnegative integer')
        key = (case, repeat, strategy)
        if key in groups:
            raise ValueError('duplicate run')
        properties = row['properties']
        if not isinstance(properties, dict) or set(properties) != set(cases[case]):
            raise ValueError('required property denominator changed')
        if any(status not in STATUSES for status in properties.values()):
            raise ValueError('invalid property status')
        identifier(row['evidence'])
        phases = row['phases']
        if not isinstance(phases, dict) or set(phases) != set(PHASES):
            raise ValueError('declare every phase, including zero or unknown costs')
        for phase in phases.values():
            if not isinstance(phase, dict) or set(phase) != set(METRICS):
                raise ValueError('declare every metric')
            for value in phase.values():
                if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                    raise ValueError('invalid cost')
        totals = {metric: None if any(phases[p][metric] is None for p in PHASES)
                  else sum(phases[p][metric] for p in PHASES) for metric in METRICS}
        groups[key] = {'properties': properties, 'totals': totals,
                       'qualified': all(s == 'pass' for s in properties.values())}
    if {key[0] for key in groups} != set(cases):
        raise ValueError('a declared case has no runs')
    pairs = []
    for case, repeat in sorted({(c, r) for c, r, _ in groups}):
        if any((case, repeat, s) not in groups for s in (baseline, candidate)):
            raise ValueError('unpaired run')
        left, right = (groups[(case, repeat, s)] for s in (baseline, candidate))
        pairs.append({'case': case, 'repeat': repeat,
                      'regressions': [p for p in cases[case] if left['properties'][p] == 'pass' and right['properties'][p] != 'pass'],
                      'new_passes': [p for p in cases[case] if left['properties'][p] != 'pass' and right['properties'][p] == 'pass'],
                      'candidate_unresolved': {p: s for p, s in right['properties'].items() if s != 'pass'},
                      'cost_delta': {m: None if left['totals'][m] is None or right['totals'][m] is None
                                     else right['totals'][m] - left['totals'][m] for m in METRICS}})
    summaries = {}
    for strategy in (baseline, candidate):
        runs = [run for key, run in groups.items() if key[2] == strategy]
        summaries[strategy] = {
            'attempts': len(runs), 'fully_qualified_runs': sum(r['qualified'] for r in runs),
            'status_counts': {status: sum(s == status for r in runs for s in r['properties'].values()) for status in sorted(STATUSES)},
            'median_all_attempt_cost': {m: None if any(r['totals'][m] is None for r in runs)
                                        else statistics.median(r['totals'][m] for r in runs) for m in METRICS},
            'total_all_attempt_cost': {m: None if any(r['totals'][m] is None for r in runs)
                                       else sum(r['totals'][m] for r in runs) for m in METRICS}}
    return {'baseline': baseline, 'candidate': candidate, 'pairs': pairs, 'strategies': summaries,
            'no_observed_regression': all(not p['regressions'] for p in pairs),
            'candidate_all_required_properties_passed': all(not p['candidate_unresolved'] for p in pairs),
            'limits': ['Receipts and evidence locations are supplied, not independently verified.',
                       'Fixed declared properties are not complete behavioral equivalence.',
                       'Unknown costs stay unknown; failures and skips remain in the denominator.',
                       'No statistical significance, automatic winner, or general speedup is claimed.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trials', type=Path)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = summarize(json.loads(args.trials.read_text()), args.baseline, args.candidate)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
