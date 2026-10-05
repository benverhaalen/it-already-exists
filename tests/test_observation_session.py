"""Failure-sensitive session checks with an explicit synthetic Android transport."""
import importlib.util
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

SCRIPTS = Path(__file__).resolve().parents[1]/'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
import observation
from process import run


def png(marker=0):
    def chunk(kind, data):
        return struct.pack('!I', len(data))+kind+data+struct.pack('!I', zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR', struct.pack('!IIBBBBB', 10, 10, 8, 2, 0, 0, 0))+chunk(b'IDAT', zlib.compress((b'\0'+bytes([marker])*30)*10))+chunk(b'IEND', b'')


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.effect = [dict(id='value', argv=['shell', 'cat', '/fixture/value'], operator='equals', expected='1')]
        self.config = dict(task_owned=True, ownership_reason='synthetic isolated fixture',
                           probe_wait_seconds=0,
                           serial='emulator-5554', device_kind='emulator', package='org.rdd.fixture',
                           component='org.rdd.fixture/.Main', reset=[dict(kind='stop'), dict(kind='launch')],
                           fixture=[dict(id='initial', argv=['shell', 'cat', '/fixture/value'], operator='equals', expected='0')])
        self.calls, self.value, self.version, self.capture_failure = [], '0', 'versionCode=1 versionName=1', False
        self.transport = patch.object(observation, 'run', side_effect=self.device)
        self.transport.start()
        self.addCleanup(self.transport.stop)

    def device(self, argv, *args, **kwargs):
        command = argv[3:]
        self.calls.append(command)
        if command == ['get-state']:
            data = b'device'
        elif command[:2] == ['shell', 'getprop']:
            data = b'1' if command[-1] in ('sys.boot_completed', 'ro.kernel.qemu') else b'synthetic'
        elif command[:3] == ['shell', 'pm', 'path']:
            data = b'package:/fixture/app.apk'
        elif command[:3] == ['shell', 'dumpsys', 'package']:
            data = self.version.encode()
        elif command[:2] == ['shell', 'cat']:
            data = self.value.encode()
        elif command[:3] == ['shell', 'input', 'tap']:
            self.value = '1'
            data = b''
        elif command[:3] == ['shell', 'am', 'start']:
            self.value = '0'
            data = b'Status: ok'
        elif command[:3] == ['shell', 'am', 'force-stop']:
            data = b''
        elif command == ['exec-out', 'screencap', '-p']:
            if self.capture_failure:
                return dict(status='timeout', exit_code=-9, elapsed=.01, stdout=b'', stderr=b'')
            data = png()
        else:
            raise AssertionError(command)
        return dict(status='completed', exit_code=0, elapsed=.001, stdout=data, stderr=b'')

    def session(self):
        return observation.Session(self.root/'evidence', self.config)

    def test_complete_journey_reset_and_fresh_capture(self):
        first = self.session().execute('qualify')['state']['capture']
        changed = self.session().execute('act', dict(kind='tap', x=1, y=1), self.effect)
        self.assertIsNone(changed['state']['uncertain_mutation'])
        self.assertNotEqual(first['capture_id'], changed['state']['capture']['capture_id'])
        reset = self.session().execute('reset')
        self.assertTrue(reset['state']['qualified'])
        self.assertEqual(self.value, '0')
        self.assertEqual(len(list((self.root/'evidence').glob('*.png'))), 5)

    def test_capture_failure_after_input_blocks_duplicate_mutation(self):
        self.session().execute('qualify')
        # Fail only after the input, rather than the pre-action freshness capture.
        original = self.device
        def fail_after_input(argv, *args, **kwargs):
            result = original(argv, *args, **kwargs)
            if argv[3:6] == ['shell', 'input', 'tap']:
                self.capture_failure = True
            return result
        with patch.object(observation, 'run', side_effect=fail_after_input):
            with self.assertRaises(RuntimeError):
                self.session().execute('act', dict(kind='tap', x=1, y=1), self.effect)
        with self.assertRaisesRegex(ValueError, 'reconciliation'):
            self.session().execute('act', dict(kind='tap', x=1, y=1), self.effect)
        self.assertEqual(sum(c[:3] == ['shell', 'input', 'tap'] for c in self.calls), 1)
        self.capture_failure = False
        with self.assertRaises(RuntimeError):
            self.session().execute('reconcile')  # Changed state is not the initial fixture.
        self.session().execute('reset')
        self.assertIsNone(self.session().execute('capture')['state']['uncertain_mutation'])

    def test_wrong_effect_is_not_completed_input_success(self):
        self.session().execute('qualify')
        wrong = [dict(self.effect[0], expected='2')]
        with self.assertRaisesRegex(RuntimeError, 'effect not established'):
            self.session().execute('act', dict(kind='tap', x=1, y=1), wrong)
        events = [json.loads(line) for line in (self.root/'evidence/events.jsonl').read_text().splitlines()]
        self.assertEqual(events[-1]['kind'], 'attempt_failed')
        self.assertIsNotNone(events[-1]['uncertain_mutation'])

    def test_delayed_effect_reads_do_not_repeat_input(self):
        self.config.update(probe_wait_seconds=.2, probe_interval=.01, probe_stability=2)
        self.session().execute('qualify')
        original = self.device
        pending, reads = False, 0
        def delayed(argv, *args, **kwargs):
            nonlocal pending, reads
            result = original(argv, *args, **kwargs)
            if argv[3:6] == ['shell', 'input', 'tap']:
                pending = True
            if pending and argv[3:5] == ['shell', 'cat']:
                reads += 1
                result['stdout'] = b'0' if reads < 3 else b'1'
            return result
        with patch.object(observation, 'run', side_effect=delayed):
            result = self.session().execute('act', dict(kind='tap', x=1, y=1), self.effect)
        self.assertIsNone(result['state']['uncertain_mutation'])
        self.assertEqual(reads, 4)
        self.assertEqual(sum(c[:3] == ['shell', 'input', 'tap'] for c in self.calls), 1)

    def test_unestablished_stability_and_expired_effect_do_not_pass(self):
        self.config['probe_stability'] = 2
        with self.assertRaises(RuntimeError):
            self.session().execute('qualify')
        self.config.update(probe_stability=1, probe_wait_seconds=.025, probe_interval=.01)
        # Config identity changed deliberately; use a fresh session.
        session = observation.Session(self.root/'timed', self.config)
        session.execute('qualify')
        with self.assertRaises(RuntimeError):
            session.execute('act', dict(kind='tap', x=1, y=1), [dict(self.effect[0], expected='never')])
        state = json.loads((self.root/'timed/session.json').read_text())
        self.assertIsNotNone(state['uncertain_mutation'])
        self.assertEqual(sum(c[:3] == ['shell', 'input', 'tap'] for c in self.calls), 1)

    def test_version_drift_and_stale_coordinate_rejection(self):
        self.session().execute('qualify')
        with self.assertRaisesRegex(ValueError, 'geometry'):
            self.session().execute('act', dict(kind='tap', x=10, y=1), self.effect)
        self.assertFalse(any(c[:2] == ['shell', 'input'] for c in self.calls))
        self.version = 'versionCode=2 versionName=2'
        with self.assertRaisesRegex(RuntimeError, 'environment changed'):
            self.session().execute('capture')
        state = json.loads((self.root/'evidence/session.json').read_text())
        self.assertFalse(state['qualified'])

    def test_installed_bytes_are_bound_when_reviewed_hash_is_supplied(self):
        self.config['apk_sha256s'] = ['a'*64]
        original = self.device
        installed_hash = 'a'*64
        def transport(argv, *args, **kwargs):
            if argv[3:5] == ['shell', 'sha256sum']:
                self.calls.append(argv[3:])
                return dict(status='completed', exit_code=0, elapsed=.001,
                            stdout=(installed_hash+'  '+argv[-1]).encode(), stderr=b'')
            return original(argv, *args, **kwargs)
        with patch.object(observation, 'run', side_effect=transport):
            self.assertEqual(self.session().execute('qualify')['state']['environment']['apk_sha256s'], ['a'*64])
            installed_hash = 'b'*64
            with self.assertRaisesRegex(RuntimeError, 'APK bytes differ'):
                self.session().execute('act', dict(kind='tap', x=1, y=1), self.effect)
        self.assertFalse(any(command[:2] == ['shell', 'input'] for command in self.calls))
        self.assertFalse(json.loads((self.root/'evidence/session.json').read_text())['qualified'])

    def test_fresh_capture_stability_does_not_reuse_prior_frame(self):
        self.config.update(capture_stability=2, capture_interval=.01, capture_wait_seconds=.2)
        original = self.device
        count = 0
        def settling(argv, *args, **kwargs):
            nonlocal count
            result = original(argv, *args, **kwargs)
            if argv[3:] == ['exec-out', 'screencap', '-p']:
                count += 1
                result['stdout'] = png(min(count, 2))
            return result
        with patch.object(observation, 'run', side_effect=settling):
            self.session().execute('qualify')
        events = [json.loads(line) for line in (self.root/'evidence/events.jsonl').read_text().splitlines()]
        stable = next(e for e in events if e['kind']=='capture_stability')
        self.assertEqual(count, 3)
        self.assertEqual(len(set(stable['capture_ids'])), 2)
        self.assertEqual(len(list((self.root/'evidence').glob('*.png'))), 3)

    def test_continuously_changing_capture_cannot_qualify(self):
        self.config.update(capture_stability=2, capture_interval=.01, capture_wait_seconds=.035)
        original = self.device
        count = 0
        def changing(argv, *args, **kwargs):
            nonlocal count
            result = original(argv, *args, **kwargs)
            if argv[3:] == ['exec-out', 'screencap', '-p']:
                count += 1
                result['stdout'] = png(count%2)
            return result
        with patch.object(observation, 'run', side_effect=changing), self.assertRaises(RuntimeError):
            self.session().execute('qualify')
        self.assertFalse(json.loads((self.root/'evidence/session.json').read_text())['qualified'])

    def test_launcher_policy_does_not_weaken_app_screen_stability(self):
        self.config.update(capture_stability=2, capture_interval=.01, capture_wait_seconds=.2,
                           capture_stability_overrides={'stop-after': 1, 'launch-before': 1})
        original = self.device
        stopped, captures = False, 0
        def transport(argv, *args, **kwargs):
            nonlocal stopped, captures
            result = original(argv, *args, **kwargs)
            command = argv[3:]
            if command[:3] == ['shell', 'am', 'force-stop']:
                stopped = True
            elif command[:3] == ['shell', 'am', 'start']:
                stopped = False
            if command == ['exec-out', 'screencap', '-p']:
                captures += 1
                result['stdout'] = png(captures%2 if stopped else 0)
            return result
        with patch.object(observation, 'run', side_effect=transport):
            session = self.session()
            session.execute('qualify')
            effect = [dict(self.effect[0], expected='0')]
            stopped_result = session.execute('act', dict(kind='stop'), effect)
            self.assertEqual(stopped_result['state']['capture']['required_stability'], 1)
            launched_result = session.execute('act', dict(kind='launch'), effect)
            self.assertEqual(launched_result['state']['capture']['required_stability'], 2)
        events = [json.loads(line) for line in (self.root/'evidence/events.jsonl').read_text().splitlines()]
        self.assertTrue(any(e['kind']=='capture_stability' and e['capture_policy']=='launch-after' for e in events))

    def test_probe_missing_or_mutating_and_png_corruption_rejected(self):
        with self.assertRaises(ValueError):
            observation.validate(dict(self.config, fixture=[]))
        with self.assertRaises(ValueError):
            observation.validate_probe(dict(self.effect[0], argv=['shell', 'input', 'tap', '1', '1']))
        bad = bytearray(png()); bad[45] ^= 1
        with self.assertRaises(ValueError):
            observation.png_geometry(bytes(bad))
        with self.assertRaises(ValueError):
            observation.png_geometry(png()[:-1])


class ProcessTests(unittest.TestCase):
    def test_output_and_time_limits_preserve_partial_evidence(self):
        with tempfile.TemporaryDirectory() as root:
            result = run([sys.executable, '-c', 'import time; print("before",flush=True); time.sleep(5)'], root, timeout=.2)
            self.assertEqual(result['status'], 'timeout')
            self.assertEqual(result['stdout'], b'before\n')
            large = run([sys.executable, '-c', 'print("x"*10000)'], root, max_bytes=100)
            self.assertEqual(large['status'], 'output_limit')
            self.assertEqual(len(large['stdout'])+len(large['stderr']), 100)


if __name__ == '__main__':
    unittest.main()
