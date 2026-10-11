#!/usr/bin/env python3
"""Check a sanitized, ordered single-service authority trace without networking.

Input version 1 declares expected_authority {scheme, host, port}, ordered phases
[{name, identity_state}], and observations. Each observation has phase, kind
('configuration' or 'request') and authority. Requests may supply guard
('allowed', 'denied', 'unknown') and transport ('succeeded', 'failed',
'not_attempted', 'unknown'); absent facts remain unresolved.

Only explicitly sanitized endpoint components and fixed state labels belong in
this input. URLs, request contents, free-form errors and unknown fields are
refused. A matched trace qualifies only the supplied observations, not service
equivalence, process containment, complete capture or a failure's cause.
"""
import argparse
import ipaddress
import json
import re
from pathlib import Path

MAX_INPUT = 1024 * 1024
MAX_PHASES = 64
MAX_OBSERVATIONS = 4096
LABEL = re.compile(r'[a-z][a-z0-9_-]{0,63}')
IDENTITY_STATES = {'fresh', 'stored', 'none', 'unknown'}
GUARD_STATES = {'allowed', 'denied', 'unknown'}
TRANSPORT_STATES = {'succeeded', 'failed', 'not_attempted', 'unknown'}
LIMITS = ('Supplied endpoint observations only; no network calls, capture '
          'completeness, account persistence verification, process containment, '
          'service equivalence or causal attribution.')


def _fields(value, required, optional=()):
    if (not isinstance(value, dict) or not set(required) <= set(value) or
            set(value) - set(required) - set(optional)):
        # Never echo untrusted fields or values; they may contain secrets.
        raise ValueError('missing or unsupported evidence fields')


def _authority(value):
    _fields(value, {'scheme', 'host', 'port'})
    scheme, host, port = value['scheme'], value['host'], value['port']
    if scheme not in ('http', 'https') or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('invalid endpoint scheme or port')
    if (not isinstance(host, str) or not 1 <= len(host) <= 253 or
            not host.isascii() or '%' in host):
        raise ValueError('invalid endpoint host')
    try:
        normalized_host = str(ipaddress.ip_address(host))
    except ValueError:
        # Bare IP literals or ASCII DNS names only. Reject alternate numeric
        # spellings, credentials, ports, trailing dots and URL components.
        labels = host.split('.')
        if (all(part.isdecimal() or re.fullmatch(r'0[xX][0-9A-Fa-f]+', part) for part in labels) or any(
                not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', part)
                for part in labels)):
            raise ValueError('invalid endpoint host') from None
        normalized_host = host.lower()
    return {'scheme': scheme, 'host': normalized_host, 'port': port}


def check_trace(data):
    """Return independent authority, guard and request findings for one boundary.

    Phase order is declared by the caller; observations must follow that order.
    Every declared phase needs an observation and request facts for a match.
    Identity state is a coverage label, never an identity value or success gate.
    Known failures do not erase unresolved facts. Malformed or contradictory
    evidence raises ValueError. The input is not mutated.
    """
    _fields(data, {'schema_version', 'expected_authority', 'phases', 'observations'})
    if type(data['schema_version']) is not int or data['schema_version'] != 1:
        raise ValueError('unsupported evidence version')
    expected = _authority(data['expected_authority'])
    phases, raw = data['phases'], data['observations']
    if not isinstance(phases, list) or not 1 <= len(phases) <= MAX_PHASES:
        raise ValueError('expected a bounded nonempty phase list')
    if not isinstance(raw, list) or len(raw) > MAX_OBSERVATIONS:
        raise ValueError('expected a bounded observation list')
    phase_order, phase_states = {}, []
    for phase in phases:
        _fields(phase, {'name', 'identity_state'})
        name, identity = phase['name'], phase['identity_state']
        if (not isinstance(name, str) or not LABEL.fullmatch(name) or
                not isinstance(identity, str) or identity not in IDENTITY_STATES):
            raise ValueError('invalid phase name or identity state')
        if name in phase_order:
            raise ValueError('duplicate phase name')
        phase_order[name] = len(phase_order)
        phase_states.append({'name': name, 'identity_state': identity})

    findings, observations, seen_phases, last_by_kind = [], [], set(), {}
    request_phases = set()
    previous_phase, last_configuration = -1, None
    authority_failed, request_failed, request_unresolved, guard_unresolved = False, False, False, False
    request_count = 0

    def finding(code, index=None, phase=None, **extra):
        item = {'code': code}
        if index is not None:
            item['observation'] = index
        if phase is not None:
            item['phase'] = phase
        findings.append(dict(item, **extra))

    for index, item in enumerate(raw):
        if not isinstance(item, dict) or item.get('kind') not in ('configuration', 'request'):
            raise ValueError('invalid observation kind')
        kind = item['kind']
        _fields(item, {'phase', 'kind', 'authority'}, {'guard', 'transport'} if kind == 'request' else ())
        phase = item['phase']
        if not isinstance(phase, str) or phase not in phase_order:
            raise ValueError('observation has an undeclared phase')
        current_phase = phase_order[phase]
        if current_phase < previous_phase:
            raise ValueError('observations must follow declared phase order')
        previous_phase = current_phase
        seen_phases.add(phase)
        authority = _authority(item['authority'])
        observed = {'phase': phase, 'kind': kind, 'authority': authority}
        if authority != expected:
            authority_failed = True
            finding('authority_mismatch', index, phase)
        previous = last_by_kind.get(kind)
        if previous is not None and authority != previous[1]:
            authority_failed = True
            finding(kind + '_authority_drift', index, phase, previous_observation=previous[0])
        last_by_kind[kind] = (index, authority)
        if kind == 'configuration':
            last_configuration = (index, authority)
        else:
            request_count += 1
            request_phases.add(phase)
            if last_configuration is not None and authority != last_configuration[1]:
                authority_failed = True
                finding('request_configuration_mismatch', index, phase,
                        configuration_observation=last_configuration[0])
            guard, transport = item.get('guard', 'unknown'), item.get('transport', 'unknown')
            if (not isinstance(guard, str) or guard not in GUARD_STATES or
                    not isinstance(transport, str) or transport not in TRANSPORT_STATES):
                raise ValueError('invalid guard or transport fact')
            if guard == 'denied' and transport in ('succeeded', 'failed'):
                raise ValueError('denied guard contradicts attempted transport')
            if guard == 'unknown':
                guard_unresolved = True
                request_unresolved = True
                finding('unknown_guard_fact' if 'guard' in item else 'missing_guard_fact', index, phase)
            if transport == 'unknown':
                request_unresolved = True
                finding('unknown_transport_fact' if 'transport' in item else 'missing_transport_fact', index, phase)
            if guard == 'denied' and transport == 'not_attempted':
                classification = 'local_denial_before_transport'
                request_failed = True
                finding(classification, index, phase)
            elif transport == 'failed':
                classification = 'transport_failure'
                request_failed = True
                finding(classification, index, phase)
            elif transport == 'succeeded':
                classification = 'transport_succeeded'
            else:
                classification = 'unresolved'
                if transport == 'not_attempted':
                    request_unresolved = True
                    finding('transport_not_attempted_without_known_denial', index, phase)
            observed.update(guard=guard, transport=transport, classification=classification)
        observations.append(observed)

    missing_phases = [phase['name'] for phase in phase_states if phase['name'] not in seen_phases]
    for phase in missing_phases:
        finding('missing_phase_observations', phase=phase)
    missing_request_phases = [phase['name'] for phase in phase_states if phase['name'] not in request_phases]
    for phase in missing_request_phases:
        finding('missing_phase_request_observations', phase=phase)
    if not request_count:
        guard_unresolved = request_unresolved = True
        finding('missing_request_observations')
    authority_status = 'failed' if authority_failed else 'unresolved' if missing_phases else 'matched'
    request_status = 'failed' if request_failed else 'unresolved' if request_unresolved or missing_request_phases else 'succeeded'
    guard_status = 'unresolved' if guard_unresolved or missing_request_phases else 'known'
    status = ('failed' if authority_failed or request_failed else
              'unresolved' if 'unresolved' in (authority_status, request_status, guard_status) else 'matched')
    return {'schema_version': 1, 'status': status, 'authority_status': authority_status,
            'request_status': request_status, 'guard_status': guard_status,
            'expected_authority': expected, 'phases': phase_states,
            'observations': observations, 'findings': findings, 'limits': LIMITS}


def load_trace(path):
    """Read bounded UTF-8 JSON, refusing duplicate keys and non-JSON constants."""
    with Path(path).open('rb') as stream:
        raw = stream.read(MAX_INPUT + 1)
    if len(raw) > MAX_INPUT:
        raise ValueError('input exceeds bound')

    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate JSON field')
            result[key] = value
        return result

    def constant(_):
        raise ValueError('non-JSON numeric constant')

    try:
        return json.loads(raw.decode('utf-8'), object_pairs_hook=unique, parse_constant=constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise ValueError('invalid JSON evidence') from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, help='new private JSON file; otherwise print JSON')
    args = parser.parse_args(argv)
    try:
        result = check_trace(load_trace(args.input))
        serialized = json.dumps(result, indent=2) + '\n'
        if args.output is not None:
            # Exclusive creation prevents overwriting evidence; mode is private
            # before the first byte is written, independent of the process umask.
            import os
            descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
                stream.write(serialized)
        else:
            print(serialized, end='')
        return 0 if result['status'] == 'matched' else 2
    except ValueError as error:
        print(json.dumps({'status': 'invalid', 'reason': str(error)}))
    except OSError:
        print(json.dumps({'status': 'invalid', 'reason': 'evidence file could not be read or created'}))
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
