#!/usr/bin/env python3
"""Read a captured local HTTP fixture from a task-owned Android process via Frida."""
import argparse
import json
import re
import subprocess
import threading

from android_http_fixture_probe import BODY_LIMIT, HEADER_LIMIT, response_matches


def validate(serial, package, host, port, path, expected_bytes, digest, timeout):
    if not re.fullmatch(r'emulator-[0-9]+', serial):
        raise ValueError('Select a task-owned Android emulator')
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+', package):
        raise ValueError('Supply the owned installed package name')
    if host not in {'127.0.0.1', '10.0.2.2'} or type(port) is not int or not 1 <= port <= 65535:
        raise ValueError('Only an explicit local fixture endpoint is supported')
    if not re.fullmatch(r'/[A-Za-z0-9._~/-]{1,1023}', path):
        raise ValueError('Supply a bounded fixture path without queries or credentials')
    if type(expected_bytes) is not int or not 0 <= expected_bytes <= BODY_LIMIT:
        raise ValueError('Expected body exceeds probe bound')
    if not re.fullmatch(r'[0-9a-f]{64}', digest) or not 1 <= timeout <= 60:
        raise ValueError('Supply an exact digest and bounded timeout')


def script_source(host, port, path, cap, timeout):
    config = json.dumps({'host': host, 'port': port, 'path': path,
                         'cap': cap, 'timeoutMs': int(timeout * 1000)})
    return 'const config = ' + config + ';\n' + r'''
if (Process.platform !== 'linux') throw new Error('Expected Android process');
rpc.exports = {async readfixture() {
  const connection = await Socket.connect({family:'ipv4',host:config.host,port:config.port});
  const deadline = setTimeout(() => connection.close(), config.timeoutMs);
  try {
    const request = 'GET '+config.path+' HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n';
    await connection.output.writeAll(request.split('').map(c => c.charCodeAt(0)));
    let total = 0;
    while (true) {
      const chunk = await connection.input.read(65536);
      if (chunk.byteLength === 0) break;
      total += chunk.byteLength;
      if (total > config.cap) throw new Error('Response exceeded bound');
      send({kind:'fixture-bytes'}, chunk);
    }
    return {total};
  } finally {clearTimeout(deadline); await connection.close();}
}};
'''


def collect(device, pid, source, expected_bytes, digest, timeout):
    """Attach temporarily; route configuration and application code are unchanged."""
    session = device.attach(pid)
    script = None
    data = bytearray()
    errors = []
    done = threading.Event()
    totals = []
    def message(event, chunk):
        if event.get('type') == 'error':
            errors.append('Instrumentation error')
        elif event.get('payload', {}).get('kind') == 'fixture-bytes' and chunk is not None:
            if len(data) + len(chunk) > HEADER_LIMIT + expected_bytes:
                errors.append('Response exceeded bound')
            elif not errors:
                data.extend(chunk)
    try:
        script = session.create_script(source)
        script.on('message', message)
        script.load()
        def read():
            try:
                totals.append(script.exports_sync.readfixture()['total'])
            except Exception:
                errors.append('Local fixture read failed')
            finally:
                done.set()
        threading.Thread(target=read, daemon=True).start()
        if not done.wait(timeout):
            raise ValueError('Local fixture read timed out')
        if errors or totals != [len(data)]:
            raise ValueError(errors[0] if errors else 'Response transport length mismatch')
        result = response_matches(bytes(data), expected_bytes, digest)
    finally:
        try:
            if script is not None:
                script.unload()
        finally:
            session.detach()
    return {**result, 'temporary_script_unloaded': True, 'session_detached': True,
            'route_mutation': False,
            'limits': 'Instrumentation-origin local GET; not an original app request, rendered fidelity, process restart or egress isolation.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--adb', default='adb')
    p.add_argument('--serial', required=True)
    p.add_argument('--package', required=True)
    p.add_argument('--frida-port', type=int, required=True)
    p.add_argument('--host', choices=['127.0.0.1', '10.0.2.2'], required=True)
    p.add_argument('--port', type=int, required=True)
    p.add_argument('--path', required=True)
    p.add_argument('--expected-bytes', type=int, required=True)
    p.add_argument('--expected-sha256', required=True)
    p.add_argument('--timeout', type=float, default=15)
    a = p.parse_args()
    try:
        validate(a.serial, a.package, a.host, a.port, a.path,
                 a.expected_bytes, a.expected_sha256, a.timeout)
        if not 1 <= a.frida_port <= 65535:
            raise ValueError('Invalid loopback Frida port')
        def query(*args):
            return subprocess.run([a.adb, '-s', a.serial, *args], check=True,
                                  capture_output=True, text=True, timeout=8).stdout.strip()
        if query('get-state') != 'device' or query('emu', 'avd', 'status').replace('\r\n','\n') != 'virtual device is running\nOK':
            raise ValueError('Owned emulator is not executing')
        pid = query('shell', 'pidof', a.package)
        if not pid.isdecimal():
            raise ValueError('Expected one running owned package process')
        import frida
        device = frida.get_device_manager().add_remote_device('127.0.0.1:'+str(a.frida_port))
        source = script_source(a.host, a.port, a.path, HEADER_LIMIT+a.expected_bytes, a.timeout)
        result = collect(device, int(pid), source, a.expected_bytes, a.expected_sha256, a.timeout)
        print(json.dumps({'passed': True, 'pid': int(pid), **result}))
        print('RDD_PROCESS_HTTP_BYTES_MATCH')
        return 0
    except Exception as error:
        print(json.dumps({'passed': False, 'error_type': type(error).__name__,
                          'reason': str(error) if isinstance(error, ValueError) else 'Process probe unavailable or failed'}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
