#!/usr/bin/env python3
"""Exact-request policy for a task-owned service observation proxy.

This is not a device firewall. Unknown requests stay local. Live forwarding
requires both a reviewed exact request and an explicit runtime opt-in.
"""
import base64
import hashlib
import json
import re

MAX_BODY = 1024 * 1024
MAX_POLICY = 4 * 1024 * 1024


def fingerprint(scheme, host, port, method, target, headers, body):
    """Include ALL headers/body bytes; changing auth or operation invalidates review."""
    if scheme not in {'http', 'https'} or not isinstance(port, int) or not 0 < port < 65536:
        raise ValueError('invalid destination')
    if not re.fullmatch(r'[A-Za-z0-9.-]{1,253}', host):
        raise ValueError('invalid host')
    if method not in {'GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'}:
        raise ValueError('unsupported method')
    if not target.startswith('/') or target.startswith('//') or '#' in target or len(target) > 8192:
        raise ValueError('invalid request target')
    if any(ord(c) < 33 or ord(c) > 126 for c in target):
        raise ValueError('non-ASCII or control character in target')
    if len(body) > MAX_BODY or len(headers) > 128:
        raise ValueError('request exceeds bound')
    normalized = []
    for name, value in headers:
        if not re.fullmatch(r'[!#$%&\'*+.^_`|~0-9A-Za-z-]{1,256}', name) or len(value) > 8192:
            raise ValueError('invalid header')
        if '\r' in value or '\n' in value:
            raise ValueError('header contains newline')
        # Upgrades/tunnels cannot escape into an unexamined bidirectional stream.
        if name.lower() == 'upgrade' or (name.lower() == 'connection' and 'upgrade' in value.lower()):
            raise ValueError('protocol upgrade is not permitted')
        normalized.append([name.lower(), value])
    record = {'scheme': scheme, 'host': host.lower(), 'port': port,
              'method': method, 'target': target,
              'headers': normalized, 'body_sha256': hashlib.sha256(body).hexdigest()}
    # Header order is retained: ambiguous/duplicate header interpretation is not normalized away.
    return hashlib.sha256(json.dumps(record, separators=(',', ':'), ensure_ascii=True).encode()).hexdigest()


class Policy:
    def __init__(self, data):
        if not isinstance(data, dict) or set(data) != {'schema_version', 'protected_hosts', 'rules'}:
            raise ValueError('invalid policy fields')
        if data['schema_version'] != 1 or not isinstance(data['rules'], list) or len(data['rules']) > 1024:
            raise ValueError('invalid policy version or rules')
        hosts = data['protected_hosts']
        if not isinstance(hosts, list) or len(hosts) > 256 or any(
                not isinstance(h, str) or not re.fullmatch(r'[a-z0-9.-]{1,253}', h) for h in hosts):
            raise ValueError('invalid protected hosts')
        self.protected = set(hosts)
        self.rules = {}
        for rule in data['rules']:
            if not isinstance(rule, dict) or not re.fullmatch(r'[a-f0-9]{64}', str(rule.get('fingerprint', ''))):
                raise ValueError('invalid request fingerprint')
            key = rule['fingerprint']
            if key in self.rules:
                raise ValueError('duplicate request fingerprint')
            if rule.get('action') == 'forward':
                if set(rule) != {'fingerprint', 'action', 'read_only_review'} or not isinstance(
                        rule['read_only_review'], str) or not rule['read_only_review'].strip():
                    raise ValueError('forward needs a read-only review reference')
            elif rule.get('action') == 'fixture':
                if set(rule) != {'fingerprint', 'action', 'status', 'content_type', 'body_base64'}:
                    raise ValueError('invalid fixture fields')
                if type(rule['status']) is not int or not 200 <= rule['status'] <= 599 or 300 <= rule['status'] < 400:
                    raise ValueError('fixture redirects are prohibited')
                if not isinstance(rule['content_type'], str) or len(rule['content_type']) > 256 or any(
                        c in rule['content_type'] for c in '\r\n'):
                    raise ValueError('invalid fixture content type')
                encoded = rule['body_base64']
                if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_BODY + 2) // 3):
                    raise ValueError('fixture exceeds bound')
                try:
                    body = base64.b64decode(encoded, validate=True)
                except ValueError as exc:
                    raise ValueError('invalid fixture encoding') from exc
                if len(body) > MAX_BODY:
                    raise ValueError('fixture exceeds bound')
                rule = dict(rule, body=body)
            else:
                raise ValueError('unknown action')
            self.rules[key] = rule

    @classmethod
    def load(cls, path):
        with open(path, 'rb') as stream:
            raw = stream.read(MAX_POLICY + 1)
        if len(raw) > MAX_POLICY:
            raise ValueError('policy exceeds bound')
        def unique(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError('duplicate JSON field')
                obj[key] = value
            return obj
        return cls(json.loads(raw, object_pairs_hook=unique))

    def decide(self, scheme, host, port, method, target, headers, body, live=False):
        try:
            key = fingerprint(scheme, host, port, method, target, headers, body)
        except (ValueError, TypeError):
            return {'action': 'deny', 'reason': 'invalid-request'}
        rule = self.rules.get(key)
        if not rule:
            return {'action': 'deny', 'reason': 'unreviewed-request', 'fingerprint': key}
        if rule['action'] == 'fixture':
            return dict(rule)
        if not live:
            return {'action': 'deny', 'reason': 'live-disabled', 'fingerprint': key}
        if any(host.lower() == h or host.lower().endswith('.' + h) for h in self.protected):
            return {'action': 'deny', 'reason': 'protected-host', 'fingerprint': key}
        return dict(rule)
