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
    def run_recording(self, mode, action=('capture',), method='exec-out', extra=()):
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
elif args[:3]==['emu','screenrecord','screenshot']:
    folder=pathlib.Path(args[3])
    assert folder.is_absolute() and not list(folder.iterdir())
    if mode!='console-empty': (folder/'result.png').write_bytes(png)
    if mode=='console-timeout': time.sleep(4)
    elif mode=='console-ko': print('KO: framebuffer unavailable\\nOK')
    else:
        if mode=='console-cleanup-warning': folder.chmod(0o555)
        print('OK')
elif 'screencap' in args:
    if mode=='timeout': time.sleep(3)
    if args[0]=='exec-out': sys.stdout.buffer.write(png)
elif args[0]=='pull':
    pathlib.Path(args[-1]).write_bytes(png)
''')
        fake.chmod(0o755)
        output = root / 'evidence'
        output.mkdir()
        (output / 'unrelated.txt').write_text('preserve existing evidence')
        env = dict(os.environ, MODE=mode, CALLS=str(root / 'calls.jsonl'), PNG=base64.b64encode(PNG).decode())
        capture_option = ['--capture-method', method] if method else []
        result = subprocess.run([sys.executable, str(RECORDER), '--serial', 'emulator-5554',
                                 '--adb', str(fake), '--timeout', '2', *capture_option,
                                 '--output', str(output), '--label', 'synthetic-fixture', *extra, *action],
                                capture_output=True, text=True, env=env, timeout=10)
        def journal(path):
            return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        events = journal(output / 'events.jsonl')
        calls = journal(root / 'calls.jsonl')
        return result, events, calls, output

    def test_success_retains_capture_hash_and_bytes(self):
        result, events, calls, output = self.run_recording('success', method=None)
        self.assertEqual(result.returncode, 0, result.stderr)
        final = events[-1]
        self.assertEqual(final['stage'], 'complete')
        self.assertEqual((output / final['screenshot']).read_bytes(), PNG)
        self.assertEqual(final['screenshot_sha256'], hashlib.sha256(PNG).hexdigest())
        self.assertEqual(final['capture_method'], 'exec-out')
        self.assertIn(['exec-out', 'screencap', '-p'], calls)

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

    def test_console_success_preserves_final_file_and_journals_its_observer(self):
        result, events, calls, output = self.run_recording('success', method='console')
        self.assertEqual(result.returncode, 0, result.stderr)
        final = events[-1]
        self.assertEqual(final['stage'], 'complete')
        self.assertEqual(final['capture_method'], 'console')
        self.assertEqual(final['capture_observer']['platform'], 'native-emulator-host')
        self.assertEqual((output / final['screenshot']).read_bytes(), PNG)
        self.assertEqual(final['screenshot_sha256'], hashlib.sha256(PNG).hexdigest())
        self.assertEqual((output / 'unrelated.txt').read_text(), 'preserve existing evidence')
        attempt = Path(final['console_capture']['host_directory'])
        self.assertEqual(attempt.parent, output.resolve())
        self.assertFalse(attempt.exists())
        self.assertTrue(final['console_capture']['intermediates_removed'])
        self.assertEqual(final['console_capture']['response'], 'OK')
        stages = [event['stage'] for event in events]
        self.assertIn('console_capture_requested', stages)
        self.assertIn('console_capture_completed', stages)
        self.assertEqual(sum(call[:3] == ['emu', 'screenrecord', 'screenshot'] for call in calls), 1)

    def test_console_ko_with_exit_zero_is_failure_even_with_ok_and_png(self):
        result, events, _, _ = self.run_recording('console-ko', method='console')
        self.assertEqual(result.returncode, 1)
        final = events[-1]
        self.assertEqual(final['failed_step'], 'validate_console_response')
        self.assertEqual(final['error_type'], 'RuntimeError')
        self.assertEqual(final['console_capture']['response'], 'KO: framebuffer unavailable\nOK')
        self.assertEqual((Path(final['console_capture']['host_directory']) / 'result.png').read_bytes(), PNG)
        self.assertNotIn('screenshot', final)

    def test_console_ok_without_png_preserves_input_completion(self):
        result, events, calls, _ = self.run_recording('console-empty', ('tap', '10', '20'), method='console')
        self.assertEqual(result.returncode, 1)
        final = events[-1]
        self.assertEqual(final['failed_step'], 'locate_console_capture')
        self.assertIn('input_completed_monotonic', final)
        self.assertEqual(sum(call[:2] == ['shell', 'input'] for call in calls), 1)
        attempt = Path(final['console_capture']['host_directory'])
        self.assertTrue(attempt.is_dir())
        self.assertEqual(list(attempt.iterdir()), [])
        self.assertNotIn('screenshot', final)

    def test_console_timeout_preserves_attempt_and_uncertain_request(self):
        result, events, calls, _ = self.run_recording('console-timeout', method='console')
        self.assertEqual(result.returncode, 1)
        final = events[-1]
        self.assertEqual(final['error_type'], 'TimeoutExpired')
        self.assertEqual(final['failed_step'], 'console_screenshot')
        self.assertNotIn('completed_monotonic', final['console_capture'])
        self.assertEqual((Path(final['console_capture']['host_directory']) / 'result.png').read_bytes(), PNG)
        self.assertEqual(sum(call[:3] == ['emu', 'screenrecord', 'screenshot'] for call in calls), 1)
        self.assertNotIn('screenshot', final)

    def test_console_rejects_container_before_device_or_input_work(self):
        result, events, calls, _ = self.run_recording('success', ('tap', '10', '20'), method='console',
                                                    extra=('--container', 'synthetic-container'))
        self.assertEqual(result.returncode, 2)
        self.assertEqual(events, [])
        self.assertEqual(calls, [])

    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0,
                     'Root can bypass the fixture directory permissions')
    def test_console_cleanup_warning_does_not_turn_saved_capture_into_failure(self):
        result, events, calls, output = self.run_recording('console-cleanup-warning', ('tap', '10', '20'),
                                                        method='console')
        final = events[-1]
        attempt = Path(final['console_capture']['host_directory'])
        # Restore this test-owned directory before TemporaryDirectory cleans it up.
        attempt.chmod(0o755)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(final['stage'], 'complete')
        self.assertFalse(final['console_capture']['intermediates_removed'])
        self.assertIn('cleanup_warning', final['console_capture'])
        self.assertIn('console_cleanup_warning', [event['stage'] for event in events])
        self.assertEqual((output / final['screenshot']).read_bytes(), PNG)
        self.assertEqual(final['screenshot_sha256'], hashlib.sha256(PNG).hexdigest())
        self.assertEqual(sum(call[:2] == ['shell', 'input'] for call in calls), 1)


if __name__ == '__main__':
    unittest.main()
