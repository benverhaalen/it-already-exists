#!/usr/bin/env python3
"""Replace explicitly reviewed asset URL leaves; never download or contact services.

Bindings use RFC 6901 JSON pointers with exact expected source values. Keep the
capture and bindings private. This does not discover assets or establish rights,
network isolation, byte equivalence, or original-client rendering correctness.
"""
import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlsplit


def tokens(pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('expected a non-root JSON pointer')
    result = []
    for part in pointer[1:].split('/'):
        if re.search(r'~(?![01])', part):
            raise ValueError('invalid JSON pointer escape')
        result.append(part.replace('~1', '/').replace('~0', '~'))
    return result


def key(container, token):
    if isinstance(container, dict):
        if token not in container:
            raise ValueError('binding field missing')
        return token
    if isinstance(container, list) and re.fullmatch(r'0|[1-9][0-9]*', token):
        index = int(token)
        if index < len(container):
            return index
    raise ValueError('binding does not address an existing leaf')


def transfer(document, bindings):
    if not isinstance(document, (dict, list)):
        raise ValueError('expected a JSON object or array')
    if not isinstance(bindings, list) or len(bindings) > 10000:
        raise ValueError('expected at most 10000 explicit bindings')
    output = copy.deepcopy(document)
    seen, changes = set(), []
    for binding in bindings:
        if not isinstance(binding, dict) or set(binding) != {'pointer', 'expected', 'replacement'}:
            raise ValueError('binding needs pointer, expected and replacement only')
        pointer, expected, replacement = (binding[n] for n in ('pointer', 'expected', 'replacement'))
        parts = tokens(pointer)
        address = tuple(parts)
        if address in seen:
            raise ValueError('duplicate binding')
        seen.add(address)
        if not isinstance(expected, str) or not isinstance(replacement, str):
            raise ValueError('asset URLs must be strings')
        # URLs remain opaque exact values: do not decode or normalize signed paths.
        for url in (expected, replacement):
            if any(ord(c) <= 32 or ord(c) == 127 for c in url):
                raise ValueError('invalid URL whitespace or control character')
            parsed = urlsplit(url)
            if parsed.scheme not in ('http', 'https') or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.fragment:
                raise ValueError('expected an HTTP asset URL without credentials or fragment')
            try:
                parsed.port
            except ValueError as exc:
                raise ValueError('invalid URL port') from exc
        parent = output
        for token in parts[:-1]:
            parent = parent[key(parent, token)]
        leaf = key(parent, parts[-1])
        if parent[leaf] != expected:
            raise ValueError('binding source mismatch')
        parent[leaf] = replacement
        changes.append({'pointer': pointer, 'source_url_sha256': hashlib.sha256(expected.encode()).hexdigest(), 'replacement_url_sha256': hashlib.sha256(replacement.encode()).hexdigest()})
    return output, changes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--bindings', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.input.read_bytes()
    binding_bytes = args.bindings.read_bytes()
    if len(raw) > 20 * 1024 * 1024 or len(binding_bytes) > 8 * 1024 * 1024:
        raise ValueError('input exceeds transfer limit')
    document, changes = transfer(json.loads(raw), json.loads(binding_bytes))
    with args.output.open('x') as stream:
        json.dump({'document': document, 'changes': changes, 'source_sha256': hashlib.sha256(raw).hexdigest(), 'bindings_sha256': hashlib.sha256(binding_bytes).hexdigest()}, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    main()
