import copy
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts'))
from project_controls import STATE, doctor, generate, inspect_project, run_controls


FIXTURE = '''import json, os, pathlib, sys, time
root = pathlib.Path(os.environ['RDD_CONTROL_PROJECT'])
state = pathlib.Path(os.environ['RDD_CONTROL_STATE'])
owner = os.environ['RDD_CONTROL_OWNER']
runtime = state / 'runtime'
runtime.mkdir(exist_ok=True)
lease = runtime / 'owner'
data = runtime / 'saved.json'
action = sys.argv[1]
if action == 'launch':
    if lease.exists() and lease.read_text() != owner:
        raise SystemExit(9)
    lease.write_text(owner)
    if not data.exists(): data.write_text('{"value":0}')
elif action == 'doctor':
    assert lease.exists() and lease.read_text() == owner
    assert not (runtime / 'wedged').exists()
elif action == 'drive':
    assert lease.read_text() == owner
    if (runtime / 'wedged').exists(): raise SystemExit(3)
    data.write_text(json.dumps({'value': json.loads(data.read_text())['value'] + 1}))
elif action == 'observe':
    assert json.loads(data.read_text())['value'] >= 1
    print(data.read_text())
elif action == 'reset':
    assert lease.exists() and lease.read_text() == owner
    (runtime / 'wedged').unlink(missing_ok=True)
elif action == 'cleanup':
    if lease.exists() and lease.read_text() == owner: lease.unlink()
elif action == 'timeout':
    data.write_text('{"value":7}')
    time.sleep(5)
elif action == 'confirm-reset':
    assert not lease.exists()
    assert not (runtime / 'wedged').exists()
    assert json.loads(data.read_text())['value'] == 7
    print('owned runtime stopped; saved value 7 retained')
elif action == 'fail':
    raise SystemExit(4)
elif action == 'mutate':
    (root / 'src' / 'product.txt').write_text('changed')
elif action == 'wedged':
    assert lease.read_text() == owner
    (runtime / 'wedged').write_text('wedged')
    raise SystemExit(3)
'''


class ProjectControlsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / 'src').mkdir()
        (self.root / 'src' / 'control.py').write_text(FIXTURE)
        (self.root / 'src' / 'product.txt').write_text('original')
        (self.root / 'src' / 'valid.json').write_text('{}')
        (self.root / 'src' / 'invalid.json').write_text('{')

    def control(self, identifier, role, effect='runtime-state', action=None, classes=None):
        value = {'id': identifier, 'argv': [sys.executable, 'src/control.py', action or identifier],
                 'cwd': '.', 'timeout_seconds': 2, 'role': role, 'effect': effect,
                 'classes': classes or ['maintenance', 'fix']}
        if effect == 'read-only':
            value['classes'] = classes or ['maintenance', 'fix', 'forensics']
        if role in ('reset', 'cleanup'):
            value['ownership'] = 'current-run-only'
        return value

    def blueprint(self):
        controls = [self.control('launch', 'launch'), self.control('doctor', 'doctor', 'read-only'),
                    self.control('drive', 'drive'), self.control('observe', 'observe', 'read-only'),
                    self.control('reset', 'reset'), self.control('cleanup', 'cleanup')]
        return {'source_roots': ['src'],
                'readiness': {'driver': 'declared', 'oracle': 'declared', 'gaps': []},
                'controls': controls,
                'features': [{'id': 'persist', 'entry': 'launch from generated command; drive then observe',
                              'default_state': 'value zero on first start; retained value on reopen',
                              'prerequisites': ['writable project-owned runtime'],
                              'state_observation': 'observe reads saved JSON after drive',
                              'expected_effect': 'drive increments retained value exactly once',
                              'oracle_scope': 'authored fixture only; independent acceptance not established',
                              'route': ['launch', 'doctor', 'drive', 'observe'],
                              'reset_control': 'reset', 'cleanup_control': 'cleanup'}],
                'development_profile': {
                    'kind': 'code', 'feature_roots': {'persist': ['src']},
                    'allowed_imports': {'persist': []},
                    'shared_invariants': [{'id': 'saved-schema', 'kind': 'schema', 'owner': 'project',
                                           'consumers': ['persist'], 'sources': ['src/product.txt'],
                                           'validator_controls': ['observe']}],
                    'diagnostics': [{'control': 'doctor', 'positive_fixture': 'src/invalid.json',
                                     'negative_fixture': 'src/valid.json', 'suppressions': []}],
                    'preview': {'control': 'observe', 'entry': 'local saved state observer',
                                'build_ref': 'source inventory', 'environment': 'isolated fixture',
                                'access': 'local project owner'}}}

    def manifest(self, blueprint=None):
        return generate(self.root, blueprint or self.blueprint())

    def test_inspection_and_missing_driver_bootstrap_stay_explicit(self):
        facts = inspect_project(self.root, ['src'])
        self.assertEqual(facts['commands_inferred'], 0)
        self.assertEqual(facts['driver'], 'missing')
        manifest = generate(self.root)
        report = doctor(self.root, manifest)
        self.assertTrue(report['fresh'])
        self.assertFalse(report['ready_for_declared_route'])
        self.assertFalse(report['oracle_verified'])
        self.assertIn('independent project oracle missing', report['gaps'])

    def test_complete_cold_consumer_uses_only_generated_output_and_project(self):
        self.manifest()
        path = self.root / STATE / 'manifest.json'
        # A fresh process has only the generated output and project; no imported
        # Python object, builder account, or prior in-memory fixture handles.
        consumer = '''import json, subprocess, sys
from pathlib import Path
m = json.loads(Path(sys.argv[1]).read_text())
base = m['control_entry']
args = ['--root', m['project_root'], '--manifest', m['manifest_path']]
subprocess.run(base + ['doctor'] + args, check=True, stdout=subprocess.PIPE)
for feature in m['features']:
    out = subprocess.run(base + ['run'] + args + ['--feature', feature['id']],
                         check=True, capture_output=True, text=True)
    print(out.stdout)
'''
        result = subprocess.run([sys.executable, '-c', consumer, str(path)], capture_output=True,
                                text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['status'], 'clean')
        self.assertFalse(receipt['oracle_verified'])
        runtime = self.root / STATE / 'runtime'
        self.assertEqual(json.loads((runtime / 'saved.json').read_text())['value'], 1)
        self.assertFalse((runtime / 'owner').exists())
        self.assertTrue(Path(receipt['evidence_path']).exists())
        self.assertTrue(doctor(self.root, json.loads(path.read_text()))['ready_for_declared_route'])

    def test_reopen_retains_state_and_cleanup_preserves_shared_unowned_service(self):
        manifest = self.manifest()
        shared = self.root / STATE / 'shared-service'
        shared.write_text('external owner; must survive')
        for _ in range(2):
            self.assertEqual(run_controls(self.root, manifest, feature_id='persist')['status'], 'clean')
        self.assertEqual(json.loads((self.root / STATE / 'runtime/saved.json').read_text())['value'], 2)
        self.assertEqual(shared.read_text(), 'external owner; must survive')

    def test_source_churn_additions_deletions_and_changes_block_dispatch(self):
        for operation in ('added', 'deleted', 'changed'):
            with self.subTest(operation=operation):
                manifest = self.manifest() if operation == 'added' else json.loads((self.root / STATE / 'manifest.json').read_text())
                path = self.root / 'src' / 'product.txt'
                if operation == 'added':
                    (self.root / 'src' / 'new-entry.txt').write_text('new UI entry')
                elif operation == 'deleted':
                    path.unlink()
                else:
                    path.write_text('changed default state')
                receipt = run_controls(self.root, manifest, feature_id='persist')
                self.assertEqual(receipt['status'], 'blocked')
                self.assertEqual(receipt['effect_state'], 'not-dispatched')
                self.assertEqual(receipt['results'], [])

    def test_missing_cwd_and_diagnostic_fixture_are_named(self):
        manifest = self.manifest()
        manifest['controls'][0]['cwd'] = 'missing'
        (self.root / 'src/valid.json').unlink()
        kinds = {p['kind'] for p in doctor(self.root, manifest)['problems']}
        self.assertIn('control-cwd-unavailable', kinds)
        self.assertIn('diagnostic-fixture-unavailable', kinds)

    def test_failed_control_keeps_evidence_reset_cleanup_and_unknown_effects(self):
        blueprint = self.blueprint()
        blueprint['controls'].append(self.control('fail', 'drive'))
        blueprint['features'][0]['route'] = ['launch', 'fail', 'observe']
        manifest = self.manifest(blueprint)
        receipt = run_controls(self.root, manifest, feature_id='persist')
        self.assertEqual(receipt['status'], 'blocked')
        self.assertEqual(receipt['effect_state'], 'unknown')
        self.assertEqual([r['control'] for r in receipt['results']], ['launch', 'fail'])
        self.assertTrue(receipt['reset_results'][0]['passed'])
        self.assertTrue(receipt['cleanup_results'][0]['passed'])
        self.assertIn(receipt['intent_attempt_id'], doctor(self.root, manifest)['unreconciled_attempts'])
        repeated = run_controls(self.root, manifest, feature_id='persist')
        self.assertEqual(repeated['reason'], 'prior_effects_unknown_requires_target_reconciliation')
        self.assertEqual(repeated['results'], [])

    def test_timeout_does_not_erase_commit_or_blindly_replay(self):
        blueprint = self.blueprint()
        control = self.control('timeout', 'drive')
        control['timeout_seconds'] = .15
        observer = self.control('confirm-reset', 'observe', 'read-only')
        observer.update(reconciliation_outcome='observed-reset',
                        reconciliation_scope='owned runtime stopped; durable value 7 retained')
        blueprint['controls'].extend([control, observer])
        blueprint['features'][0]['route'] = ['launch', 'timeout', 'observe']
        manifest = self.manifest(blueprint)
        receipt = run_controls(self.root, manifest, feature_id='persist')
        self.assertEqual(receipt['results'][1]['status'], 'timeout')
        self.assertEqual(json.loads((self.root / STATE / 'runtime/saved.json').read_text())['value'], 7)
        self.assertEqual(receipt['effect_state'], 'unknown')
        observed = run_controls(self.root, manifest, control_id='confirm-reset',
                                reconcile_attempt_id=receipt['intent_attempt_id'])
        self.assertEqual(observed['reconciliation_outcome'], 'observed-reset')
        self.assertEqual(doctor(self.root, manifest)['unreconciled_attempts'], [])
        self.assertFalse(observed['oracle_verified'])

    def test_wedged_state_recovery_is_observed_without_repeating_failed_action(self):
        blueprint = self.blueprint()
        blueprint['controls'].append(self.control('wedged', 'drive'))
        blueprint['features'][0]['route'] = ['launch', 'wedged', 'observe']
        receipt = run_controls(self.root, self.manifest(blueprint), feature_id='persist')
        self.assertEqual(receipt['status'], 'blocked')
        self.assertFalse((self.root / STATE / 'runtime/wedged').exists())
        self.assertFalse((self.root / STATE / 'runtime/owner').exists())
        self.assertEqual(len(receipt['results']), 2)
        self.assertTrue(receipt['after_reset_doctor']['fresh'])

    def test_live_owner_lock_blocks_parallel_mutating_route(self):
        manifest = self.manifest()
        with (self.root / STATE / 'live-owner.lock').open('a+') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, 'another live'):
                run_controls(self.root, manifest, feature_id='persist')

    def test_class_authority_and_product_drift_do_not_rewrite_expectations(self):
        blueprint = self.blueprint()
        blueprint['controls'].append(self.control('fix', 'drive', 'product-mutation', 'mutate', ['fix']))
        manifest = self.manifest(blueprint)
        with self.assertRaisesRegex(ValueError, 'lacks authority'):
            run_controls(self.root, manifest, control_id='fix')
        with self.assertRaisesRegex(ValueError, 'lacks authority'):
            run_controls(self.root, manifest, feature_id='persist', task_class='forensics')
        original = copy.deepcopy(manifest['source_inventory'])
        receipt = run_controls(self.root, manifest, control_id='fix', task_class='fix')
        self.assertEqual(receipt['status'], 'changed')
        self.assertEqual(manifest['source_inventory'], original)
        self.assertFalse(doctor(self.root, manifest)['fresh'])

    def test_misdeclared_maintenance_product_mutation_is_blocked_after_observation(self):
        blueprint = self.blueprint()
        blueprint['controls'].append(self.control('bad', 'drive', 'runtime-state', 'mutate'))
        manifest = self.manifest(blueprint)
        receipt = run_controls(self.root, manifest, control_id='bad')
        self.assertEqual(receipt['status'], 'blocked')
        self.assertEqual(receipt['reason'], 'product_changed_requires_review_and_fresh_controls')
        # This helper detects declared-source drift after execution; it does not
        # pretend to sandbox or undo a malicious/misdeclared command.
        self.assertEqual((self.root / 'src/product.txt').read_text(), 'changed')

    def test_path_boundaries_root_identity_and_symlink_rejection(self):
        blueprint = self.blueprint()
        for cwd in ('..', '/tmp'):
            bad = copy.deepcopy(blueprint)
            bad['controls'][0]['cwd'] = cwd
            with self.assertRaises(ValueError):
                generate(self.root, bad)
        (self.root / 'src/link').symlink_to('/tmp')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            inspect_project(self.root, ['src'])
        (self.root / 'src/link').unlink()
        manifest = self.manifest()
        with tempfile.TemporaryDirectory() as other:
            with self.assertRaisesRegex(ValueError, 'exact project root'):
                doctor(other, manifest)

    def test_generation_does_not_replace_existing_files_or_run_commands(self):
        manifest = self.manifest()
        self.assertFalse((self.root / STATE / 'runtime').exists())
        with self.assertRaises(FileExistsError):
            generate(self.root, self.blueprint())
        with self.assertRaisesRegex(ValueError, 'generation'):
            run_controls(self.root, manifest, feature_id='persist', task_class='generation')
        with self.assertRaisesRegex(ValueError, 'project-owned'):
            generate(self.root, self.blueprint(), 'src/generated.json')

    def test_unknown_control_missing_recovery_ownership_and_false_oracle_status(self):
        blueprint = self.blueprint()
        del blueprint['controls'][-1]['ownership']
        with self.assertRaisesRegex(ValueError, 'current-run-only'):
            generate(self.root, blueprint)
        blueprint = self.blueprint()
        blueprint['readiness']['oracle'] = 'missing'
        manifest = self.manifest(blueprint)
        with self.assertRaises(ValueError):
            run_controls(self.root, manifest, control_id='not-declared')
        receipt = run_controls(self.root, manifest, feature_id='persist')
        self.assertEqual(receipt['status'], 'clean')
        self.assertIn('acceptance_gap', receipt)
        self.assertFalse(receipt['oracle_verified'])

    def test_unfinished_intent_survives_process_loss(self):
        manifest = self.manifest()
        (self.root / STATE / 'lost.json').write_text(json.dumps({'status': 'admitted', 'attempt_id': 'lost'}))
        receipt = run_controls(self.root, manifest, feature_id='persist')
        self.assertEqual(receipt['reason'], 'prior_effects_unknown_requires_target_reconciliation')
        self.assertEqual(receipt['results'], [])

    def test_shared_change_invalidates_inverse_consumers_without_forcing_local_helper_sharing(self):
        blueprint = self.blueprint()
        second = copy.deepcopy(blueprint['features'][0])
        second['id'] = 'export'
        blueprint['features'].append(second)
        profile = blueprint['development_profile']
        profile['feature_roots']['export'] = ['export']
        profile['allowed_imports']['export'] = ['persist']
        profile['shared_invariants'][0]['consumers'] = ['persist', 'export']
        (self.root / 'export').mkdir()
        # A feature-local helper may be duplicated. The profile does not mandate
        # sharing it, while shared schema changes name both consumers explicitly.
        (self.root / 'src/local-helper.py').write_text('def caption(): return "value"\n')
        (self.root / 'export/local-helper.py').write_text('def caption(): return "value"\n')
        blueprint['source_roots'].append('export')
        manifest = self.manifest(blueprint)
        self.assertTrue(doctor(self.root, manifest)['fresh'])
        (self.root / 'src/product.txt').write_text('changed shared schema')
        impact = doctor(self.root, manifest)['declared_impact']
        self.assertEqual(impact['shared_invariant_ids'], ['saved-schema'])
        self.assertEqual(impact['feature_ids'], ['export', 'persist'])

    def test_unmapped_change_conservatively_invalidates_all_features(self):
        blueprint = self.blueprint()
        (self.root / 'configuration').mkdir()
        (self.root / 'configuration/runtime.json').write_text('{}')
        blueprint['source_roots'].append('configuration')
        manifest = self.manifest(blueprint)
        (self.root / 'configuration/runtime.json').write_text('{"different":true}')
        impact = doctor(self.root, manifest)['declared_impact']
        self.assertEqual(impact['unknown_impact_paths'], ['configuration/runtime.json'])
        self.assertEqual(impact['feature_ids'], ['persist'])

    def test_corrupt_evidence_cannot_disappear_into_safe_retry(self):
        manifest = self.manifest()
        (self.root / STATE / 'lost.json').write_text('{')
        report = doctor(self.root, manifest)
        self.assertFalse(report['fresh'])
        self.assertIn('control-evidence-unreadable', [p['kind'] for p in report['problems']])
        receipt = run_controls(self.root, manifest, feature_id='persist')
        self.assertEqual(receipt['effect_state'], 'not-dispatched')
        self.assertEqual(receipt['results'], [])

    def test_missing_executable_is_pre_dispatch_failure_not_unknown_committed_action(self):
        blueprint = self.blueprint()
        missing = self.control('missing-executable', 'observe', 'read-only')
        missing['argv'] = [str(self.root / 'does-not-exist')]
        blueprint['controls'].append(missing)
        manifest = self.manifest(blueprint)
        receipt = run_controls(self.root, manifest, control_id='missing-executable')
        self.assertEqual(receipt['status'], 'blocked')
        self.assertEqual(receipt['results'][0]['status'], 'launch-failed')
        self.assertEqual(receipt['effect_state'], 'not-dispatched')
        self.assertEqual(doctor(self.root, manifest)['unreconciled_attempts'], [])


if __name__ == '__main__':
    unittest.main()
