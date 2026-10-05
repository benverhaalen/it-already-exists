"""Reject misleading evidence handoffs, independently of recorder implementation."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/reference-driven-development/scripts'))
import observation_packet as p


class PacketTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.apk = self.root/'app.apk'
        self.apk.write_bytes(b'owned test build')
        self.hash = hashlib.sha256(self.apk.read_bytes()).hexdigest()
        self.config = dict(apk_sha256s=[self.hash], capture_stability=2)
        self.contract = dict(properties=[dict(id='count', kind='state', observation='after', path=['count'])])
        self.selection = dict(fixture='cleared counter', journey='increment', milestones=[dict(
            id='after', attempt_id='attempt', operation='act', actions=[dict(kind='tap', x=2, y=3)],
            state=dict(count=dict(probe='count', kind='android-preference-int', name='count')))])
        data = b'capture bytes hashed here; decoding belongs to comparator'
        self.capture = dict(path='fresh.png', capture_id='fresh', sha256=p.sha(data), session_id='run',
                            required_stability=2, capture_policy='tap-after', geometry=[10, 10])
        (self.root/'fresh.png').write_bytes(data)
        (self.root/'first.png').write_bytes(data)
        state = dict(session_id='run', config_sha256=p.sha(json.dumps(self.config, sort_keys=True).encode()),
                     qualified=True, uncertain_mutation=None, environment=dict(apk_sha256s=[self.hash]), capture=self.capture)
        self.events = [dict(kind='attempt_started', operation='act'),
                       dict(kind='probes', outcomes=[dict(id='count', status='passed', actual='<map><int name="count" value="0"/></map>')]),
                       dict(kind='input_acknowledged', action=dict(kind='tap', x=2, y=3)),
                       dict(kind='probes', outcomes=[dict(id='count', status='passed', actual='<map><int name="count" value="1"/></map>')]),
                       dict(kind='capture', **dict(self.capture, path='first.png', capture_id='first')),
                       dict(kind='capture', **self.capture),
                       dict(kind='capture_stability', capture_ids=['first', 'fresh'], required_stability=2, capture_policy='tap-after'),
                       dict(kind='attempt_completed', operation='act', state=state)]
        for i, event in enumerate(self.events):
            event.update(session_id='run', attempt_id='attempt', monotonic=i+1)

    def review(self):
        raw = ''.join(json.dumps(e)+'\n' for e in self.events).encode()
        (self.root/'events.jsonl').write_bytes(raw)
        return dict(approved=True, reviewer='independent analyst', journal_sha256=p.sha(raw),
                    config_sha256=p.sha(json.dumps(self.config, sort_keys=True).encode()),
                    contract_sha256=p.canonical(self.contract), selection_sha256=p.canonical(self.selection))

    def prepare(self):
        return p.prepare(self.root, self.config, self.contract, self.selection, self.review(), [self.apk])

    def test_post_input_projection_and_bound_copy(self):
        packet, images = self.prepare()
        self.assertEqual(packet['observations'][0]['state'], {'count': 1})
        self.assertEqual(packet['artifact_sha256'], self.hash)
        output = self.root/'bundle'
        p.publish(output, packet, images)
        self.assertEqual((output/'fresh.png').read_bytes(), images['fresh.png'])
        with self.assertRaises(ValueError):
            p.publish(output, packet, images)

    def test_stale_review_and_changed_build(self):
        review = self.review()
        self.selection['journey'] = 'different journey'
        with self.assertRaisesRegex(ValueError, 'review'):
            p.prepare(self.root, self.config, self.contract, self.selection, review, [self.apk])
        self.apk.write_bytes(b'different build')
        with self.assertRaisesRegex(ValueError, 'APK'):
            self.prepare()

    def test_failed_uncertain_or_wrong_input(self):
        original = copy.deepcopy(self.events)
        for mutation in ('failed', 'uncertain', 'action'):
            self.events = copy.deepcopy(original)
            if mutation == 'failed':
                self.events[-1]['kind'] = 'attempt_failed'
            elif mutation == 'uncertain':
                self.events[-1]['state']['uncertain_mutation'] = dict(kind='tap')
            else:
                self.events[2]['action']['x'] = 99
            with self.assertRaises(ValueError):
                self.prepare()

    def test_pre_input_state_cannot_substitute_for_effect(self):
        self.events[3]['kind'] = 'command'
        with self.assertRaisesRegex(ValueError, 'post-input'):
            self.prepare()

    def test_stability_cannot_use_old_or_mixed_frames(self):
        original = copy.deepcopy(self.events)
        for mutation in ('old', 'missing', 'mixed', 'policy'):
            self.events = copy.deepcopy(original)
            if mutation == 'old':
                self.events[4]['monotonic'] = 2
            elif mutation == 'missing':
                self.events[6]['capture_ids'] = ['fresh']
            elif mutation == 'mixed':
                self.events[4]['sha256'] = '0'*64
            else:
                self.events[-1]['state']['capture']['required_stability'] = 1
            with self.assertRaises(ValueError):
                self.prepare()

    def test_ambiguous_state_and_changed_capture(self):
        self.events[3]['outcomes'][0]['actual'] = '<map><int name="count" value="1"/><int name="count" value="2"/></map>'
        with self.assertRaisesRegex(ValueError, 'unique'):
            self.prepare()
        self.events[3]['outcomes'][0]['actual'] = '<map><int name="count" value="1"/></map>'
        (self.root/'fresh.png').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.prepare()

    def test_intermediate_stability_bytes_and_empty_probes_are_not_evidence(self):
        (self.root/'first.png').write_bytes(b'changed intermediate image')
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.prepare()
        (self.root/'first.png').write_bytes((self.root/'fresh.png').read_bytes())
        self.events[3]['outcomes'] = []
        self.selection['milestones'][0]['state'] = {}
        with self.assertRaisesRegex(ValueError, 'probes'):
            self.prepare()

    def test_journey_cannot_cherry_pick_around_intervening_attempt(self):
        first = copy.deepcopy(self.events)
        middle = copy.deepcopy(self.events)
        last = copy.deepcopy(self.events)
        for offset, aid, history in [(0, 'attempt', first), (10, 'hidden', middle), (20, 'last', last)]:
            for e in history:
                e['attempt_id'] = aid
                e['monotonic'] += offset
        self.events = first+middle+last
        second = copy.deepcopy(self.selection['milestones'][0])
        second.update(id='last', attempt_id='last')
        self.selection['milestones'].append(second)
        with self.assertRaisesRegex(ValueError, 'omit'):
            self.prepare()


if __name__ == '__main__':
    unittest.main()
