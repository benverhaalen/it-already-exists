"""Exercise the recorder's evidence boundary through its real command interface."""
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

RECORDER = Path(__file__).resolve().parents[1] / 'tools/capture_android_reference.py'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a5ZkAAAAASUVORK5CYII=')


class RecorderEvidenceTests(unittest.TestCase):
    def run_recording(self, mode, action=('capture',), method='exec-out'):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        fake = root / 'adb'
        fake.write_text('#!' + sys.executable + '\n' + '''
import base64, json, os, pathlib, sys, time
args=sys.argv[3:]
with open(os.environ['CALLS'],'a') as f: f.write(json.dumps(args)+'\\n')
mode=os.environ['MODE']
png=base64.b64decode(os.environ['PNG'])
if args==['shell','getprop','ro.kernel.qemu']:
    print('0' if mode=='physical' else '1')
elif args[:2]==['shell','input']:
    pass
elif 'screencap' in args:
    if mode=='timeout': time.sleep(3)
    if args[0]=='exec-out': sys.stdout.buffer.write(png)
elif args[0]=='pull':
    pathlib.Path(args[-1]).write_bytes(png)
''')
        fake.chmod(0o755)
        output = root / 'evidence'
        env = dict(os.environ, MODE=mode, CALLS=str(root / 'calls.jsonl'), PNG=base64.b64encode(PNG).decode())
        result = subprocess.run([sys.executable, str(RECORDER), '--serial', 'emulator-5554',
                                 '--adb', str(fake), '--timeout', '0.5', '--capture-method', method,
                                 '--output', str(output), '--label', 'synthetic-fixture', *action],
                                capture_output=True, text=True, env=env, timeout=10)
        events = [json.loads(line) for line in (output / 'events.jsonl').read_text().splitlines()]
        calls = [json.loads(line) for line in (root / 'calls.jsonl').read_text().splitlines()]
        return result, events, calls, output

    def test_success_retains_capture_hash_and_bytes(self):
        result, events, _, output = self.run_recording('success')
        self.assertEqual(result.returncode, 0, result.stderr)
        final = events[-1]
        self.assertEqual(final['stage'], 'complete')
        self.assertEqual((output / final['screenshot']).read_bytes(), PNG)
        self.assertEqual(final['screenshot_sha256'], hashlib.sha256(PNG).hexdigest())

    def test_timeout_after_input_preserves_completed_input_without_claiming_capture(self):
        result, events, calls, output = self.run_recording('timeout', ('tap', '10', '20'))
        self.assertEqual(result.returncode, 1)
        self.assertIn('input_completed', [event['stage'] for event in events])
        self.assertEqual(sum(call[:2] == ['shell','input'] for call in calls), 1)
        self.assertEqual(events[-1]['stage'], 'failed')
        self.assertEqual(events[-1]['failed_step'], 'screencap')
        self.assertEqual(events[-1]['error_type'], 'TimeoutExpired')
        self.assertNotIn('screenshot', events[-1])
        self.assertFalse(list(output.glob('*.png')))

    def test_device_check_failure_does_not_send_input(self):
        result, events, calls, _ = self.run_recording('physical', ('tap', '10', '20'))
        self.assertEqual(result.returncode, 1)
        self.assertEqual(events[-1]['failed_step'], 'validate_emulator')
        self.assertFalse(any('input' in call for call in calls))

    def test_old_adb_pull_does_not_require_exec_out(self):
        result, events, calls, output = self.run_recording('success', method='pull')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(any(call[0] == 'exec-out' for call in calls))
        self.assertEqual((output / events[-1]['screenshot']).read_bytes(), PNG)


if __name__ == '__main__':
    unittest.main()
