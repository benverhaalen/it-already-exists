#!/usr/bin/env python3
"""Package a qualified ELF snapshot layout; does not port or execute an app."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
from elftools.elf.elffile import ELFFile
from elftools.common.exceptions import ELFError

MAX_BYTES = 64 * 1024 * 1024
PAGE = 16384
SYMBOLS = ('_kDartVmSnapshotData', '_kDartVmSnapshotInstructions',
           '_kDartIsolateSnapshotData', '_kDartIsolateSnapshotInstructions')


def qualify(data):
    if not 64 <= len(data) <= MAX_BYTES:
        raise ValueError('ELF size outside bounded input range')
    if data[:7] != b'\x7fELF\x02\x01\x01':
        raise ValueError('Only little-endian ELF64 is supported')
    values = struct.unpack_from('<HHIQQQIHHHHHH', data, 16)
    kind, machine, version, _, phoff, shoff, _, ehsize, phsize, phnum, shsize, shnum, shstr = values
    if (kind, machine, version, ehsize, phsize, shsize) != (3, 183, 1, 64, 56, 64):
        raise ValueError('Expected ARM64 ET_DYN with standard tables')
    if not 1 <= phnum <= 64 or not 1 <= shnum <= 256:
        raise ValueError('Unsupported or excessive table counts')
    if not 0 < shstr < shnum:
        raise ValueError('Invalid section-name table index')
    if phoff < 64 or phoff + phnum * phsize > len(data) or shoff < 64 or shoff + shnum * shsize > len(data):
        raise ValueError('Header table outside input')
    elf = ELFFile(io.BytesIO(data))
    loads = sorted((dict(s.header) for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD'), key=lambda s:s['p_vaddr'])
    end = 0
    for s in loads:
        if s['p_offset'] != s['p_vaddr']:
            raise ValueError('Non-identity file/virtual mapping requires a different packer')
        if s['p_filesz'] > s['p_memsz'] or s['p_offset'] + s['p_filesz'] > len(data):
            raise ValueError('Load range outside input')
        if s['p_memsz'] == 0 or s['p_vaddr'] < end or s['p_vaddr'] + s['p_memsz'] > MAX_BYTES:
            raise ValueError('Overlapping, empty, or excessive load ranges')
        if s['p_flags'] not in (4, 5, 6):
            raise ValueError('Unexpected load permissions')
        end = s['p_vaddr'] + s['p_memsz']
    if not loads or loads[0]['p_vaddr'] != 0:
        raise ValueError('Expected a load at the ELF base')
    writable = [s for s in loads if s['p_flags'] & 2]
    if len(writable) != 1 or writable[0] is not loads[-1]:
        raise ValueError('Expected exactly one final writable load')
    rw = writable[0]
    if any(s['p_memsz'] != s['p_filesz'] for s in loads[:-1]):
        raise ValueError('Non-final zero-fill requires a different packer')
    if rw['p_vaddr'] % PAGE or not any(s['p_flags'] & 1 for s in loads[:-1]):
        raise ValueError('Expected aligned writable storage following executable code')
    for section in elf.iter_sections():
        h = section.header
        if h['sh_type'] != 'SHT_NOBITS' and h['sh_offset'] + h['sh_size'] > len(data):
            raise ValueError('Section range outside input')
    dynsym = elf.get_section_by_name('.dynsym')
    if dynsym is None or dynsym['sh_entsize'] != 24 or dynsym['sh_size'] % 24 or dynsym.num_symbols() > 10000:
        raise ValueError('Missing or excessive dynamic symbol table')
    found = {}
    for symbol in dynsym.iter_symbols():
        if symbol.name not in SYMBOLS:
            continue
        if symbol.name in found or symbol['st_shndx'] == 'SHN_UNDEF':
            raise ValueError('Ambiguous or undefined snapshot symbol')
        offset, size = symbol['st_value'], symbol['st_size']
        segment = next((s for s in loads if s['p_vaddr'] <= offset < s['p_vaddr'] + s['p_filesz']), None)
        if segment is None or offset + max(size, 1) > segment['p_vaddr'] + segment['p_filesz']:
            raise ValueError('Snapshot symbol outside a file-backed load')
        instructions = symbol.name.endswith('Instructions')
        if bool(segment['p_flags'] & 1) != instructions or segment['p_flags'] & 2:
            raise ValueError('Snapshot symbol has unexpected permissions')
        found[symbol.name] = {'offset': offset, 'size': size}
    if set(found) != set(SYMBOLS):
        raise ValueError('All four Dart snapshot symbols are required')
    return {'sha256': hashlib.sha256(data).hexdigest(), 'source_bytes': len(data),
            'writable_offset': rw['p_vaddr'], 'writable_file_bytes': rw['p_filesz'],
            'writable_memory_bytes': rw['p_memsz'], 'snapshot_symbols': found,
            'required_linker_flags': ['-Wl,-segprot,__RDDTEXT,rx,rx', '-Wl,-segprot,__RDDDATA,rw,rw'],
            'required_runtime_check': 'rdd_snapshot_bss - rdd_snapshot_start == writable_offset',
            'qualification': 'bounded packaging geometry only',
            'not_verified': ['snapshot VM compatibility', 'FFI and platform ABI', 'Flutter rendering and plugins', 'physical device execution', 'application equivalence']}


def pack(source, destination):
    source, destination = Path(source), Path(destination)
    with source.open('rb') as handle:
        data = handle.read(MAX_BYTES + 1)
    receipt = qualify(data)
    # Refuse replacing any existing work. Output is private executable material.
    destination.mkdir(parents=True, exist_ok=False)
    blob = destination.resolve() / 'snapshot.bin'
    path = str(blob)
    if any(ord(c) < 32 for c in path):
        destination.rmdir()
        raise ValueError('Control characters in assembly path')
    quoted = path.replace('\\', '\\\\').replace('"', '\\"')
    offset, size, memory = (receipt[k] for k in ('writable_offset', 'writable_file_bytes', 'writable_memory_bytes'))
    assembly = f'''// Qualified layout only; host must check the linked symbol distance.
.section __RDDTEXT,__snapshot,regular,pure_instructions
.p2align 14
.globl _rdd_snapshot_start
_rdd_snapshot_start:
.incbin "{quoted}",0,{offset}
.section __RDDDATA,__bssdata,regular
.p2align 14
.globl _rdd_snapshot_bss
_rdd_snapshot_bss:
.incbin "{quoted}",{offset},{size}
.space {memory-size}
'''
    # Mach-O's leading underscore maps these ELF snapshot names to the
    # kDart* C exports that Flutter's dynamic-library snapshot loader expects.
    for name in SYMBOLS:
        assembly += f'\n.globl {name}\n.set {name}, _rdd_snapshot_start + {receipt["snapshot_symbols"][name]["offset"]}\n'
    blob.write_bytes(data)
    (destination / 'snapshot.S').write_text(assembly)
    (destination / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    try:
        result = pack(args.source, args.destination)
    except (ValueError, OSError, ELFError) as error:
        parser.exit(1, f'Packaging refused: {error}\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__':
    main()
