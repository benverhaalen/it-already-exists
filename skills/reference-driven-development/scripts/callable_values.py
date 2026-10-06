#!/usr/bin/env python3
"""Decode bounded Firebase callable values for local fixtures; no service access."""
import argparse
import json
import math
import os
from pathlib import Path
import re

TYPES = {'type.googleapis.com/google.protobuf.Int64Value': (-(1 << 63), (1 << 63) - 1),
         'type.googleapis.com/google.protobuf.UInt64Value': (0, (1 << 64) - 1)}


def decode(value, max_nodes=10000, max_depth=64):
    """Return fresh JSON containers; preserve unknown typed maps for compatibility.

    Known integer wrappers require a canonical decimal string in range. This is
    deliberately stricter than SDK coercion. Python integers retain magnitude,
    not wire signedness; do not use the result as a lossless re-encoding oracle.
    """
    if type(max_nodes) is not int or max_nodes < 1 or type(max_depth) is not int or max_depth < 0:
        raise ValueError('invalid traversal bound')
    remaining = max_nodes

    def visit(item, depth):
        nonlocal remaining
        remaining -= 1
        if remaining < 0 or depth > max_depth:
            raise ValueError('callable value exceeds traversal bound')
        if isinstance(item, dict):
            if any(not isinstance(key, str) for key in item):
                raise ValueError('callable maps require string keys')
            tag = item.get('@type')
            if isinstance(tag, str) and tag in TYPES:
                text = item.get('value')
                if (set(item) != {'@type', 'value'} or not isinstance(text, str) or
                        len(text) > 20 or not re.fullmatch(r'(?:0|-?[1-9][0-9]*)', text)):
                    raise ValueError('invalid typed integer')
                number = int(text)
                low, high = TYPES[tag]
                if not low <= number <= high:
                    raise ValueError('typed integer out of range')
                return number
            return {key: visit(child, depth + 1) for key, child in item.items()}
        if isinstance(item, list):
            return [visit(child, depth + 1) for child in item]
        if item is None or type(item) in (str, bool, int):
            return item
        if type(item) is float and math.isfinite(item):
            return item
        raise ValueError('unsupported callable value')

    return visit(value, 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.input.stat().st_size > 1024 * 1024:
        parser.error('input exceeds 1 MiB')
    try:
        value = decode(json.loads(args.input.read_text()))
    except RecursionError:
        parser.error('JSON nesting exceeds parser capacity')
    except ValueError:
        parser.error('invalid or unsupported callable JSON value')
    with open(args.output, 'x', opener=lambda path, flags: os.open(path, flags, 0o600)) as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


if __name__ == '__main__':
    main()
