#!/usr/bin/env python3
"""Summarize paired, externally judged research trials; never infer source quality."""
import argparse
import json
import math
from pathlib import Path


def summarize(rows, baseline, candidate):
    groups = {}
    for row in rows:
        case, strategy = row['case'], row['strategy']
        if not isinstance(case, str) or not case or strategy not in {baseline, candidate}:
            raise ValueError('invalid case or strategy')
        if (case, strategy) in groups:
            raise ValueError('duplicate case/strategy trial')
        contributions = row['verified_contributions']
        if not isinstance(contributions, list) or any(not isinstance(x, str) or not x for x in contributions):
            raise ValueError('contributions must be externally reviewed identifiers')
        for metric in ['seconds', 'dollars', 'tokens']:
            value = row.get(metric)
            if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
                raise ValueError('invalid cost metric')
        if not isinstance(row.get('judgment_evidence'), str) or not row['judgment_evidence'].strip():
            raise ValueError('missing judgment evidence location')
        groups[(case, strategy)] = row
    cases = sorted({case for case, _ in groups})
    if not cases or baseline == candidate:
        raise ValueError('need distinct strategies and at least one paired case')
    paired = []
    for case in cases:
        if (case, baseline) not in groups or (case, candidate) not in groups:
            raise ValueError('unpaired case: ' + case)
        left, right = groups[(case, baseline)], groups[(case, candidate)]
        a, b = set(left['verified_contributions']), set(right['verified_contributions'])
        paired.append({'case': case, 'baseline_count': len(a), 'candidate_count': len(b),
                       'added': sorted(b - a), 'missed': sorted(a - b),
                       'cost_delta': {m: None if left.get(m) is None or right.get(m) is None else right[m] - left[m]
                                      for m in ['seconds', 'dollars', 'tokens']}})
    return {'baseline': baseline, 'candidate': candidate, 'paired_cases': paired,
            'mean_contribution_delta': sum(x['candidate_count'] - x['baseline_count'] for x in paired) / len(paired),
            'cost_delta_totals': {m: None if any(x['cost_delta'][m] is None for x in paired)
                                 else sum(x['cost_delta'][m] for x in paired) for m in ['seconds', 'dollars', 'tokens']},
            'limits': ['Judgments and evidence links are supplied, not independently verified by this helper.',
                       'Counts are not importance, correctness, completeness or downstream effectiveness.',
                       'No statistical significance or automatic provider promotion is claimed.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trials', type=Path)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = summarize(json.loads(args.trials.read_text()), args.baseline, args.candidate)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
