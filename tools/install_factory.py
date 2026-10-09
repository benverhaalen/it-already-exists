#!/usr/bin/env python3
"""Stage and activate reversible RDD skill releases in native discovery roots.

No model, background service, plugin manager or project-state migration runs.
The maintenance lock coordinates this installer, not arbitrary external writers.
"""
import argparse
import base64
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import shutil
import stat
import subprocess
import sys
import tempfile
import zipfile

_spec = importlib.util.spec_from_file_location('rdd_package', Path(__file__).with_name('package_rdd.py'))
package = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(package)
NAME = package.NAME
VERSION = 1
START = b'<!-- reference-factory:start -->'
END = b'<!-- reference-factory:end -->'
POLICY = b'''<!-- reference-factory:start -->
## Reference-driven factory

For substantial product or artifact creation, improvement, or reconstruction, use the
installed `reference-driven-development` skill. Read its `references/factory.md`
when relevant. Recover the full objective, constraints, references, and current
project state before selecting methods. Preserve useful reference mechanisms,
research consequential unknowns, and verify the complete requested journey.
Keep simple tasks direct. Keep the native conversation, model, permissions, and
existing global policy in control. Do not start unrelated background jobs.
<!-- reference-factory:end -->'''


class InstallError(ValueError):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def default_store(home):
    return Path(home) / '.local/share/it-already-exists/factory'


def roots(home):
    home = Path(home)
    return {'codex': home / '.agents/skills' / NAME,
            'claude': home / '.claude/skills' / NAME}


def policy_roots(home):
    home = Path(home)
    return {'codex': home / '.codex/AGENTS.md', 'claude': home / '.claude/CLAUDE.md'}


def native_executable(host, home):
    found = shutil.which(host)
    if found:
        return found
    # Claude's native installer commonly exposes this outside an agent shell's
    # PATH. Checking a path is not a launch, authentication or version receipt.
    candidates = [Path(home) / '.local/bin' / host]
    if host == 'claude':
        candidates.append(Path(home) / '.claude/local/claude')
    return next((str(path) for path in candidates if path.is_file() and os.access(path, os.X_OK)), None)


def require_directory(path):
    path = Path(path)
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise InstallError('directory collision: ' + str(path))
    # Refuse symlink ancestors: installation may not silently redirect ownership.
    for parent in path.parents:
        if parent.is_symlink():
            aliases = {'/var': '/private/var', '/tmp': '/private/tmp', '/etc': '/private/etc'}
            if platform.system() == 'Darwin' and aliases.get(str(parent)) == str(parent.resolve()):
                continue  # Standard macOS filesystem aliases are not user entry redirections.
            raise InstallError('symlink ancestor: ' + str(parent))
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextmanager
def maintenance(store):
    store = require_directory(store)
    lock = store / 'maintenance.lock'
    if lock.is_symlink() or (lock.exists() and not lock.is_file()):
        raise InstallError('unsafe maintenance lock')
    with lock.open('a+b') as stream:
        os.chmod(lock, 0o600)
        fcntl.flock(stream, fcntl.LOCK_EX)
        yield


def empty_state():
    return {'schema_version': VERSION, 'package': NAME, 'active_release': None,
            'installations': {}, 'policies': {}, 'history': []}


def load_state(store):
    path = Path(store) / 'installation.json'
    if path.is_symlink():
        raise InstallError('unsafe installation registry')
    if not path.exists():
        return empty_state()
    state = json.loads(path.read_text())
    if state.get('schema_version') != VERSION or state.get('package') != NAME:
        raise InstallError('unsupported installation state; preserve it and use its matching installer')
    return state


UNSPECIFIED = object()


def atomic_file(path, data, expected=UNSPECIFIED, mode=0o600):
    path = Path(path)
    require_directory(path.parent)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise InstallError('file collision: ' + str(path))
    current = path.read_bytes() if path.exists() else None
    if expected is not UNSPECIFIED and current != expected:
        raise InstallError('concurrent file change: ' + str(path))
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        if (path.read_bytes() if path.exists() else None) != current:
            raise InstallError('concurrent file change: ' + str(path))
        os.replace(name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.lexists(name):
            os.unlink(name)


def save_state(store, state):
    atomic_file(Path(store) / 'installation.json', (json.dumps(state, indent=2, sort_keys=True) + '\n').encode())


def archive_inventory(payload, *, current_only=True):
    """Validate before extraction: positive paths, inventory, bytes and licenses."""
    files = {}
    if len(payload) > package.LIMIT:
        raise InstallError('archive exceeds byte bound')
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            total = 0
            for entry in archive.infolist():
                prefix = NAME + '/'
                if not entry.filename.startswith(prefix) or entry.is_dir():
                    raise InstallError('unexpected archive entry')
                name = entry.filename[len(prefix):]
                package.safe_relative(name)
                kind = stat.S_IFMT(entry.external_attr >> 16)
                if kind not in {0, stat.S_IFREG} or name in files:
                    raise InstallError('duplicate or non-regular archive entry')
                if entry.file_size > package.LIMIT - total:
                    raise InstallError('expanded archive exceeds byte bound')
                data = archive.read(entry)
                total += len(data)
                files[name] = data
    except (zipfile.BadZipFile, RuntimeError) as exc:
        raise InstallError('invalid archive: ' + str(exc)) from exc
    try:
        manifest = json.loads(files['package-manifest.json'])
        if (type(manifest['schema_version']) is not int
                or manifest['schema_version'] != 1 or manifest['package'] != NAME):
            raise InstallError('unsupported package manifest')
        listed = manifest['files']
        inventory_version, reviewed_files = package.reviewed_inventory(manifest)
        if current_only and inventory_version != package.INVENTORY_VERSION:
            raise InstallError('archive requires current factory inventory version')
        if set(files) != set(listed) | {'package-manifest.json'}:
            raise InstallError('package inventory mismatch')
        for name, info in listed.items():
            package.safe_relative(name)
            if not package.allowed(Path(name), reviewed_files):
                raise InstallError('unreviewed package path: ' + name)
            if (not isinstance(info, dict) or type(info.get('bytes')) is not int
                    or info['bytes'] < 0 or not isinstance(info.get('sha256'), str)
                    or len(info['sha256']) != 64
                    or any(char not in '0123456789abcdef' for char in info['sha256'])):
                raise InstallError('invalid package file metadata: ' + name)
            data = files[name]
            if len(data) != info['bytes'] or digest(data) != info['sha256']:
                raise InstallError('package digest mismatch: ' + name)
        if 'scripts/factory_procedures.py' in files and 'upstream/pstack/manifest.json' not in files:
            raise InstallError('procedure selector lacks its original-source closure')
        package.validate_upstream(files)
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise InstallError('invalid package manifest: ' + str(exc)) from exc
    return files, manifest


def qualify_helpers(skill):
    """Exercise owned core entry points from copied files with an isolated home.

    This is import/CLI qualification, not execution of a project or a model.
    The reviewed public membership prevents arbitrary extra entry points.
    """
    with tempfile.TemporaryDirectory(prefix='rdd-cold-cli-') as scratch:
        home = Path(scratch) / 'home'
        home.mkdir()
        environment = {'PATH': os.environ.get('PATH', ''), 'HOME': str(home),
                       'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONNOUSERSITE': '1', 'PYTHONPATH': ''}
        for name in ('factory.py', 'factory_procedures.py', 'project_controls.py'):
            try:
                result = subprocess.run([sys.executable, '-B', str(Path(skill) / 'scripts' / name), '--help'],
                                        cwd=scratch, env=environment, text=True, capture_output=True, timeout=15)
            except subprocess.TimeoutExpired as exc:
                raise InstallError('cold CLI import timed out for ' + name) from exc
            if result.returncode:
                raise InstallError('cold CLI import failed for ' + name + ': ' + result.stderr[:2000])
        try:
            result = subprocess.run([sys.executable, '-B', str(Path(skill) / 'scripts/factory_procedures.py'), 'validate'],
                                    cwd=scratch, env=environment, text=True, capture_output=True, timeout=15)
        except subprocess.TimeoutExpired as exc:
            raise InstallError('copied source selector validation timed out') from exc
        if result.returncode:
            raise InstallError('copied source selector validation failed: ' + result.stderr[:2000])
    return {'status': 'passed', 'entry_points': ['factory.py', 'factory_procedures.py', 'project_controls.py'],
            'python': platform.python_version(), 'model_calls': 0, 'scope': 'CLI imports/help only'}


def inspect_release(store, release):
    if not isinstance(release, str) or len(release) != 64 or any(c not in '0123456789abcdef' for c in release):
        raise InstallError('invalid release identity')
    root = Path(store) / 'releases' / release
    if root.is_symlink() or not root.is_dir():
        raise InstallError('release missing or redirected: ' + release)
    if set(p.name for p in root.iterdir()) != {'capsule.zip', 'receipt.json', NAME}:
        raise InstallError('release root inventory drift: ' + release)
    if (root / 'capsule.zip').is_symlink() or (root / 'receipt.json').is_symlink():
        raise InstallError('release metadata redirected')
    payload = (root / 'capsule.zip').read_bytes()
    if digest(payload) != release:
        raise InstallError('archive identity drift')
    files, manifest = archive_inventory(payload, current_only=False)
    skill = root / NAME
    if skill.is_symlink() or not skill.is_dir():
        raise InstallError('skill root redirected')
    observed, directories = {}, set()
    for directory, children, names in os.walk(skill, followlinks=False):
        for child in children:
            path = Path(directory) / child
            if path.is_symlink():
                raise InstallError('release directory redirected')
            directories.add(path.relative_to(skill).as_posix())
        for name in names:
            path = Path(directory) / name
            if path.is_symlink() or not path.is_file():
                raise InstallError('release file redirected')
            observed[path.relative_to(skill).as_posix()] = path.read_bytes()
    expected_dirs = {parent.as_posix() for name in files for parent in Path(name).parents if parent != Path('.')}
    if observed != files or directories != expected_dirs:
        raise InstallError('release content/discovery drift (added, changed or missing entries)')
    qualify_helpers(skill)
    receipt = json.loads((root / 'receipt.json').read_text())
    if (not isinstance(receipt, dict) or type(receipt.get('schema_version')) is not int
            or receipt['schema_version'] != 1 or receipt.get('package') != NAME
            or receipt.get('release') != release or type(receipt.get('files')) is not int
            or receipt['files'] != len(manifest['files'])):
        raise InstallError('release receipt mismatch')
    inventory_version, _ = package.reviewed_inventory(manifest)
    if 'inventory_version' in receipt and (type(receipt['inventory_version']) is not int
                                          or receipt['inventory_version'] != inventory_version):
        raise InstallError('release receipt inventory mismatch')
    return {**receipt, 'inventory_version': inventory_version}


def stage(store, source=None, archive=None):
    store = require_directory(store)
    releases = require_directory(store / 'releases')
    if archive is not None:
        payload = Path(archive).read_bytes()
    else:
        with tempfile.TemporaryDirectory(prefix='rdd-package-') as scratch:
            output = Path(scratch) / 'capsule.zip'
            package.build(source or package.SOURCE, output)
            payload = output.read_bytes()
    files, manifest = archive_inventory(payload)
    release = digest(payload)
    final = releases / release
    if final.exists() or final.is_symlink():
        return inspect_release(store, release)
    temporary = Path(tempfile.mkdtemp(prefix='.stage-', dir=releases))
    try:
        skill = temporary / NAME
        skill.mkdir()
        for name, data in files.items():
            path = skill / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        cold_cli = qualify_helpers(skill)
        receipt = {'schema_version': 1, 'package': NAME, 'release': release,
                   'inventory_version': package.reviewed_inventory(manifest)[0],
                   'files': len(manifest['files']), 'staged_at': now(),
                   'cold_cli_imports': cold_cli,
                   'skill_root': str(final / NAME), 'source': str(Path(source).resolve()) if source and archive is None else None,
                   'license_scope': 'Included original licenses; no blanket legal clearance.',
                   'state_compatibility': 'Installation schema 1 only; project/native state is not migrated.',
                   'activation': 'staged_only; native discovery/invocation not demonstrated'}
        (temporary / 'capsule.zip').write_bytes(payload)
        (temporary / 'receipt.json').write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
        for path in temporary.rglob('*'):
            os.chmod(path, 0o555 if path.is_dir() else 0o444)
        os.chmod(temporary, 0o555)
        os.rename(temporary, final)
        return inspect_release(store, release)
    finally:
        if temporary.exists():
            for path in temporary.rglob('*'):
                os.chmod(path, 0o755 if path.is_dir() else 0o644)
            os.chmod(temporary, 0o755)
            shutil.rmtree(temporary)


def link_snapshot(path):
    path = Path(path)
    if path.is_symlink():
        return {'kind': 'symlink', 'target': os.readlink(path)}
    if path.exists():
        raise InstallError('unowned skill collision: ' + str(path))
    return {'kind': 'absent'}


def replace_link(path, expected, desired):
    path = Path(path)
    if link_snapshot(path) != expected:
        raise InstallError('skill pointer changed: ' + str(path))
    require_directory(path.parent)
    if desired['kind'] == 'absent':
        if expected['kind'] != 'absent':
            path.unlink()
            sync_directory(path.parent)
        return
    temporary = path.parent / ('.' + path.name + '.' + next(tempfile._get_candidate_names()))
    try:
        temporary.symlink_to(desired['target'])
        if link_snapshot(path) != expected:
            raise InstallError('concurrent skill pointer change: ' + str(path))
        os.replace(temporary, path)
        sync_directory(path.parent)
    finally:
        if temporary.is_symlink():
            temporary.unlink()


def policy_bytes(path):
    path = Path(path)
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise InstallError('unowned policy collision: ' + str(path))
    return path.read_bytes() if path.exists() else b''


def sync_directory(path):
    directory = os.open(path, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def policy_block(data):
    if START not in data and END not in data:
        return None
    if data.count(START) != 1 or data.count(END) != 1 or data.index(END) < data.index(START):
        raise InstallError('ambiguous managed policy block')
    return data[data.index(START):data.index(END) + len(END)]


def backup_policy(store, data):
    folder = require_directory(Path(store) / 'policy-backups')
    path = folder / digest(data)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != data:
            raise InstallError('policy backup collision')
    else:
        with path.open('xb') as stream:
            stream.write(data)
        os.chmod(path, 0o600)
    return str(path)


def read_policy_backup(change):
    path = Path(change['backup'])
    if path.is_symlink() or not path.is_file():
        raise InstallError('policy backup missing or redirected')
    data = path.read_bytes()
    if digest(data) != change['original_sha256']:
        raise InstallError('policy backup drift')
    return data


def replace_policy(change, reverse=False):
    path = Path(change['path'])
    existed = path.exists()
    data = policy_bytes(path)
    before = base64.b64decode(change['before_block']) if change['before_block'] else None
    after = base64.b64decode(change['after_block']) if change['after_block'] else None
    expected, desired = (after, before) if reverse else (before, after)
    block = policy_block(data)
    if block == desired:
        return
    if block != expected:
        raise InstallError('managed policy drift: ' + str(path))
    if desired is None:
        if digest(data) == change['published_sha256']:
            updated = read_policy_backup(change)
        else:
            updated = data.replace(expected, b'', 1)  # Preserve subsequent outside-block edits.
    elif expected is None:
        updated = data + (b'\n\n' if data else b'') + desired + b'\n'
    else:
        updated = data.replace(expected, desired, 1)
    if not updated and not change['original_exists']:
        if policy_bytes(path) != data:
            raise InstallError('concurrent policy change')
        if path.exists():
            path.unlink()
    else:
        atomic_file(path, updated, expected=data if existed else None,
                    mode=change['original_mode'] if change['original_exists'] else 0o600)


def apply_change(change, reverse=False):
    if change['type'] == 'policy':
        replace_policy(change, reverse)
    else:
        expected, desired = (change['after'], change['before']) if reverse else (change['before'], change['after'])
        observed = link_snapshot(change['path'])
        if observed == desired:
            return
        replace_link(change['path'], expected, desired)


def transition(store, before, after, changes):
    if before.get('pending'):
        raise InstallError('pending maintenance; run recover before another change')
    pending = dict(before)
    pending['pending'] = {'started_at': now(), 'after': after, 'changes': changes}
    save_state(store, pending)  # Durable recovery intent precedes discovery effects.
    for change in changes:
        apply_change(change)
    save_state(store, after)
    return after


def state_snapshot(state):
    return {key: state[key] for key in ('active_release', 'installations', 'policies')}


def activate(home, store, release, source=package.SOURCE, enable_policy=False):
    inspect_release(store, release)
    state = load_state(store)
    if state.get('pending'):
        raise InstallError('pending maintenance; run recover first')
    if state['active_release']:
        inspect_release(store, state['active_release'])
    after = json.loads(json.dumps(state))
    changes = []
    target = str(Path(store).resolve() / 'releases' / release / NAME)
    for host, path in roots(home).items():
        observed = link_snapshot(path)
        owned = state['installations'].get(host)
        if owned:
            if str(path) != owned['path'] or observed != owned['current']:
                raise InstallError('owned skill pointer drift: ' + str(path))
            baseline = owned['baseline']
        else:
            # Only this precise canonical source entry may be migrated. A random
            # symlink, even into another release store, remains user-owned.
            if observed['kind'] == 'symlink' and observed['target'] != str(Path(source).absolute()):
                raise InstallError('unowned skill symlink: ' + str(path))
            baseline = observed
        desired = {'kind': 'symlink', 'target': target}
        after['installations'][host] = {'path': str(path), 'baseline': baseline, 'current': desired}
        if observed != desired:
            changes.append({'type': 'link', 'path': str(path), 'before': observed, 'after': desired})
    if enable_policy:
        for host, path in policy_roots(home).items():
            data = policy_bytes(path)
            block = policy_block(data)
            owned = state['policies'].get(host)
            if owned:
                if block != POLICY or str(path) != owned['path']:
                    raise InstallError('managed policy drift: ' + str(path))
                continue
            if block is not None:
                raise InstallError('unowned policy block: ' + str(path))
            backup = backup_policy(store, data)
            published = data + (b'\n\n' if data else b'') + POLICY + b'\n'
            record = {'path': str(path), 'backup': backup, 'original_exists': path.exists(),
                      'original_mode': stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o600,
                      'original_sha256': digest(data), 'published_sha256': digest(published),
                      'block_sha256': digest(POLICY)}
            after['policies'][host] = record
            changes.append({'type': 'policy', **record, 'before_block': None,
                            'after_block': base64.b64encode(POLICY).decode()})
    after['active_release'] = release
    if state_snapshot(after) == state_snapshot(state):
        return state
    after['history'].append(state_snapshot(state))
    after['updated_at'] = now()
    return transition(store, state, after, changes)


def restore_state(store, state, snapshot, history):
    changes = []
    # Preflight every owned entry before touching any target.
    for host, owned in state['installations'].items():
        if link_snapshot(owned['path']) != owned['current']:
            raise InstallError('owned skill pointer drift: ' + owned['path'])
        replacement = snapshot['installations'].get(host)
        desired = replacement['current'] if replacement else owned['baseline']
        if desired != owned['current']:
            changes.append({'type': 'link', 'path': owned['path'], 'before': owned['current'], 'after': desired})
    for host, owned in state['policies'].items():
        if policy_block(policy_bytes(owned['path'])) != POLICY:
            raise InstallError('managed policy drift: ' + owned['path'])
        read_policy_backup(owned)
        if host not in snapshot['policies']:
            changes.append({'type': 'policy', **owned,
                            'before_block': base64.b64encode(POLICY).decode(), 'after_block': None})
    after = {**empty_state(), **snapshot, 'history': history, 'updated_at': now()}
    if after['active_release']:
        inspect_release(store, after['active_release'])
    return transition(store, state, after, changes)


def rollback(store):
    state = load_state(store)
    if state.get('pending'):
        raise InstallError('pending maintenance; run recover first')
    if not state['history']:
        raise InstallError('no previous installation state')
    return restore_state(store, state, state['history'][-1], state['history'][:-1])


def remove(store):
    state = load_state(store)
    if state.get('pending'):
        raise InstallError('pending maintenance; run recover first')
    return restore_state(store, state, state_snapshot(empty_state()), [])


def recover(store, action):
    state = load_state(store)
    pending = state.get('pending')
    if not pending:
        return state
    changes = pending['changes']
    selected = pending['after']['active_release'] if action == 'complete' else state['active_release']
    if selected:
        inspect_release(store, selected)
    for change in reversed(changes) if action == 'rollback' else changes:
        apply_change(change, reverse=action == 'rollback')
    if action == 'complete':
        state = pending['after']
    else:
        del state['pending']
    save_state(store, state)
    return state


def doctor(home, store, release=None):
    state = load_state(store)
    selected = release or state['active_release']
    errors = []
    content = 'not_staged'
    inventory_version = None
    if selected:
        try:
            inventory_version = inspect_release(store, selected)['inventory_version']
            content = 'verified_complete_inventory'
        except (ValueError, OSError) as exc:
            errors.append(str(exc))
            content = 'drift_or_missing'
    hosts = {}
    for host, path in roots(home).items():
        owned = state['installations'].get(host)
        try:
            observed = link_snapshot(path)
            pointer = 'owned_pointer_installed' if owned and observed == owned['current'] else 'not_owned'
            if owned and observed != owned['current']:
                errors.append('owned skill pointer drift: ' + str(path))
                pointer = 'drift'
        except ValueError as exc:
            errors.append(str(exc))
            pointer = 'unowned_collision'
        policy = state['policies'].get(host)
        policy_status = 'not_enabled'
        if policy:
            try:
                policy_status = 'owned_block_enabled' if policy_block(policy_bytes(policy['path'])) == POLICY else 'drift'
                if policy_status == 'drift':
                    errors.append('managed policy drift: ' + policy['path'])
            except ValueError as exc:
                policy_status = 'drift'
                errors.append(str(exc))
        hosts[host] = {'entry': str(path), 'installation': pointer, 'policy': policy_status,
                       'native_cli': native_executable(host, home),
                       'native_cli_discovery': 'PATH and named native-home locations; version not executed',
                       'inventory_refresh': 'new_session_or_host_refresh_required',
                       'current_session_activation': 'not_demonstrated', 'invocation': 'not_demonstrated',
                       'applied': 'not_demonstrated', 'accepted_product': 'not_demonstrated'}
    return {'schema_version': 1, 'package': NAME, 'active_release': state['active_release'],
            'checked_release': selected, 'content': content, 'hosts': hosts, 'errors': errors,
            'inventory_version': inventory_version, 'current_inventory_version': package.INVENTORY_VERSION,
            'cold_cli_imports': 'passed_current_python' if content == 'verified_complete_inventory' else 'not_qualified',
            'maintenance': 'pending_recovery' if state.get('pending') else 'idle',
            'platform': {'system': platform.system(), 'python': platform.python_version(),
                         'installer_scope': 'POSIX; Windows not qualified'},
            'personal_overlay': str(Path(home) / '.config/it-already-exists/factory'),
            'state_compatibility': 'Installation schema 1 only; no project/native state rewrite.',
            'reader_lifetime': 'All prior release roots retained; active sessions are not restarted.',
            'consistency': 'Installer lock and compared atomic pointer/file replacement; external writers/readers do not share its gate.',
            'model_calls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home(), help='Native discovery home; use a temporary home for qualification.')
    parser.add_argument('--store', type=Path, help='Release/installation store; defaults below --home.')
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('stage', 'install'):
        sub = commands.add_parser(command)
        inputs = sub.add_mutually_exclusive_group()
        inputs.add_argument('--source', type=Path, default=package.SOURCE)
        inputs.add_argument('--archive', type=Path)
        if command == 'install':
            sub.add_argument('--enable-policy', action='store_true', help='Own only the short factory block in existing native global files.')
    activate_parser = commands.add_parser('activate')
    activate_parser.add_argument('release')
    activate_parser.add_argument('--source', type=Path, default=package.SOURCE, help='Exact source symlink that this operation may migrate.')
    activate_parser.add_argument('--enable-policy', action='store_true')
    doctor_parser = commands.add_parser('doctor')
    doctor_parser.add_argument('--release')
    commands.add_parser('status')
    commands.add_parser('rollback')
    commands.add_parser('remove')
    recovery = commands.add_parser('recover')
    recovery.add_argument('action', choices=('complete', 'rollback'))
    args = parser.parse_args()
    home = args.home.absolute()
    store = (args.store or default_store(home)).absolute()
    try:
        if args.command in {'status', 'doctor'}:
            output = doctor(home, store, getattr(args, 'release', None))
        else:
            with maintenance(store):
                if args.command in {'stage', 'install'}:
                    output = stage(store, args.source, args.archive)
                    if args.command == 'install':
                        activate(home, store, output['release'], args.source, args.enable_policy)
                        output = doctor(home, store)
                elif args.command == 'activate':
                    activate(home, store, args.release, args.source, args.enable_policy)
                    output = doctor(home, store)
                elif args.command == 'recover':
                    recover(store, args.action)
                    output = doctor(home, store)
                else:
                    globals()[args.command](store)
                    output = doctor(home, store)
        print(json.dumps(output, indent=2, sort_keys=True))
        if output.get('errors') or output.get('maintenance') == 'pending_recovery':
            return 2
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.exit(2, 'Factory installation blocked: ' + str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
