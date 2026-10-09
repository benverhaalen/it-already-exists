#!/usr/bin/env python3
"""Find missing typed references in captured Firestore documents, without requests.

Input is a JSON list of REST documents. Findings are discovery leads, not read
permissions, complete dependency coverage, or evidence of runtime use.
"""
import argparse
import json
import re
from pathlib import Path
from firestore_reference_transfer import ROOT, transfer


MAX_RELATIONSHIP_STEPS = 16


def _document_name(name):
    if not isinstance(name, str):
        raise ValueError('document name must be a full reference string')
    namespace, separator, suffix = name.partition('/documents/')
    segments = suffix.split('/')
    if (not separator or not re.fullmatch(r'projects/[A-Za-z0-9_-]+/databases/(?:\(default\)|[A-Za-z0-9_-]+)/documents/', namespace + separator) or
            len(segments) % 2 or any(not part or part in ('.', '..') for part in segments)):
        raise ValueError('invalid full document name')
    return namespace + separator, '/'.join(segments[:-1])


def _validate_captured_values(fields):
    # transfer has already validated field/value containers. Validate foreign
    # reference syntax too; transfer deliberately leaves those paths untouched.
    for item in fields.values():
        kind, value = next(iter(item.items()))
        if kind == 'referenceValue':
            _document_name(value)
        elif kind == 'mapValue':
            _validate_captured_values(value.get('fields', {}))
        elif kind == 'arrayValue':
            _validate_captured_values(dict(enumerate(value.get('values', []))))
        elif kind in ('stringValue', 'timestampValue', 'bytesValue'):
            if not isinstance(value, str):
                raise ValueError('invalid captured ' + kind)
        elif kind == 'booleanValue':
            if not isinstance(value, bool):
                raise ValueError('invalid captured booleanValue')
        elif kind == 'integerValue':
            if not isinstance(value, str) or not re.fullmatch(r'-?[0-9]+', value):
                raise ValueError('invalid captured integerValue')
        elif kind == 'doubleValue':
            if (isinstance(value, bool) or not isinstance(value, (int, float)) and
                    value not in ('NaN', 'Infinity', '-Infinity')):
                raise ValueError('invalid captured doubleValue')
        elif kind == 'nullValue':
            if value is not None and value != 'NULL_VALUE':
                raise ValueError('invalid captured nullValue')
        elif kind == 'geoPointValue':
            if (not isinstance(value, dict) or set(value) != {'latitude', 'longitude'} or
                    any(isinstance(number, bool) or not isinstance(number, (int, float))
                        for number in value.values())):
                raise ValueError('invalid captured geoPointValue')
        else:
            raise ValueError('unsupported captured value kind')


def check_relationship(documents, source_root, start_name, steps, expected_name):
    """Check an explicitly declared offline join against a full endpoint name.

    start_name and expected_name are independently qualified full document names
    in source_root. Each step is {field, collection, encoding?}; field is a literal
    top-level key and collection is an exact relative collection path, including
    any parent document path. The
    default encoding, 'reference', requires referenceValue. Only an explicitly
    declared 'relative_path' step accepts stringValue containing collection/id.

    Invalid API contracts, invalid reference names, unsupported typed-value
    shapes or conflicting captures raise ValueError. Other Firestore scalar
    validity is outside this check. Missing records/fields are unresolved;
    observed contract or endpoint mismatches fail. Only status 'matched' qualifies
    this declared join. No role is inferred from an ID, and this does not
    establish business rules or runtime use. An empty steps list checks endpoint
    identity only; it supplies no witnessed relationship traversal.
    """
    if not isinstance(source_root, str) or not ROOT.fullmatch(source_root) or not isinstance(documents, list):
        raise ValueError('expected a document list and explicit default-database root')
    for name in (start_name, expected_name):
        namespace, _ = _document_name(name)
        if namespace != source_root:
            raise ValueError('endpoint contract outside source root')
    if not isinstance(steps, list) or len(steps) > MAX_RELATIONSHIP_STEPS:
        raise ValueError('expected at most %d explicit relationship steps' % MAX_RELATIONSHIP_STEPS)
    declared = []
    for step in steps:
        if (not isinstance(step, dict) or set(step) - {'field', 'collection', 'encoding'} or
                not {'field', 'collection'} <= set(step) or
                not isinstance(step['field'], str) or not step['field'] or
                not isinstance(step['collection'], str)):
            raise ValueError('invalid relationship step')
        collection = step['collection']
        parts = collection.split('/')
        encoding = step.get('encoding', 'reference')
        if (len(parts) % 2 != 1 or any(not part or part in ('.', '..') for part in parts) or
                encoding not in ('reference', 'relative_path')):
            raise ValueError('invalid relationship collection or encoding')
        declared.append({'field': step['field'], 'collection': collection, 'encoding': encoding})

    captured = {}
    for document in documents:
        if not isinstance(document, dict) or not isinstance(document.get('name'), str):
            raise ValueError('invalid captured document')
        name = document['name']
        namespace, _ = _document_name(name)
        if namespace != source_root:
            raise ValueError('captured document outside source root')
        try:
            fields, _ = transfer(document.get('fields', {}), source_root, source_root)
        except (TypeError, RecursionError) as error:
            raise ValueError('malformed captured fields') from error
        _validate_captured_values(fields)
        if name in captured and captured[name] != fields:
            raise ValueError('conflicting captures for ' + name)
        captured[name] = fields

    current = start_name
    trace = []

    def result(status, reason):
        return {'status': status, 'reason': reason, 'start_name': start_name,
                'expected_name': expected_name, 'endpoint': current if current in captured else None, 'trace': trace}

    if current not in captured:
        return result('unresolved', 'missing_start_document')
    seen = {current}
    for step in declared:
        field = step['field']
        entry = {'document': current, 'field': '/' + field.replace('~', '~0').replace('/', '~1'),
                 'collection': step['collection'], 'encoding': step['encoding'], 'target': None}
        trace.append(entry)
        if field not in captured[current]:
            entry['status'] = 'missing_field'
            return result('unresolved', 'missing_field')
        item = captured[current][field]
        kind = 'referenceValue' if step['encoding'] == 'reference' else 'stringValue'
        if kind not in item or not isinstance(item[kind], str):
            entry['status'] = 'wrong_encoding'
            return result('failed', 'wrong_encoding')
        target = item[kind] if kind == 'referenceValue' else source_root + item[kind]
        entry['target'] = target
        try:
            namespace, collection = _document_name(target)
        except ValueError:
            entry['status'] = 'invalid_reference'
            return result('failed', 'invalid_reference')
        if namespace != source_root:
            entry['status'] = 'foreign_namespace'
            return result('failed', 'foreign_namespace')
        if collection != step['collection']:
            entry['status'] = 'wrong_collection'
            return result('failed', 'wrong_collection')
        if target in seen:
            entry['status'] = 'cycle'
            return result('failed', 'cycle')
        if target not in captured:
            entry['status'] = 'missing_reference_document'
            return result('unresolved', 'missing_reference_document')
        entry['status'] = 'resolved'
        current = target
        seen.add(current)
    return result('matched' if current == expected_name else 'failed',
                  'endpoint_match' if current == expected_name else 'endpoint_mismatch')


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
