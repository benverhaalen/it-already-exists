"""Synthetic mechanics only; no product, device or reconstruction scenarios."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'
sys.path.insert(0, str(SCRIPTS))
import rdd
import workflow


def record(identifier, kind, links=(), **extra):
    data = {field: 'declared ' + field for field in rdd.REQUIRED[kind]}
    data['links'] = list(links)
    if kind == 'evidence':
        data['basis'] = 'observed'
    if kind == 'decision':
        data['status'] = 'adopted'
    if kind == 'check':
        data['outcome'] = 'not-run'
    data.update(extra)
    return dict(id=identifier, kind=kind, data=data)


class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = self.root / 'records.jsonl'
        (self.root / 'input.txt').write_text('v1')
        self.task = dict(scope='a', goal='declared outcome', audience='declared audience', surface='web',
                         operation='adapt', access='source-assisted', tags=['x'], capabilities=[],
                         contributions=['c'], transfers=['t'], competence=[], character=[],
                         competence_omitted_reason='mechanical fixture', character_omitted_reason='mechanical fixture',
                         journey={k: 'declared ' + k for k in ('entry', 'default', 'action', 'outcome', 'reset')},
                         inputs=workflow.fingerprint(self.root, ['input.txt']))
        self.add('r', 'reference')
        self.add('e', 'evidence', ['r'])
        self.add('c', 'contribution', ['e'])
        self.add('d', 'decision', ['c'], task_scope='a', context_sha256=workflow.decision_basis(self.task))
        self.add('t', 'transfer', ['c'], task_scope='a', depends_on=['d'])

    def add(self, identifier, kind, links=(), **extra):
        return rdd.append(self.store, record(identifier, kind, links, **extra))

    def compile(self):
        records, _ = rdd.read_records(self.store, verify_files=False)
        return workflow.compile_context(workflow.task_spec(self.task), records, self.store)

    def test_approach_research_reaches_plan_and_actual_handoff(self):
        plan = workflow.investigate(workflow.task_spec(self.task), workflow.catalog())
        packet = self.compile()
        for result in (plan, packet):
            review = result['approach_review']
            self.assertEqual(review['goal'], self.task['goal'])
            self.assertEqual(review['journey'], self.task['journey'])
            self.assertEqual(review['access'], self.task['access'])
            self.assertEqual(review['stage'], 'before-approach-commitment')
            self.assertIn('remove work', review['questions'][3])
            self.assertIn('not evidence', review['status'])
        self.task['access'] = 'strict-clean-room'
        self.task['operation'] = 'repair'
        repair = workflow.investigate(workflow.task_spec(self.task), workflow.catalog())
        self.assertEqual(repair['approach_review']['stage'], 'diagnose-and-reconsider')
        self.assertEqual(repair['approach_review']['access'], 'strict-clean-room')

    def test_ui_feedback_is_routed_without_imposing_it_on_other_domains(self):
        self.assertEqual(self.compile()['ui_review']['journey'], self.task['journey'])
        self.task['surface'] = 'document'
        self.assertIsNone(self.compile()['ui_review'])
        self.task['tags'] = ['visual']
        self.assertEqual(self.compile()['ui_review']['module'], 'references/ui-continuity.md')

    def test_apk_first_reference_reaches_actual_builder_without_ios_dependency(self):
        self.assertIsNone(self.compile()['apk_reconstruction_review'])
        self.task.update(surface='apk', operation='reconstruct')
        plan = workflow.investigate(workflow.task_spec(self.task), workflow.catalog())
        for result in (plan, self.compile()):
            review = result['apk_reconstruction_review']
            self.assertEqual(review['goal'], self.task['goal'])
            self.assertEqual(review['journey'], self.task['journey'])
            self.assertIn('not prerequisites', review['reference'])
            self.assertIn('decoded bytes', review['encoded_artifacts'])
            self.assertIn('both sides', review['service_boundary'])
        self.task.update(surface='ios', access='strict-clean-room', tags=['apk-iphone'])
        packet = self.compile()
        self.assertFalse(packet['ready_for_handoff'])
        self.assertEqual(packet['apk_reconstruction_review']['access'], 'strict-clean-room')
        self.task.update(surface='document', tags=[])
        self.assertIsNone(self.compile()['apk_reconstruction_review'])

    def test_scoped_latest_decisions_do_not_override_other_tasks(self):
        self.add('other', 'decision', ['c'], task_scope='b', status='contradicted')
        packet = self.compile()
        self.assertTrue(packet['ready_for_handoff'])
        self.assertIn('d', [r['id'] for r in packet['records']])
        self.add('withdraw', 'decision', ['c'], task_scope='a', status='deferred')
        self.assertFalse(self.compile()['ready_for_handoff'])

    def test_declared_change_invalidates_transitive_chain(self):
        self.add('change', 'change', ['e'], reason='new input', scope='shared fact', revisit='reobserve')
        records, _ = rdd.read_records(self.store)
        result = workflow.impact(records, self.store)
        self.assertTrue({'e', 'c', 'd', 't'} <= set(result['affected']))
        self.assertFalse(self.compile()['ready_for_handoff'])

    def test_hash_drift_recovery_preserves_history_and_blocks_stale_handoff(self):
        self.add('local', 'evidence', ['r'], local_path='input.txt')
        self.add('c2', 'contribution', ['local'])
        original = self.store.read_bytes()
        (self.root / 'input.txt').write_text('v2')
        with self.assertRaises(rdd.JournalError):
            self.add('new', 'reference')
        rdd.append(self.store, record('changed', 'change', ['local']), allow_drift=True)
        self.assertTrue(self.store.read_bytes().startswith(original))
        records, _ = rdd.read_records(self.store, verify_files=False)
        self.assertIn('c2', workflow.impact(records, self.store)['affected'])
        self.assertFalse(self.compile()['ready_for_handoff'])

    def test_new_tree_member_invalidates_context(self):
        directory = self.root / 'selected'
        directory.mkdir()
        (directory / 'a').write_text('a')
        self.task['inputs'] = workflow.fingerprint(self.root, trees=['selected'])
        self.add('tree-decision', 'decision', ['c'], task_scope='a', context_sha256=workflow.decision_basis(self.task))
        self.add('tree-transfer', 'transfer', ['c'], task_scope='a', depends_on=['tree-decision'])
        self.task['transfers'] = ['tree-transfer']
        self.assertTrue(self.compile()['ready_for_handoff'])
        (directory / 'b').write_text('b')
        self.assertFalse(self.compile()['ready_for_handoff'])
        with self.assertRaises(ValueError):
            workflow.fingerprint(self.root, ['../outside'])

    def test_correction_is_scoped_injected_and_requires_receipt(self):
        self.add('checked', 'check', ['t'], outcome='failed')
        self.add('lesson', 'lesson', ['checked'], targets=['c'], applies_to={'scopes': ['a'], 'tags': ['x']})
        packet = self.compile()
        self.assertEqual(len(packet['corrections']), 1)
        self.assertFalse(packet['ready_for_handoff'])
        self.add('t2', 'transfer', ['c'], task_scope='a', depends_on=['d', 'lesson'],
                 correction_applications={'lesson': dict(operation='producing boundary', change='scoped repair', check='discriminating check', limits='not demonstrated')})
        self.task['transfers'] = ['t2']
        packet = self.compile()
        self.assertTrue(packet['ready_for_handoff'])
        self.assertEqual(packet['corrections'][0]['received_by_transfers'], ['t2'])
        self.assertEqual(packet['corrections'][0]['demonstrated'], 'not established')
        self.task['tags'] = ['y']
        self.assertEqual(self.compile()['corrections'], [])

    def test_lesson_receipt_without_operation_change_is_blocked(self):
        self.add('trigger', 'check', ['t'], outcome='failed')
        self.add('lesson', 'lesson', ['trigger'], targets=['c'], applies_to={'scopes': ['a']})
        self.add('receipt-only', 'transfer', ['c'], task_scope='a', depends_on=['d', 'lesson'])
        self.task['transfers'] = ['receipt-only']
        self.assertFalse(self.compile()['ready_for_handoff'])
        self.assertTrue(any('actionable correction' in b['reason'] for b in self.compile()['blockers']))

    def test_constraints_invalidate_adoption_and_unknown_prerequisite_is_rejected(self):
        self.task['constraints'] = ['new hard constraint']
        self.assertFalse(self.compile()['ready_for_handoff'])
        self.task['input_requests'] = [dict(id='q', decision='intent', why_user='private', consequence='different choice', wait=True, dependent_work=['build'], prerequisites=['typo'])]
        with self.assertRaises(ValueError):
            workflow.task_spec(self.task)

    def test_input_wait_and_reuse_do_not_fabricate_authorization(self):
        request = dict(id='q', decision='choose intent', why_user='private preference', consequence='different output',
                       wait=True, dependent_work=['t'], independent_work=['inspect'], category='preference', reversible=True)
        self.task['input_requests'] = [request]
        self.assertFalse(self.compile()['ready_for_handoff'])
        self.assertEqual(workflow.input_status(self.task)['blocked_work'], ['t'])
        request['intent_inference'] = dict(interpretation='reuse intent', past_response='declared prior response',
                                         source='private message id', original_scope='a', current_fit='same cue',
                                         changed_conditions='none observed', revisit='changed audience')
        self.assertTrue(self.compile()['ready_for_handoff'])
        self.assertEqual(workflow.input_status(self.task)['answered'], [])
        request['category'] = 'authorization'
        with self.assertRaises(ValueError):
            workflow.task_spec(self.task)

    def test_question_frontier_defers_dependent_questions(self):
        def question(identifier, prerequisites):
            return dict(id=identifier, decision='private preference', why_user='user judgment',
                        consequence='different result', wait=True, dependent_work=['build'],
                        prerequisites=prerequisites)
        self.task['input_requests'] = [question('first', ['fact']), question('second', ['first'])]
        self.task['prerequisite_facts'] = [dict(id='fact', evidence='pending inspection', next_action='inspect project')]
        self.assertEqual(workflow.input_status(self.task)['question_batch'], [])
        self.task['settled_prerequisites'] = ['fact']
        self.assertEqual([x['id'] for x in workflow.input_status(self.task)['question_batch']], ['first'])
        self.task['input_requests'][0].update(response='choice', response_source='user')
        self.assertEqual([x['id'] for x in workflow.input_status(self.task)['question_batch']], ['second'])

    def test_unresolved_conflict_blocks_synthesis(self):
        self.task['conflicts'] = [dict(id='conflict', issue='incompatible invariants', reason='cannot preserve both', sources=['one', 'two'], resolved=False)]
        self.assertFalse(self.compile()['ready_for_handoff'])
        self.task['conflicts'][0].update(resolved=True, resolution='scoped choice')
        self.add('resolved-decision', 'decision', ['c'], task_scope='a', context_sha256=workflow.decision_basis(self.task))
        self.add('resolved-transfer', 'transfer', ['c'], task_scope='a', depends_on=['resolved-decision'])
        self.task['transfers'] = ['resolved-transfer']
        self.assertTrue(self.compile()['ready_for_handoff'])

    def test_changed_contract_and_new_decision_require_new_transfer(self):
        self.task['goal'] = 'changed outcome'
        self.assertFalse(self.compile()['ready_for_handoff'])
        self.add('d2', 'decision', ['c'], task_scope='a', context_sha256=workflow.decision_basis(self.task))
        self.assertFalse(self.compile()['ready_for_handoff'])
        self.add('t2', 'transfer', ['c'], task_scope='a', depends_on=['d2'])
        self.task['transfers'] = ['t2']
        self.assertTrue(self.compile()['ready_for_handoff'])

    def test_failure_review_reaches_repair_packet_without_claiming_execution(self):
        self.assertIsNone(workflow.investigate(self.task, workflow.catalog())['failure_review'])
        records, _ = rdd.read_records(self.store, verify_files=False)
        packet = workflow.compile_context(workflow.task_spec(self.task), records, self.store, purpose='repair')
        review = packet['failure_review']
        self.assertEqual(review['goal'], self.task['goal'])
        self.assertEqual(review['journey'], self.task['journey'])
        self.assertEqual(review['access'], self.task['access'])
        self.assertTrue((SCRIPTS.parent / review['module']).is_file())
        self.assertIn('no tools ran', review['limits'])
        self.task['surface'] = 'document'
        self.task['tags'] = ['reliability']
        self.assertIsNotNone(workflow.investigate(self.task, workflow.catalog())['failure_review'])
        self.task['tags'] = []
        self.task['operation'] = 'repair'
        self.assertIsNotNone(workflow.investigate(self.task, workflow.catalog())['failure_review'])

    def test_catalog_candidates_preserve_limits_and_unavailable_methods(self):
        methods = workflow.catalog()
        self.task['unknowns'] = [dict(id='unknown', property='hidden-state', alternatives=['one', 'two'], next_evidence='discriminating cue', stop='bounded observation')]
        result = workflow.investigate(self.task, methods)
        self.assertTrue(result['investigation'][0]['unavailable'])
        self.assertNotIn('active-state-learning', [m['id'] for m in result['investigation'][0]['candidates']])
        self.task['capabilities'] = ['reset', 'control', 'capture']
        result = workflow.investigate(self.task, methods)
        self.assertIn('active-state-learning', [m['id'] for m in result['investigation'][0]['candidates']])
        self.assertTrue(all(m['limit'] and m['delta'] for m in result['investigation'][0]['candidates']))

    def test_assessment_requires_property_mapping_and_observed_check_evidence(self):
        self.task['competence'] = [dict(property='declared property', authority='e', preserve='retain', adapt='none', check='observe', transfers=['t'])]
        self.add('assess-decision', 'decision', ['c'], task_scope='a', context_sha256=workflow.decision_basis(self.task))
        self.add('assess-transfer', 'transfer', ['c'], task_scope='a', depends_on=['assess-decision'])
        self.task['transfers'] = ['assess-transfer']
        self.task['competence'][0]['transfers'] = ['assess-transfer']
        def result():
            records, _ = rdd.read_records(self.store, verify_files=False)
            return workflow.assess(self.task, records, self.store)
        self.assertFalse(result()['ready_for_review'])
        self.add('capture', 'evidence', ['r'], local_path='input.txt')
        self.add('observed-check', 'check', ['assess-transfer', 'capture'], outcome='passed', artifact_inputs=workflow.fingerprint(self.root, ['input.txt']))
        self.assertTrue(result()['ready_for_review'])
        (self.root / 'input.txt').write_text('changed')
        self.assertFalse(result()['ready_for_review'])

    def test_repair_packet_retains_failure_and_requires_rerun_without_waiving_other_blocks(self):
        self.add('failed-check', 'check', ['t'], outcome='failed')
        records, _ = rdd.read_records(self.store, verify_files=False)
        packet = workflow.compile_context(self.task, records, self.store, purpose='repair')
        self.assertTrue(packet['ready_for_handoff'])
        self.assertEqual(packet['required_reruns'][0]['failed_check'], 'failed-check')
        self.assertIn('failed-check', [r['id'] for r in packet['records']])
        self.assertFalse(workflow.compile_context(self.task, records, self.store)['ready_for_handoff'])
        task_path = self.root / 'task.json'
        task_path.write_text(json.dumps(self.task))
        cli = subprocess.run([sys.executable, str(SCRIPTS / 'workflow.py'), 'compile', str(self.store), '--task', str(task_path), '--purpose', 'repair'], capture_output=True, text=True)
        self.assertEqual(cli.returncode, 0, cli.stderr)
        self.assertEqual(json.loads(cli.stdout)['purpose'], 'repair')
        self.task['access'] = 'strict-clean-room'
        self.assertFalse(workflow.compile_context(self.task, records, self.store, purpose='repair')['ready_for_handoff'])
        self.task['access'] = 'source-assisted'
        (self.root / 'input.txt').write_text('changed')
        self.assertFalse(workflow.compile_context(self.task, records, self.store, purpose='repair')['ready_for_handoff'])

    def test_strict_assessment_separates_property_review_from_captured_access_receipt(self):
        self.task['access'] = 'strict-clean-room'
        self.task['competence'] = [dict(property='declared property', authority='e', preserve='retain', adapt='none', check='observe', transfers=['strict-transfer'])]
        self.add('strict-decision', 'decision', ['c'], task_scope='a', context_sha256=workflow.decision_basis(self.task))
        self.add('strict-transfer', 'transfer', ['c'], task_scope='a', depends_on=['strict-decision'])
        self.task['transfers'] = ['strict-transfer']
        self.add('capture', 'evidence', ['r'], local_path='input.txt')
        self.add('strict-check', 'check', ['strict-transfer', 'capture'], outcome='passed', artifact_inputs=workflow.fingerprint(self.root, ['input.txt']))
        def result():
            records, _ = rdd.read_records(self.store, verify_files=False)
            return workflow.assess(self.task, records, self.store)
        self.assertTrue(result()['ready_for_property_review'])
        self.assertFalse(result()['ready_for_review'])
        self.assertTrue(result()['access_review']['gaps'])
        spec = {k: self.task[k] for k in ('scope', 'goal', 'audience', 'journey')}
        spec.update(behaviors=['observable response'], unknowns=[], acceptance=['declared condition'],
                    review=dict(reviewer='reviewer', implementation_independent=True, source_free=True, asset_rights=True, limits='semantic review declaration'))
        (self.root / 'spec.json').write_text(json.dumps(spec))
        output = self.root / 'worker-output'
        output.mkdir()
        (output / 'artifact.txt').write_text('synthetic fixture')
        image = 'sha256:' + 'a' * 64
        import hashlib
        receipt = dict(image=image, specification_sha256=hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest(), boundary_probes_passed=True,
                       worker_executed=True, worker_exit=0, output_directory='worker-output',
                       output_inventory=[dict(path='artifact.txt', sha256=rdd.digest(output / 'artifact.txt'))])
        (self.root / 'receipt.json').write_text(json.dumps(receipt))
        self.add('spec-capture', 'evidence', ['r'], local_path='spec.json')
        self.add('receipt-capture', 'evidence', ['r'], local_path='receipt.json')
        review = dict(reviewed=True, reviewer='reviewer', declaration='inspected supplied boundary', limits='mechanical only')
        self.task['clean_room'] = dict(specification_evidence='spec-capture', receipt_evidence='receipt-capture',
                                       image_review=dict(review, image=image), worker_review=review, output_directory=str(output))
        self.assertTrue(result()['ready_for_review'])
        self.assertFalse(self.compile()['ready_for_handoff'])
        self.task['clean_room']['image_review']['image'] = 'sha256:' + 'b' * 64
        self.assertFalse(result()['ready_for_review'])
        self.task['clean_room']['image_review']['image'] = image
        (output / 'artifact.txt').write_text('changed')
        self.assertFalse(result()['ready_for_review'])
        self.assertTrue(any('inventory' in gap for gap in result()['access_review']['gaps']))

    def test_seed_is_idempotent_and_does_not_adopt(self):
        methods = workflow.catalog()
        added = workflow.seed(self.store, methods)['added']
        self.assertEqual(added, len(methods['methods']) * 3)
        self.assertEqual(workflow.seed(self.store, methods)['added'], 0)
        records, _ = rdd.read_records(self.store)
        self.assertEqual(len([r for r in records if r['kind'] == 'decision']), 1)

    def test_strict_packet_is_blocked_and_export_never_claims_isolation(self):
        self.task['access'] = 'strict-clean-room'
        self.assertFalse(self.compile()['ready_for_handoff'])
        spec = {k: self.task[k] for k in ('scope', 'goal', 'audience', 'journey')}
        spec.update(behaviors=['observable response'], unknowns=[], acceptance=['declared condition'],
                    review=dict(reviewer='declared reviewer', implementation_independent=True, source_free=True, asset_rights=True, limits='manual review required'))
        self.assertFalse(workflow.review_export(spec)['isolation_verified'])
        spec['behaviors'] = ['see https://source.example']
        with self.assertRaises(ValueError):
            workflow.review_export(spec)

    def test_cli_emits_blocked_packet_with_distinct_exit_code(self):
        path = self.root / 'task.json'
        self.task['transfers'] = []
        path.write_text(json.dumps(self.task))
        result = subprocess.run([sys.executable, str(SCRIPTS / 'workflow.py'), 'compile', str(self.store), '--task', str(path)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(json.loads(result.stdout)['ready_for_handoff'])


if __name__ == '__main__':
    unittest.main()
