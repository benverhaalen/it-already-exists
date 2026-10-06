#!/usr/bin/env python3
"""Build a deterministic portable skill ZIP, without repository/private state.

This is a packaging receipt, not a license grant or a harness activation test.
Only the reviewed package layout is accepted. Existing outputs are not replaced.
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import zipfile

NAME = 'reference-driven-development'
SOURCE = Path(__file__).resolve().parents[1] / 'skills' / NAME
LIMIT = 10 * 1024 * 1024


def allowed(path):
    parts = path.parts
    if path.as_posix() in {'SKILL.md', 'agents/openai.yaml', 'LICENSE'}:
        return True
    if path.as_posix() in {
            'scripts/fixtures/arm64_abi/stack-prefix.c',
            'scripts/fixtures/arm64_abi/bridge-control.c',
            'scripts/fixtures/arm64_abi/bridge-control.S',
            'scripts/fixtures/arm64_abi/mixed-control.c',
            'scripts/fixtures/arm64_abi/mixed-control.S',
            'scripts/fixtures/flutter_abi/flutter-tonic.patch',
            'scripts/fixtures/flutter_abi/dart-snapshot.patch',
            'scripts/fixtures/flutter_abi/dart-loopback.patch',
            'scripts/fixtures/flutter_abi/ios-channel-trace.patch',
            'scripts/fixtures/flutter_abi/TONIC-LICENSE',
            'scripts/fixtures/flutter_abi/DART-LICENSE',
            'scripts/fixtures/firebase_core/android-app-id.patch',
            'scripts/fixtures/firebase_core/registry-control.m',
            'scripts/fixtures/firebase_core/LICENSE',
            'scripts/fixtures/firebase_firestore/LocalFirestoreSettings.h',
            'scripts/fixtures/firebase_firestore/local-control.m',
            'scripts/fixtures/stripe_core/local-startup-control.swift',
            'scripts/fixtures/datadog_core/local-transport.swift',
            'scripts/fixtures/datadog_core/crash-control.swift',
            'scripts/fixtures/datadog_core/startup-control.swift',
            'scripts/fixtures/datadog_core/flutter-local-startup.patch',
            'scripts/fixtures/datadog_core/LICENSE',
            'scripts/fixtures/path_provider/android-ios-directories.swift',
            'scripts/fixtures/path_provider/LICENSE',
            'scripts/fixtures/sqflite/RDDSQLiteControl.h',
            'scripts/fixtures/sqflite/RDDSQLiteControl.m',
            'scripts/fixtures/sqflite/standalone-import.patch',
            'scripts/fixtures/sqflite/LICENSE',
            'scripts/fixtures/sqflite/FMDB_LICENSE.txt'}:
        return True
    if len(parts) == 2 and parts[0] == 'scripts':
        return path.suffix == '.py' or parts[1] in {'requirements-comparison.txt', 'requirements-native-profile.txt', 'requirements-service-guard.txt'}
    if len(parts) == 2 and parts[0] == 'references':
        return path.suffix == '.md' or parts[1] == 'methods.json'
    return path.as_posix() in {
        'runtimes/android/Dockerfile', 'runtimes/android/README.md',
        'runtimes/android/prepare.py', 'runtimes/android/qualify.py'}


def build(source, output):
    source, output = Path(source), Path(output)
    if source.is_symlink() or not source.is_dir():
        raise ValueError('source must be a real skill directory')
    files, total = {}, 0
    for directory, dirs, names in os.walk(source, followlinks=False):
        # Python creates these during ordinary helper usage; they are not inputs.
        for name in list(dirs):
            child = Path(directory) / name
            if child.is_symlink():
                raise ValueError('symlink in package: ' + str(child))
            if name == '__pycache__':
                dirs.remove(name)
        for name in names:
            path = Path(directory) / name
            relative = path.relative_to(source)
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode):
                raise ValueError('non-regular package entry: ' + str(relative))
            if not allowed(relative):
                raise ValueError('unreviewed package entry: ' + str(relative))
            if info.st_size > LIMIT - total:
                raise ValueError('package exceeds byte bound')
            data = path.read_bytes()
            if len(data) > LIMIT - total:
                raise ValueError('package exceeds byte bound')
            files[relative.as_posix()] = data
            total += len(data)
    if not {'SKILL.md', 'agents/openai.yaml', 'scripts/apk_intake.py',
            'references/pipeline.md'} <= files.keys():
        raise ValueError('incomplete portable skill')
    manifest = {'schema_version': 1, 'package': NAME,
                'files': {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                          for name, data in sorted(files.items())},
                'limits': 'Content hashes are not signatures, licensing or live harness qualification.'}
    files['package-manifest.json'] = (json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(NAME + '/' + name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, data, compresslevel=9)
    payload = buffer.getvalue()
    with output.open('xb') as stream:
        stream.write(payload)
    return {'package': NAME, 'files': len(manifest['files']), 'bytes': len(payload),
            'sha256': hashlib.sha256(payload).hexdigest(), 'output': str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.source, args.output), indent=2))
    except (ValueError, OSError) as exc:
        parser.exit(2, f'Packaging blocked: {exc}\n')


if __name__ == '__main__':
    main()
