#!/usr/bin/env python3
"""Project-owned executable controls, source freshness, and cold-use evidence.

Commands are explicit trusted argv arrays. This is not an access sandbox or an
oracle: declarations cannot establish correctness, causation, or equivalence.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import uuid

from process import run as run_process


STATE = '.rdd/project-controls'
CLASSES = {'generation', 'maintenance', 'fix', 'forensics'}
ROLES = {'launch', 'doctor', 'drive', 'observe', 'verify', 'reset', 'cleanup', 'diagnostic'}
EFFECTS = {'read-only', 'runtime-state', 'product-mutation'}


def _json(payload):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON key: ' + key)
            result[key] = value
        return result
    return json.loads(payload, object_pairs_hook=unique)


def _root(root):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('project root must be a directory')
    return root


def _bound(root, path, must_exist=False):
    if not isinstance(path, str) or not path or '\x00' in path:
        raise ValueError('explicit relative project path required')
    relative = Path(path)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('path must stay inside the selected project')
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('symlink paths require a separate qualified adapter')
    resolved = current.resolve(strict=must_exist)
    if not resolved.is_relative_to(root):
        raise ValueError('path escapes the selected project')
    return resolved


def _digest(data):
    return hashlib.sha256(data).hexdigest()


def _now():
    return datetime.now(timezone.utc).isoformat()


def _inventory(root, source_roots):
    result = {}
    for name in source_roots:
        path = _bound(root, name, must_exist=True)
        items = [path] if path.is_file() else sorted(path.rglob('*'))
        for item in items:
            relative = item.relative_to(root).as_posix()
            if relative == '.git' or relative.startswith('.git/'):
                continue
            if relative == '.rdd' or relative.startswith('.rdd/'):
                continue
            _bound(root, relative, must_exist=True)
            if item.is_file():
                result[relative] = _digest(item.read_bytes())
    return result


def inspect_project(root, source_roots=None):
    """Inspect file identities only; never infer a working command from a name."""
    root = _root(root)
    source_roots = source_roots or ['.']
    inventory = _inventory(root, source_roots)
    return {'schema_version': 1, 'project_root': str(root), 'observed_at': _now(),
            'source_roots': source_roots, 'source_inventory': inventory,
            'commands_inferred': 0, 'driver': 'missing', 'oracle': 'missing',
            'limits': 'Selected file identities only; entries, commands, imports, '
                      'behavior and oracle authority require project inspection.'}


def _nonempty(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + ' must be a nonempty string')


def _validate(root, manifest):
    if manifest.get('schema_version') != 1 or manifest.get('project_root') != str(root):
        raise ValueError('manifest must bind this exact project root and schema')
    source_roots = manifest.get('source_roots')
    if not isinstance(source_roots, list) or not source_roots:
        raise ValueError('selected source_roots required')
    for path in source_roots:
        _bound(root, path)
    inventory = manifest.get('source_inventory')
    if not isinstance(inventory, dict):
        raise ValueError('captured source_inventory required')
    for path, digest in inventory.items():
        _bound(root, path)
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise ValueError('source SHA256 required')
    readiness = manifest.get('readiness', {})
    for kind in ('driver', 'oracle'):
        if readiness.get(kind) not in ('declared', 'missing'):
            raise ValueError('explicit driver/oracle readiness required')
    if not isinstance(readiness.get('gaps'), list) or any(not isinstance(x, str) for x in readiness['gaps']):
        raise ValueError('explicit readiness gaps list required')
    controls = {}
    for control in manifest.get('controls', []):
        identifier = control.get('id')
        _nonempty(identifier, 'control id')
        if identifier in controls:
            raise ValueError('duplicate control id')
        argv = control.get('argv')
        if not isinstance(argv, list) or not argv or any(not isinstance(x, str) or not x or '\x00' in x for x in argv):
            raise ValueError('nonempty command argv array required')
        _bound(root, control.get('cwd'))
        timeout = control.get('timeout_seconds')
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0 < timeout <= 3600:
            raise ValueError('explicit timeout between zero and 3600 seconds required')
        limit = control.get('max_output_bytes', 1048576)
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 < limit <= 67108864:
            raise ValueError('bounded max_output_bytes required')
        if control.get('role') not in ROLES or control.get('effect') not in EFFECTS:
            raise ValueError('explicit supported control role/effect required')
        classes = control.get('classes')
        if not isinstance(classes, list) or not classes or not set(classes) <= CLASSES:
            raise ValueError('explicit operation classes required')
        if control['effect'] == 'product-mutation' and set(classes) != {'fix'}:
            raise ValueError('only explicitly selected fix controls may mutate product')
        if 'forensics' in classes and control['effect'] != 'read-only':
            raise ValueError('forensics controls must be read-only')
        if 'generation' in classes:
            raise ValueError('generation scaffolds controls; it does not execute them')
        if control['role'] in ('reset', 'cleanup') and control.get('ownership') != 'current-run-only':
            raise ValueError('reset/cleanup must declare current-run-only ownership')
        if control.get('reconciliation_outcome') is not None:
            if control['role'] not in ('observe', 'verify') or control['effect'] != 'read-only':
                raise ValueError('reconciliation requires a read-only target observer')
            if control['reconciliation_outcome'] not in ('observed-completed', 'observed-not-applied', 'observed-reset'):
                raise ValueError('explicit target reconciliation outcome required')
            _nonempty(control.get('reconciliation_scope'), 'reconciliation scope')
        expected = control.get('expected_exit_codes', [0])
        if not isinstance(expected, list) or not expected or any(type(x) is not int for x in expected):
            raise ValueError('explicit expected exit code list required')
        controls[identifier] = control
    features = {}
    for feature in manifest.get('features', []):
        identifier = feature.get('id')
        _nonempty(identifier, 'feature id')
        if identifier in features:
            raise ValueError('duplicate feature id')
        for key in ('entry', 'default_state', 'state_observation', 'expected_effect', 'oracle_scope'):
            _nonempty(feature.get(key), key)
        if not isinstance(feature.get('prerequisites'), list):
            raise ValueError('feature prerequisites required, including empty when none')
        route = feature.get('route')
        if not isinstance(route, list) or not route or any(c not in controls for c in route):
            raise ValueError('feature requires a route over declared controls')
        for key in ('reset_control', 'cleanup_control'):
            if feature.get(key) is not None:
                if feature[key] not in controls:
                    raise ValueError('unknown feature recovery control')
                role = 'reset' if key == 'reset_control' else 'cleanup'
                if controls[feature[key]]['role'] != role:
                    raise ValueError('recovery control role mismatch')
        features[identifier] = feature
    profile = manifest.get('development_profile', {})
    if profile.get('kind') not in ('code', 'non-code'):
        raise ValueError('explicit development profile kind required')
    for identifier, paths in profile.get('feature_roots', {}).items():
        if identifier not in features or not isinstance(paths, list):
            raise ValueError('feature roots must map declared features')
        for path in paths:
            _bound(root, path)
    for identifier, dependencies in profile.get('allowed_imports', {}).items():
        if identifier not in features or not isinstance(dependencies, list) or any(x not in features for x in dependencies):
            raise ValueError('allowed imports must map declared feature identifiers')
    for shared in profile.get('shared_invariants', []):
        _nonempty(shared.get('id'), 'shared invariant id')
        if shared.get('kind') not in ('schema', 'token', 'primitive'):
            raise ValueError('shared invariant kind required')
        _nonempty(shared.get('owner'), 'shared owner')
        if not isinstance(shared.get('consumers'), list) or any(x not in features for x in shared['consumers']):
            raise ValueError('shared invariant inverse consumers required')
        for path in shared.get('sources', []):
            _bound(root, path)
        if any(x not in controls for x in shared.get('validator_controls', [])):
            raise ValueError('unknown shared invariant validator')
    for diagnostic in profile.get('diagnostics', []):
        if diagnostic.get('control') not in controls:
            raise ValueError('diagnostic must bind an actual declared control')
        for field in ('positive_fixture', 'negative_fixture'):
            _bound(root, diagnostic.get(field))
        if not isinstance(diagnostic.get('suppressions'), list):
            raise ValueError('explicit diagnostic suppressions required')
    if profile.get('preview') is not None:
        for field in ('entry', 'build_ref', 'environment', 'access'):
            _nonempty(profile['preview'].get(field), 'preview ' + field)
        if profile['preview'].get('control') not in controls:
            raise ValueError('preview must bind a declared control')
    return controls, features


def generate(root, blueprint=None, output=None):
    """Scaffold from facts plus reviewed declarations; missing capability stays missing."""
    root = _root(root)
    blueprint = blueprint or {}
    facts = inspect_project(root, blueprint.get('source_roots'))
    manifest = {key: facts[key] for key in ('schema_version', 'project_root', 'source_roots', 'source_inventory')}
    manifest.update({'captured_at': facts['observed_at'],
                     'readiness': blueprint.get('readiness', {'driver': 'missing', 'oracle': 'missing',
                                                            'gaps': ['project controls and independent oracle not acquired']}),
                     'controls': blueprint.get('controls', []), 'features': blueprint.get('features', []),
                     'development_profile': blueprint.get('development_profile', {'kind': 'non-code'}),
                     'authority': 'Reviewed project declarations, not inferred behavioral truth.'})
    _validate(root, manifest)
    state = _bound(root, STATE)
    state.mkdir(parents=True, exist_ok=True)
    destination = _bound(root, output or STATE + '/manifest.json')
    if not destination.is_relative_to(state):
        raise ValueError('generated control must live inside project-owned control state')
    destination.parent.mkdir(parents=True, exist_ok=True)
    guide = destination.with_suffix('.md')
    if destination.exists() or guide.exists():
        raise FileExistsError('generation does not replace existing project controls')
    manifest['control_entry'] = [sys.executable, str(Path(__file__).resolve())]
    manifest['evidence_directory'] = str(state)
    manifest['manifest_path'] = str(destination)
    with destination.open('x') as stream:
        json.dump(manifest, stream, indent=2)
        stream.write('\n')
    with guide.open('x') as stream:
        stream.write('# Project controls\n\nUse the `control_entry` command array in the adjacent JSON. '
                     'Append `doctor --root <project_root> --manifest <manifest_path>` first. '
                     'For each feature append `run --root <project_root> --manifest <manifest_path> '
                     '--feature <id> --class maintenance`. Select exactly one live owner. '
                     'The map supplies entry/default/prerequisites/state/effect; do not guess missing routes.\n\n'
                     'Failed or timed-out effects remain unknown. Inspect retained attempt receipts in '
                     '`evidence_directory`; use a declared target observer with `--reconcile-attempt <id>` '
                     'before retrying. Reset/cleanup may affect only resources belonging to `RDD_CONTROL_OWNER`. '
                     'This helper is not a sandbox, and passing commands do not prove independent acceptance.\n')
    return manifest


def doctor(root, manifest):
    root = _root(root)
    controls, features = _validate(root, manifest)
    problems = []
    try:
        actual = _inventory(root, manifest['source_roots'])
        expected = manifest['source_inventory']
        for path in sorted(set(actual) | set(expected)):
            if actual.get(path) != expected.get(path):
                problems.append({'kind': 'source-drift', 'path': path,
                                 'expected': expected.get(path), 'actual': actual.get(path)})
    except (OSError, ValueError) as error:
        problems.append({'kind': 'source-unavailable', 'detail': str(error)})
    for control in controls.values():
        try:
            cwd = _bound(root, control['cwd'], must_exist=True)
            if not cwd.is_dir():
                raise ValueError('control cwd is not a directory')
        except (OSError, ValueError) as error:
            problems.append({'kind': 'control-cwd-unavailable', 'control': control['id'], 'detail': str(error)})
    for diagnostic in manifest['development_profile'].get('diagnostics', []):
        for key in ('positive_fixture', 'negative_fixture'):
            if not _bound(root, diagnostic[key]).is_file():
                problems.append({'kind': 'diagnostic-fixture-unavailable', 'path': diagnostic[key]})
    ready = manifest['readiness']
    gaps = list(ready['gaps'])
    if ready['driver'] == 'missing' or not controls or not features:
        gaps.append('declared executable project driver missing')
    if ready['oracle'] == 'missing':
        gaps.append('independent project oracle missing')
    state = _bound(root, STATE)
    try:
        pending = _pending_attempts(state) if state.exists() else []
    except (OSError, ValueError) as error:
        pending = []
        problems.append({'kind': 'control-evidence-unreadable', 'detail': str(error)})
    if pending:
        gaps.append('unreconciled prior attempt effects; inspect target before retry')
    changed_paths = [p['path'] for p in problems if p['kind'] == 'source-drift']
    impact = _impact(manifest, changed_paths)
    return {'fresh': not problems, 'ready_for_declared_route': not problems and not gaps,
            'problems': problems, 'gaps': list(dict.fromkeys(gaps)),
            'unreconciled_attempts': pending,
            'declared_impact': impact,
            'control_ids': list(controls), 'feature_ids': list(features),
            'oracle_verified': False,
            'limits': 'Inventory and declarations only; run the route and independently '
                      'inspect its actual product state and full required coverage.'}


def _impact(manifest, changed_paths):
    """Invalidate declared inverse consumers; unknown coverage widens to all features."""
    profile = manifest['development_profile']
    affected, shared_ids, unmapped = set(), set(), []

    def under(path, parent):
        return parent == '.' or path == parent or path.startswith(parent.rstrip('/') + '/')

    for path in changed_paths:
        matched = False
        for feature, roots in profile.get('feature_roots', {}).items():
            if any(under(path, parent) for parent in roots):
                affected.add(feature)
                matched = True
        for shared in profile.get('shared_invariants', []):
            if any(under(path, parent) for parent in shared.get('sources', [])):
                affected.update(shared['consumers'])
                shared_ids.add(shared['id'])
                matched = True
        if not matched:
            unmapped.append(path)
    if unmapped:
        affected.update(feature['id'] for feature in manifest['features'])
    while True:
        previous = set(affected)
        for consumer, imports in profile.get('allowed_imports', {}).items():
            if affected.intersection(imports):
                affected.add(consumer)
        if previous == affected:
            break
    return {'feature_ids': sorted(affected), 'shared_invariant_ids': sorted(shared_ids),
            'unknown_impact_paths': unmapped,
            'scope': 'declared dependency map; not extracted or semantically proven'}


def _pending_attempts(state):
    intents, resolved = set(), set()
    for path in sorted(state.glob('*.json')):
        receipt = _json(path.read_text())
        if not isinstance(receipt, dict):
            raise ValueError('project control evidence must be a JSON object: ' + path.name)
        if receipt.get('status') == 'admitted':
            intents.add(receipt.get('attempt_id'))
        if receipt.get('intent_attempt_id') and receipt.get('finished_at') and receipt.get('effect_state') != 'unknown':
            resolved.add(receipt['intent_attempt_id'])
        if receipt.get('reconciled_attempt_id') and receipt.get('finished_at') and receipt.get('reconciliation_outcome'):
            resolved.add(receipt['reconciled_attempt_id'])
    return sorted(x for x in intents - resolved if isinstance(x, str))


@contextmanager
def _lease(root, owner):
    state = _bound(root, STATE)
    state.mkdir(parents=True, exist_ok=True)
    lock_path = _bound(root, STATE + '/live-owner.lock')
    with lock_path.open('a+') as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('another live project control owner holds this project') from error
        stream.seek(0)
        stream.truncate()
        stream.write(json.dumps({'owner': owner, 'pid': os.getpid(), 'acquired_at': _now()}))
        stream.flush()
        os.fsync(stream.fileno())
        try:
            yield state
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def _write_evidence(state, receipt):
    path = state / (receipt['attempt_id'] + '.json')
    with path.open('x') as stream:
        json.dump(receipt, stream, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(state, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    return str(path)


def run_controls(root, manifest, feature_id=None, control_id=None, task_class='maintenance', owner=None,
                 reconcile_attempt_id=None):
    """Drive one explicitly mapped route serially, retaining failure and cleanup evidence."""
    root = _root(root)
    controls, features = _validate(root, manifest)
    if task_class not in CLASSES or task_class == 'generation':
        raise ValueError('run requires maintenance, fix, or forensics; generation uses generate')
    if (feature_id is None) == (control_id is None):
        raise ValueError('select exactly one feature or control')
    feature = features.get(feature_id) if feature_id else None
    if feature_id and feature is None or control_id and control_id not in controls:
        raise ValueError('selected feature/control is not declared')
    route = feature['route'] if feature else [control_id]
    if reconcile_attempt_id is not None and (feature or not controls[control_id].get('reconciliation_outcome')):
        raise ValueError('reconciliation requires a selected qualified target observer control')
    recovery = [feature.get('reset_control'), feature.get('cleanup_control')] if feature else []
    for identifier in route + [x for x in recovery if x]:
        if task_class not in controls[identifier]['classes']:
            raise ValueError('selected task class lacks authority for control ' + identifier)
    owner = owner or str(uuid.uuid4())
    _nonempty(owner, 'owner')
    started = time.monotonic()
    with _lease(root, owner) as state:
        freshness = doctor(root, manifest)
        if reconcile_attempt_id is not None and reconcile_attempt_id not in freshness['unreconciled_attempts']:
            raise ValueError('reconciliation must name an actual unreconciled intent')
        receipt = {'schema_version': 1, 'attempt_id': str(uuid.uuid4()), 'owner': owner,
                   'project_root': str(root), 'manifest_sha256': _digest(json.dumps(manifest, sort_keys=True).encode()),
                   'task_class': task_class, 'feature': feature_id, 'control': control_id,
                   'started_at': _now(), 'status': 'blocked', 'effect_state': 'not-dispatched',
                   'doctor': freshness, 'results': [], 'reset_results': [], 'cleanup_results': [],
                   'oracle_verified': False}
        observation_only = all(controls[x]['effect'] == 'read-only' for x in route)
        if not freshness['fresh'] or manifest['readiness']['driver'] == 'missing':
            receipt['reason'] = 'stale_or_missing_driver'
        elif freshness['unreconciled_attempts'] and not observation_only:
            receipt['reason'] = 'prior_effects_unknown_requires_target_reconciliation'
        else:
            # Persist dispatch intent before external effects. A process crash leaves
            # an open attempt requiring project-specific reconciliation, not replay.
            intent = dict(receipt, status='admitted', effect_state='unknown')
            _write_evidence(state, intent)
            receipt['attempt_id'] = str(uuid.uuid4())
            receipt['intent_attempt_id'] = intent['attempt_id']

            def execute(identifier):
                control = controls[identifier]
                environment = dict(os.environ, RDD_CONTROL_OWNER=owner,
                                   RDD_CONTROL_STATE=str(state), RDD_CONTROL_PROJECT=str(root))
                try:
                    result = run_process(control['argv'], _bound(root, control['cwd'], must_exist=True),
                                         timeout=control['timeout_seconds'],
                                         max_bytes=control.get('max_output_bytes', 1048576), env=environment)
                    passed = result['status'] == 'completed' and result['exit_code'] in control.get('expected_exit_codes', [0])
                    return {'control': identifier, 'role': control['role'], 'status': result['status'],
                            'exit_code': result['exit_code'], 'passed': passed, 'elapsed_seconds': result['elapsed'],
                            'stdout': result['stdout'].decode('utf-8', errors='replace'),
                            'stderr': result['stderr'].decode('utf-8', errors='replace'),
                            'effect_state': 'unknown' if not passed else 'command-completed',
                            'command': control['argv'], 'cwd': control['cwd']}
                except OSError as error:
                    return {'control': identifier, 'role': control['role'], 'status': 'launch-failed',
                            'passed': False, 'effect_state': 'not-dispatched', 'detail': str(error)}

            receipt['status'] = 'clean'
            try:
                for identifier in route:
                    result = execute(identifier)
                    receipt['results'].append(result)
                    if not result['passed']:
                        receipt['status'] = 'blocked'
                        receipt['reason'] = 'failed_control_requires_inspection'
                        if feature and feature.get('reset_control'):
                            reset = execute(feature['reset_control'])
                            receipt['reset_results'].append(reset)
                            # Re-doctor records recovery readiness; no blind replay of
                            # an action whose target effects may already have committed.
                            receipt['after_reset_doctor'] = doctor(root, manifest)
                        break
            finally:
                if feature and feature.get('cleanup_control'):
                    receipt['cleanup_results'].append(execute(feature['cleanup_control']))
            all_results = receipt['results'] + receipt['reset_results'] + receipt['cleanup_results']
            if any(not r['passed'] for r in receipt['cleanup_results']):
                receipt['status'] = 'blocked'
                receipt['reason'] = 'owned_cleanup_failed'
            if any(r['effect_state'] == 'unknown' for r in all_results):
                receipt['effect_state'] = 'unknown'
            elif all(r['effect_state'] == 'not-dispatched' for r in all_results):
                receipt['effect_state'] = 'not-dispatched'
            else:
                receipt['effect_state'] = 'commands-completed'
            after = doctor(root, manifest)
            receipt['after_doctor'] = after
            if not after['fresh']:
                receipt['status'] = 'changed' if task_class == 'fix' else 'blocked'
                receipt['reason'] = 'product_changed_requires_review_and_fresh_controls'
            if manifest['readiness']['oracle'] == 'missing':
                receipt['acceptance_gap'] = 'independent oracle missing; command completion is not acceptance'
            if reconcile_attempt_id and receipt['status'] == 'clean' and all(r['passed'] for r in all_results):
                receipt['reconciled_attempt_id'] = reconcile_attempt_id
                receipt['reconciliation_outcome'] = controls[control_id]['reconciliation_outcome']
                receipt['reconciliation_scope'] = controls[control_id]['reconciliation_scope']
        receipt['elapsed_seconds'] = time.monotonic() - started
        receipt['finished_at'] = _now()
        receipt['evidence_path'] = str(state / (receipt['attempt_id'] + '.json'))
        _write_evidence(state, receipt)
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('inspect', 'generate', 'doctor', 'run'))
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--blueprint', type=Path)
    parser.add_argument('--output')
    parser.add_argument('--source-root', action='append')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--feature')
    group.add_argument('--control')
    parser.add_argument('--class', dest='task_class', choices=sorted(CLASSES), default='maintenance')
    parser.add_argument('--reconcile-attempt', help='pending intent ID, with a declared read-only target observer')
    args = parser.parse_args()
    root = _root(args.root)
    if args.operation == 'inspect':
        result = inspect_project(root, args.source_root)
    elif args.operation == 'generate':
        blueprint = _json(args.blueprint.read_text()) if args.blueprint else {}
        result = generate(root, blueprint, args.output)
    else:
        manifest_path = args.manifest or root / STATE / 'manifest.json'
        manifest = _json(manifest_path.read_text())
        result = doctor(root, manifest) if args.operation == 'doctor' else run_controls(
            root, manifest, feature_id=args.feature, control_id=args.control, task_class=args.task_class,
            reconcile_attempt_id=args.reconcile_attempt)
    print(json.dumps(result, indent=2))
    if args.operation == 'doctor':
        return 0 if result['ready_for_declared_route'] else 2
    if args.operation == 'run':
        return 0 if result['status'] in ('clean', 'changed') else 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
