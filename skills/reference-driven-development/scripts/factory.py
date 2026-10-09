#!/usr/bin/env python3
"""Owned factory operations over the existing RDD evidence journal.

Native hosts retain conversation, permissions and models. File locks serialize only
callers using this helper. External/native bypasses and target commits are not
fenced. Acceptance checks evidence bindings and caller-declared independence; it
cannot manufacture a domain oracle or establish semantic truth.
"""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

import rdd
import workflow

VERSION = '1'
LIMITS = ('Owned helper admission/delivery only; external writes are not fenced. '
          'Native permissions, model selection and semantic acceptance remain native-owned.')
UNITS = {'episodes', 'operations', 'requests', 'tokens', 'cash_usd', 'wall_seconds'}


class FactoryError(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))


def hash_value(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require(value, keys, label):
    if not isinstance(value, dict):
        raise FactoryError(f'{label} must be an object')
    for key in keys:
        item = value.get(key)
        if item is None or item == '' or item == [] or item == {}:
            raise FactoryError(f'{label} needs {key}')
    return value


def string(value, label):
    if not isinstance(value, str) or not value.strip():
        raise FactoryError(f'{label} must be a nonempty string')
    return value


def amounts(value):
    if not isinstance(value, dict) or not value or set(value) - UNITS:
        raise FactoryError('amounts need known explicit units')
    for key, number in value.items():
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or number < 0:
            raise FactoryError(f'{key} needs a finite nonnegative quantity')
        if key in {'episodes', 'operations', 'requests', 'tokens'} and int(number) != number:
            raise FactoryError(f'{key} must be an integer')
    return value


def copy_json(value):
    return json.loads(canonical(value))


class Factory:
    def __init__(self, store, resource_registry=None):
        self.store = Path(store).expanduser().resolve()
        self.materials = self.store.parent / '.factory-materials'
        # Disposable lookup/index pointers, never a second task/status authority.
        # Missing journal/receipt is unknown and blocks overlapping admission.
        self.resource_registry = Path(resource_registry or Path.home() / '.local/state/it-already-exists/factory-resource-owners').expanduser().resolve()

    @contextmanager
    def gate(self):
        self.store.parent.mkdir(parents=True, exist_ok=True)
        # Stable lock inode is never removed by this helper.
        with self.store.with_name(self.store.name + '.factory.lock').open('a+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    @contextmanager
    def resource_gates(self, paths):
        """Cross-journal exclusion for owned local paths, never a global scheduler.

        The short global gate serializes publishing/scanning ownership pointers;
        running tasks remain concurrent when their canonical write sets do not
        overlap. Parent/child conflicts persist through unresolved lifecycle.
        No inference is made about unowned writers or another configured index.
        """
        self.resource_registry.mkdir(mode=0o700, parents=True, exist_ok=True)
        with (self.resource_registry / 'admission.lock').open('a+b') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def publish_resource_claim(self, root, operation_ref, paths):
        claim = {'store': str(self.store), 'root_task_id': root, 'operation_ref': operation_ref,
                 'canonical_write_set': paths, 'authority': 'referenced journal operation; this file is only a lookup pointer'}
        target = self.resource_registry / (hash_value([str(self.store), operation_ref]) + '.json')
        with tempfile.NamedTemporaryFile(dir=self.resource_registry, mode='w', delete=False) as stream:
            temporary = Path(stream.name)
            try:
                stream.write(canonical(claim))
                stream.flush()
                os.fsync(stream.fileno())
                os.replace(temporary, target)
                directory = os.open(self.resource_registry, os.O_RDONLY)
                try:
                    os.fsync(directory)
                finally:
                    os.close(directory)
            finally:
                if temporary.exists():
                    temporary.unlink()

    def unresolved_resource_claims(self, paths):
        conflicts = []
        for path in self.resource_registry.glob('*.json'):
            try:
                claim = workflow.load(path)
                if not self.overlaps(paths, claim['canonical_write_set']):
                    continue
                source = Factory(claim['store'], self.resource_registry)
                operation = source.operations(claim['root_task_id']).get(claim['operation_ref'])
                if operation is None or operation['producer_lifecycle'] not in {'stopped', 'not_started'} or operation['descendant_lifecycle'] not in {'none_confirmed', 'stopped_confirmed'} or operation['target_effects'] not in {'no_effect_confirmed', 'committed', 'not_dispatched'}:
                    conflicts.append(claim)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                # A corrupt index is not proof of absent ownership. This fails
                # conservatively; the journal remains the recovery authority.
                conflicts.append({'claim_path': str(path), 'reason': f'owner evidence unavailable: {exc}'})
        return conflicts

    def records(self):
        return rdd.read_records(self.store, allow_missing=True, verify_files=False)[0]

    def events(self, root=None):
        return [r for r in self.records() if r['kind'] == 'factory_event' and
                (root is None or r['data']['root_task_id'] == root)]

    def append(self, root, event, payload, identifier=None):
        value = {'id': identifier or 'factory-' + uuid.uuid4().hex, 'kind': 'factory_event',
                 'data': {'root_task_id': string(root, 'root_task_id'), 'event': event,
                          'payload': copy_json(payload), 'recorded_at': datetime.now(timezone.utc).isoformat(),
                          'runtime_version': VERSION}}
        return rdd.append(self.store, value, allow_drift=True)

    def state(self, root):
        events = self.events(root)
        objectives = [e for e in events if e['data']['event'] == 'native_input']
        if not objectives:
            raise FactoryError(f'unknown root task: {root}')
        return objectives[-1], events

    @staticmethod
    def payload(event):
        return event['data']['payload']

    def find(self, identifier, event=None):
        matches = [r for r in self.events() if r['id'] == identifier and
                   (event is None or r['data']['event'] == event)]
        if not matches:
            raise FactoryError(f'unknown {event or "event"}: {identifier}')
        return matches[0]

    def capture_material(self, item):
        require(item, ('path',), 'material')
        source = Path(item['path']).expanduser().resolve()
        result = {'original_path': str(source), 'required': item.get('required', True),
                  'role': item.get('role', 'evidence')}
        if type(result['required']) is not bool:
            raise FactoryError('material required must be boolean')
        try:
            actual = rdd.digest(source)
            if item.get('sha256') and item['sha256'] != actual:
                raise FactoryError(f'material hash mismatch: {source}')
            self.materials.mkdir(parents=True, exist_ok=True)
            destination = self.materials / actual
            if not destination.exists():
                with tempfile.NamedTemporaryFile(dir=self.materials, delete=False) as temporary:
                    temp_path = Path(temporary.name)
                    try:
                        with source.open('rb') as reader:
                            for chunk in iter(lambda: reader.read(1024 * 1024), b''):
                                temporary.write(chunk)
                        temporary.flush()
                        os.fsync(temporary.fileno())
                        if rdd.digest(temp_path) != actual:
                            raise FactoryError('source changed during capture')
                        os.replace(temp_path, destination)
                        directory = os.open(self.materials, os.O_RDONLY)
                        try:
                            os.fsync(directory)
                        finally:
                            os.close(directory)
                    finally:
                        if temp_path.exists():
                            temp_path.unlink()
            if rdd.digest(destination) != actual:
                raise FactoryError('captured material drift')
            result.update(local_path=destination.relative_to(self.store.parent).as_posix(), sha256=actual,
                          reader='immutable local content-addressed file; retained until explicit owner cleanup')
        except OSError as exc:
            result['missing'] = str(exc)
        return result

    def material_gaps(self, materials):
        gaps = []
        for material in materials:
            try:
                if 'local_path' not in material:
                    raise FactoryError(material.get('missing', 'no captured bytes'))
                path = workflow.safe_path(self.store.parent, material['local_path'])
                if rdd.digest(path) != material['sha256']:
                    raise FactoryError('hash drift')
            except (ValueError, OSError) as exc:
                gaps.append({'original_path': material.get('original_path'), 'required': material.get('required', True), 'reason': str(exc)})
        return gaps

    def bind_native_input(self, request):
        require(request, ('root_task_id', 'native_identity', 'full_text', 'task', 'requirements', 'authorization_scope'), 'intake')
        require(request['native_identity'], ('host', 'session', 'turn'), 'native identity')
        for key in ('host', 'session', 'turn'):
            string(request['native_identity'][key], key)
        string(request['full_text'], 'full_text')
        string(request['authorization_scope'], 'authorization_scope')
        task = workflow.task_spec(copy_json(request['task']))
        requirements = request['requirements']
        if not isinstance(requirements, list) or not requirements:
            raise FactoryError('requirements must enumerate the full task')
        keys = []
        for item in requirements:
            require(item, ('id', 'property', 'description'), 'requirement')
            keys.append((string(item['id'], 'requirement id'), string(item['property'], 'property')))
        if len(set(keys)) != len(keys):
            raise FactoryError('duplicate requirement/property')
        attachments = request.get('attachments', [])
        if not isinstance(attachments, list):
            raise FactoryError('attachments must be a list of actual files')
        with self.gate():
            existing = self.events(request['root_task_id'])
            prior = [e for e in existing if e['data']['event'] == 'native_input']
            if prior:
                old = self.payload(prior[-1])
                if request.get('expected_revision') != old['revision']:
                    raise FactoryError('correction needs exact expected_revision')
                before = {(x['id'], x['property']) for x in old['requirements']}
                if not before <= set(keys) and not request.get('authorized_scope_change'):
                    raise FactoryError('correction drops full obligations without explicit user scope-change provenance')
                if request.get('authorized_scope_change'):
                    require(request['authorized_scope_change'], ('user_response_ref', 'reason'), 'scope change')
                limits = self.root_limits(request['root_task_id'])
                if request.get('resource_limits') is not None and request['resource_limits'] != limits:
                    raise FactoryError('resume/correction cannot reset root allowance')
                original = self.payload(prior[0])['original_scope_digest']
                revision = old['revision'] + 1
            else:
                limits = amounts(request.get('resource_limits'))
                if 'operations' not in limits or 'episodes' not in limits:
                    raise FactoryError('root limits need operations and episodes ceilings')
                original = hash_value({'full_text': request['full_text'], 'requirements': requirements, 'task_scope': task['scope']})
                revision = 1
            materials = copy_json(old['attachments']) if prior else []
            removal = request.get('authorized_attachment_removal')
            if removal:
                require(removal, ('user_response_ref', 'reason', 'sha256s'), 'attachment removal')
                workflow.strings(removal['sha256s'], 'removed attachment hashes')
                if set(removal['sha256s']) - {m.get('sha256') for m in materials}:
                    raise FactoryError('attachment removal names unknown material')
                materials = [m for m in materials if m.get('sha256') not in removal['sha256s']]
            for material in [self.capture_material(x) for x in attachments]:
                if not any(m.get('sha256') == material.get('sha256') and m.get('role') == material.get('role') and m.get('original_path') == material.get('original_path') for m in materials):
                    materials.append(material)
            if not prior:
                original = hash_value({'full_text': request['full_text'], 'requirements': requirements,
                                       'task_scope': task['scope'], 'attachments': materials})
            payload = dict(native_identity=request['native_identity'], full_text=request['full_text'], task=task,
                           requirements=requirements, authorization_scope=request['authorization_scope'],
                           attachments=materials, revision=revision, acceptance_version=hash_value(requirements),
                           original_scope_digest=original, resource_limits=limits,
                           correction_ref=prior[-1]['id'] if prior else None,
                           authorized_scope_change=request.get('authorized_scope_change'),
                           authorized_attachment_removal=removal,
                           attachment_gaps=self.material_gaps(materials))
            return self.append(request['root_task_id'], 'native_input', payload)

    def root_limits(self, root):
        _, events = self.state(root)
        return self.payload(next(e for e in events if e['data']['event'] == 'native_input'))['resource_limits']

    def allocation(self, root):
        limits = self.root_limits(root)
        reservations = [e for e in self.events(root) if e['data']['event'] == 'reservation']
        settlements = {self.payload(e)['reservation_ref']: self.payload(e) for e in self.events(root)
                       if e['data']['event'] == 'settlement'}
        pending = {k: 0 for k in limits}
        observed = {k: 0 for k in limits}
        for reservation in reservations:
            settled = settlements.get(reservation['id'])
            for key, value in self.payload(reservation)['amounts'].items():
                (observed if settled else pending)[key] += settled['actual'].get(key, 0) if settled else value
        return {'limits': limits, 'reserved_pending': pending, 'observed_settled': observed,
                'headroom': {key: max(0, limits[key] - pending[key] - observed[key]) for key in limits},
                'unresolved_liability': {key: max(0, pending[key] + observed[key] - limits[key]) for key in limits},
                'pending_policy': 'reserve full ceiling until explicit settlement; resume never resets'}

    def _reserve(self, root, request):
        require(request, ('reservation_key', 'purpose', 'amounts', 'objective_revision'), 'reservation')
        quantities = amounts(request['amounts'])
        objective, events = self.state(root)
        if request['objective_revision'] != self.payload(objective)['revision']:
            raise FactoryError('stale reservation revision')
        prior = [e for e in events if e['data']['event'] == 'reservation' and
                 self.payload(e)['reservation_key'] == request['reservation_key']]
        if prior:
            if self.payload(prior[0]) != request:
                raise FactoryError('reservation key reused with different intent')
            return prior[0]
        allocation = self.allocation(root)
        if set(quantities) - set(allocation['limits']):
            raise FactoryError('reservation uses unit without root ceiling')
        if any(amount > allocation['headroom'][key] for key, amount in quantities.items()):
            raise FactoryError('root allowance exhausted; retain full obligations and stop optional work')
        if request.get('parent_reservation_ref'):
            parent = self.find(request['parent_reservation_ref'], 'reservation')
            if parent['data']['root_task_id'] != root:
                raise FactoryError('child reservation belongs to different root')
        return self.append(root, 'reservation', request)

    def reserve(self, root, request):
        with self.gate():
            return self._reserve(root, request)

    def settle(self, root, request):
        require(request, ('reservation_ref', 'actual', 'observation_ref'), 'settlement')
        reservation = self.find(request['reservation_ref'], 'reservation')
        if reservation['data']['root_task_id'] != root:
            raise FactoryError('reservation root mismatch')
        actual = amounts(request['actual'])
        if set(actual) != set(self.payload(reservation)['amounts']):
            raise FactoryError('settle every reserved unit, including zero; additional units require a new reservation')
        with self.gate():
            bound_operations = [value for value in self.operations(root).values()
                                if self.payload(value['receipt'])['reservation_ref'] == request['reservation_ref']]
            if any(value['producer_lifecycle'] not in {'not_started', 'stopped'} or
                   value['descendant_lifecycle'] not in {'none_confirmed', 'stopped_confirmed'} or
                   value['target_effects'] not in {'not_dispatched', 'no_effect_confirmed', 'committed'}
                   for value in bound_operations):
                raise FactoryError('cannot release a reservation while producer/descendant/effects are unresolved')
            bound_episodes = [e for e in self.events(root) if e['data']['event'] == 'episode_admission' and
                              self.payload(e)['reservation_ref'] == request['reservation_ref']]
            closed = {self.payload(e)['episode_ref'] for e in self.events(root) if e['data']['event'] == 'episode_closure'}
            if any(e['id'] not in closed for e in bound_episodes):
                raise FactoryError('close episode before settlement; preparation failure is an inaccessible closure')
            if actual.get('operations', 0) < len(bound_operations) or actual.get('episodes', 0) < len(bound_episodes):
                raise FactoryError('actual cannot erase an admitted operation/episode attempt')
            prior = [e for e in self.events(root) if e['data']['event'] == 'settlement' and
                     self.payload(e)['reservation_ref'] == request['reservation_ref']]
            if prior:
                if self.payload(prior[0]) != request:
                    raise FactoryError('settlement conflict')
                return prior[0]
            return self.append(root, 'settlement', request)

    def import_origin_event(self, root, request):
        require(request, ('origin_namespace', 'source_stream', 'source_event_identity', 'source_schema', 'parser_version', 'payload'), 'import')
        with self.gate():
            self.state(root)
            key = [request[k] for k in ('origin_namespace', 'source_stream', 'source_event_identity')]
            raw_hash = hash_value(request['payload'])
            prior = [e for e in self.events(root) if e['data']['event'] == 'origin_import' and self.payload(e)['origin_key'] == key]
            previous_materials = self.payload(prior[0])['referenced_materials'] if prior else []
            material_identity = []
            captures = []
            for item in request.get('referenced_materials', []):
                require(item, ('path',), 'referenced material')
                source = Path(item['path']).expanduser().resolve()
                actual_hash = rdd.digest(source) if source.is_file() else item.get('sha256')
                if actual_hash is None:
                    actual_hash = next((m.get('sha256') for m in previous_materials if m['original_path'] == str(source) and m['role'] == item.get('role', 'evidence')), None)
                if item.get('sha256') and actual_hash != item['sha256']:
                    raise FactoryError('referenced source changed from declared hash')
                material_identity.append({'path': str(source), 'sha256': actual_hash,
                                          'required': item.get('required', True), 'role': item.get('role', 'evidence')})
                captures.append({**item, **({'sha256': actual_hash} if actual_hash else {})})
            identity = hash_value({'key': key, 'payload': raw_hash, 'materials': material_identity,
                                   'schema': request['source_schema'], 'parser': request['parser_version'],
                                   'sequence': request.get('source_sequence')})
            if prior:
                old = self.payload(prior[0])
                if old['identity_digest'] != identity:
                    conflict = self.append(root, 'origin_conflict', {'origin_key': key, 'existing_ref': prior[0]['id'], 'conflicting_digest': identity})
                    return {'status': 'quarantined_identity_conflict', 'receipt': conflict, 'complete_recovery_ack': False}
                gaps = self.material_gaps(old['referenced_materials'])
                return {'status': 'duplicate', 'receipt': prior[0], 'material_gaps': gaps,
                        'complete_recovery_ack': not any(g['required'] for g in gaps)}
            sequence = request.get('source_sequence')
            if sequence is not None and (type(sequence) is not int or sequence < 1):
                raise FactoryError('source sequence must be a positive integer')
            materials = [self.capture_material(x) for x in captures]
            gaps = self.material_gaps(materials)
            receipt = self.append(root, 'origin_import', {'origin_key': key, 'identity_digest': identity,
                                  'source_payload_hash': raw_hash, 'original_payload': request['payload'],
                                  'source_hash_semantics': 'canonical JSON payload; original raw bytes require a referenced material',
                                  'source_schema': request['source_schema'], 'parser_version': request['parser_version'],
                                  'source_sequence': sequence, 'referenced_materials': materials, 'material_gaps': gaps,
                                  'authority': 'historical imported evidence; never current native authority'})
            return {'status': 'imported', 'receipt': receipt, 'material_gaps': gaps,
                    'complete_recovery_ack': not any(g['required'] for g in gaps)}

    def import_watermarks(self, root):
        streams = {}
        for event in self.events(root):
            if event['data']['event'] != 'origin_import':
                continue
            data = self.payload(event)
            key = canonical(data['origin_key'][:2])
            stream = streams.setdefault(key, {'contiguous_through': 0, 'seen_sequences': [], 'gaps': [], 'material_gaps': []})
            if data['source_sequence'] is not None:
                stream['seen_sequences'].append(data['source_sequence'])
            stream['material_gaps'] += self.material_gaps(data['referenced_materials'])
        for stream in streams.values():
            sequence = set(stream['seen_sequences'])
            while stream['contiguous_through'] + 1 in sequence:
                stream['contiguous_through'] += 1
            if sequence:
                cursor, ranges = 1, []
                for observed in sorted(sequence):
                    if observed > cursor:
                        ranges.append([cursor, observed - 1])
                    cursor = observed + 1
                stream['gap_ranges'] = ranges
                missing_count = sum(end - start + 1 for start, end in ranges)
                stream['gaps'] = [value for start, end in ranges for value in range(start, end + 1)] if missing_count <= 10000 else []
                stream['gap_listing_truncated'] = missing_count > 10000
        return streams

    def compile(self, root, purpose='implement'):
        objective, events = self.state(root)
        data = self.payload(objective)
        packet = workflow.compile_context(data['task'], self.records(), self.store, purpose)
        gaps = self.material_gaps(data['attachments'])
        packet['factory_binding'] = {'root_task_id': root, 'objective_ref': objective['id'], 'revision': data['revision'],
                                     'acceptance_version': data['acceptance_version'], 'full_text': data['full_text'],
                                     'requirements': data['requirements'], 'native_identity': data['native_identity'],
                                     'attachments': data['attachments'], 'attachment_gaps': gaps,
                                     'authorization_scope': data['authorization_scope'], 'limits': LIMITS}
        packet['factory_binding']['native_input_lineage'] = [
            {'receipt_ref': event['id'], 'revision': self.payload(event)['revision'],
             'full_text': self.payload(event)['full_text'], 'native_identity': self.payload(event)['native_identity'],
             'authorized_scope_change': self.payload(event).get('authorized_scope_change'),
             'authorized_attachment_removal': self.payload(event).get('authorized_attachment_removal')}
            for event in events if event['data']['event'] == 'native_input']
        packet['factory_binding']['lineage_semantics'] = 'Exact original and corrections in native order. Later applicable corrections supersede conflicting earlier intent; unchanged full obligations remain.'
        if any(g['required'] for g in gaps):
            packet['ready_for_handoff'] = False
            packet['blockers'].append({'id': root, 'reason': 'required attachment unavailable', 'gaps': gaps})
        # Selected closure excludes the growing receipt log and pins actual RDD inputs.
        packet['factory_binding']['selected_closure_digest'] = hash_value(packet['records'])
        return packet

    @staticmethod
    def producing_context(packet):
        """Exact selected input, excluding only unrelated growing log metadata."""
        selected = copy_json(packet)
        selected.pop('journal_sha256', None)
        selected['factory_projection_omissions'] = {
            'journal_sha256': 'Whole append-only log hash omitted from producing input identity: unrelated receipts change it. All selected records, source/task hashes, exact native lineage, obligations, corrections and material bindings remain.'}
        return selected

    def prepare_owned_operation(self, root, request):
        """Bind current context into the actual transport before dispatch.

        Preparation does not execute, reserve, switch models or grant permission.
        Admission subsequently compares this current full selected context.
        """
        with self.gate():
            packet = self.producing_context(self.compile(root, request.get('purpose', 'implement')))
            digest = hash_value(packet)
            self.materials.mkdir(parents=True, exist_ok=True)
            context_path = self.materials / digest
            if not context_path.exists():
                with tempfile.NamedTemporaryFile(dir=self.materials, delete=False) as stream:
                    temporary = Path(stream.name)
                    try:
                        stream.write(canonical(packet).encode())
                        stream.flush()
                        os.fsync(stream.fileno())
                        os.replace(temporary, context_path)
                        directory = os.open(self.materials, os.O_RDONLY)
                        try:
                            os.fsync(directory)
                        finally:
                            os.close(directory)
                    finally:
                        if temporary.exists():
                            temporary.unlink()
            if rdd.digest(context_path) != digest:
                raise FactoryError('prepared context bytes drift')
            prepared = copy_json(request)
            require(prepared, ('producing_input',), 'operation preparation')
            if not isinstance(prepared['producing_input'], dict):
                raise FactoryError('producing_input must be an object with explicit transport')
            prepared['compiled_context_digest'] = digest
            prepared['producing_input']['factory_context'] = {
                'path': str(context_path), 'sha256': digest, 'root_task_id': root,
                'objective_ref': packet['factory_binding']['objective_ref'],
                'objective_revision': packet['factory_binding']['revision'],
                'transport': 'custom dispatcher receives this object; owned subprocess receives RDD_FACTORY_CONTEXT_PATH and RDD_FACTORY_CONTEXT_SHA256'}
            for association in prepared.get('applied_transfer_associations', []):
                association['producing_input_digest'] = hash_value(prepared['producing_input'])
            return prepared

    def admit_episode(self, root, request):
        require(request, ('seed_id', 'decision', 'mechanism_question', 'alternatives', 'counterlead', 'next_discriminator',
                          'access_scope', 'stop_condition', 'reopen_condition', 'prior_feasible_action', 'reservation'), 'episode')
        workflow.strings(request['alternatives'], 'alternatives')
        if len(request['alternatives']) < 2:
            raise FactoryError('research must distinguish at least two alternatives')
        if request['reservation']['amounts'].get('episodes', 0) < 1:
            raise FactoryError('episode admission reserves at least one episode')
        with self.gate():
            reservation = self._reserve(root, request['reservation'])
            prior = [e for e in self.events(root) if e['data']['event'] == 'episode_admission' and
                     self.payload(e)['reservation_ref'] == reservation['id']]
            if prior:
                if {k: self.payload(prior[0])[k] for k in request} != request:
                    raise FactoryError('episode reservation already assigned')
                return prior[0]
            return self.append(root, 'episode_admission', {**request, 'reservation_ref': reservation['id'],
                                                          'execution_status': 'prepared_not_dispatched'})

    def record_episode_dispatch(self, root, request):
        require(request, ('episode_ref', 'actual_adapter', 'actual_worker_identity', 'assignment', 'output_refs'), 'episode dispatch')
        with self.gate():
            episode = self.find(request['episode_ref'], 'episode_admission')
            if episode['data']['root_task_id'] != root:
                raise FactoryError('episode root mismatch')
            current, _ = self.state(root)
            if self.payload(episode)['reservation']['objective_revision'] != self.payload(current)['revision']:
                raise FactoryError('stale episode must be re-admitted')
            if any(e['data']['event'] in {'episode_closure', 'episode_dispatch'} and self.payload(e)['episode_ref'] == request['episode_ref'] for e in self.events(root)):
                raise FactoryError('episode already dispatched or closed; reserve a fresh bounded attempt')
            if any(e['data']['event'] == 'settlement' and self.payload(e)['reservation_ref'] == self.payload(episode)['reservation_ref'] for e in self.events(root)):
                raise FactoryError('settled episode reservation cannot dispatch')
            return self.append(root, 'episode_dispatch', request)

    def close_episode(self, root, request):
        require(request, ('episode_ref', 'disposition', 'stop_reason', 'decision_effect'), 'episode closure')
        if not isinstance(request.get('actual_inspection_refs'), list):
            raise FactoryError('closure needs explicit actual_inspection_refs, empty for no inspection')
        if request['disposition'] not in {'adopt', 'confirm', 'reject_for_scope', 'defer', 'inaccessible'}:
            raise FactoryError('unknown research disposition')
        with self.gate():
            episode = self.find(request['episode_ref'], 'episode_admission')
            if episode['data']['root_task_id'] != root:
                raise FactoryError('episode root mismatch')
            records = {r['id']: r for r in self.records()}
            for ref in request['actual_inspection_refs']:
                if ref not in records or records[ref]['kind'] != 'evidence' or records[ref]['data']['basis'] == 'proposed':
                    raise FactoryError('inspection needs actual observed/documented evidence')
            if request['disposition'] in {'adopt', 'confirm', 'reject_for_scope'}:
                decision = records.get(request.get('decision_ref'))
                if not decision or decision['kind'] != 'decision':
                    raise FactoryError('closure must consume a real RDD decision')
                require(request, ('consumer_refs',), 'decision consumption')
                for consumer in request['consumer_refs']:
                    require(consumer, ('record_ref', 'effect'), 'consumer')
                    if consumer['record_ref'] not in records:
                        raise FactoryError('decision consumer not found')
            else:
                require(request, ('deferred_trigger',), 'deferred closure')
            if any(e['data']['event'] == 'episode_closure' and self.payload(e)['episode_ref'] == request['episode_ref'] for e in self.events(root)):
                raise FactoryError('episode already closed; reopen reserves a new episode')
            return self.append(root, 'episode_closure', request)

    def paths(self, request):
        root = Path(request['project_root']).resolve(strict=True)
        if not root.is_dir():
            raise FactoryError('project_root must be a directory')
        write_set = workflow.strings(request.get('write_set', []), 'write_set', True)
        return [str(workflow.safe_path(root, x)) for x in write_set]

    @staticmethod
    def overlaps(left, right):
        return any(Path(a) == Path(b) or Path(a).is_relative_to(Path(b)) or Path(b).is_relative_to(Path(a)) for a in left for b in right)

    def operations(self, root):
        result = {}
        current, events = self.state(root)
        revision = self.payload(current)['revision']
        for event in events:
            name, data = event['data']['event'], self.payload(event)
            if name == 'operation_admission':
                result[event['id']] = {'receipt': event, 'assignment_relevance': 'current' if data['objective_revision'] == revision else 'superseded',
                                      'producer_lifecycle': 'unknown', 'descendant_lifecycle': 'unknown', 'target_effects': 'unknown'}
            elif name in {'operation_dispatch', 'operation_result', 'operation_reconciliation'} and data['operation_ref'] in result:
                operation = result[data['operation_ref']]
                if name == 'operation_dispatch':
                    operation.update(producer_lifecycle='running', producer_identity=data['producer_identity'])
                elif name == 'operation_result':
                    operation.update(producer_lifecycle='stopped', result_ref=event['id'])
                    # The parent stopping does not prove descendants stopped or no target effect.
                else:
                    operation.update({k: data[k] for k in ('producer_lifecycle', 'descendant_lifecycle', 'target_effects')})
                    operation['reconciliation_ref'] = event['id']
        return result

    def _validate_operation(self, root, request, actual_input, actual_closure_digest):
        require(request, ('objective_revision', 'project_root', 'operation_class', 'producing_input', 'selected_closure_digest',
                          'reservation_ref', 'capability', 'permitted_effect_scope', 'expected_target_manifest', 'compiled_context_digest'), 'operation')
        current, _ = self.state(root)
        objective = self.payload(current)
        if request['objective_revision'] != objective['revision']:
            raise FactoryError('stale objective revision')
        if request['operation_class'] not in {'generation', 'maintenance', 'product_repair', 'diagnosis', 'research', 'integration'}:
            raise FactoryError('unknown operation class')
        if request['operation_class'] == 'diagnosis' and request.get('write_set'):
            raise FactoryError('diagnosis cannot authorize product writes')
        if hash_value(actual_input) != hash_value(request['producing_input']):
            raise FactoryError('actual producing input differs from authoritative intent')
        packet = self.compile(root, request.get('purpose', 'implement'))
        if not packet['ready_for_handoff']:
            raise FactoryError('handoff blocked: ' + canonical(packet['blockers']))
        context = actual_input.get('factory_context') if isinstance(actual_input, dict) else None
        require(context, ('path', 'sha256', 'root_task_id', 'objective_ref', 'objective_revision'), 'actual producing context transport')
        digest = hash_value(self.producing_context(packet))
        if request['compiled_context_digest'] != digest or context['sha256'] != digest or Path(context['path']).resolve() != self.materials / digest or rdd.digest(Path(context['path'])) != digest or context['root_task_id'] != root or context['objective_ref'] != current['id'] or context['objective_revision'] != objective['revision']:
            raise FactoryError('actual context capsule does not bind exact current selected input/objective/material closure')
        closure_digest = packet['factory_binding']['selected_closure_digest']
        if request['selected_closure_digest'] != closure_digest or actual_closure_digest != closure_digest:
            raise FactoryError('selected closure changed or actual dispatch closure differs')
        reservation = self.find(request['reservation_ref'], 'reservation')
        if reservation['data']['root_task_id'] != root or self.payload(reservation)['objective_revision'] != objective['revision']:
            raise FactoryError('reservation is not current for root')
        if self.payload(reservation)['amounts'].get('operations', 0) < 1:
            raise FactoryError('owned operation needs operations reservation')
        if any(e['data']['event'] == 'settlement' and self.payload(e)['reservation_ref'] == reservation['id'] for e in self.events(root)):
            raise FactoryError('settled reservation cannot dispatch')
        if any(e['data']['event'] == 'operation_admission' and self.payload(e)['reservation_ref'] == reservation['id'] for e in self.events(root)):
            raise FactoryError('reservation already dispatched; retries reserve from the same root')
        require(request['capability'], ('adapter', 'guarantee_scope', 'permission_scope'), 'capability')
        if workflow.input_drift({'inputs': request['expected_target_manifest']}):
            raise FactoryError('target changed before admission')
        paths = self.paths(request)
        manifest = request['expected_target_manifest']
        if Path(manifest['root']).resolve() != Path(request['project_root']).resolve():
            raise FactoryError('expected target manifest must bind canonical project_root')
        for target in paths:
            if not any(str(workflow.safe_path(Path(manifest['root']).resolve(), item['path'])) == target or
                       (item['kind'] == 'tree' and Path(target).is_relative_to(workflow.safe_path(Path(manifest['root']).resolve(), item['path'])))
                       for item in manifest['entries']):
                raise FactoryError('expected target manifest does not cover declared write_set; use bounded parent tree for new files')
        if self.unresolved_resource_claims(paths):
            raise FactoryError('conflicting prior producer/descendant/effect unresolved across owned journals; observe before retry')
        by_id = {r['id']: r for r in self.records()}
        associations = request.get('applied_transfer_associations', [])
        if not isinstance(associations, list):
            raise FactoryError('applied transfers require keyed associations')
        selected = objective['task'].get('transfers', [])
        if {a.get('transfer_ref') for a in associations} != set(selected) or len(associations) != len(selected):
            raise FactoryError('bind each selected transfer exactly once')
        for association in associations:
            require(association, ('transfer_ref', 'property', 'conditions', 'composition_version', 'check_plan', 'producing_input_digest', 'selected_closure_digest'), 'transfer association')
            if by_id.get(association['transfer_ref'], {}).get('kind') != 'transfer':
                raise FactoryError('association is not a transfer')
            if association['producing_input_digest'] != hash_value(actual_input) or association['selected_closure_digest'] != closure_digest:
                raise FactoryError('transfer association binds wrong producing input/closure')
        if request.get('rebase_ref'):
            rebase = self.find(request['rebase_ref'], 'operation_rebase')
            data = self.payload(rebase)
            if rebase['data']['root_task_id'] != root or data['new_objective_ref'] != current['id'] or hash_value(data['fresh_producing_input']) != hash_value(actual_input):
                raise FactoryError('executor rejects rebase without exact current objective and fresh input binding')
        return packet, paths

    def admit_owned_operation(self, root, request, dispatcher):
        """Compare/persist/start under one gate. Dispatcher must be fast (e.g. Popen).

        If the process escapes or dispatch raises after acting, durable admission
        remains unknown. An observer must reconcile it before conflicting replay.
        No arbitrary native action is intercepted by this method.
        """
        if not callable(dispatcher):
            raise FactoryError('actual owned dispatcher required; a packet is not execution')
        paths = self.paths(request)
        with self.resource_gates(paths), self.gate():
            actual = request.get('actual_producing_input', request['producing_input'])
            closure_digest = request.get('actual_selected_closure_digest', request['selected_closure_digest'])
            _, paths = self._validate_operation(root, request, actual, closure_digest)
            intent = {k: v for k, v in request.items() if k not in {'actual_producing_input', 'actual_selected_closure_digest'}}
            intent.update(canonical_write_set=paths, producing_input_digest=hash_value(actual),
                          fence_level='admission_fenced', effects_status='unknown_until_observed',
                          dispatch_binding='actual input/closure compared under journal and canonical-path gate',
                          guarantee_scope=LIMITS)
            operation_ref = 'factory-' + uuid.uuid4().hex
            # Pointer first: crash before journal append leaves an unknown owner,
            # which must block, rather than an unindexed live writer.
            self.publish_resource_claim(root, operation_ref, paths)
            receipt = self.append(root, 'operation_admission', intent, identifier=operation_ref)
            # This call is the actual producing boundary, not an independent declaration.
            dispatched = dispatcher(copy_json(actual), receipt['id'])
            require(dispatched, ('producer_identity',), 'dispatcher result')
            launch = self.append(root, 'operation_dispatch', {'operation_ref': receipt['id'],
                                 'producer_identity': dispatched['producer_identity'],
                                 'actual_producing_input_digest': hash_value(actual),
                                 'actual_selected_closure_digest': closure_digest})
            return {'admission': receipt, 'dispatch': launch, 'producer': dispatched.get('producer')}

    def run_owned_operation(self, root, request):
        actual = request['producing_input']
        require(actual, ('command',), 'subprocess producing input')
        workflow.strings(actual['command'], 'command')
        cwd = Path(actual.get('cwd', request['project_root'])).resolve(strict=True)
        if cwd != Path(request['project_root']).resolve():
            raise FactoryError('owned subprocess cwd must equal project_root')
        output_dir = self.store.parent / '.factory-operation-output'
        output_dir.mkdir(parents=True, exist_ok=True)
        streams = {}
        def dispatch(bound, operation_ref):
            if bound != actual:
                raise FactoryError('dispatch input mismatch')
            for name in ('stdout', 'stderr'):
                streams[name] = (output_dir / f'{operation_ref}.{name}').open('wb')
            process = subprocess.Popen(bound['command'], cwd=cwd, stdin=subprocess.DEVNULL,
                                       stdout=streams['stdout'], stderr=streams['stderr'], start_new_session=True,
                                       env={**os.environ, 'RDD_FACTORY_CONTEXT_PATH': bound['factory_context']['path'],
                                            'RDD_FACTORY_CONTEXT_SHA256': bound['factory_context']['sha256']})
            return {'producer': process, 'producer_identity': {'pid': process.pid, 'attempt': operation_ref,
                    'start_monotonic_ns': time.monotonic_ns(), 'identity_scope': 'owned launch receipt; PID alone insufficient'}}
        started = time.monotonic()
        try:
            result = self.admit_owned_operation(root, request, dispatch)
            process = result['producer']
            code = process.wait(timeout=request.get('timeout_seconds'))
        except subprocess.TimeoutExpired:
            # Stop request is not no-effect proof; preserve logs and unknown descendants.
            process.terminate()
            with self.gate():
                self.append(root, 'operation_stop_request', {'operation_ref': result['admission']['id'], 'reason': 'timeout; target/descendants unresolved'})
            raise FactoryError('owned operation timeout; observe/reconcile before retry')
        finally:
            for stream in streams.values():
                stream.flush()
                os.fsync(stream.fileno())
                stream.close()
        with self.gate():
            outputs = [self.capture_material({'path': stream.name, 'role': name}) for name, stream in streams.items()]
            elapsed = time.monotonic() - started
            receipt = self.append(root, 'operation_result', {'operation_ref': result['admission']['id'], 'exit_code': code,
                                 'outputs': outputs, 'wall_seconds': elapsed,
                                 'target_effects': 'unknown', 'descendant_lifecycle': 'unknown'})
            self.append(root, 'resource', {'attempt_id': result['admission']['id'], 'source_ref': receipt['id'],
                        'resource_kind': 'owned_process_elapsed', 'snapshot_semantics': 'delta',
                        'values': {'wall_seconds': elapsed}, 'coverage': 'complete_for_declared_scope',
                        'scope': 'this invocation elapsed time only; no provider, quota, native or descendant census'})
        return {'admission_ref': result['admission']['id'], 'result': receipt,
                'limits': 'Process completion is observed; target effects and descendant cessation require separate observation.'}

    def reconcile_operation(self, root, request):
        require(request, ('operation_ref', 'observer', 'observed_at', 'observation_materials', 'attribution',
                          'producer_lifecycle', 'descendant_lifecycle', 'target_effects', 'consistency_scope'), 'reconciliation')
        if request['producer_lifecycle'] not in {'not_started', 'running', 'stop_requested', 'stopped', 'unknown'}:
            raise FactoryError('invalid producer lifecycle')
        if request['descendant_lifecycle'] not in {'none_confirmed', 'active', 'cleanup_requested', 'stopped_confirmed', 'unknown'}:
            raise FactoryError('invalid descendant lifecycle')
        if request['target_effects'] not in {'not_dispatched', 'no_effect_confirmed', 'committed', 'partial', 'unknown'}:
            raise FactoryError('invalid effect state')
        with self.gate():
            operation = self.find(request['operation_ref'], 'operation_admission')
            if operation['data']['root_task_id'] != root:
                raise FactoryError('operation root mismatch')
            materials = [self.capture_material(x) for x in request['observation_materials']]
            if self.material_gaps(materials):
                raise FactoryError('reconciliation evidence missing')
            if request['target_effects'] not in {'partial', 'unknown'} and request['attribution'] == 'process disappeared':
                raise FactoryError('process disappearance cannot prove target effect')
            return self.append(root, 'operation_reconciliation', {**request, 'observation_materials': materials,
                               'limits': 'Observer attribution and target consistency are scoped declarations, not universal attestation.'})

    def rebase_operation(self, root, request):
        require(request, ('prior_operation_ref', 'old_objective_ref', 'new_objective_ref', 'relevant_generations',
                          'semantic_applicability_evidence', 'fresh_producing_input', 'changed_scope'), 'rebase')
        with self.gate():
            current, _ = self.state(root)
            old = self.find(request['old_objective_ref'], 'native_input')
            operation = self.find(request['prior_operation_ref'], 'operation_admission')
            if current['id'] != request['new_objective_ref'] or operation['data']['root_task_id'] != root or old['data']['root_task_id'] != root:
                raise FactoryError('rebase bases are not current for root')
            if self.payload(operation)['objective_revision'] != self.payload(old)['revision']:
                raise FactoryError('prior operation does not bind old objective')
            if self.payload(old)['requirements'] != self.payload(current)['requirements']:
                raise FactoryError('selective rebase cannot drop/change full obligations; fresh operation required')
            for item in request['relevant_generations']:
                require(item, ('name', 'old', 'new'), 'generation')
                if item['old'] != item['new'] or item['old'] in ('unknown', None):
                    raise FactoryError('changed or unknown relevant generation; fresh rebind/check required')
            return self.append(root, 'operation_rebase', {**request, 'old_acceptance_version': self.payload(old)['acceptance_version'],
                               'new_acceptance_version': self.payload(current)['acceptance_version'],
                               'status': 'eligible_for_fresh_admission_and_check; prior effect authority remains superseded'})

    def _acceptance(self, root, request):
        require(request, ('objective_revision', 'subject_manifest', 'composition_version', 'property_verdicts',
                          'driver_closure', 'oracle_closure', 'independence_scope', 'current_producer_identity'), 'acceptance')
        objective, _ = self.state(root)
        data = self.payload(objective)
        if request['objective_revision'] != data['revision']:
            raise FactoryError('stale acceptance objective')
        for field in ('subject_manifest', 'driver_closure', 'oracle_closure'):
            if workflow.input_drift({'inputs': request[field]}):
                raise FactoryError(f'acceptance {field} changed or unavailable')
        # Reuse existing RDD declared property, correction and access assessment.
        assessment = workflow.assess(data['task'], self.records(), self.store)
        if not assessment['ready_for_review']:
            raise FactoryError('RDD property/access review blocked: ' + canonical(assessment))
        required = {(x['id'], x['property']) for x in data['requirements']}
        verdicts = request['property_verdicts']
        if not isinstance(verdicts, list):
            raise FactoryError('property_verdicts must be a list')
        mapped = [(v.get('requirement_id'), v.get('property')) for v in verdicts]
        if set(mapped) != required or len(mapped) != len(required):
            raise FactoryError('full original requirement/property denominator not covered exactly once')
        records = {r['id']: r for r in self.records()}
        for verdict in verdicts:
            require(verdict, ('check_ref', 'checker_identity', 'oracle_authority', 'independence', 'outcome'), 'property verdict')
            check = records.get(verdict['check_ref'])
            if not check or check['kind'] != 'check' or check['data']['outcome'] != 'passed' or verdict['outcome'] != 'passed':
                raise FactoryError('property lacks passed captured RDD check')
            check_data = check['data']
            require(check_data, ('property_ids', 'objective_ref', 'objective_revision', 'acceptance_version',
                                 'composition_version', 'driver_closure', 'oracle_closure', 'checker_identity'), 'captured check binding')
            covered = check_data['property_ids']
            if not isinstance(covered, list) or any(not isinstance(item, list) or len(item) != 2 or any(not isinstance(v, str) or not v for v in item) for item in covered):
                raise FactoryError('check property_ids must be explicit [requirement_id, property] pairs')
            if [verdict['requirement_id'], verdict['property']] not in covered:
                raise FactoryError('captured check does not cover this requirement/property')
            if check_data['objective_ref'] != objective['id'] or check_data['objective_revision'] != data['revision'] or check_data['acceptance_version'] != data['acceptance_version']:
                raise FactoryError('captured check binds a different objective/acceptance version; reevaluate current obligations')
            for field in ('composition_version', 'driver_closure', 'oracle_closure'):
                if hash_value(check_data[field]) != hash_value(request[field]):
                    raise FactoryError(f'captured check binds different {field}')
            if check_data['checker_identity'] != verdict['checker_identity']:
                raise FactoryError('captured checker identity differs from claimed property verdict')
            if verdict['checker_identity'] == request['current_producer_identity']:
                raise FactoryError('same producer/checker identity is not independent acceptance')
            if hash_value(check_data.get('artifact_inputs')) != hash_value(request['subject_manifest']):
                raise FactoryError('check binds a different subject')
            if not set(check['data'].get('links', [])) & set(data['task'].get('transfers', [])):
                raise FactoryError('check does not bind selected transfer')
        if any(s['producer_lifecycle'] in {'running', 'stop_requested', 'unknown'} or
               s['descendant_lifecycle'] in {'active', 'cleanup_requested', 'unknown'} or
               s['target_effects'] in {'partial', 'unknown'} for s in self.operations(root).values()):
            raise FactoryError('unknown or active owned producer/descendant/effects block acceptance')
        gaps = self.material_gaps(data['attachments'])
        if any(g['required'] for g in gaps):
            raise FactoryError('required original attachment lost')
        return objective, {'declared_current': True, 'independently_complete': 'caller-declared property verdicts; semantic truth requires oracle review',
                           'assessment': assessment, 'limits': LIMITS}

    def eligible_acceptance(self, root, request):
        with self.gate():
            objective, result = self._acceptance(root, request)
            return self.append(root, 'acceptance', {**request, 'objective_ref': objective['id'],
                               'original_scope_digest': self.payload(objective)['original_scope_digest'], **result})

    def finalize_delivery(self, root, request):
        require(request, ('acceptance_ref', 'usable_entry', 'default_state', 'runtime_environment_closure',
                          'demonstration_materials', 'fresh_consumer_identity', 'native_continuation_ref', 'external_consistency_limits'), 'delivery')
        acceptance = self.find(request['acceptance_ref'], 'acceptance')
        if acceptance['data']['root_task_id'] != root:
            raise FactoryError('acceptance root mismatch')
        subject = self.payload(acceptance)['subject_manifest']
        paths = [str(workflow.safe_path(Path(subject['root']).resolve(), x['path'])) for x in subject['entries']]
        with self.resource_gates(paths), self.gate():
            # Check + durable append share the same correction/admission gate.
            current, _ = self._acceptance(root, self.payload(acceptance))
            if self.payload(acceptance)['objective_ref'] != current['id']:
                raise FactoryError('acceptance no longer current')
            if request['fresh_consumer_identity'] == self.payload(acceptance)['current_producer_identity']:
                raise FactoryError('fresh consumer must differ from current producer')
            if workflow.input_drift({'inputs': request['runtime_environment_closure']}):
                raise FactoryError('delivery runtime environment changed')
            materials = [self.capture_material(x) for x in request['demonstration_materials']]
            if self.material_gaps(materials):
                raise FactoryError('fresh consumer demonstration unavailable')
            return self.append(root, 'delivery', {**request, 'demonstration_materials': materials,
                               'subject_manifest': subject, 'objective_ref': current['id'],
                               'correction_integration_epoch': self.payload(current)['revision'],
                               'finalization_ordering_scope': 'same owned journal gate as correction and admission; canonical local-path locks',
                               'remaining_limits': request.get('remaining_limits', [])})

    def record_resource(self, root, request):
        require(request, ('attempt_id', 'source_ref', 'resource_kind', 'snapshot_semantics', 'values', 'coverage'), 'resource')
        if request['snapshot_semantics'] not in {'delta', 'cumulative'}:
            raise FactoryError('resource semantics must be delta or cumulative')
        if request['coverage'] not in {'complete_for_declared_scope', 'partial', 'unknown'}:
            raise FactoryError('unknown resource coverage')
        for key, value in request['values'].items():
            if key not in {'marginal_cash', 'api_equivalent', 'subscription_quota', 'wall_seconds', 'tokens'} or isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise FactoryError('resource values need nonnegative separate supported units')
        with self.gate():
            self.state(root)
            identity = (request['attempt_id'], request['source_ref'], request['resource_kind'])
            prior = [e for e in self.events(root) if e['data']['event'] == 'resource' and
                     tuple(self.payload(e)[k] for k in ('attempt_id', 'source_ref', 'resource_kind')) == identity]
            if prior:
                if self.payload(prior[0]) != request:
                    raise FactoryError('conflicting resource observation; retain original and resolve explicitly')
                return prior[0]
            return self.append(root, 'resource', request)

    def project_outcome_resources(self, root):
        objective, events = self.state(root)
        resources = [self.payload(e) for e in events if e['data']['event'] == 'resource']
        groups = {}
        for resource in resources:
            groups.setdefault((resource['attempt_id'], resource['resource_kind']), []).append(resource)
        totals = {k: 0 for k in ('marginal_cash', 'api_equivalent', 'subscription_quota', 'wall_seconds', 'tokens')}
        conflicts = []
        for identity, values in groups.items():
            semantics = {v['snapshot_semantics'] for v in values}
            if len(semantics) > 1:
                conflicts.append({'attempt': identity, 'reason': 'mixed delta/cumulative semantics require explicit reconciliation'})
                continue
            for key in totals:
                observed = [v['values'][key] for v in values if key in v['values']]
                totals[key] += max(observed, default=0) if semantics == {'cumulative'} else sum(observed)
        operation_refs = {e['id'] for e in events if e['data']['event'] == 'operation_admission'}
        episode_refs = {self.payload(e)['episode_ref'] for e in events if e['data']['event'] == 'episode_dispatch'}
        enrolled = operation_refs | episode_refs
        captured = {r['attempt_id'] for r in resources}
        missing = sorted(enrolled - captured)
        deliveries = [e for e in events if e['data']['event'] == 'delivery']
        current_deliveries, delivery_gaps = [], []
        for delivery in deliveries:
            data = self.payload(delivery)
            try:
                if data['objective_ref'] != objective['id']:
                    raise FactoryError('objective superseded')
                acceptance = self.find(data['acceptance_ref'], 'acceptance')
                self._acceptance(root, self.payload(acceptance))
                if workflow.input_drift({'inputs': data['runtime_environment_closure']}):
                    raise FactoryError('runtime environment closure changed')
                if self.material_gaps(data['demonstration_materials']):
                    raise FactoryError('required demonstration material unavailable')
                current_deliveries.append(delivery)
            except (ValueError, OSError, KeyError, TypeError) as exc:
                delivery_gaps.append({'delivery_ref': delivery['id'], 'reason': str(exc)})
        return {'root_task_id': root, 'original_scope_digest': self.payload(objective)['original_scope_digest'],
                'supported_subtotals': totals, 'all_attempts_retained': len({r['attempt_id'] for r in resources}), 'enrolled_owned_attempts': sorted(enrolled),
                'missing_owned_attempts': missing, 'observation_conflicts': conflicts,
                'current_delivery_refs': [e['id'] for e in current_deliveries],
                'delivery_projection_gaps': delivery_gaps,
                'whole_task_savings': None,
                'coverage': 'partial' if missing or conflicts or any(r['coverage'] != 'complete_for_declared_scope' for r in resources) else 'complete_for_declared_owned_enrollments_only',
                'limits': 'Native bypasses, subscription usage and provider boundaries are not automatically enrolled. Subtotals are not whole-task savings or comparative advantage.'}

    def status(self, root):
        objective, _ = self.state(root)
        return {'objective_ref': objective['id'], 'objective': self.payload(objective), 'allocation': self.allocation(root),
                'operations': self.operations(root), 'import_watermarks': self.import_watermarks(root),
                'resources': self.project_outcome_resources(root),
                'resource_owner_index': str(self.resource_registry),
                'resource_owner_index_semantics': 'Durable lookup pointers; referenced RDD journal alone owns lifecycle. Missing owners block conflicts.',
                'limits': LIMITS}


ACTIONS = {'bind': 'bind_native_input', 'reserve': 'reserve', 'settle': 'settle', 'import': 'import_origin_event', 'prepare': 'prepare_owned_operation',
           'episode': 'admit_episode', 'episode-dispatch': 'record_episode_dispatch', 'close-episode': 'close_episode',
           'run': 'run_owned_operation', 'reconcile': 'reconcile_operation', 'rebase': 'rebase_operation',
           'accept': 'eligible_acceptance', 'deliver': 'finalize_delivery', 'resource': 'record_resource'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--store', type=Path, required=True, help='existing RDD records.jsonl; private project notes')
    parser.add_argument('action', choices=[*ACTIONS, 'status', 'compile', 'resources'])
    parser.add_argument('--root', help='stable original task identity; required after bind')
    parser.add_argument('--request', type=Path, help='exact JSON request; native lead prepares it')
    parser.add_argument('--purpose', choices=('implement', 'repair'), default='implement')
    args = parser.parse_args(argv)
    try:
        factory = Factory(args.store)
        if args.action == 'bind':
            if args.request is None:
                raise FactoryError('bind needs --request')
            result = factory.bind_native_input(workflow.load(args.request))
        else:
            if not args.root:
                raise FactoryError('action needs --root')
            if args.action == 'status':
                result = factory.status(args.root)
            elif args.action == 'compile':
                result = factory.compile(args.root, args.purpose)
            elif args.action == 'resources':
                result = factory.project_outcome_resources(args.root)
            else:
                if args.request is None:
                    raise FactoryError('action needs --request')
                result = getattr(factory, ACTIONS[args.action])(args.root, workflow.load(args.request))
        print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f'factory: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
