#!/usr/bin/env python3
"""Compare ordered recorded boundaries and qualify supplied closure receipts.

Does not execute the original, authenticate observations, or certify equivalence.
"""
import argparse
import hashlib
import json
from pathlib import Path


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('missing ' + label)
    return value


def compare(original, candidate):
    for trace in (original, candidate):
        for key in ('case', 'environment', 'inputs_sha256'):
            nonempty(trace.get(key), key)
        if not isinstance(trace.get('events'), list) or not trace['events']:
            raise ValueError('nonempty ordered events required')
        for event in trace['events']:
            if not isinstance(event, dict):
                raise ValueError('event must be an object')
            nonempty(event.get('boundary'), 'boundary')
            if 'state' not in event:
                raise ValueError('phase-entry state required at each boundary')
        if 'final_state' not in trace:
            raise ValueError('final_state required')
    for key in ('case', 'environment', 'inputs_sha256'):
        if original[key] != candidate[key]:
            raise ValueError('comparison context mismatch: ' + key)
    left, right = original['events'], candidate['events']
    different = next((i for i, (a, b) in enumerate(zip(left, right)) if a != b), None)
    if different is None and len(left) != len(right):
        different = min(len(left), len(right))
    final_equal = original['final_state'] == candidate['final_state']
    return {'case': original['case'], 'environment': original['environment'],
            'inputs_sha256': original['inputs_sha256'],
            'status': 'pass' if different is None and final_equal else 'fail',
            'events_equal': different is None, 'final_state_equal': final_equal,
            'first_difference': different, 'original_events': len(left), 'candidate_events': len(right),
            'limits': 'Exact comparison of supplied traces only; unobserved behavior remains unverified.'}


def closure(packet, root):
    """Missing, stale, inferred or context-mismatched receipts cannot close cases."""
    root = Path(root).resolve()
    obligations = packet.get('obligations')
    if not isinstance(obligations, list) or not obligations:
        raise ValueError('nonempty obligations required')
    identifiers = set()
    unresolved = []
    for obligation in obligations:
        identifier = nonempty(obligation.get('id'), 'obligation id')
        if identifier in identifiers:
            raise ValueError('duplicate obligation id')
        identifiers.add(identifier)
        cases = obligation.get('required_cases')
        if not isinstance(cases, list) or not cases or any(not isinstance(c, str) or not c.strip() for c in cases) or len(set(cases)) != len(cases):
            raise ValueError('fixed nonempty unique required_cases needed')
        environment = nonempty(obligation.get('environment'), 'environment')
        receipts = obligation.get('receipts')
        if not isinstance(receipts, list):
            raise ValueError('receipts must be a list')
        for case in cases:
            qualified = False
            for receipt in receipts:
                if receipt.get('case') != case:
                    continue
                relative = Path(nonempty(receipt.get('file'), 'receipt file'))
                path = (root / relative).resolve()
                if relative.is_absolute() or not path.is_relative_to(root):
                    raise ValueError('receipt must remain within root')
                if not path.is_file():
                    continue
                raw = path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != receipt.get('sha256'):
                    continue
                result = json.loads(raw)
                if (result.get('case') == case and result.get('environment') == environment
                        and result.get('obligation') == identifier and result.get('status') == 'pass'
                        and result.get('original_basis') == 'observed'
                        and result.get('verifier_executed') is True
                        and result.get('events_equal') is True and result.get('final_state_equal') is True):
                    qualified = True
                    break
            if not qualified:
                unresolved.append({'obligation': identifier, 'case': case, 'reason': 'missing or unqualified observed verifier receipt'})
    return {'status': 'qualified' if not unresolved else 'unresolved', 'unresolved': unresolved,
            'limits': 'Checks supplied receipt structure/context and file integrity, not observation authenticity or unenumerated requirements.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    trace = sub.add_parser('compare')
    trace.add_argument('original', type=Path)
    trace.add_argument('candidate', type=Path)
    trace.add_argument('--output', required=True, type=Path)
    gate = sub.add_parser('closure')
    gate.add_argument('packet', type=Path)
    gate.add_argument('--root', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'compare':
            original, candidate = (json.loads(p.read_text()) for p in (args.original, args.candidate))
            report = compare(original, candidate)
            report['trace_sha256'] = {k: hashlib.sha256(p.read_bytes()).hexdigest() for k, p in [('original', args.original), ('candidate', args.candidate)]}
            args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + '\n')
        else:
            report = closure(json.loads(args.packet.read_text()), args.root)
        print(json.dumps(report, allow_nan=False))
        if report['status'] in {'fail', 'unresolved'}:
            raise SystemExit(1)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
