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
PSTACK_REVISION = 'ccb5507cec1546dc88135c1139c811e6c59115ba'

# Positive public export membership. New modules need an explicit reviewed entry.
INVENTORY_V1 = frozenset({
    'LICENSE',
    'SKILL.md',
    'agents/openai.yaml',
    'references/adaptive-verification.md',
    'references/analysis-reuse.md',
    'references/apk-acquisition.md',
    'references/apk-iphone.md',
    'references/clean-room.md',
    'references/coding-loop.md',
    'references/comparison.md',
    'references/delivery.md',
    'references/discovery.md',
    'references/expert-integration.md',
    'references/expert-process-example.md',
    'references/expert-processes.md',
    'references/factory-procedures.md',
    'references/factory.md',
    'references/failure-families.md',
    'references/flutter-wire.md',
    'references/formal-methods.md',
    'references/frontier-worker.md',
    'references/graphics-qualification.md',
    'references/human-input.md',
    'references/image-ideation-example.md',
    'references/ios-session-storage.md',
    'references/lineage.md',
    'references/methods.json',
    'references/observation-sessions.md',
    'references/observation.md',
    'references/pipeline.md',
    'references/project-controls.md',
    'references/reconstruction-bottlenecks.md',
    'references/records.md',
    'references/research-improvement.md',
    'references/reverse-engineering-catalog.md',
    'references/service-testing.md',
    'references/surface-methods.md',
    'references/synthesis.md',
    'references/ui-continuity.md',
    'references/video-timeline.md',
    'references/workflow.md',
    'runtimes/android/Dockerfile',
    'runtimes/android/README.md',
    'runtimes/android/prepare.py',
    'runtimes/android/qualify.py',
    'scripts/analysis_reuse.py',
    'scripts/android_http_fixture_probe.py',
    'scripts/android_loopback_fixture.py',
    'scripts/android_process_http_probe.py',
    'scripts/apk_intake.py',
    'scripts/apk_native_compare.py',
    'scripts/apk_native_profile.py',
    'scripts/arm64_abi_control.py',
    'scripts/asset_field_transfer.py',
    'scripts/assets.py',
    'scripts/behavioral_evidence.py',
    'scripts/callable_values.py',
    'scripts/cleanroom.py',
    'scripts/coding_loop.py',
    'scripts/comparison.py',
    'scripts/dart_aot_macho_pack.py',
    'scripts/dart_aot_pool_xrefs.py',
    'scripts/factory.py',
    'scripts/factory_procedures.py',
    'scripts/firestore_dependency_audit.py',
    'scripts/firestore_reference_transfer.py',
    'scripts/fixtures/arm64_abi/bridge-control.S',
    'scripts/fixtures/arm64_abi/bridge-control.c',
    'scripts/fixtures/arm64_abi/mixed-control.S',
    'scripts/fixtures/arm64_abi/mixed-control.c',
    'scripts/fixtures/arm64_abi/stack-prefix.c',
    'scripts/fixtures/datadog_core/LICENSE',
    'scripts/fixtures/datadog_core/crash-control.swift',
    'scripts/fixtures/datadog_core/flutter-local-startup.patch',
    'scripts/fixtures/datadog_core/local-transport.swift',
    'scripts/fixtures/datadog_core/startup-control.swift',
    'scripts/fixtures/firebase_core/LICENSE',
    'scripts/fixtures/firebase_core/android-app-id.patch',
    'scripts/fixtures/firebase_core/registry-control.m',
    'scripts/fixtures/firebase_firestore/LocalFirestoreSettings.h',
    'scripts/fixtures/firebase_firestore/local-control.m',
    'scripts/fixtures/firebase_functions/AppDelegate.swift',
    'scripts/fixtures/firebase_functions/GuardControl.swift',
    'scripts/fixtures/firebase_functions/RDDLocalCallableTransport.swift',
    'scripts/fixtures/firebase_functions/firebase-ios-sdk-LICENSE',
    'scripts/fixtures/firebase_functions/local-callable-server.py',
    'scripts/fixtures/firebase_functions/local-callable.patch',
    'scripts/fixtures/flutter_abi/DART-LICENSE',
    'scripts/fixtures/flutter_abi/TONIC-LICENSE',
    'scripts/fixtures/flutter_abi/dart-loopback.patch',
    'scripts/fixtures/flutter_abi/dart-snapshot.patch',
    'scripts/fixtures/flutter_abi/flutter-tonic.patch',
    'scripts/fixtures/flutter_abi/ios-channel-trace.patch',
    'scripts/fixtures/keychain/KeychainControl.swift',
    'scripts/fixtures/path_provider/LICENSE',
    'scripts/fixtures/path_provider/android-ios-directories.swift',
    'scripts/fixtures/sqflite/FMDB_LICENSE.txt',
    'scripts/fixtures/sqflite/LICENSE',
    'scripts/fixtures/sqflite/RDDSQLiteControl.h',
    'scripts/fixtures/sqflite/RDDSQLiteControl.m',
    'scripts/fixtures/sqflite/standalone-import.patch',
    'scripts/fixtures/stripe_core/local-startup-control.swift',
    'scripts/flutter_wire_inspect.py',
    'scripts/frontier_worker.py',
    'scripts/intake.py',
    'scripts/ios_location_fixture.py',
    'scripts/json_state_delta.py',
    'scripts/local_auth.py',
    'scripts/observation.py',
    'scripts/observation_packet.py',
    'scripts/offline_worker.py',
    'scripts/process.py',
    'scripts/project_controls.py',
    'scripts/rdd.py',
    'scripts/reconstruction_trials.py',
    'scripts/reference_provider.py',
    'scripts/repair.py',
    'scripts/replay_readiness.py',
    'scripts/requirements-comparison.txt',
    'scripts/requirements-native-profile.txt',
    'scripts/requirements-service-guard.txt',
    'scripts/research_trials.py',
    'scripts/service_guard.py',
    'scripts/service_guard_mitm.py',
    'scripts/video_timeline.py',
    'scripts/workflow.py',
})

# Retain complete historical memberships: a new export must not invalidate an
# unchanged installed release. Add a new edition instead of editing prior sets.
INVENTORY_VERSION = 2
REVIEWED_INVENTORIES = {
    1: INVENTORY_V1,
    2: INVENTORY_V1 | {'scripts/firestore_query_scenario.py'},
}
REVIEWED_FILES = REVIEWED_INVENTORIES[INVENTORY_VERSION]


def reviewed_inventory(manifest):
    if not isinstance(manifest['files'], dict):
        raise ValueError('invalid factory file inventory')
    authored = {name for name in manifest['files'] if not name.startswith('upstream/pstack/')}
    version = manifest.get('inventory_version')
    if 'inventory_version' not in manifest:
        # Early schema-1 capsules had no edition field. Infer only an exact,
        # explicitly retained membership; self-listed subsets are insufficient.
        matches = [key for key, files in REVIEWED_INVENTORIES.items() if authored == files]
        if len(matches) != 1:
            raise ValueError('unsupported legacy factory inventory')
        version = matches[0]
    if type(version) is not int or version not in REVIEWED_INVENTORIES:
        raise ValueError('unsupported factory inventory version')
    required = REVIEWED_INVENTORIES[version]
    if authored != required:
        missing, extra = required - authored, authored - required
        raise ValueError('factory inventory mismatch: missing=' + ', '.join(sorted(missing))
                         + '; extra=' + ', '.join(sorted(extra)))
    return version, required


def safe_relative(value):
    if not isinstance(value, str):
        raise ValueError('unsafe package path: ' + str(value))
    path = Path(value)
    if not value or '\0' in value or path.is_absolute() or '\\' in value or any(
            part in {'', '.', '..'} for part in value.split('/')):
        raise ValueError('unsafe package path: ' + str(value))
    return path


def validate_upstream(files):
    """Check the explicitly selected upstream closure, including original blobs.

    A source manifest is provenance, not legal clearance or a signature. Its
    original license travels with the source; local adaptations remain explicit.
    """
    prefix = 'upstream/pstack/'
    selected = {name[len(prefix):]: data for name, data in files.items() if name.startswith(prefix)}
    if not selected:
        return
    try:
        manifest = json.loads(selected['manifest.json'])
        source = manifest['source']
        if (manifest['format_version'] != 1 or source['repository'] != 'cursor/plugins'
                or source['revision'] != PSTACK_REVISION
                or source['license'] != 'MIT'):
            raise ValueError('unsupported upstream identity/license')
        expected = {'manifest.json', 'README.md'}
        originals = set()
        for entry in manifest['source_files']:
            name = safe_relative(entry['installed_path']).as_posix()
            original = safe_relative(entry['original_path']).as_posix()
            expected_name = 'sources/' + original + ('.source' if original.endswith('.md') else '')
            if not original.startswith('pstack/') or name != expected_name or name in expected or original in originals:
                raise ValueError('invalid or duplicate upstream source path')
            originals.add(original)
            expected.add(name)
            data = selected[name]
            if (type(entry['bytes']) is not int or len(data) != entry['bytes'] or hashlib.sha256(data).hexdigest() != entry['sha256']
                    or hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
                    != entry['git_blob_sha1']):
                raise ValueError('upstream source digest mismatch: ' + name)
            if Path(name).name == 'SKILL.md':
                raise ValueError('upstream discovery surface must remain inactive')
        if (set(selected) != expected or 'pstack/LICENSE' not in originals
                or not selected['sources/pstack/LICENSE'].startswith(b'MIT License\n')):
            raise ValueError('incomplete or unreviewed upstream inventory/license')
        for group in ('procedures', 'conditional_modules'):
            modules = manifest.get(group)
            if not isinstance(modules, dict) or not modules:
                raise ValueError('procedure selection map missing: ' + group)
            for module in modules.values():
                paths = module['read_paths']
                if not isinstance(paths, list) or not paths or len(paths) != len(set(paths)) or any(path not in originals for path in paths):
                    raise ValueError('invalid or unretained procedure dependency')
        for procedure in manifest['procedures'].values():
            required = procedure.get('required_modules', [])
            if not isinstance(required, list) or any(name not in manifest['conditional_modules'] for name in required):
                raise ValueError('unknown required procedure module')
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError('invalid upstream manifest: ' + str(exc)) from exc


def allowed(path, reviewed_files=REVIEWED_FILES):
    if len(path.parts) >= 3 and path.parts[:2] == ('upstream', 'pstack'):
        return True  # Its exact original-source inventory is checked separately.
    return path.as_posix() in reviewed_files


def collect_files(source):
    source = Path(source)
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
    missing = REVIEWED_FILES - files.keys()
    if missing:
        raise ValueError('incomplete portable skill: ' + ', '.join(sorted(missing)))
    if 'upstream/pstack/manifest.json' not in files:
        raise ValueError('incomplete original procedure closure')
    validate_upstream(files)
    return files


def build(source, output):
    output = Path(output)
    files = collect_files(source)
    manifest = {'schema_version': 1, 'package': NAME, 'inventory_version': INVENTORY_VERSION,
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
