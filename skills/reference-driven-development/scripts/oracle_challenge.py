#!/usr/bin/env python3
"""Challenge an evaluator with seeded defective candidates and keep every outcome.

Runs the declared evaluator on a control and on each candidate. It cannot tell
whether a declared author is really independent, whether a defect is realistic,
or whether an "equivalent"/"unverifiable" disposition is true.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

PASS = 'pass'
STATUSES = {'pass', 'fail', 'error', 'timeout', 'skipped'}
LIMITS = ('Detection of these supplied candidates only. Authorship, realism and dispositions are '
          'declarations; a qualified result does not establish evaluator completeness or product fidelity.')


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('missing ' + label)
    return value


def inside(root, relative, label):
    path = (root / text(relative, label)).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root) or not path.exists():
        raise ValueError(label + ' must exist within root: ' + str(relative))
    return path


def digest(path):
    """Content hash of one file or of a tree's relative names and bytes."""
    h = hashlib.sha256()
    files = [path] if path.is_file() else sorted(p for p in path.rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for f in files:
        h.update(str(f.relative_to(path) if path.is_dir() else f.name).encode() + b'\0')
        h.update(hashlib.sha256(f.read_bytes()).digest())
    return h.hexdigest()


def cases(ledger):
    """Accept {"cases": {id: status}} or {"tests": {id: {"status": status}}}."""
    raw = ledger.get('cases', ledger.get('tests')) if isinstance(ledger, dict) else None
    if not isinstance(raw, dict) or not raw:
        raise ValueError('ledger has no cases')
    out = {}
    for name, value in raw.items():
        status = value.get('status') if isinstance(value, dict) else value
        if status not in STATUSES:
            raise ValueError('unknown case status for ' + str(name))
        out[name] = status
    return out


def evaluate(command, candidate, timeout, cwd):
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Path(tmp) / 'ledger.json'
        argv = [a.replace('{candidate}', str(candidate)).replace('{ledger}', str(ledger)) for a in command]
        try:
            done = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return None, 'evaluator exceeded %ss' % timeout
        except OSError as exc:
            return None, 'evaluator did not start: %s' % exc
        try:
            return cases(json.loads(ledger.read_text())), None
        except (OSError, ValueError) as exc:
            return None, 'no usable ledger (exit %s): %s' % (done.returncode, exc)


def summarize(rows, evaluator_author, minimum):
    """Recomputed from rows on every read; stored summaries are never trusted."""
    def count(selected):
        valid = [r for r in selected if r['state'] not in ('invalid', 'equivalent')]
        return {'candidates': len(selected), 'valid': len(valid),
                'killed': sum(r['state'] == 'killed' for r in valid),
                'unverifiable': sum(r['state'] == 'unverifiable' for r in valid),
                'survived': sum(r['state'] == 'survived' for r in valid),
                'evaluator_error': sum(r['state'] == 'evaluator_error' for r in valid)}
    independent = [r for r in rows if r['author'] != evaluator_author]
    own = [r for r in rows if r['author'] == evaluator_author]
    strata = {'independent': count(independent), 'evaluator_author': count(own)}
    blockers = []
    if strata['independent']['valid'] < minimum:
        blockers.append('fewer than %d valid candidates from an author other than the evaluator author' % minimum)
    for row in rows:
        if row['state'] == 'survived':
            blockers.append('%s survived without a disposition' % row['id'])
        if row['state'] == 'evaluator_error':
            blockers.append('%s: %s' % (row['id'], row['detail']))
        if row.get('dropped_cases') or row.get('unexpected_cases'):
            blockers.append('%s changed the compared case set' % row['id'])
    claim_limits = [{'candidate': r['id'], 'limit': r['claim_limit'], 'reason': r['reason']}
                    for r in rows if r['state'] == 'unverifiable']
    status = 'unqualified' if blockers else 'qualified_with_limits' if claim_limits else 'qualified'
    return {'status': status, 'strata': strata, 'blockers': blockers, 'claim_limits': claim_limits}


def run(manifest, root, timeout=600):
    root = Path(root).resolve()
    evaluator = manifest.get('evaluator') or {}
    command = evaluator.get('command')
    if not isinstance(command, list) or not command or not any('{candidate}' in a for a in command) \
            or not any('{ledger}' in a for a in command):
        raise ValueError('evaluator.command must be an argv list containing {candidate} and {ledger}')
    author = text(evaluator.get('author'), 'evaluator.author')
    files = evaluator.get('files')
    if not isinstance(files, list) or not files:
        raise ValueError('evaluator.files must list the evaluator sources to bind')
    bound = {f: digest(inside(root, f, 'evaluator file')) for f in files}
    control = inside(root, manifest.get('control'), 'control')
    minimum = manifest.get('minimum_independent', 3)
    if not isinstance(minimum, int) or minimum < 1:
        raise ValueError('minimum_independent must be a positive integer')
    baseline, problem = evaluate(command, control, timeout, root)
    if problem or any(s != PASS for s in baseline.values()):
        failing = problem or sorted(k for k, s in baseline.items() if s != PASS)
        return {'status': 'evaluator_rejects_control', 'detail': failing, 'limits': LIMITS}
    control_digest = digest(control)
    candidates = manifest.get('candidates')
    if not isinstance(candidates, list) or not candidates:
        raise ValueError('nonempty candidates required')
    rows, seen = [], set()
    for item in candidates:
        identifier = text(item.get('id'), 'candidate id')
        if identifier in seen:
            raise ValueError('duplicate candidate id ' + identifier)
        seen.add(identifier)
        path = inside(root, item.get('path'), 'candidate path')
        row = {'id': identifier, 'author': text(item.get('author'), 'candidate author'),
               'intent': text(item.get('intent'), 'candidate intent'), 'sha256': digest(path)}
        disposition = item.get('disposition') or {}
        if row['sha256'] == control_digest:
            row.update(state='invalid', detail='identical to control')
            rows.append(row)
            continue
        observed, problem = evaluate(command, path, timeout, root)
        if problem:
            row.update(state='evaluator_error', detail=problem)
            rows.append(row)
            continue
        row['dropped_cases'] = sorted(set(baseline) - set(observed))
        row['unexpected_cases'] = sorted(set(observed) - set(baseline))
        witnesses = {k: s for k, s in sorted(observed.items()) if s != PASS}
        if witnesses:
            row.update(state='killed', witnesses=witnesses,
                       precise=any(s == 'fail' for s in witnesses.values()))
        elif disposition.get('state') == 'unverifiable':
            row.update(state='unverifiable', reason=text(disposition.get('reason'), 'unverifiable reason'),
                       claim_limit=text(disposition.get('claim_limit'), 'claim_limit'))
        elif disposition.get('state') == 'equivalent':
            row.update(state='equivalent', reason=text(disposition.get('evidence'), 'equivalence evidence'))
        else:
            row['state'] = 'survived'
        rows.append(row)
    report = {'evaluator': {'author': author, 'command': command, 'files': bound},
              'control': {'path': manifest['control'], 'sha256': control_digest, 'cases': len(baseline)},
              'minimum_independent': minimum, 'rows': rows, 'limits': LIMITS}
    report.update(summarize(rows, author, minimum))
    return report


def check(report, root):
    """Reject a stored ledger whose evaluator, control or candidates changed, or whose totals were edited."""
    root = Path(root).resolve()
    problems = []
    for name, expected in report['evaluator']['files'].items():
        path = root / name
        if not path.exists() or digest(path) != expected:
            problems.append('evaluator changed: ' + name)
    control = root / report['control']['path']
    if not control.exists() or digest(control) != report['control']['sha256']:
        problems.append('control changed')
    fresh = summarize(report['rows'], report['evaluator']['author'], report['minimum_independent'])
    if any(report.get(key) != fresh[key] for key in fresh):
        problems.append('stored summary differs from its rows')
    return {'status': 'stale' if problems else fresh['status'], 'problems': problems,
            'claim_limits': fresh['claim_limits'], 'blockers': fresh['blockers'], 'limits': LIMITS}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    execute = sub.add_parser('run', help='execute the evaluator on the control and every candidate')
    execute.add_argument('manifest', type=Path)
    execute.add_argument('--root', required=True, type=Path)
    execute.add_argument('--output', required=True, type=Path)
    execute.add_argument('--timeout', type=int, default=600)
    verify = sub.add_parser('check', help='recompute a stored ledger and detect evaluator/control drift')
    verify.add_argument('ledger', type=Path)
    verify.add_argument('--root', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'run':
            report = run(json.loads(args.manifest.read_text()), args.root, args.timeout)
            args.output.write_text(json.dumps(report, indent=2) + '\n')
            brief = {k: report[k] for k in ('status', 'strata', 'blockers', 'claim_limits', 'detail') if k in report}
        else:
            brief = check(json.loads(args.ledger.read_text()), args.root)
        print(json.dumps(brief))
        if brief['status'] not in ('qualified', 'qualified_with_limits'):
            raise SystemExit(1)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
