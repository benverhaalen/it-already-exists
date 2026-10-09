#!/usr/bin/env python3
"""Retain immutable analysis and return bounded views; does not run analyzers.

Bindings and digests detect stale/mixed results, not semantic truth. Single writer.
"""
import argparse
import hashlib
import json
from pathlib import Path


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('missing ' + label)
    return value


def binding(artifact, query):
    """Explicit immutable queries only; artifact/profile/parameters all bind reuse."""
    profile = query.get('provider_profile')
    if not isinstance(profile, dict) or not profile:
        raise ValueError('provider_profile must include identity, version and settings')
    for key in ('provider', 'version'):
        text(profile.get(key), key)
    if not isinstance(profile.get('settings'), dict):
        raise ValueError('explicit provider settings required')
    text(query.get('operation'), 'operation')
    parameters = query.get('parameters')
    if not isinstance(parameters, dict):
        raise ValueError('explicit parameters required')
    effects = query.get('effects')
    required = {'immutable': True, 'mutates_artifact': False,
                'depends_on_live_state': False, 'depends_on_implicit_cursor': False}
    if not isinstance(effects, dict) or any(type(effects.get(k)) is not bool or effects[k] != v for k, v in required.items()):
        raise ValueError('query is live, mutable, cursor-dependent or unqualified')
    artifact = Path(artifact)
    if not artifact.is_file():
        raise ValueError('artifact must be an explicit file')
    return {'artifact_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
            'provider_profile': profile, 'operation': query['operation'],
            'parameters': parameters, 'effects': required}


def retain(store, artifact, query, result, evidence):
    key = binding(artifact, query)
    text(evidence.get('basis'), 'evidence basis')
    if evidence['basis'] not in {'observed', 'documented', 'inferred'}:
        raise ValueError('invalid evidence basis')
    for field in ('source', 'conditions'):
        text(evidence.get(field), field)
    if not isinstance(evidence.get('limitations'), list) or any(not isinstance(v, str) for v in evidence['limitations']):
        raise ValueError('limitations must be an explicit string list')
    body = {'binding': key, 'result': result, 'evidence': evidence}
    identifier = digest(body)
    store = Path(store)
    store.mkdir(parents=True, exist_ok=True)
    # Keep every retained parent immutable, even when the same query is rerun.
    parent = store / (identifier + '.json')
    if parent.exists():
        if parent.read_bytes() != encoded(body):
            raise ValueError('retained evidence was modified')
    else:
        with parent.open('xb') as stream:
            stream.write(encoded(body))
    index = store / (digest(key) + '.ref')
    temporary = index.with_suffix('.tmp')
    temporary.write_text(identifier)
    temporary.replace(index)
    return {'evidence_id': identifier, 'binding_id': digest(key), 'status': 'retained'}


def lookup(store, artifact, query):
    key = binding(artifact, query)
    index = Path(store) / (digest(key) + '.ref')
    if not index.exists():
        return {'status': 'miss', 'binding_id': digest(key)}
    identifier = index.read_text()
    parent = read_parent(store, identifier)
    if parent['binding'] != key:
        raise ValueError('cache binding mismatch')
    return {'status': 'hit', 'evidence_id': identifier, 'binding_id': digest(key)}


def read_parent(store, identifier):
    if not isinstance(identifier, str) or len(identifier) != 64 or any(c not in '0123456789abcdef' for c in identifier):
        raise ValueError('invalid evidence id')
    parent = json.loads((Path(store) / (identifier + '.json')).read_text())
    if digest(parent) != identifier:
        raise ValueError('retained evidence digest mismatch')
    return parent


def view(store, identifier, artifact, query, pointer='', offset=0, limit=20, max_bytes=65536):
    parent = read_parent(store, identifier)
    if parent['binding'] != binding(artifact, query):
        raise ValueError('view belongs to another artifact or provider profile')
    if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError('invalid page bounds')
    value = parent['result']
    if pointer:
        if not pointer.startswith('/'):
            raise ValueError('use a JSON pointer')
        for part in pointer[1:].split('/'):
            part = part.replace('~1', '/').replace('~0', '~')
            value = value[int(part)] if isinstance(value, list) else value[part]
    if isinstance(value, list):
        total = len(value)
        selected = value[offset:offset + limit]
    elif isinstance(value, dict):
        keys = sorted(value)
        total = len(keys)
        selected = {k: value[k] for k in keys[offset:offset + limit]}
    else:
        raise ValueError('select a collection to page; scalar output is unbounded')
    if type(max_bytes) is not int or not 256 <= max_bytes <= 1048576:
        raise ValueError('view byte budget must be between 256 and 1048576')
    report = {'parent_evidence_id': identifier, 'binding_id': digest(parent['binding']),
            'evidence': parent['evidence'], 'pointer': pointer, 'offset': offset,
            'total': total, 'next_offset': offset + limit if offset + limit < total else None,
            'value': selected, 'limits': 'Bounded view of retained data; does not prove truth.'}
    if len(encoded(report)) > max_bytes:
        raise ValueError('view exceeds byte budget; select a deeper collection or smaller page')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['retain', 'lookup', 'view'])
    parser.add_argument('--store', required=True, type=Path)
    parser.add_argument('--artifact', required=True, type=Path)
    parser.add_argument('--query', required=True, type=Path)
    parser.add_argument('--result', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--id')
    parser.add_argument('--pointer', default='')
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--limit', type=int, default=20)
    parser.add_argument('--max-bytes', type=int, default=65536)
    args = parser.parse_args()
    query = json.loads(args.query.read_text())
    try:
        if args.action == 'retain':
            if not args.result or not args.evidence:
                raise ValueError('retain needs --result and --evidence')
            report = retain(args.store, args.artifact, query, json.loads(args.result.read_text()), json.loads(args.evidence.read_text()))
        elif args.action == 'lookup':
            report = lookup(args.store, args.artifact, query)
        else:
            report = view(args.store, args.id, args.artifact, query, args.pointer, args.offset, args.limit, args.max_bytes)
        print(json.dumps(report, allow_nan=False))
    except (ValueError, KeyError, IndexError, OSError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
