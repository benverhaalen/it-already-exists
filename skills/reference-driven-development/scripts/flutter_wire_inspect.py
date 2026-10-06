#!/usr/bin/env python3
"""Inspect one StandardMessageCodec message without erasing wire identities.

Protocol references: Flutter message_codecs.dart and StandardMessageCodec.java.
This is an offline diagnostic reader, not a platform-channel implementation.
Custom tags are supported only when explicitly declared to wrap one value.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import struct
import sys

MAX_BYTES = 1024 * 1024
MAX_NODES = 10000
MAX_DEPTH = 64
NAMES = {0: 'null', 1: 'true', 2: 'false', 3: 'int32', 4: 'int64',
         5: 'large-int-text', 6: 'float64', 7: 'string', 8: 'uint8-list',
         9: 'int32-list', 10: 'int64-list', 11: 'float64-list',
         12: 'list', 13: 'map', 14: 'float32-list'}


class Reader:
    def __init__(self, data, byte_order, custom_tags, max_nodes, max_depth):
        self.data, self.offset = data, 0
        self.order = '<' if byte_order == 'little' else '>'
        self.custom_tags = custom_tags
        self.remaining_nodes, self.max_depth = max_nodes, max_depth

    def fail(self, message):
        raise ValueError(f'{message} at byte {self.offset}')

    def take(self, count):
        if count < 0 or count > len(self.data) - self.offset:
            self.fail('Truncated message')
        start = self.offset
        self.offset += count
        return self.data[start:self.offset]

    def number(self, fmt):
        return struct.unpack(self.order + fmt, self.take(struct.calcsize(fmt)))[0]

    def size(self):
        first = self.number('B')
        return self.number('H') if first == 254 else self.number('I') if first == 255 else first

    def align(self, width):
        # Alignment is relative to the complete message, never a nested value.
        padding = self.take((-self.offset) % width)
        return padding.hex()

    def budget(self, count):
        if count > self.remaining_nodes:
            self.fail('Node budget exceeded')
        self.remaining_nodes -= count

    @staticmethod
    def float_value(value):
        return value if math.isfinite(value) else 'nan' if math.isnan(value) else '+inf' if value > 0 else '-inf'

    def value(self, depth=0):
        if depth > self.max_depth:
            self.fail('Depth budget exceeded')
        self.budget(1)
        start = self.offset
        tag = self.number('B')
        node = {'tag': tag, 'type': NAMES.get(tag, 'custom'), 'offset': start}
        if tag in self.custom_tags:
            node['wrapped'] = self.value(depth + 1)
        elif tag <= 2:
            node['value'] = None if tag == 0 else tag == 1
        elif tag in (3, 4):
            node['value'] = self.number('i' if tag == 3 else 'q')
        elif tag == 6:
            node['padding_hex'] = self.align(8)
            raw = self.take(8)
            node['bits_hex'] = raw.hex()
            node['value'] = self.float_value(struct.unpack(self.order + 'd', raw)[0])
        elif tag in (5, 7):
            raw = self.take(self.size())
            try:
                node['value'] = raw.decode('utf-8')
            except UnicodeDecodeError:
                self.fail('Invalid UTF-8')
        elif tag in (8, 9, 10, 11, 14):
            count = self.size()
            self.budget(count)
            fmt = {8: 'B', 9: 'i', 10: 'q', 11: 'd', 14: 'f'}[tag]
            width = struct.calcsize(fmt)
            node['padding_hex'] = self.align(width)
            raw = self.take(count * width)
            node['count'] = count
            node['bits_hex'] = raw.hex()
            if tag != 8:
                node['values'] = [self.float_value(x[0]) if tag in (11, 14) else x[0]
                                  for x in struct.iter_unpack(self.order + fmt, raw)]
        elif tag in (12, 13):
            count = self.size()
            if count * (2 if tag == 13 else 1) > self.remaining_nodes:
                self.fail('Node budget exceeded')
            # Preserve duplicate and non-string map keys instead of JSON coercion.
            node['items' if tag == 12 else 'pairs'] = [
                self.value(depth + 1) if tag == 12 else
                [self.value(depth + 1), self.value(depth + 1)] for _ in range(count)]
        else:
            self.fail('Unknown tag; inspect the versioned custom codec')
        node['end'] = self.offset
        return node


def inspect_message(data, *, byte_order, custom_tags=(), max_nodes=MAX_NODES, max_depth=MAX_DEPTH):
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_BYTES:
        raise ValueError('Expected nonempty bytes within input limit')
    if byte_order not in ('little', 'big'):
        raise ValueError('Explicit guest byte order required')
    tags = set(custom_tags)
    if any(type(tag) is not int or not 128 <= tag <= 255 for tag in tags):
        raise ValueError('Custom wrapping tags must be integers in 128..255')
    if type(max_nodes) is not int or not 1 <= max_nodes <= MAX_NODES:
        raise ValueError('Invalid node budget')
    if type(max_depth) is not int or not 0 <= max_depth <= MAX_DEPTH:
        raise ValueError('Invalid depth budget')
    reader = Reader(data, byte_order, tags, max_nodes, max_depth)
    root = reader.value()
    if reader.offset != len(data):
        reader.fail('Trailing bytes')
    return {'format': 'flutter-standard-message', 'bytes': len(data),
            'sha256': hashlib.sha256(data).hexdigest(), 'byte_order': byte_order,
            'custom_single_value_tags': sorted(tags), 'root': root,
            'limits': 'Wire inspection only; custom layouts require source evidence. '
                      'Not a method envelope, contract validator, or app behavior proof.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='Private binary message capture')
    parser.add_argument('--byte-order', required=True, choices=('little', 'big'))
    parser.add_argument('--wrap-tag', type=int, action='append', default=[],
                        help='Source-confirmed custom tag followed by one encoded value')
    parser.add_argument('--output', type=Path, required=True, help='New private JSON trace')
    args = parser.parse_args()
    try:
        with args.input.open('rb') as source:
            data = source.read(MAX_BYTES + 1)
        report = inspect_message(data, byte_order=args.byte_order, custom_tags=args.wrap_tag)
        rendered = json.dumps(report, ensure_ascii=True, allow_nan=False, indent=2) + '\n'
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as output:
            output.write(rendered)
        print('Wire trace saved; review privately.')
    except (ValueError, OSError) as error:
        # Never print the message contents or a path embedded in an OS exception.
        print('Wire inspection failed: ' + (str(error) if isinstance(error, ValueError)
                                            else type(error).__name__), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
