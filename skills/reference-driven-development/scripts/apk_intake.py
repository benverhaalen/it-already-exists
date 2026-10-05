#!/usr/bin/env python3
"""Bounded analyst-side APK/ZIP metadata intake; never executes or extracts input.

Names are observations, framework associations are hypotheses. This is not a
manifest/signature verifier or a decompiler. ZIP64 requires a separate inspector.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import zipfile

MAX_DIRECTORY = 8 * 1024 * 1024
MAX_ENTRIES = 10000
CATALOG = 'references/reverse-engineering-catalog.md'


class IntakeError(ValueError):
    pass


def directory_guard(stream, size):
    """Bound central directory before zipfile materializes its records."""
    stream.seek(max(0, size - 65557))
    tail = stream.read(65557)
    marker = tail.rfind(b'PK\x05\x06')
    if marker < 0 or len(tail) - marker < 22:
        raise IntakeError('missing ZIP end-of-central-directory record')
    fields = struct.unpack_from('<4s4H2LH', tail, marker)
    _, disk, start_disk, disk_count, count, length, offset, comment = fields
    if marker + 22 + comment != len(tail):
        raise IntakeError('ambiguous or trailing ZIP end record')
    if disk or start_disk or disk_count != count:
        raise IntakeError('multi-disk archives require a separate inspector')
    if count == 65535 or length == 0xffffffff or offset == 0xffffffff:
        raise IntakeError('ZIP64 requires a separately bounded inspector')
    if count > MAX_ENTRIES or length > MAX_DIRECTORY:
        raise IntakeError('central-directory metadata exceeds intake bounds')
    if offset + length > size:
        raise IntakeError('central directory extends beyond archive')
    return count


def inspect(path, max_report=2000):
    if not 1 <= max_report <= MAX_ENTRIES:
        raise IntakeError(f'max-report must be between 1 and {MAX_ENTRIES}')
    path = Path(path).absolute()
    if not stat.S_ISREG(path.lstat().st_mode):
        raise IntakeError('input must be a regular file, not a symlink or special file')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    with os.fdopen(os.open(path, flags), 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise IntakeError('input must be a regular file')
        count = directory_guard(stream, before.st_size)
        stream.seek(0)
        digest = hashlib.sha256()
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
        stream.seek(0)
        with zipfile.ZipFile(stream) as archive:
            entries = archive.infolist()
            if len(entries) != count:
                raise IntakeError('central-directory entry count mismatch')
            if sum(46 + len(i.filename.encode('utf-8')) + len(i.extra) + len(i.comment)
                   for i in entries) > MAX_DIRECTORY:
                raise IntakeError('decoded metadata exceeds intake bounds')
            inventory = sorted([{
                'name': i.filename, 'uncompressed_bytes': i.file_size,
                'compressed_bytes': i.compress_size, 'compression': i.compress_type,
                'encrypted': bool(i.flag_bits & 1),
                'unsafe_path': i.filename.startswith(('/', '\\')) or '..' in i.filename.replace('\\', '/').split('/'),
                'symlink': stat.S_ISLNK(i.external_attr >> 16),
            } for i in entries], key=lambda i: i['name'])
        after = os.fstat(stream.fileno())
    current = path.stat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
    if identity(before) != identity(after) or identity(after) != identity(current):
        raise IntakeError('input changed during intake; retry with an immutable copy')
    sha = digest.hexdigest()
    names = [i['name'] for i in inventory]
    dex = [n for n in names if re.fullmatch(r'classes(?:[2-9]|[1-9][0-9]+)?\.dex', n)]
    native = [n for n in names if re.fullmatch(r'lib/[^/]+/[^/]+\.so', n)]
    nested = [n for n in names if n.lower().endswith('.apk')]
    signatures = {
        'flutter': [n for n in names if n.endswith(('/libflutter.so', '/libapp.so')) or n.startswith('assets/flutter_assets/')],
        'unity': [n for n in names if n.endswith(('/libunity.so', '/libil2cpp.so', '/global-metadata.dat')) or n.startswith('assets/bin/Data/')],
        'react-native-or-javascript': [n for n in names if n.endswith(('/libhermes.so', '/libreactnative.so')) or n == 'assets/index.android.bundle'],
    }
    route_ids = ['framework-triage']
    if dex:
        route_ids.append('dex-recovery')
    if native:
        route_ids.append('bounded-binary-query')
    if signatures['flutter']:
        route_ids.extend(['dart-aot', 'cross-language-boundary'])
    if signatures['unity']:
        route_ids.append('unity-layer-recovery')
    if signatures['react-native-or-javascript']:
        route_ids.append('hermes-tables')
    cap = lambda values: {'items': values[:max_report], 'total': len(values), 'truncated': len(values) > max_report}
    return {
        'schema_version': 1, 'reference_id': 'apk-' + sha,
        'input': {'path': str(path), 'sha256': sha, 'bytes': before.st_size, 'identity_stable_during_intake': True},
        'mode': 'analyst-side static archive metadata only',
        'readiness': 'initial static intake only; runtime and recovery readiness not established',
        'bounds': {'max_directory_bytes': MAX_DIRECTORY, 'max_entries': MAX_ENTRIES,
                   'max_report_items_per_list': max_report, 'decoded_payload_bytes': 0,
                   'complete_archive_metadata_scan': True, 'complete_payload_scan': False,
                   'truncated': len(inventory) > max_report},
        'inventory': cap(inventory), 'dex': cap(dex), 'native_libraries': cap(native),
        'native_abis': sorted({n.split('/')[1] for n in native}),
        'assets': cap([n for n in names if n.startswith('assets/')]),
        'package': {'manifest_entry_present': 'AndroidManifest.xml' in names,
                    'nested_apks': cap(nested),
                    'split_indicators': cap([n for n in nested if 'split' in n.lower() or 'config.' in n.lower()]),
                    'split_status': 'unknown: binary manifest and external sibling packages not inspected',
                    'signature_status': 'not verified; ZIP metadata does not authenticate a package'},
        'framework_hypotheses': [{'framework': label, 'evidence': cap(values),
            'basis': 'inferred from archive entry names',
            'limits': 'May identify an embedded SDK, misleading name, unused component or mixed package; verify payload and reachable entry paths.'}
            for label, values in signatures.items() if values],
        'next_inspection': [{'method_id': m, 'catalog': CATALOG, 'status': 'conditional candidate, not executed'} for m in route_ids],
        'next_questions': ['Inspect manifest/package set and required splits before device acquisition.',
                           'Choose a user-relevant journey and inspect only its implicated components.',
                           'Check actual payload format and version before choosing recovery tools.',
                           'Correlate static paths with unmodified runtime evidence; static presence does not establish reachability.'],
        'limits': ['No extraction, execution, manifest decoding, decompilation, signature verification or behavior recovery.',
                   'Entry names and sizes are archive claims; contents and CRC were not verified.',
                   'Reported lists may truncate; totals and routing scan all bounded metadata.',
                   'No absence claim about components outside this archive or hidden/renamed/encrypted payloads.',
                   'Hashing reads the original file once; work scales with its size. No source bytes are sent to a model.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    parser.add_argument('--max-report', type=int, default=2000)
    parser.add_argument('--output', type=Path, help='Fresh JSON file; existing paths are never overwritten')
    args = parser.parse_args()
    try:
        result = inspect(args.apk, args.max_report)
        rendered = json.dumps(result, indent=2, ensure_ascii=True) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8') as output:
                output.write(rendered)
        else:
            print(rendered, end='')
    except (IntakeError, OSError, zipfile.BadZipFile, RuntimeError, UnicodeError) as exc:
        print(f'APK intake blocked: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
