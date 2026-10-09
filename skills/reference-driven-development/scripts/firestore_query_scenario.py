#!/usr/bin/env python3
"""Project observed Firestore rows into a private, partial historical fixture.

No requests, namespace changes, cache-key reconstruction or freshness claims.
Input manifests contain parsed JSON bodies, not the original request body bytes.
Output wraps derived rows with provenance; it is not a captured runQuery response.
"""
import argparse
import base64
import binascii
import copy
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import urlsplit

from offline_worker import strict_json

MAX_BYTES = 32 * 1024 * 1024
MAX_ROWS = 10000
RESOURCE = re.compile(r'projects/[A-Za-z0-9_-]+/databases/(?:\(default\)|[A-Za-z0-9_-]+)/documents(?:/.*)?')
FIELD = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
STAMP = re.compile(r'([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,9}))?(Z|[+-][0-9]{2}:[0-9]{2})')
KINDS = {'nullValue', 'booleanValue', 'integerValue', 'doubleValue', 'timestampValue',
         'stringValue', 'bytesValue', 'referenceValue', 'geoPointValue', 'arrayValue', 'mapValue'}


def _object(value, required, optional=()):
    if not isinstance(value, dict) or not set(required) <= set(value) or set(value) - set(required) - set(optional):
        raise ValueError('unsupported or malformed object shape')
    return value


def _segment(value):
    if (not isinstance(value, str) or not value or value in ('.', '..')
            or any(c in value for c in '/\\%?#') or any(c.isspace() or ord(c) < 32 for c in value)):
        raise ValueError('unsupported resource segment')
    return value


def _resource(value, document=False):
    if not isinstance(value, str) or not RESOURCE.fullmatch(value):
        raise ValueError('canonical Firestore resource required')
    parts = value.split('/')
    for part in parts:
        _segment(part)
    suffix = parts[5:]
    if len(suffix) % 2 or (document and not suffix):
        raise ValueError('resource must identify a document or the document root')
    return '/'.join(parts[:5]), suffix


def _field(value):
    if isinstance(value, str) and value.startswith('`') and value.endswith('`'):
        value = value[1:-1]
    if not isinstance(value, str) or not FIELD.fullmatch(value) or value.startswith('__') and value.endswith('__'):
        raise ValueError('only simple top-level field paths supported')
    return value


def _timestamp(value):
    """Compare instants at nanosecond precision without losing source spelling."""
    match = STAMP.fullmatch(value) if isinstance(value, str) else None
    if match is None or match[8] == '-00:00':
        raise ValueError('explicit known RFC3339 timezone and at most nine fractional digits required')
    year, month, day, hour, minute, second = map(int, match.groups()[:6])
    stamp = datetime(year, month, day, hour, minute, second)
    seconds = (stamp.toordinal() - 1) * 86400 + hour * 3600 + minute * 60 + second
    zone = match[8]
    if zone != 'Z':
        zh, zm = map(int, zone[1:].split(':'))
        if zh > 23 or zm > 59:
            raise ValueError('invalid timezone offset')
        seconds -= (1 if zone[0] == '+' else -1) * (zh * 3600 + zm * 60)
    if not 0 <= seconds < datetime.max.toordinal() * 86400:
        raise ValueError('timestamp instant outside supported year range')
    return seconds, int((match[7] or '').ljust(9, '0'))


def _value_kind(item):
    if not isinstance(item, dict) or len(item) != 1 or next(iter(item)) not in KINDS:
        raise ValueError('relevant field must contain exactly one recognized Firestore value type')
    kind, value = next(iter(item.items()))
    if kind == 'booleanValue' and type(value) is not bool:
        raise ValueError('booleanValue must be a JSON boolean')
    if kind == 'timestampValue':
        _timestamp(value)
    elif kind == 'referenceValue':
        _resource(value, document=True)
    elif kind in ('stringValue', 'bytesValue') and not isinstance(value, str):
        raise ValueError('string or bytes value must be a string')
    elif kind == 'bytesValue':
        try:
            base64.b64decode(value, altchars=b'-_', validate=True)
        except (ValueError, binascii.Error):
            raise ValueError('invalid base64 bytesValue') from None
    elif kind == 'integerValue':
        if not isinstance(value, str) or not re.fullmatch(r'-?(?:0|[1-9][0-9]*)', value) or not -(2**63) <= int(value) < 2**63:
            raise ValueError('integerValue must be an int64 decimal string')
    elif kind == 'doubleValue' and not (type(value) in (int, float) or value in ('NaN', 'Infinity', '-Infinity')):
        raise ValueError('invalid doubleValue')
    elif kind == 'nullValue' and value not in (None, 'NULL_VALUE'):
        raise ValueError('invalid nullValue')
    elif kind == 'mapValue':
        _object(value, (), ('fields',))
        if not isinstance(value.get('fields', {}), dict):
            raise ValueError('invalid mapValue')
    elif kind == 'arrayValue':
        _object(value, (), ('values',))
        if not isinstance(value.get('values', []), list):
            raise ValueError('invalid arrayValue')
    elif kind == 'geoPointValue':
        _object(value, ('latitude', 'longitude'))
        if (any(type(v) not in (int, float) for v in value.values())
                or not -90 <= value['latitude'] <= 90 or not -180 <= value['longitude'] <= 180):
            raise ValueError('invalid geoPointValue')
    return kind


def _filter(value, op, kind):
    body = _object(value, ('fieldFilter',))['fieldFilter']
    _object(body, ('field', 'op', 'value'))
    name = _field(_object(body['field'], ('fieldPath',))['fieldPath'])
    if body['op'] != op or _value_kind(body['value']) != kind:
        raise ValueError('unsupported typed filter')
    return name, copy.deepcopy(body['value'])


def _manifest(value, source):
    _object(value, ('url', 'method', 'body'), ('responseFile',))
    if (value['method'] != 'POST' or not isinstance(value['url'], str)
            or any(c.isspace() or ord(c) < 32 for c in value['url'])):
        raise ValueError('explicit POST runQuery manifest required')
    url = urlsplit(value['url'])
    if (url.scheme != 'https' or url.netloc != 'firestore.googleapis.com' or url.query or url.fragment
            or not url.path.startswith('/v1/') or not url.path.endswith(':runQuery')):
        raise ValueError('canonical Firestore REST runQuery endpoint required')
    parent = url.path[4:-9]
    database, _ = _resource(parent)
    declared = value.get('responseFile')
    if declared is not None and (not isinstance(declared, str) or not re.fullmatch(r'[0-9a-f]{64}\.json', declared)):
        raise ValueError('responseFile must be a declared cache basename, never a path')
    query = _object(value['body'], ('structuredQuery',))['structuredQuery']
    _object(query, ('from', 'where'), ('limit',) if source else ())
    if not isinstance(query['from'], list) or len(query['from']) != 1:
        raise ValueError('exactly one collection selector required')
    selector = _object(query['from'][0], ('collectionId',), ('allDescendants',))
    collection = _segment(selector['collectionId'])
    descendants = selector.get('allDescendants', False)
    if type(descendants) is not bool or (not source and descendants):
        raise ValueError('target must select an immediate collection')
    result = {'parent': parent, 'database': database, 'collection': collection,
              'all_descendants': descendants, 'declared_response_file': declared}
    if source:
        name, predicate = _filter(query['where'], 'EQUAL', 'referenceValue')
        limit = query.get('limit')
        if limit is not None and (type(limit) is not int or not 0 <= limit <= MAX_ROWS):
            raise ValueError('source limit outside supported row bound')
        result.update(reference_field=name, reference_value=predicate, limit=limit)
    else:
        composite = _object(query['where'], ('compositeFilter',))['compositeFilter']
        _object(composite, ('op', 'filters'))
        if composite['op'] != 'AND' or not isinstance(composite['filters'], list) or len(composite['filters']) != 2:
            raise ValueError('target requires exactly two AND filters')
        predicates = {}
        for item in composite['filters']:
            body = _object(item, ('fieldFilter',))['fieldFilter']
            op = body.get('op') if isinstance(body, dict) else None
            kind = {'GREATER_THAN_OR_EQUAL': 'timestampValue', 'EQUAL': 'booleanValue'}.get(op)
            if kind is None or op in predicates:
                raise ValueError('target requires one timestamp lower bound and one boolean equality')
            predicates[op] = _filter(item, op, kind)
        tf, tv = predicates['GREATER_THAN_OR_EQUAL']
        bf, bv = predicates['EQUAL']
        if tf == bf:
            raise ValueError('target filters must address distinct fields')
        result.update(timestamp_field=tf, timestamp_value=tv, boolean_field=bf, boolean_value=bv)
    return result


def _rows(value):
    if isinstance(value, dict):
        value = [value]
    if not isinstance(value, list) or len(value) > MAX_ROWS:
        raise ValueError('bounded REST document or query-row list required')
    documents, observations = [], []
    shape, finished = None, False
    for index, row in enumerate(value):
        if not isinstance(row, dict) or finished:
            raise ValueError('malformed row or rows after completion')
        current = 'documents' if 'name' in row else 'query-rows'
        if shape is not None and shape != current:
            raise ValueError('mixed response shapes unsupported')
        shape = current
        if current == 'documents':
            document = row
        else:
            _object(row, (), ('document', 'readTime', 'done', 'skippedResults'))
            if not row:
                raise ValueError('empty query row')
            if 'readTime' in row:
                _timestamp(row['readTime'])
            if 'done' in row and type(row['done']) is not bool:
                raise ValueError('invalid completion marker')
            if 'skippedResults' in row and (type(row['skippedResults']) is not int or row['skippedResults'] != 0):
                raise ValueError('offset or skipped results unsupported')
            metadata = {k: copy.deepcopy(v) for k, v in row.items() if k != 'document'}
            if metadata:
                observations.append({'source_row': index, **metadata})
            finished = row.get('done', False)
            document = row.get('document')
            if document is None:
                if 'document' in row:
                    raise ValueError('null document unsupported')
                continue
        _object(document, ('name',), ('fields', 'createTime', 'updateTime'))
        _resource(document['name'], document=True)
        if not isinstance(document.get('fields', {}), dict):
            raise ValueError('document fields must be an object')
        for key in ('createTime', 'updateTime'):
            if key in document:
                _timestamp(document[key])
        documents.append(document)
    return documents, observations, shape or 'empty-list'


def _in_scope(name, scope):
    prefix = scope['parent'] + '/'
    if not name.startswith(prefix):
        return False
    relative = name[len(prefix):].split('/')
    if scope['all_descendants']:
        return relative[-2] == scope['collection']
    return len(relative) == 2 and relative[0] == scope['collection']


def _decode(payload):
    if not isinstance(payload, bytes) or len(payload) > MAX_BYTES:
        raise ValueError('bounded UTF-8 JSON bytes required')
    value = strict_json(payload.decode('utf-8'))
    pending = [value]
    while pending:
        item = pending.pop()
        if isinstance(item, float) and not math.isfinite(item):
            raise ValueError('non-finite JSON number')
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, list):
            pending.extend(item)
    return value


def project(response_bytes, source_manifest_bytes, target_manifest_bytes):
    source = _manifest(_decode(source_manifest_bytes), source=True)
    target = _manifest(_decode(target_manifest_bytes), source=False)
    if source['database'] != target['database']:
        raise ValueError('source and target must use the same database; reference transfer is separate')
    documents, observations, shape = _rows(_decode(response_bytes))
    if source['limit'] is not None and len(documents) > source['limit']:
        raise ValueError('observed rows exceed declared source limit')
    seen, selected, excluded = set(), [], {'collection_scope': 0, 'timestamp_filter': 0, 'boolean_filter': 0}
    threshold = _timestamp(target['timestamp_value']['timestampValue'])
    for document in documents:
        name = document['name']
        if name in seen:
            raise ValueError('duplicate document names are ambiguous')
        seen.add(name)
        fields = document.get('fields', {})
        reference = fields.get(source['reference_field'])
        if (not _in_scope(name, source) or reference is None
                or _value_kind(reference) != 'referenceValue' or reference != source['reference_value']):
            raise ValueError('observed document does not satisfy declared source scope')
        # Validate both relevant leaves before exclusion; AND must not hide malformed input.
        stamp = fields.get(target['timestamp_field'])
        boolean = fields.get(target['boolean_field'])
        sk = _value_kind(stamp) if target['timestamp_field'] in fields else None
        bk = _value_kind(boolean) if target['boolean_field'] in fields else None
        if not _in_scope(name, target):
            excluded['collection_scope'] += 1
        elif sk != 'timestampValue' or _timestamp(stamp['timestampValue']) < threshold:
            excluded['timestamp_filter'] += 1
        elif bk != 'booleanValue' or boolean != target['boolean_value']:
            excluded['boolean_filter'] += 1
        else:
            selected.append(copy.deepcopy(document))
    selected.sort(key=lambda doc: (_timestamp(doc['fields'][target['timestamp_field']]['timestampValue']),
                                   doc['name'].encode('utf-8')))
    return {'response': [{'document': document} for document in selected], 'provenance': {
        'schema_version': 1, 'evidence_mode': 'derived-fixture', 'coverage': 'observed-subset-only',
        'complete': False, 'current_state': 'unknown', 'ready_for_fidelity': False,
        'source_response_sha256': hashlib.sha256(response_bytes).hexdigest(),
        'source_manifest_sha256': hashlib.sha256(source_manifest_bytes).hexdigest(),
        'target_manifest_sha256': hashlib.sha256(target_manifest_bytes).hexdigest(),
        'request_body_bytes_available': False, 'request_cache_keys_verified': False,
        'source_scope': source, 'target_scope': target,
        'coverage_difference': {'source': 'collection/reference-equality observation, possibly limited',
                                'target': 'immediate collection/timestamp lower bound AND boolean equality',
                                'source_scope_implies_target_completeness': False},
        'source_response_shape': shape, 'source_observations': observations,
        'observed_documents': len(documents), 'selected_documents': len(selected), 'excluded_documents': excluded,
        'ordering': 'deterministic timestamp-instant then UTF-8 document-name order; target order unverified',
        'network_calls': 0,
        'limits': 'Supplied observations only; acquisition and source completeness unverified. '
                  'Different filters/scopes cannot establish a complete target query even when all rows match. '
                  'No current state, backend fidelity, runtime use or journey coverage established. '
                  'Relevant leaves only, not a full Firestore schema validator. Source readTime metadata '
                  'does not describe the target; no target readTime is fabricated. Manifest hashes cover '
                  'manifest bytes, not original request-body bytes or cache identity.'}}


def _safe_path(path):
    if '..' in path.parts:
        raise ValueError('path traversal unsupported')
    current = path.absolute()
    while current != current.parent:
        if current.is_symlink():
            # These root-owned macOS aliases can prefix ordinary tempfile paths.
            aliases = {Path('/var'): Path('/private/var'), Path('/tmp'): Path('/private/tmp')}
            if current not in aliases or current.resolve() != aliases[current]:
                raise ValueError('symlink path components unsupported')
        current = current.parent


def _read(path):
    _safe_path(path)
    if not path.is_file():
        raise ValueError('input must be an ordinary file without path traversal')
    if path.stat().st_size > MAX_BYTES:
        raise ValueError('input exceeds byte bound')
    with path.open('rb') as stream:
        payload = stream.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError('input exceeds byte bound')
    return payload


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--target-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    _safe_path(args.output)
    if not args.output.parent.is_dir():
        raise ValueError('output requires an existing ordinary directory without path traversal')
    result = project(_read(args.input), _read(args.source_manifest), _read(args.target_manifest))
    payload = (json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(payload)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
