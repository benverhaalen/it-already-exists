#!/usr/bin/env python3
"""Find missing typed references in captured Firestore documents, without requests.

Input is a JSON list of REST documents. Findings are discovery leads, not read
permissions, complete dependency coverage, or evidence of runtime use.
"""
import argparse
import json
from pathlib import Path
from firestore_reference_transfer import ROOT, transfer


def audit(documents, source_root):
    if not ROOT.fullmatch(source_root) or not isinstance(documents, list):
        raise ValueError('expected a document list and explicit default-database root')
    captured = {}
    references = {}
    external = {}

    def pointer(path, name):
        return path + '/' + str(name).replace('~', '~0').replace('/', '~1')

    def walk(item, document, path):
        kind, value = next(iter(item.items()))
        if kind == 'referenceValue':
            bucket = references if value.startswith(source_root) else external
            bucket.setdefault(value, []).append({'document': document, 'field': path})
        elif kind == 'mapValue':
            for name, child in value.get('fields', {}).items():
                walk(child, document, pointer(path, name))
        elif kind == 'arrayValue':
            for index, child in enumerate(value.get('values', [])):
                walk(child, document, pointer(path, index))

    for document in documents:
        if not isinstance(document, dict) or not isinstance(document.get('name'), str):
            raise ValueError('invalid captured document')
        name = document['name']
        if not name.startswith(source_root):
            raise ValueError('captured document outside source root')
        # Reuse typed-reference validation. No namespace or input mutation.
        transfer({'name': {'referenceValue': name}}, source_root, source_root)
        fields = document.get('fields', {})
        validated, _ = transfer(fields, source_root, source_root)
        if name in captured:
            if captured[name] != validated:
                raise ValueError('conflicting captures for ' + name)
            continue
        captured[name] = validated
        for field, item in validated.items():
            walk(item, name, pointer('', field))
    return {
        'captured_documents': len(captured),
        'referenced_documents': len(references),
        'missing': {name: references[name] for name in sorted(references) if name not in captured},
        'external': {name: external[name] for name in sorted(external)},
        'limits': 'Typed references only; does not discover queries, string IDs, server rules or authorize reads.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--source-root', required=True)
    args = parser.parse_args()
    if args.input.stat().st_size > 16 * 1024 * 1024:
        raise ValueError('input exceeds 16 MiB')
    result = audit(json.loads(args.input.read_text()), args.source_root)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
