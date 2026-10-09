"""Owned runtime paths with real subprocess/artifact checks; no native qualification.

These authored fixtures exercise the kernel's guarantees, not general product
fidelity, host hooks, independence of arbitrary reviewers or economic advantage.
"""
from contextlib import contextmanager
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
import factory
import rdd
import workflow


class FactoryRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / 'project'
        self.project.mkdir()
        self.store = Path(self.temp.name) / 'private' / 'records.jsonl'
        self.store.parent.mkdir()
        self.registry = Path(self.temp.name) / 'resource-owner-index'
        self.core = factory.Factory(self.store, self.registry)
        self.root = 'complete-original-task'
        (self.project / 'intent.txt').write_text('reference property: persist a useful result')
        (self.project / 'product.txt').write_text('before')
        (self.project / 'oracle.py').write_text("from pathlib import Path\nassert Path('product.txt').read_text() == 'produced'\nprint('persistent result checked')\n")
        self.task = dict(scope='fixture-project', goal='deliver persistent result', audience='test consumer', surface='cli',
                         operation='adapt', access='source-assisted', tags=[], capabilities=[], contributions=['c'], transfers=['t'],
                         competence=[dict(property='persistence', authority='actual product oracle', preserve='persistent value',
                                          adapt='owned file fixture', check='separate process reads output', transfers=['t'])],
                         character=[], character_omitted_reason='fixture has no sensory requirement',
                         journey=dict(entry='invoke producer', default='before', action='produce', outcome='produced', reset='restore before'),
                         inputs=workflow.fingerprint(self.project, ['intent.txt']))
        self.add('r', 'reference', locator='authored fixture', job='behavior evidence', inspection='read expected persisted value')
        self.add('e', 'evidence', ['r'], claim='value persists', basis='documented', conditions='owned local file')
        self.add('c', 'contribution', ['e'], property='persistence', conditions='owned local file', delta='actual durable check', test='oracle.py')
        self.add('d', 'decision', ['c'], status='adopted', conditions='fixture task', reason='discriminating file read', revisit='changed oracle',
                 task_scope=self.task['scope'], context_sha256=workflow.decision_basis(self.task))
        self.add('t', 'transfer', ['c'], invariant='persist exact value', adaptation='file output', artifact='product.txt',
                 check_plan='separate process reads value', task_scope=self.task['scope'], depends_on=['d'])
        self.intake = dict(root_task_id=self.root, native_identity=dict(host='authored-host-fixture', session='session-a', turn='turn-1'),
                           full_text='Create and deliver the persistent result; do not drop this requirement.', task=self.task,
                           requirements=[dict(id='R1', property='persistence', description='consumer can reopen exact result')],
                           authorization_scope='owned temporary fixture files and subprocesses', resource_limits=dict(operations=4, episodes=2, tokens=1000))
        self.objective = self.core.bind_native_input(self.intake)

    def add(self, identifier, kind, links=(), **data):
        return rdd.append(self.store, dict(id=identifier, kind=kind, data=dict(links=list(links), **data)), allow_drift=True)

    def reservation(self, key='producer', operations=1, revision=1):
        return self.core.reserve(self.root, dict(reservation_key=key, purpose='complete fixture output', amounts=dict(operations=operations), objective_revision=revision))

    def operation(self, reservation=None, root=None, core=None):
        root = root or self.root
        core = core or self.core
        if reservation is None:
            reservation = self.reservation()
        packet = core.compile(root)
        closure = packet['factory_binding']['selected_closure_digest']
        command = [sys.executable, '-c', "from pathlib import Path; Path('product.txt').write_text('produced')"]
        producing = dict(command=command, cwd=str(self.project), objective='complete persistent result')
        request = dict(objective_revision=packet['factory_binding']['revision'], project_root=str(self.project), operation_class='generation',
                    write_set=['product.txt'], producing_input=producing, selected_closure_digest=closure,
                    expected_target_manifest=workflow.fingerprint(self.project, ['product.txt']), reservation_ref=reservation['id'],
                    capability=dict(adapter='owned-subprocess-v1', guarantee_scope='local admission only', permission_scope='authorized temporary fixture'),
                    permitted_effect_scope='product.txt only, authored command fixture',
                    applied_transfer_associations=[dict(transfer_ref='t', property='persistence', conditions='authored fixture',
                                                       composition_version='fixture-v1', check_plan='oracle.py',
                                                       producing_input_digest=factory.hash_value(producing), selected_closure_digest=closure)])
        return core.prepare_owned_operation(root, request)

    def correct(self, text='No Inter.', requirements=None):
        request = deepcopy(self.intake)
        request['full_text'] = text
        request['expected_revision'] = self.core.payload(self.core.state(self.root)[0])['revision']
        request['native_identity']['turn'] = 'correction-' + str(request['expected_revision'])
        if requirements is not None:
            request['requirements'] = requirements
        return self.core.bind_native_input(request)

    def reconcile(self, operation_ref, effects='committed'):
        evidence = self.project / 'observer.json'
        evidence.write_text(json.dumps(dict(product=(self.project / 'product.txt').read_text(),
                                            process='authored single process returned; no spawned fixture children')))
        return self.core.reconcile_operation(self.root, dict(operation_ref=operation_ref, observer='fixture exact target observer',
                   observed_at='fixture observed after process returned', observation_materials=[dict(path=str(evidence))],
                   attribution='exact authored operation and resulting file value', producer_lifecycle='stopped',
                   descendant_lifecycle='none_confirmed', target_effects=effects, consistency_scope='local authored fixture target snapshot'))

    def build_acceptance(self):
        run = self.core.run_owned_operation(self.root, self.operation())
        self.assertEqual((self.project / 'product.txt').read_text(), 'produced')
        self.reconcile(run['admission_ref'])
        result = subprocess.run([sys.executable, 'oracle.py'], cwd=self.project, capture_output=True, check=True)
        observed = self.project / 'checker.stdout'
        observed.write_bytes(result.stdout)
        captured = self.core.capture_material(dict(path=str(observed)))
        self.add('observed', 'evidence', ['r'], claim='independent fixture process read persisted output', basis='observed',
                 conditions='separate known expectation', local_path=captured['local_path'])
        subject = workflow.fingerprint(self.project, ['product.txt'])
        driver = workflow.fingerprint(self.project, ['intent.txt'])
        oracle = workflow.fingerprint(self.project, ['oracle.py'])
        self.add('check', 'check', ['t', 'observed'], method='separate python oracle process', outcome='passed',
                 result='read produced', limits='authored local fixture only', artifact_inputs=subject,
                 property_ids=[['R1', 'persistence']], objective_ref=self.objective['id'], objective_revision=1,
                 acceptance_version=self.core.payload(self.objective)['acceptance_version'],
                 composition_version='fixture-v1', driver_closure=driver, oracle_closure=oracle,
                 checker_identity='fixture-checker')
        request = dict(objective_revision=1, subject_manifest=subject, composition_version='fixture-v1',
                       driver_closure=driver, oracle_closure=oracle,
                       independence_scope='fixture oracle authored before producer, separate invocation', current_producer_identity='fixture-producer',
                       property_verdicts=[dict(requirement_id='R1', property='persistence', check_ref='check', checker_identity='fixture-checker',
                                               oracle_authority='authored acceptance expectation', independence='separate process and preexisting expectation', outcome='passed')])
        return self.core.eligible_acceptance(self.root, request), run, request

    def delivery_request(self, acceptance):
        return dict(acceptance_ref=acceptance['id'], usable_entry='python oracle.py in fixture project', default_state='persisted produced value',
                    runtime_environment_closure=workflow.fingerprint(self.project, ['oracle.py']),
                    demonstration_materials=[dict(path=str(self.project / 'checker.stdout'))], fresh_consumer_identity='cold-fixture-consumer',
                    native_continuation_ref='fixture-native-session', external_consistency_limits='unowned writers remain outside lock guarantee')

    def test_actual_subprocess_to_current_complete_delivery(self):
        acceptance, run, _ = self.build_acceptance()
        delivered = self.core.finalize_delivery(self.root, self.delivery_request(acceptance))
        self.assertEqual(self.core.payload(delivered)['subject_manifest'], workflow.fingerprint(self.project, ['product.txt']))
        self.assertEqual(self.core.status(self.root)['resources']['current_delivery_refs'], [delivered['id']])
        self.assertNotIn(run['admission_ref'], self.core.project_outcome_resources(self.root)['missing_owned_attempts'])
        self.assertGreater(self.core.project_outcome_resources(self.root)['supported_subtotals']['wall_seconds'], 0)
        self.assertIsNone(self.core.project_outcome_resources(self.root)['whole_task_savings'])

    def test_full_native_input_attachments_short_correction_recoverable(self):
        image = self.project / 'image.bin'
        image.write_bytes(b'actual attachment bytes')
        update = deepcopy(self.intake)
        update.update(expected_revision=1, attachments=[dict(path=str(image), role='reference-image')])
        bound = self.core.bind_native_input(update)
        saved = self.core.payload(bound)['attachments'][0]
        image.unlink()
        self.assertEqual(self.core.material_gaps([saved]), [])
        correction = self.correct()
        self.assertEqual(self.core.payload(correction)['full_text'], 'No Inter.')
        self.assertEqual(self.core.payload(correction)['original_scope_digest'], self.core.payload(self.objective)['original_scope_digest'])
        self.assertEqual(self.core.payload(bound)['full_text'], self.intake['full_text'])

    def test_resume_cannot_reset_root_and_children_share_headroom(self):
        self.core.reserve(self.root, dict(reservation_key='seed-a', purpose='mechanism research', amounts=dict(episodes=1, tokens=800), objective_revision=1))
        self.correct('continue research')
        resumed = factory.Factory(self.store, self.registry)
        with self.assertRaisesRegex(factory.FactoryError, 'allowance exhausted'):
            resumed.reserve(self.root, dict(reservation_key='seed-b', purpose='recursive child', amounts=dict(episodes=1, tokens=300), objective_revision=2))
        reset = deepcopy(self.intake)
        reset.update(expected_revision=2, resource_limits=dict(operations=99, episodes=99, tokens=999999))
        with self.assertRaisesRegex(factory.FactoryError, 'cannot reset'):
            self.core.bind_native_input(reset)

    def test_origin_idempotence_conflict_gap_and_lost_material(self):
        source = self.project / 'source.txt'
        source.write_text('original evidence')
        request = dict(origin_namespace='fixture', source_stream='native-a', source_event_identity='e3', source_sequence=3,
                       source_schema='fixture-v1', parser_version='v1', payload=dict(message='evidence'),
                       referenced_materials=[dict(path=str(source), sha256=rdd.digest(source))])
        imported = self.core.import_origin_event(self.root, request)
        self.assertTrue(imported['complete_recovery_ack'])
        duplicate = self.core.import_origin_event(self.root, request)
        self.assertEqual(imported['receipt']['id'], duplicate['receipt']['id'])
        watermarks = next(iter(self.core.import_watermarks(self.root).values()))
        self.assertEqual(watermarks['contiguous_through'], 0)
        self.assertEqual(watermarks['gaps'], [1, 2])
        drift = deepcopy(request)
        drift['payload']['message'] = 'different origin payload'
        self.assertEqual(self.core.import_origin_event(self.root, drift)['status'], 'quarantined_identity_conflict')
        saved = self.core.payload(imported['receipt'])['referenced_materials'][0]
        (self.store.parent / saved['local_path']).unlink()
        replay = self.core.import_origin_event(self.root, request)
        self.assertFalse(replay['complete_recovery_ack'])
        self.assertTrue(replay['material_gaps'])

    def test_wrong_actual_input_and_closure_do_not_dispatch(self):
        called = []
        request = self.operation()
        request['actual_producing_input'] = dict(command=['wrong'])
        with self.assertRaisesRegex(factory.FactoryError, 'actual producing input'):
            self.core.admit_owned_operation(self.root, request, lambda *args: called.append(args))
        self.assertEqual(called, [])
        request = self.operation(self.reservation())
        request['actual_selected_closure_digest'] = '0' * 64
        with self.assertRaisesRegex(factory.FactoryError, 'closure differs'):
            self.core.admit_owned_operation(self.root, request, lambda *args: called.append(args))
        self.assertEqual(self.core.operations(self.root), {})

    def test_changed_intake_and_target_reject_admission(self):
        request = self.operation()
        self.correct('preserve current requirement but change direction')
        with self.assertRaisesRegex(factory.FactoryError, 'stale objective'):
            self.core.run_owned_operation(self.root, request)
        self.assertEqual((self.project / 'product.txt').read_text(), 'before')
        new = self.operation(self.reservation('new-revision', revision=2))
        (self.project / 'product.txt').write_text('unowned change')
        with self.assertRaisesRegex(factory.FactoryError, 'target changed'):
            self.core.run_owned_operation(self.root, new)

    def test_unknown_dispatch_failure_is_not_blindly_replayed(self):
        request = self.operation()
        def lost_reply(bound, ref):
            (self.project / 'product.txt').write_text('produced')
            raise OSError('lost result after actual write')
        with self.assertRaises(OSError):
            self.core.admit_owned_operation(self.root, request, lost_reply)
        operation_ref = next(iter(self.core.operations(self.root)))
        self.assertEqual(self.core.operations(self.root)[operation_ref]['target_effects'], 'unknown')
        retry = self.operation(self.reservation('retry'))
        with self.assertRaisesRegex(factory.FactoryError, 'unresolved'):
            self.core.run_owned_operation(self.root, retry)
        with self.assertRaisesRegex(factory.FactoryError, 'unresolved'):
            self.core.settle(self.root, dict(reservation_ref=request['reservation_ref'], actual=dict(operations=0), observation_ref='no output'))
        self.reconcile(operation_ref)
        completed = self.core.run_owned_operation(self.root, retry)
        self.assertEqual(self.core.payload(completed['result'])['exit_code'], 0)

    def test_reservation_cannot_dispatch_twice(self):
        request = self.operation()
        result = self.core.run_owned_operation(self.root, request)
        self.reconcile(result['admission_ref'])
        request['expected_target_manifest'] = workflow.fingerprint(self.project, ['product.txt'])
        with self.assertRaisesRegex(factory.FactoryError, 'already dispatched'):
            self.core.run_owned_operation(self.root, request)

    def test_correction_invalidates_historical_acceptance_delivery(self):
        acceptance, _, _ = self.build_acceptance()
        self.correct()
        with self.assertRaisesRegex(factory.FactoryError, 'stale acceptance'):
            self.core.finalize_delivery(self.root, self.delivery_request(acceptance))
        self.assertEqual(self.core.project_outcome_resources(self.root)['current_delivery_refs'], [])

    def test_current_delivery_projection_rechecks_driver_oracle_and_materials(self):
        acceptance, _, _ = self.build_acceptance()
        self.core.finalize_delivery(self.root, self.delivery_request(acceptance))
        (self.project / 'oracle.py').write_text("print('wrong changed oracle')\n")
        result = self.core.project_outcome_resources(self.root)
        self.assertEqual(result['current_delivery_refs'], [])
        self.assertIn('oracle_closure', result['delivery_projection_gaps'][0]['reason'])

    def test_missing_property_wrong_subject_and_self_oracle_rejected(self):
        _, _, request = self.build_acceptance()
        missing = deepcopy(request)
        missing['property_verdicts'] = []
        with self.assertRaises(factory.FactoryError):
            self.core.eligible_acceptance(self.root, missing)
        wrong = deepcopy(request)
        wrong['subject_manifest'] = workflow.fingerprint(self.project, ['intent.txt'])
        with self.assertRaisesRegex(factory.FactoryError, 'different subject'):
            self.core.eligible_acceptance(self.root, wrong)
        self_oracle = deepcopy(request)
        self_oracle['current_producer_identity'] = self_oracle['property_verdicts'][0]['checker_identity']
        with self.assertRaisesRegex(factory.FactoryError, 'not independent'):
            self.core.eligible_acceptance(self.root, self_oracle)

    def test_delivery_gate_serializes_actual_correction_race(self):
        acceptance, _, _ = self.build_acceptance()
        check_entered = threading.Event()
        release_check = threading.Event()
        correction_started = threading.Event()
        correction_done = threading.Event()
        errors = []
        original = self.core._acceptance
        def slow_check(root, request):
            answer = original(root, request)
            check_entered.set()
            self.assertTrue(release_check.wait(5))
            return answer
        self.core._acceptance = slow_check
        def deliver():
            try:
                self.core.finalize_delivery(self.root, self.delivery_request(acceptance))
            except Exception as exc:
                errors.append(exc)
        def correct():
            correction_started.set()
            try:
                self.correct('race correction')
            except Exception as exc:
                errors.append(exc)
            correction_done.set()
        delivery_thread = threading.Thread(target=deliver)
        delivery_thread.start()
        self.assertTrue(check_entered.wait(5))
        correction_thread = threading.Thread(target=correct)
        correction_thread.start()
        self.assertTrue(correction_started.wait(5))
        self.assertFalse(correction_done.wait(0.05))
        release_check.set()
        delivery_thread.join(5)
        correction_thread.join(5)
        self.assertFalse(errors)
        names = [e['data']['event'] for e in self.core.events(self.root)]
        self.assertLess(names.index('delivery'), len(names) - 1)
        self.assertEqual(names[-1], 'native_input')
        self.assertEqual(self.core.project_outcome_resources(self.root)['current_delivery_refs'], [])

    def test_bounded_episode_requires_inspection_and_decision_consumer(self):
        request = dict(seed_id='mechanism-seed', decision='choose persistence mechanism', mechanism_question='does result survive cold read?',
                       alternatives=['file persistence', 'memory only'], counterlead='temporary state may look correct', next_discriminator='cold process read',
                       access_scope='fixture files', stop_condition='one distinguishing read', reopen_condition='changed persistence boundary',
                       prior_feasible_action='use memory state', reservation=dict(reservation_key='episode-a', purpose='research', amounts=dict(episodes=1), objective_revision=1))
        episode = self.core.admit_episode(self.root, request)
        self.assertEqual(self.core.admit_episode(self.root, request)['id'], episode['id'])
        bad = dict(episode_ref=episode['id'], disposition='adopt', stop_reason='evidence read', decision_effect='choose actual file', actual_inspection_refs=['e'], decision_ref='d')
        with self.assertRaisesRegex(factory.FactoryError, 'consumer_refs'):
            self.core.close_episode(self.root, bad)
        good = dict(bad, consumer_refs=[dict(record_ref='t', effect='bind persistence into actual operation')])
        closed = self.core.close_episode(self.root, good)
        self.assertEqual(self.core.payload(closed)['decision_effect'], 'choose actual file')
        self.core.settle(self.root, dict(reservation_ref=self.core.payload(episode)['reservation_ref'], actual=dict(episodes=1), observation_ref=closed['id']))
        self.assertEqual(self.core.allocation(self.root)['observed_settled']['episodes'], 1)
        with self.assertRaisesRegex(factory.FactoryError, 'already dispatched or closed'):
            self.core.record_episode_dispatch(self.root, dict(episode_ref=episode['id'], actual_adapter='fake reuse', actual_worker_identity='fake worker', assignment='reuse closed work', output_refs=['fake']))
        with self.assertRaisesRegex(factory.FactoryError, 'cannot erase'):
            self.core.settle(self.root, dict(reservation_ref=self.core.payload(episode)['reservation_ref'], actual=dict(episodes=0), observation_ref=closed['id']))

    def test_actual_live_owner_blocks_other_roots_and_journals(self):
        request = self.operation()
        request['producing_input']['command'] = [sys.executable, '-c', 'import time; time.sleep(0.2)']
        request['applied_transfer_associations'][0]['producing_input_digest'] = factory.hash_value(request['producing_input'])
        def launch(bound, ref):
            process = subprocess.Popen(bound['command'], cwd=self.project)
            return dict(producer=process, producer_identity=dict(pid=process.pid, attempt=ref))
        running = self.core.admit_owned_operation(self.root, request, launch)
        self.addCleanup(running['producer'].wait)
        second_intake = deepcopy(self.intake)
        second_intake['root_task_id'] = 'other-root'
        self.core.bind_native_input(second_intake)
        other = self.core.reserve('other-root', dict(reservation_key='second-root', purpose='other target write', amounts=dict(operations=1), objective_revision=1))
        conflicting = self.operation(other, root='other-root')
        with self.assertRaisesRegex(factory.FactoryError, 'across owned journals'):
            self.core.admit_owned_operation('other-root', conflicting, launch)
        second_store = Path(self.temp.name) / 'another-private' / 'records.jsonl'
        second_store.parent.mkdir()
        for record in self.core.records():
            if record['kind'] != 'factory_event':
                rdd.append(second_store, record)
        second = factory.Factory(second_store, self.registry)
        second.bind_native_input(second_intake)
        third = second.reserve('other-root', dict(reservation_key='second-journal', purpose='other target write', amounts=dict(operations=1), objective_revision=1))
        conflicting = self.operation(third, root='other-root', core=second)
        with self.assertRaisesRegex(factory.FactoryError, 'across owned journals'):
            second.admit_owned_operation('other-root', conflicting, launch)

    def test_manifest_must_cover_writes_and_new_file_absence(self):
        request = self.operation()
        request['expected_target_manifest'] = workflow.fingerprint(self.project, ['intent.txt'])
        (self.project / 'product.txt').write_text('intervening change')
        with self.assertRaisesRegex(factory.FactoryError, 'does not cover'):
            self.core.run_owned_operation(self.root, request)
        new = self.operation(self.reservation('new-file'))
        new['write_set'] = ['new.txt']
        new['producing_input']['command'] = [sys.executable, '-c', "from pathlib import Path; Path('new.txt').write_text('new')"]
        new['applied_transfer_associations'][0]['producing_input_digest'] = factory.hash_value(new['producing_input'])
        new['expected_target_manifest'] = workflow.fingerprint(self.project, trees=['.'])
        (self.project / 'new.txt').write_text('external new file')
        with self.assertRaisesRegex(factory.FactoryError, 'target changed'):
            self.core.run_owned_operation(self.root, new)

    def test_original_text_and_attachment_survive_correction_consumption(self):
        image = self.project / 'original-image.bin'
        image.write_bytes(b'original required pixels')
        request = deepcopy(self.intake)
        request.update(expected_revision=1, attachments=[dict(path=str(image), required=True)])
        image_bound = self.core.bind_native_input(request)
        self.correct('No Inter.')
        packet = self.core.compile(self.root)
        self.assertIn(self.intake['full_text'], [item['full_text'] for item in packet['factory_binding']['native_input_lineage']])
        self.assertEqual(packet['factory_binding']['native_input_lineage'][-1]['full_text'], 'No Inter.')
        saved = self.core.payload(image_bound)['attachments'][0]
        (self.store.parent / saved['local_path']).unlink()
        packet = self.core.compile(self.root)
        self.assertFalse(packet['ready_for_handoff'])
        self.assertTrue(packet['factory_binding']['attachment_gaps'])

    def test_child_reads_exact_current_original_correction_source_and_image_context(self):
        image = self.project / 'uploaded-image.bin'
        image.write_bytes(b'actual uploaded reference pixels')
        request = deepcopy(self.intake)
        request.update(expected_revision=1, attachments=[dict(path=str(image), role='reference-image')])
        self.core.bind_native_input(request)
        self.correct('No Inter.')
        operation = self.operation(self.reservation('context-consumer', revision=3))
        child = """import hashlib, json, os
from pathlib import Path
context_path = Path(os.environ['RDD_FACTORY_CONTEXT_PATH'])
raw = context_path.read_bytes()
assert hashlib.sha256(raw).hexdigest() == os.environ['RDD_FACTORY_CONTEXT_SHA256']
packet = json.loads(raw)
binding = packet['factory_binding']
assert binding['revision'] == 3
assert binding['native_input_lineage'][0]['full_text'].startswith('Create and deliver')
assert binding['native_input_lineage'][-1]['full_text'] == 'No Inter.'
image = binding['attachments'][0]
assert (context_path.parent.parent / image['local_path']).read_bytes() == b'actual uploaded reference pixels'
assert any(r['id'] == 'c' and r['data']['property'] == 'persistence' for r in packet['records'])
Path('product.txt').write_text('produced')
print('child read exact original, correction, uploaded bytes and selected mechanism')
"""
        operation['producing_input']['command'] = [sys.executable, '-c', child]
        operation = self.core.prepare_owned_operation(self.root, operation)
        result = self.core.run_owned_operation(self.root, operation)
        self.assertEqual(self.core.payload(result['result'])['exit_code'], 0)
        output = self.core.payload(result['result'])['outputs'][0]
        self.assertIn('child read exact original', (self.store.parent / output['local_path']).read_text())
        admitted = self.core.payload(self.core.find(result['admission_ref']))
        self.assertEqual(admitted['producing_input']['factory_context']['sha256'], operation['compiled_context_digest'])

    def test_missing_context_transport_or_changed_native_capsule_blocks_dispatch(self):
        request = self.operation()
        request.pop('compiled_context_digest')
        with self.assertRaisesRegex(factory.FactoryError, 'compiled_context_digest'):
            self.core.run_owned_operation(self.root, request)
        request = self.operation()
        request['producing_input']['factory_context']['root_task_id'] = 'other-native-task'
        request['applied_transfer_associations'][0]['producing_input_digest'] = factory.hash_value(request['producing_input'])
        with self.assertRaisesRegex(factory.FactoryError, 'exact current selected'):
            self.core.run_owned_operation(self.root, request)

    def test_old_check_cannot_substitute_property_or_checking_tuple(self):
        _, _, request = self.build_acceptance()
        substituted = deepcopy(request)
        substituted['composition_version'] = 'different-composition'
        with self.assertRaisesRegex(factory.FactoryError, 'different composition'):
            self.core.eligible_acceptance(self.root, substituted)
        (self.project / 'oracle.py').write_text("print('always passes')\n")
        substituted = deepcopy(request)
        substituted['oracle_closure'] = workflow.fingerprint(self.project, ['oracle.py'])
        with self.assertRaisesRegex(factory.FactoryError, 'different oracle'):
            self.core.eligible_acceptance(self.root, substituted)
        # Add an obligation without changing the subject, then relabel the old
        # check. A passed persistence check must not become an encryption check.
        self.correct('also support encryption', requirements=self.intake['requirements'] + [dict(id='R2', property='encryption', description='encrypted output')])
        substituted['objective_revision'] = 2
        extra = deepcopy(substituted['property_verdicts'][0])
        extra.update(requirement_id='R2', property='encryption')
        substituted['property_verdicts'].append(extra)
        with self.assertRaisesRegex(factory.FactoryError, 'different objective/acceptance'):
            self.core.eligible_acceptance(self.root, substituted)

    def test_failed_preparation_is_not_dispatch_or_result(self):
        request = dict(seed_id='unavailable-seed', decision='choose source', mechanism_question='source accessible?', alternatives=['inspect source', 'retain uncertainty'],
                       counterlead='missing source cannot settle fidelity', next_discriminator='read source', access_scope='fixture', stop_condition='source inaccessible',
                       reopen_condition='source access restored', prior_feasible_action='leave uncertainty',
                       reservation=dict(reservation_key='episode-unavailable', purpose='research', amounts=dict(episodes=1), objective_revision=1))
        episode = self.core.admit_episode(self.root, request)
        self.core.close_episode(self.root, dict(episode_ref=episode['id'], disposition='inaccessible', stop_reason='source missing',
                                               decision_effect='retain uncertainty', actual_inspection_refs=[], deferred_trigger='access restored'))
        self.assertFalse(any(e['data']['event'] == 'episode_dispatch' for e in self.core.events(self.root)))

    def test_rebase_requires_current_full_known_basis_and_consumes_input(self):
        result = self.core.run_owned_operation(self.root, self.operation())
        self.reconcile(result['admission_ref'])
        current = self.correct('retain requirements and continue')
        fresh = self.operation(self.reservation('new-op', revision=2))
        request = dict(prior_operation_ref=result['admission_ref'], old_objective_ref=self.objective['id'], new_objective_ref=current['id'],
                       relevant_generations=[dict(name='selected reference', old='v1', new='v1')], semantic_applicability_evidence='same fixture property',
                       fresh_producing_input=fresh['producing_input'], changed_scope='native wording only')
        bad = deepcopy(request)
        bad['relevant_generations'][0]['new'] = 'unknown'
        with self.assertRaisesRegex(factory.FactoryError, 'unknown relevant'):
            self.core.rebase_operation(self.root, bad)
        rebased = self.core.rebase_operation(self.root, request)
        fresh['rebase_ref'] = rebased['id']
        fresh['producing_input']['objective'] = 'unbound different input'
        fresh['applied_transfer_associations'][0]['producing_input_digest'] = factory.hash_value(fresh['producing_input'])
        with self.assertRaisesRegex(factory.FactoryError, 'executor rejects rebase'):
            self.core.run_owned_operation(self.root, fresh)

    def test_resources_deduplicate_cumulative_and_retain_failed_attempts(self):
        result = self.core.run_owned_operation(self.root, self.operation())
        attempt = result['admission_ref']
        first = dict(attempt_id=attempt, source_ref='provider-snapshot-1', resource_kind='model', snapshot_semantics='cumulative',
                     values=dict(tokens=20, api_equivalent=0.10), coverage='partial')
        self.core.record_resource(self.root, first)
        self.core.record_resource(self.root, first)
        self.core.record_resource(self.root, dict(first, source_ref='provider-snapshot-2', values=dict(tokens=30, api_equivalent=0.15)))
        self.core.record_resource(self.root, dict(attempt_id='failed-provider-attempt', source_ref='failure-log', resource_kind='model',
                                                 snapshot_semantics='delta', values=dict(tokens=10, api_equivalent=0.05), coverage='partial'))
        projected = self.core.project_outcome_resources(self.root)
        self.assertEqual(projected['supported_subtotals']['tokens'], 40)
        self.assertAlmostEqual(projected['supported_subtotals']['api_equivalent'], 0.20)
        self.assertEqual(projected['all_attempts_retained'], 2)
        self.assertIsNone(projected['whole_task_savings'])

    def test_cli_status_uses_same_journal(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / 'factory.py'), '--store', str(self.store), 'status', '--root', self.root], capture_output=True, check=True)
        self.assertEqual(json.loads(result.stdout)['objective_ref'], self.objective['id'])
        records, _ = rdd.read_records(self.store)
        self.assertEqual(len([r for r in records if r['kind'] == 'factory_event']), 1)


if __name__ == '__main__':
    unittest.main()
