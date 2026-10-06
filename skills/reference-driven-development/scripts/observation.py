#!/usr/bin/env python3
"""Task-owned Android sessions: qualify, observe, reset and reconcile mutations.

No automatic device selection, downloads, snapshot equivalence claim or action retry.
The analyst owns this adapter; never expose it to the strict implementer.
"""
import argparse
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct
import sys
import time
import uuid
import zlib

from process import run
from offline_worker import strict_json


def digest(data):
    return hashlib.sha256(data).hexdigest()


def png_geometry(data):
    """Validate chunk boundaries/CRC and require image data, without decoding pixels."""
    if not data.startswith(b'\x89PNG\r\n\x1a\n') or len(data) > 33554432:
        raise ValueError('capture is not a bounded PNG')
    offset, geometry, image_data = 8, None, False
    while offset + 12 <= len(data):
        size = struct.unpack('!I', data[offset:offset+4])[0]
        end = offset + 12 + size
        if end > len(data):
            raise ValueError('truncated PNG chunk')
        kind, payload = data[offset+4:offset+8], data[offset+8:end-4]
        if zlib.crc32(kind+payload) & 0xffffffff != struct.unpack('!I', data[end-4:end])[0]:
            raise ValueError('invalid PNG CRC')
        if offset == 8:
            if kind != b'IHDR' or size != 13:
                raise ValueError('missing PNG header')
            geometry = struct.unpack('!II', payload[:8])
            if not all(0 < n <= 16384 for n in geometry) or geometry[0]*geometry[1] > 32000000:
                raise ValueError('capture geometry outside bounds')
        image_data |= kind == b'IDAT' and size > 0
        if kind == b'IEND':
            if size or end != len(data) or not image_data:
                raise ValueError('invalid PNG termination')
            return list(geometry)
        offset = end
    raise ValueError('missing PNG termination')


def validate(config):
    if config.get('task_owned') is not True or not config.get('ownership_reason'):
        raise ValueError('explicit task ownership and reason required')
    if not re.fullmatch(r'[A-Za-z0-9._:-]+', config.get('serial', '')):
        raise ValueError('explicit valid device serial required')
    if config.get('device_kind') not in ('emulator', 'physical'):
        raise ValueError('device_kind must be emulator or physical')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.]+', config.get('package', '')):
        raise ValueError('valid installed package required')
    if config.get('container') and not re.fullmatch(r'[A-Za-z0-9_.-]+', config['container']):
        raise ValueError('invalid container name')
    fixture = config.get('fixture', [])
    if not fixture:
        raise ValueError('at least one independent starting-fixture probe required')
    for probe in fixture + config.get('ready', []):
        validate_probe(probe)
    for action in config.get('reset', []):
        action_command(action, config)
    if not config.get('reset'):
        raise ValueError('explicit reset sequence required; no implicit app-data deletion')
    for key, default, low, high in [('probe_wait_seconds', 10, 0, 60), ('probe_interval', .1, .01, 5), ('command_timeout', 30, .01, 3600),
                                  ('capture_wait_seconds', 5, .01, 60), ('capture_interval', .1, .01, 5)]:
        value = config.get(key, default)
        if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
            raise ValueError('invalid '+key)
    if type(config.get('probe_stability', 1)) is not int or not 1 <= config.get('probe_stability', 1) <= 20:
        raise ValueError('probe_stability must be 1..20 complete matching polls')
    if type(config.get('capture_stability', 1)) is not int or not 1 <= config.get('capture_stability', 1) <= 20:
        raise ValueError('capture_stability must be 1..20 fresh matching captures')
    policies = config.get('capture_stability_overrides', {})
    allowed_profiles = {'qualify', 'capture', 'reconcile', 'reset-before', 'reset-after'} | {kind+'-'+phase for kind in ('launch', 'stop', 'clear-data', 'tap', 'swipe', 'back') for phase in ('before', 'after')}
    if not isinstance(policies, dict) or any(key not in allowed_profiles or type(value) is not int or not 1 <= value <= 20 for key, value in policies.items()):
        raise ValueError('capture stability overrides need named observation points and 1..20 captures')
    if 'apk_sha256s' in config:
        hashes = config['apk_sha256s']
        if not isinstance(hashes, list) or not 1 <= len(hashes) <= 64 or any(not isinstance(h, str) or not re.fullmatch(r'[0-9a-f]{64}', h) for h in hashes):
            raise ValueError('apk_sha256s must be reviewed input digests for all installed APK splits')
    return config


def validate_probe(probe):
    if not isinstance(probe, dict) or not probe.get('id') or probe.get('operator') not in ('equals', 'contains', 'regex'):
        raise ValueError('probe needs id, operator and expected text')
    if not isinstance(probe.get('expected'), str):
        raise ValueError('probe expected must be text')
    if probe['operator'] == 'regex':
        try:
            re.compile(probe['expected'])
        except re.error as error:
            raise ValueError('invalid probe regex') from error
    if not isinstance(probe.get('argv'), list) or not probe['argv'] or any(not isinstance(x, str) or '\x00' in x for x in probe['argv']):
        raise ValueError('probe needs explicit device argv')
    # Probe commands are observer-authored. Do not permit input/installation
    # commands masquerading as fixture checks; custom read-only shell probes
    # still require review before use.
    if probe['argv'][0] != 'shell' or any(x in ('input', 'am', 'pm', 'reboot') for x in probe['argv'][1:]):
        raise ValueError('fixture probes must be reviewed read-only shell queries')


def action_command(action, config):
    kind = action.get('kind')
    package = config['package']
    if kind == 'launch':
        component = action.get('component', config.get('component'))
        if not isinstance(component, str) or not component.startswith(package+'/') or not re.fullmatch(r'[A-Za-z0-9_.$/]+', component):
            raise ValueError('launch needs a component inside the selected package')
        return ['shell', 'am', 'start', '-W', '-n', component]
    if kind == 'stop':
        return ['shell', 'am', 'force-stop', package]
    if kind == 'clear-data':
        if config.get('allow_clear_data') is not True:
            raise ValueError('clear-data requires explicit task-owned fixture permission')
        return ['shell', 'pm', 'clear', package]
    if kind == 'tap':
        keys = ('x', 'y')
    elif kind == 'swipe':
        keys = ('x1', 'y1', 'x2', 'y2', 'duration_ms')
    elif kind == 'back':
        return ['shell', 'input', 'keyevent', '4']
    else:
        raise ValueError('unsupported action kind')
    if any(type(action.get(k)) is not int or action[k] < 0 for k in keys):
        raise ValueError('coordinates/duration must be nonnegative integers')
    if kind == 'swipe' and not 0 < action['duration_ms'] <= 60000:
        raise ValueError('swipe duration out of bounds')
    return ['shell', 'input', kind, *[str(action[k]) for k in keys]]


class Session:
    def __init__(self, root, config):
        self.root = Path(root)
        self.config = validate(config)
        self.identity = digest(json.dumps(config, sort_keys=True).encode())
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.is_symlink():
            raise ValueError('session directory cannot be a symlink')
        self.state_path = self.root/'session.json'
        self.state = None

    def event(self, kind, **values):
        record = dict(values, session_id=self.state['session_id'], attempt_id=self.attempt,
                      kind=kind, monotonic=time.monotonic())
        with (self.root/'events.jsonl').open('a') as stream:
            stream.write(json.dumps(record)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        return record

    def save(self):
        temporary = self.root/('.state-'+uuid.uuid4().hex)
        with temporary.open('x') as stream:
            json.dump(self.state, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(self.state_path)

    def device(self, argv, deadline=None):
        prefix = ['docker', 'exec', self.config['container']] if self.config.get('container') else []
        command = prefix + [self.config.get('adb', 'adb'), '-s', self.config['serial'], *argv]
        timeout = self.config.get('command_timeout', 30)
        if deadline is not None:
            timeout = min(timeout, deadline-time.monotonic())
            if timeout <= 0:
                raise RuntimeError('read-only probe deadline expired')
        result = run(command, self.root, timeout=timeout, max_bytes=33554432)
        self.event('command', argv=argv, status=result['status'], exit_code=result['exit_code'],
                   elapsed=result['elapsed'], stdout_sha256=digest(result['stdout']),
                   stderr=result['stderr'][:1500].decode(errors='replace'))
        if result['status'] != 'completed' or result['exit_code']:
            raise RuntimeError('device command failed: '+result['status'])
        return result['stdout']

    def probes(self, probes, deadline=None):
        outcomes = []
        for probe in probes:
            validate_probe(probe)
            actual = self.device(probe['argv'], deadline=deadline).decode('utf-8').strip()
            expected = probe['expected']
            passed = actual == expected if probe['operator'] == 'equals' else expected in actual if probe['operator'] == 'contains' else re.search(expected, actual) is not None
            outcomes.append(dict(id=probe['id'], status='passed' if passed else 'failed', actual=actual, expected=expected))
        self.event('probes', outcomes=outcomes)
        return outcomes

    def wait_probes(self, probes):
        """Poll reviewed reads only; transport failure never retries an input."""
        if not probes:
            return []
        wait = self.config.get('probe_wait_seconds', 10)
        deadline = time.monotonic()+wait if wait else None
        stable = 0
        while True:
            outcomes = self.probes(probes, deadline=deadline)
            stable = stable+1 if all(p['status'] == 'passed' for p in outcomes) else 0
            if stable >= self.config.get('probe_stability', 1):
                return outcomes
            if deadline is None or time.monotonic() >= deadline:
                if stable:
                    outcomes.append(dict(id='observer_stability', status='failed', actual=stable,
                                         expected=self.config.get('probe_stability', 1)))
                return outcomes
            time.sleep(min(self.config.get('probe_interval', .1), max(0, deadline-time.monotonic())))

    def capture_once(self, deadline=None, profile='capture', required=1):
        data = self.device(['exec-out', 'screencap', '-p'], deadline=deadline)
        geometry = png_geometry(data)
        capture_id = uuid.uuid4().hex
        name = capture_id+'.png'
        with (self.root/name).open('xb') as stream:
            stream.write(data)
        evidence = dict(path=name, sha256=digest(data), geometry=geometry,
                        capture_id=capture_id, session_id=self.state['session_id'],
                        capture_policy=profile, required_stability=required,
                        timestamp_basis='host monotonic; guest presentation time unmeasured')
        self.state['capture'] = evidence
        self.event('capture', **evidence)
        return evidence

    def capture(self, profile='capture'):
        required = self.config.get('capture_stability_overrides', {}).get(profile, self.config.get('capture_stability', 1))
        if required == 1:
            return self.capture_once(profile=profile)
        deadline = time.monotonic()+self.config.get('capture_wait_seconds', 5)
        matched, last_hash = [], None
        while time.monotonic() < deadline:
            evidence = self.capture_once(deadline, profile=profile, required=required)
            if evidence['sha256'] != last_hash:
                matched = []
            matched.append(evidence['capture_id'])
            last_hash = evidence['sha256']
            if len(matched) >= required:
                self.event('capture_stability', capture_ids=matched, sha256=last_hash,
                           capture_policy=profile, required_stability=required,
                           criterion='consecutive identical PNG bytes; not guest frame presentation or future stability')
                return evidence
            time.sleep(min(self.config.get('capture_interval', .1), max(0, deadline-time.monotonic())))
        raise RuntimeError('fresh capture stability not established before deadline')

    def qualify(self, fixture=False, capture_profile='qualify'):
        if self.device(['get-state']).decode().strip() != 'device':
            raise RuntimeError('device not responsive')
        # ADB transport can stay online while the standard emulator VM is stopped.
        # Query its control plane before waiting on a guest that cannot execute.
        if self.config['device_kind'] == 'emulator' and re.fullmatch(r'emulator-[0-9]+', self.config['serial']):
            try:
                execution = self.device(['emu', 'avd', 'status']).decode().strip()
            except (OSError, RuntimeError, UnicodeError):
                self.state['qualified'] = False
                raise
            states = {'virtual device is running\nOK': 'running',
                      'virtual device is stopped\nOK': 'stopped'}
            state = states.get(execution.replace('\r\n', '\n'))
            self.event('emulator_execution', state=state or 'unknown')
            if state != 'running':
                self.state['qualified'] = False
                raise RuntimeError('emulator execution '+(state or 'unknown')+'; inspect before recovery')
        qemu = self.device(['shell', 'getprop', 'ro.kernel.qemu']).decode().strip()
        if (qemu == '1') != (self.config['device_kind'] == 'emulator'):
            raise RuntimeError('device kind does not match declared route')
        if self.device(['shell', 'getprop', 'sys.boot_completed']).decode().strip() != '1':
            raise RuntimeError('device not boot-ready')
        installed = self.device(['shell', 'pm', 'path', self.config['package']]).decode().strip()
        if not installed.startswith('package:'):
            raise RuntimeError('selected package not installed')
        info = {key: self.device(['shell', 'getprop', prop]).decode().strip() for key, prop in
                [('abi', 'ro.product.cpu.abi'), ('os', 'ro.build.version.release'), ('fingerprint', 'ro.build.fingerprint')]}
        package = self.device(['shell', 'dumpsys', 'package', self.config['package']]).decode()
        info['package_version'] = re.findall(r'version(?:Code|Name)=[^\s]+', package)
        if not info['package_version']:
            raise RuntimeError('package version could not be established')
        if 'apk_sha256s' in self.config:
            paths = [line[len('package:'):] for line in installed.splitlines() if line.startswith('package:')]
            if not 1 <= len(paths) <= 64 or any(not re.fullmatch(r'/[A-Za-z0-9/._~+=-]+', path) for path in paths):
                raise RuntimeError('installed APK locations could not be safely established')
            hashes = []
            for path in paths:
                output = self.device(['shell', 'sha256sum', path]).decode().strip()
                match = re.fullmatch(r'([0-9a-f]{64})\s+\*?'+re.escape(path), output)
                if not match:
                    raise RuntimeError('installed APK byte identity unavailable')
                hashes.append(match.group(1))
            info['apk_sha256s'] = sorted(hashes)
            if info['apk_sha256s'] != sorted(self.config['apk_sha256s']):
                self.state['qualified'] = False
                self.save()
                raise RuntimeError('installed APK bytes differ from reviewed inputs')
        if self.state.get('environment') and self.state['environment'] != info:
            self.state['qualified'] = False
            self.save()
            raise RuntimeError('environment changed; create a new qualified session')
        self.state['environment'] = info
        outcomes = self.wait_probes(self.config.get('ready', []) + (self.config['fixture'] if fixture else []))
        if any(p['status'] != 'passed' for p in outcomes):
            raise RuntimeError('readiness or fixture probe failed')
        self.capture(profile=capture_profile)
        return outcomes

    def mutate(self, action):
        command = action_command(action, self.config)
        geometry = self.state.get('capture', {}).get('geometry')
        if action['kind'] in ('tap', 'swipe'):
            if not geometry:
                raise ValueError('positional input requires a fresh qualified capture')
            for x, y in ([('x', 'y')] if action['kind'] == 'tap' else [('x1', 'y1'), ('x2', 'y2')]):
                if action[x] >= geometry[0] or action[y] >= geometry[1]:
                    raise ValueError('input outside current capture geometry')
        # Persist uncertainty before sending any mutation; crashes retain it.
        self.state['uncertain_mutation'] = dict(attempt_id=self.attempt, action=action)
        self.save()
        self.event('input_requested', action=action)
        output = self.device(command)
        if action['kind'] == 'clear-data' and output.decode().strip() != 'Success':
            raise RuntimeError('data-clear acknowledgment missing')
        if action['kind'] == 'launch' and b'Error:' in output:
            raise RuntimeError('launch failed despite transport success')
        self.event('input_acknowledged', action=action)

    def execute(self, operation, action=None, effect=None):
        with (self.root/'session.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.attempt = uuid.uuid4().hex
            if self.state_path.exists():
                self.state = strict_json(self.state_path.read_text())
                if self.state['config_sha256'] != self.identity:
                    raise ValueError('session configuration changed; use a new session directory')
            else:
                self.state = dict(session_id=uuid.uuid4().hex, config_sha256=self.identity,
                                  qualified=False, uncertain_mutation=None)
            self.event('attempt_started', operation=operation)
            try:
                if operation == 'qualify':
                    self.qualify(fixture=True)
                    self.state['qualified'] = True
                elif operation == 'capture':
                    self.qualify(capture_profile='capture')
                elif operation == 'reconcile':
                    self.qualify(fixture=True, capture_profile='reconcile')
                    self.state['uncertain_mutation'] = None
                    self.state['qualified'] = True
                elif operation == 'reset':
                    self.qualify(capture_profile='reset-before')
                    for item in self.config['reset']:
                        self.mutate(item)
                    self.qualify(fixture=True, capture_profile='reset-after')
                    self.state['uncertain_mutation'] = None
                    self.state['qualified'] = True
                elif operation == 'act':
                    if not self.state['qualified'] or self.state['uncertain_mutation']:
                        raise ValueError('action blocked until qualification/reset/reconciliation')
                    if not effect:
                        raise ValueError('action requires independent expected-effect probes')
                    for probe in effect:
                        validate_probe(probe)
                    action_command(action, self.config)
                    self.qualify(capture_profile=action['kind']+'-before')
                    self.mutate(action)
                    outcomes = self.wait_probes(effect)
                    self.capture(profile=action['kind']+'-after')
                    if any(p['status'] != 'passed' for p in outcomes):
                        raise RuntimeError('action effect not established; inspect before repeating')
                    self.state['uncertain_mutation'] = None
                else:
                    raise ValueError('unknown session operation')
                self.save()
                return self.event('attempt_completed', operation=operation, state=self.state)
            except (OSError, ValueError, RuntimeError) as error:
                self.save()
                self.event('attempt_failed', operation=operation, error=str(error),
                           uncertain_mutation=self.state['uncertain_mutation'])
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('operation', choices=['qualify', 'capture', 'reset', 'act', 'reconcile'])
    parser.add_argument('--action', type=Path)
    parser.add_argument('--effect', type=Path)
    args = parser.parse_args()
    try:
        load = lambda path: strict_json(path.read_text()) if path else None
        result = Session(args.session, load(args.config)).execute(args.operation, load(args.action), load(args.effect))
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print('error: '+str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
