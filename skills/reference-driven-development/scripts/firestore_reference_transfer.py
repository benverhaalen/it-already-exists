#!/usr/bin/env python3
"""Translate typed Firestore references without rewriting strings or source data.

This helper does not contact services or establish permission to read documents.
Use it on a reviewed REST fields object, keeping the original capture separately.
"""
import argparse
import copy
import json
import re
from pathlib import Path

ROOT = re.compile(r'^projects/[A-Za-z0-9_-]+/databases/\((?:default)\)/documents/$')


def transfer(fields, source_root, target_root):
    if not ROOT.fullmatch(source_root) or not ROOT.fullmatch(target_root):
        raise ValueError('expected explicit default-database document roots')
    if not isinstance(fields, dict):
        raise ValueError('fields must be a Firestore REST fields object')
    changes = []

    def value(item, path):
        if not isinstance(item, dict) or len(item) != 1:
            raise ValueError('invalid Firestore value at ' + path)
        kind, data = next(iter(item.items()))
        if kind == 'referenceValue':
            if not isinstance(data, str):
                raise ValueError('reference must be a string')
            if data.startswith(source_root):
                suffix = data[len(source_root):]
                segments = suffix.split('/')
                if not suffix or len(segments) % 2 or any(not s or s in ('.', '..') for s in segments):
                    raise ValueError('invalid document reference at ' + path)
                changes.append(path)
                return {kind: target_root + suffix}
        elif kind == 'mapValue':
            if not isinstance(data, dict) or set(data) - {'fields'}:
                raise ValueError('invalid map at ' + path)
            return {kind: {'fields': walk(data['fields'], path)} if 'fields' in data else {}}
        elif kind == 'arrayValue':
            if not isinstance(data, dict) or set(data) - {'values'} or not isinstance(data.get('values', []), list):
                raise ValueError('invalid array at ' + path)
            return {kind: {'values': [value(v, path + '/' + str(i)) for i, v in enumerate(data['values'])]} if 'values' in data else {}}
        return copy.deepcopy(item)

    def walk(items, path):
        if not isinstance(items, dict):
            raise ValueError('invalid fields at ' + path)
        return {name: value(item, path + '/' + name) for name, item in items.items()}

    return walk(fields, ''), changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', required=True)
    parser.add_argument('--target-root', required=True)
    args = parser.parse_args()
    fields, changes = transfer(json.loads(args.input.read_text()), args.source_root, args.target_root)
    with args.output.open('x') as stream:
        json.dump({'fields': fields, 'translated_reference_paths': changes}, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
