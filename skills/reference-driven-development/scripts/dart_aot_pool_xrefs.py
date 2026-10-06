#!/usr/bin/env python3
"""Find narrow ARM64 object-pool load patterns in explicitly supplied ELF ranges.

Requires pyelftools. Does not deserialize snapshots, infer schemas, follow control
flow or discover function boundaries. Keep generated labels and receipts private.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


def number(value):
    if type(value) is int:
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise ValueError('Expected an integer or integer string')


def pool_load(word, previous=None):
    # LDR Xt,[Xn,#unsigned_imm12*8], excluding discarded XZR destinations.
    if word & 0xffc00000 != 0xf9400000 or word & 31 == 31:
        return None
    base = (word >> 5) & 31
    low = ((word >> 10) & 4095) * 8
    if base == 27:
        return (low, 'ldr-pool')
    # Only an immediately adjacent ADD Xd,X27,#imm{,LSL #12} qualifies.
    if previous is None or previous & 0xff800000 != 0x91000000:
        return None
    destination = previous & 31
    source = (previous >> 5) & 31
    if source != 27 or destination in (27, 31) or destination != base:
        return None
    high = ((previous >> 10) & 4095) << (12 if previous & (1 << 22) else 0)
    return (high + low, 'adjacent-add-ldr-pool')


def scan(data, start, wanted):
    rows = []
    previous = None
    for offset in range(0, len(data), 4):
        word = struct.unpack_from('<I', data, offset)[0]
        hit = pool_load(word, previous)
        if hit and hit[0] in wanted:
            rows.append({'instruction': hex(start + offset), 'pool_offset': hex(hit[0]),
                         'pattern': hit[1]})
        previous = word
    return rows


def ranges_from_json(value):
    if not isinstance(value, list) or not 0 < len(value) <= 100000:
        raise ValueError('Supply 1..100000 explicitly qualified ranges')
    rows = []
    for row in value:
        if not isinstance(row, dict) or set(row) != {'start', 'end'}:
            raise ValueError('Each range needs only start and end')
        start, end = number(row['start']), number(row['end'])
        if start < 0 or end <= start or start % 4 or end % 4:
            raise ValueError('Ranges must be positive-length and instruction-aligned')
        rows.append((start, end))
    rows.sort()
    if any(rows[i][0] < rows[i-1][1] for i in range(1, len(rows))):
        raise ValueError('Ranges must not overlap')
    if sum(end-start for start, end in rows) > 256*1024*1024:
        raise ValueError('Qualified ranges exceed scan limit')
    return rows


def analyze(elf_path, ranges_path, pool_path, wanted):
    from elftools.elf.elffile import ELFFile
    range_bytes = ranges_path.read_bytes()
    pool_bytes = pool_path.read_bytes()
    if len(range_bytes) > 16*1024*1024 or len(pool_bytes) > 64*1024*1024:
        raise ValueError('Metadata exceeds input limits')
    ranges = ranges_from_json(json.loads(range_bytes))
    labels = {}
    for slot, label in re.findall(r'^\[pp\+(0x[0-9a-f]+)\] (.*)$', pool_bytes.decode('utf-8'), re.M):
        offset = int(slot, 16)
        if offset in labels and labels[offset] != label:
            raise ValueError('Conflicting pool labels')
        labels[offset] = label
    rows = []
    with elf_path.open('rb') as stream:
        elf = ELFFile(stream)
        if elf.elfclass != 64 or not elf.little_endian or elf['e_machine'] != 'EM_AARCH64':
            raise ValueError('Expected a little-endian ARM64 ELF')
        segments = [(int(s['p_vaddr']), int(s['p_filesz']), int(s['p_offset']))
                    for s in elf.iter_segments() if s['p_type'] == 'PT_LOAD' and int(s['p_flags']) & 1]
        for start, end in ranges:
            matches = [s for s in segments if s[0] <= start and end <= s[0]+s[1]]
            if len(matches) != 1:
                raise ValueError('Range must fit exactly one file-backed executable segment')
            address, _, position = matches[0]
            stream.seek(position+start-address)
            data = stream.read(end-start)
            if len(data) != end-start:
                raise ValueError('Truncated executable range')
            for row in scan(data, start, wanted):
                row.update(range_start=hex(start), range_end=hex(end),
                           label=labels.get(int(row['pool_offset'], 16)))
                rows.append(row)
        stream.seek(0)
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'schema_version': 1, 'elf_sha256': digest,
            'ranges_sha256': hashlib.sha256(range_bytes).hexdigest(),
            'pool_sha256': hashlib.sha256(pool_bytes).hexdigest(),
            'range_count': len(ranges), 'scanned_bytes': sum(e-s for s,e in ranges),
            'requested_slots': [hex(s) for s in sorted(wanted)], 'references': rows,
            'limits': 'Pattern candidates only, within caller-qualified ranges. No CFG, delayed loads, other registers, snapshot/schema recovery or behavioral parity. Absence is not proof of no reference.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--elf', type=Path, required=True)
    parser.add_argument('--ranges', type=Path, required=True)
    parser.add_argument('--pool', type=Path, required=True)
    parser.add_argument('--slot', action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    wanted = {number(s) for s in args.slot}
    if not 0 < len(wanted) <= 4096 or any(s < 0 or s % 8 for s in wanted):
        parser.error('Supply 1..4096 nonnegative 8-byte-aligned pool offsets')
    result = analyze(args.elf, args.ranges, args.pool, wanted)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({'candidate_references': len(result['references']),
                      'range_count': result['range_count']}))


if __name__ == '__main__':
    main()
