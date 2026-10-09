#!/usr/bin/env python3
"""Select and resolve exact pinned procedures for a native factory lead.

This is a material-integrity/source-selection operation. It does not execute
upstream commands, change models, dispatch workers, or establish application.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
import stat
import sys

REVISION = 'ccb5507cec1546dc88135c1139c811e6c59115ba'
VENDOR = Path(__file__).resolve().parents[1] / 'upstream' / 'pstack'
MAX_BYTES = 4 * 1024 * 1024


def _path(value):
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError('source path must be a nonempty POSIX path')
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {'..', '.'} for part in value.split('/')):
        raise ValueError('unsafe source path: ' + value)
    if str(path) != value:
        raise ValueError('noncanonical source path: ' + value)
    return path


def _bytes(path):
    info = path.lstat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('source entry must be a regular file: ' + str(path))
    if info.st_size > MAX_BYTES:
        raise ValueError('source entry exceeds byte bound: ' + str(path))
    return path.read_bytes()


def load(vendor=VENDOR):
    vendor = Path(vendor)
    if vendor.is_symlink() or not vendor.is_dir():
        raise ValueError('vendor must be a real directory')
    raw = _bytes(vendor / 'manifest.json')
    try:
        manifest = json.loads(raw)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid source manifest') from exc
    source = manifest.get('source', {})
    if (manifest.get('format_version') != 1 or
            source.get('repository') != 'cursor/plugins' or
            source.get('revision') != REVISION or source.get('license') != 'MIT'):
        raise ValueError('unsupported source pin/license')
    entries, installed, total = {}, set(), 0
    records = manifest.get('source_files')
    if not isinstance(records, list) or not records:
        raise ValueError('source inventory is missing')
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('source record must be an object')
        original = record.get('original_path')
        relative = record.get('installed_path')
        orig_path, target_path = _path(original), _path(relative)
        if (orig_path.parts[0] != 'pstack' or target_path.parts[:2] != ('sources', 'pstack') or
                original in entries or relative in installed):
            raise ValueError('invalid or duplicate source mapping')
        if target_path.name == 'SKILL.md':
            raise ValueError('nested active SKILL.md is prohibited')
        expected_path = 'sources/' + original + ('.source' if original.endswith('.md') else '')
        if relative != expected_path:
            raise ValueError('source rename differs from explicit map: ' + original)
        data = _bytes(vendor / relative)
        total += len(data)
        if total > MAX_BYTES:
            raise ValueError('source closure exceeds byte bound')
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if (type(record.get('bytes')) is not int or len(data) != record['bytes'] or
                hashlib.sha256(data).hexdigest() != record.get('sha256') or
                blob != record.get('git_blob_sha1')):
            raise ValueError('source material changed: ' + original)
        entries[original] = record
        installed.add(relative)
    if 'pstack/LICENSE' not in entries or not _bytes(vendor / entries['pstack/LICENSE']['installed_path']).startswith(b'MIT License\n'):
        raise ValueError('original MIT license is missing')
    expected = installed | {'manifest.json', 'README.md'}
    actual = set()
    for path in vendor.rglob('*'):
        if path.is_symlink():
            raise ValueError('symlink in source closure: ' + str(path))
        if path.is_file():
            actual.add(path.relative_to(vendor).as_posix())
    if actual != expected:
        raise ValueError('source inventory drift: missing=' + str(sorted(expected - actual)) +
                         ', extra=' + str(sorted(actual - expected)))
    for group in ('procedures', 'conditional_modules'):
        modules = manifest.get(group)
        if not isinstance(modules, dict) or not modules:
            raise ValueError('procedure selection map missing: ' + group)
        for name, module in modules.items():
            if not isinstance(module, dict):
                raise ValueError('selection module must be an object: ' + name)
            paths = module.get('read_paths')
            if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)):
                raise ValueError('invalid ordered read paths: ' + name)
            if any(path not in entries for path in paths):
                raise ValueError('unretained procedure dependency: ' + name)
    for name, procedure in manifest['procedures'].items():
        required = procedure.get('required_modules', [])
        if (not isinstance(required, list) or
                any(item not in manifest['conditional_modules'] for item in required)):
            raise ValueError('unknown required procedure module: ' + name)
    return manifest, entries, hashlib.sha256(raw).hexdigest()


def select(task_class, include=(), vendor=VENDOR):
    manifest, entries, digest = load(vendor)
    procedures = manifest['procedures']
    if task_class not in procedures:
        raise ValueError('unknown task class: ' + str(task_class))
    procedure = procedures[task_class]
    paths = list(procedure['read_paths'])
    chosen = []
    for condition in procedure.get('required_modules', []) + list(include):
        module = manifest['conditional_modules'].get(condition)
        if module is None:
            raise ValueError('unknown conditional module: ' + str(condition))
        if condition not in chosen:
            chosen.append(condition)
            paths.extend(module['read_paths'])
    paths = list(dict.fromkeys(paths))
    reads = [{'original_path': path,
              'installed_path': entries[path]['installed_path'],
              'file': str(Path(vendor) / entries[path]['installed_path']),
              'sha256': entries[path]['sha256'], 'bytes': entries[path]['bytes']}
             for path in paths]
    identity = json.dumps({'revision': REVISION, 'manifest_sha256': digest,
                           'task_class': task_class, 'conditional_modules': chosen,
                           'ordered_sources': [{'original_path': path,
                                                'sha256': entries[path]['sha256']}
                                               for path in paths]}, sort_keys=True,
                          separators=(',', ':')).encode()
    return {'format_version': 1, 'source': manifest['source'],
            'manifest_sha256': digest,
            'source_closure_sha256': hashlib.sha256(identity).hexdigest(),
            'task_class': task_class, 'conditional_modules': chosen,
            'required_modules': procedure.get('required_modules', []),
            'ordered_reads': reads, 'roles': procedure['roles'],
            'required_inputs': ['full original objective and all current corrections',
                                'actual project/surface and candidate identity',
                                'authorized stage/write/effect scope',
                                'current verified native capabilities and role identities',
                                'complete required acceptance obligations and unresolved conditions'],
            'required_outputs': procedure['required_outputs'],
            'write_scope': procedure['write_scope'],
            'adaptations': manifest['adaptations'],
            'conditional_options': {name: value['when'] for name, value in
                                    manifest['conditional_modules'].items()},
            'limits': {'source_integrity_verified': True,
                       'procedure_applied': False,
                       'native_driver_qualified': False,
                       'upstream_commands_executed': False,
                       'note': 'Lead must read selected bytes and bind their relevant properties to actual producing/control assignments. Selection is not execution or fidelity proof.'}}


def resolve(original_path, reference, vendor=VENDOR):
    _, entries, _ = load(vendor)
    if original_path not in entries:
        raise ValueError('unretained source origin')
    if not isinstance(reference, str) or not reference:
        raise ValueError('reference must be nonempty')
    if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', reference) or reference.startswith('//'):
        return {'kind': 'external_reference', 'reference': reference,
                'fetched': False, 'qualified': False}
    reference_path = reference.split('#', 1)[0]
    normalized = (original_path if not reference_path else
                  posixpath.normpath(posixpath.join(posixpath.dirname(original_path), reference_path)))
    _path(normalized)
    if normalized not in entries:
        raise ValueError('reference dependency not retained: ' + normalized)
    record = entries[normalized]
    return {'kind': 'retained_source', 'original_path': normalized,
            'installed_path': record['installed_path'],
            'file': str(Path(vendor) / record['installed_path']),
            'sha256': record['sha256']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--vendor', type=Path, default=VENDOR)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('validate')
    chosen = commands.add_parser('select')
    chosen.add_argument('task_class')
    chosen.add_argument('--include', action='append', default=[])
    reader = commands.add_parser('read')
    reader.add_argument('original_path')
    resolver = commands.add_parser('resolve')
    resolver.add_argument('original_path')
    resolver.add_argument('reference')
    args = parser.parse_args()
    try:
        if args.command == 'select':
            result = select(args.task_class, args.include, args.vendor)
        elif args.command == 'resolve':
            result = resolve(args.original_path, args.reference, args.vendor)
        else:
            manifest, entries, digest = load(args.vendor)
            if args.command == 'read':
                if args.original_path not in entries:
                    raise ValueError('unretained source path')
                sys.stdout.buffer.write(_bytes(args.vendor / entries[args.original_path]['installed_path']))
                return
            result = {'source': manifest['source'], 'manifest_sha256': digest,
                      'source_files': len(entries), 'source_bytes': sum(e['bytes'] for e in entries.values()),
                      'task_classes': list(manifest['procedures']),
                      'conditional_modules': list(manifest['conditional_modules']),
                      'material_integrity': 'verified', 'procedure_application': 'unobserved',
                      'limit': 'Git blob/SHA256 hashes verify retained bytes against this manifest; they are not an independent signature or live effectiveness proof.'}
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, 'Procedure selection blocked: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
