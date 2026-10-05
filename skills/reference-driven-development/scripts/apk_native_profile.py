#!/usr/bin/env python3
"""Bounded analyst-side ELF dependencies; never executes or extracts APK code."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import zipfile

import apk_intake

MAX_LIBRARY = 32 * 1024 * 1024
MAX_TOTAL = 128 * 1024 * 1024
MAX_LIBRARIES = 256
MAX_HEADERS = 4096
MAX_TAGS = 4096
ABI = {'armeabi': (32, 'EM_ARM'), 'armeabi-v7a': (32, 'EM_ARM'),
       'arm64-v8a': (64, 'EM_AARCH64'), 'x86': (32, 'EM_386'),
       'x86_64': (64, 'EM_X86_64')}


class ReadBudget(io.BytesIO):
    """Bound cumulative parser reads, including repeated malformed string scans."""
    def __init__(self, data):
        super().__init__(data)
        self.remaining = min(64 * 1024 * 1024, len(data) * 8 + 1024 * 1024)

    def read(self, size=-1):
        if size < 0:
            size = len(self.getbuffer()) - self.tell()
        if size > self.remaining:
            raise ValueError('ELF parser read budget exceeded')
        value = super().read(size)
        self.remaining -= len(value)
        return value


def elf_profile(data):
    from elftools.elf.elffile import ELFFile
    if len(data) < 52 or data[:4] != b'\x7fELF' or data[4] not in (1, 2) or data[5] not in (1, 2):
        raise ValueError('invalid ELF identification/header')
    order = '<' if data[5] == 1 else '>'
    wide = data[4] == 2
    fmt = order + ('HHIQQQIHHHHHH' if wide else 'HHIIIIIHHHHHH')
    h = struct.unpack_from(fmt, data, 16)
    # Validate tables before a third-party parser traverses attacker-supplied counts.
    phoff, shoff, phsize, phnum, shsize, shnum = h[4], h[5], h[8], h[9], h[10], h[11]
    if phnum == 65535 or (shoff and shnum == 0):
        raise ValueError('extended header numbering requires another bounded inspector')
    for offset, size, count, minimum in ((phoff, phsize, phnum, 56 if wide else 32),
                                        (shoff, shsize, shnum, 64 if wide else 40)):
        if count > MAX_HEADERS or (count and (size < minimum or offset + size * count > len(data))):
            raise ValueError('ELF header table exceeds bounds')
    elf = ELFFile(ReadBudget(data))
    needed, sonames, dynamic = [], [], False
    for segment in elf.iter_segments():
        start, size = segment['p_offset'], segment['p_filesz']
        if start + size > len(data):
            raise ValueError('ELF segment exceeds payload')
        if segment['p_type'] == 'PT_DYNAMIC':
            dynamic = True
            if size // (16 if wide else 8) > MAX_TAGS:
                raise ValueError('dynamic table exceeds bounds')
            terminated = False
            for index, tag in enumerate(segment.iter_tags()):
                if index >= MAX_TAGS:
                    raise ValueError('dynamic table exceeds bounds')
                if tag.entry.d_tag == 'DT_NULL':
                    terminated = True
                    break
                if tag.entry.d_tag == 'DT_NEEDED':
                    needed.append(tag.needed)
                if tag.entry.d_tag == 'DT_SONAME':
                    sonames.append(tag.soname)
                if len(needed) + len(sonames) > 256 or any(len(s) > 1024 for s in needed[-1:] + sonames[-1:]):
                    raise ValueError('dependency report exceeds bounds')
            if not terminated:
                raise ValueError('unterminated dynamic table')
    return {'bits': elf.elfclass, 'machine': elf['e_machine'],
            'little_endian': elf.little_endian, 'elf_type': elf['e_type'],
            'dynamic_table_present': dynamic, 'needed': needed, 'sonames': sonames,
            'basis': 'ELF program headers and DT_NEEDED/DT_SONAME, including stripped files'}


def profile(path):
    from elftools.common.exceptions import ELFError
    intake = apk_intake.inspect(path, apk_intake.MAX_ENTRIES)
    libraries = intake['native_libraries']['items']
    records, decoded, charged = [], 0, 0
    with zipfile.ZipFile(path) as archive:
        counts = {}
        for item in archive.infolist():
            counts[item.filename] = counts.get(item.filename, 0) + 1
        for index, name in enumerate(libraries):
            record = {'entry': name, 'declared_abi': name.split('/')[1], 'status': 'uninspected'}
            records.append(record)
            item = archive.getinfo(name)
            if counts[name] != 1:
                record['reason'] = 'duplicate archive path; payload selection ambiguous'
                continue
            read_limit = item.file_size + 1
            if index >= MAX_LIBRARIES or item.file_size > MAX_LIBRARY or charged + read_limit > MAX_TOTAL:
                record['reason'] = 'payload inspection budget exceeded'
                continue
            try:
                # Charge attempts even when CRC/decompression fails before returning bytes.
                charged += read_limit
                with archive.open(item) as source:
                    data = source.read(read_limit)
                decoded += len(data)
                if len(data) != item.file_size or len(data) > MAX_LIBRARY or decoded > MAX_TOTAL:
                    raise ValueError('decoded payload size exceeds declaration/budget')
                record['sha256'] = hashlib.sha256(data).hexdigest()
                record['elf'] = elf_profile(data)
                actual = record['elf']
                expected = ABI.get(record['declared_abi'])
                record['abi_matches_payload'] = (actual['bits'], actual['machine']) == expected and actual['little_endian'] if expected else None
                record['status'] = 'inspected'
            except (ValueError, ELFError, EOFError, struct.error, RuntimeError, zipfile.BadZipFile) as exc:
                record['status'] = 'invalid-or-unsupported'
                record['reason'] = str(exc)
    after = apk_intake.inspect(path, 1)
    if after['input']['sha256'] != intake['input']['sha256']:
        raise apk_intake.IntakeError('input changed during payload profiling')
    # Preserve ABI-specific alternatives: a dependency in one ABI need not exist in another.
    graphs = {}
    for record in records:
        if record['status'] != 'inspected':
            continue
        group = graphs.setdefault(record['declared_abi'], {'nodes': [], 'edges': []})
        group['nodes'].append(record['entry'])
        for dependency in record['elf']['needed']:
            candidates = [r['entry'] for r in records if r['declared_abi'] == record['declared_abi'] and
                          (Path(r['entry']).name == dependency or dependency in r.get('elf', {}).get('sonames', []))]
            group['edges'].append({'from': record['entry'], 'needed': dependency,
                                   'packaged_candidates': candidates,
                                   'resolution': 'candidate only; Android linker namespaces and runtime loads uninspected'})
    return {'schema_version': 1, 'reference_id': intake['reference_id'],
            'input': intake['input'], 'libraries': records, 'graphs_by_declared_abi': graphs,
            'managed_dex_present': bool(intake['dex']['total']),
            'framework_hypotheses': intake['framework_hypotheses'],
            'bounds': {'max_library_bytes': MAX_LIBRARY, 'max_decoded_total_bytes': MAX_TOTAL,
                       'max_libraries': MAX_LIBRARIES, 'decoded_bytes': decoded,
                       'charged_read_bytes': charged},
            'next_action': 'Inspect reachable entry paths and platform contracts before selecting an iPhone execution route.',
            'limits': ['No execution, extraction, signature or manifest verification, iPhone packaging or installability proof.',
                       'No JNI/Java API, relocation, syscall, dynamic dlopen, asset-contained code or external split closure.',
                       'A packaged dependency candidate is not proven linker resolution; unknown dependencies are not proven missing.',
                       'No native libraries found does not establish a pure Java app. Static presence does not prove reachability.',
                       'Analyst-side binary evidence is not a reviewed clean-room specification.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('apk', type=Path)
    parser.add_argument('--output', type=Path, required=True, help='Fresh private JSON path')
    args = parser.parse_args()
    try:
        from elftools.common.exceptions import ELFError
    except ImportError:
        parser.exit(2, 'Install requirements-native-profile.txt in a task-owned Python environment.\n')
    try:
        result = profile(args.apk)
        with args.output.open('x', encoding='utf-8') as output:
            json.dump(result, output, indent=2)
            output.write('\n')
    except (apk_intake.IntakeError, OSError, ValueError, ELFError, zipfile.BadZipFile) as exc:
        print(f'Native profiling blocked: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
