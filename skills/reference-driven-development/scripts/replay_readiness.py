#!/usr/bin/env python3
"""Audit declared offline request dependencies; never open a network connection.

This adapter uses SHA256(URL UTF-8 bytes + exact request body bytes) cache keys.
It checks availability and recorded provenance, not response semantics, freshness,
or whether the declared requests cover the full journey.
"""
import argparse
import hashlib
import json
from pathlib import Path
from comparison import bound_file
from offline_worker import strict_json


def audit(manifest, root):
    cases = manifest.get('requests')
    if not isinstance(cases, list) or not cases or len(cases) > 1000:
        raise ValueError('nonempty bounded request list required')
    seen = set()
    outcomes = []
    for case in cases:
        identifier = case.get('id')
        url = case.get('url')
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError('unique request ids required')
        seen.add(identifier)
        if not isinstance(url, str) or not url.startswith(('https://', 'http://')):
            raise ValueError('explicit HTTP URL required')
        mode = case.get('evidence_mode')
        if mode not in ('captured-response', 'derived-fixture', 'unknown'):
            raise ValueError('explicit evidence mode required')
        body = bound_file(root, case['body']) if 'body' in case else b''
        key = hashlib.sha256(url.encode('utf-8') + body).hexdigest()
        result = {'id': identifier, 'cache_key': key, 'evidence_mode': mode,
                  'ready': False, 'response_verified': False}
        response = case.get('response')
        if response is None:
            result['reason'] = 'missing_declared_response'
        else:
            if response.get('path') != key + '.json':
                raise ValueError('response path must match exact request cache key')
            try:
                payload = bound_file(root, response)
                strict_json(payload.decode('utf-8'))
                result['response_verified'] = True
                result['ready'] = mode == 'captured-response'
                result['reason'] = ('captured_response_available' if result['ready']
                                    else 'derived_or_unknown_response_requires_review')
            except (ValueError, OSError, UnicodeError) as error:
                result['reason'] = 'missing_changed_or_invalid_response'
                result['detail'] = str(error)
        outcomes.append(result)
    return {'ready_for_declared_replay': all(r['ready'] for r in outcomes),
            'requests': outcomes, 'network_calls': 0,
            'limits': 'Declared exact byte dependencies only. Provenance labels are supplied, '
                      'not independently established. Does not prove query completeness, '
                      'freshness, response semantics, runtime use or whole-journey coverage.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = audit(strict_json(args.manifest.read_text()), args.root)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    return 0 if report['ready_for_declared_replay'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
