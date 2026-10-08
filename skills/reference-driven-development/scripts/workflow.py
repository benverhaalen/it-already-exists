#!/usr/bin/env python3
"""Optional RDD planning and context compiler; no acquisition or model calls.

Inspect generated plans. Structural validity is not semantic correctness.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import rdd
import assets

PACKAGE = Path(__file__).resolve().parents[1]
METHODS = PACKAGE / 'references/methods.json'


def load(path):
    with Path(path).open(encoding='utf-8') as stream:
        return json.load(stream, parse_constant=rdd.reject_constant)


def strings(value, label, allow_empty=False):
    if not isinstance(value, list) or (not value and not allow_empty) or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(f'{label} must be a list of nonempty strings')
    if len(value) != len(set(value)):
        raise ValueError(f'{label} contains duplicates')
    return value


def task_spec(value):
    if not isinstance(value, dict):
        raise ValueError('task must be an object')
    for field in ('scope', 'goal', 'audience', 'surface', 'operation', 'access'):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f'task needs {field}')
    if value['access'] not in ('source-assisted', 'strict-clean-room'):
        raise ValueError('access must be source-assisted or strict-clean-room')
    if value['operation'] not in ('adapt', 'reconstruct', 'extend', 'refine', 'repair', 'explore'):
        raise ValueError('unknown operation')
    journey = value.get('journey')
    if not isinstance(journey, dict) or any(not isinstance(journey.get(k), str) or not journey[k].strip() for k in ('entry', 'default', 'action', 'outcome', 'reset')):
        raise ValueError('journey needs entry/default/action/outcome/reset')
    for key in ('tags', 'capabilities', 'contributions', 'transfers'):
        strings(value.get(key, []), key, True)
    strings(value.get('settled_prerequisites', []), 'settled_prerequisites', True)
    prerequisites = value.get('prerequisite_facts', [])
    if not isinstance(prerequisites, list):
        raise ValueError('prerequisite_facts must be a list')
    for fact in prerequisites:
        if not isinstance(fact, dict) or any(not isinstance(fact.get(k), str) or not fact[k].strip() for k in ('id', 'evidence', 'next_action')):
            raise ValueError('prerequisite fact needs id/evidence/next_action')
    if not value.get('contributions') and not value.get('selection_reason'):
        raise ValueError('empty contribution selection needs selection_reason; planning can state selection is pending')
    for field in ('conflicts', 'input_requests', 'unknowns'):
        if not isinstance(value.get(field, []), list):
            raise ValueError(f'{field} must be a list')
    for conflict in value.get('conflicts', []):
        if not isinstance(conflict, dict) or any(not isinstance(conflict.get(k), str) or not conflict[k].strip() for k in ('id', 'issue', 'reason')) or type(conflict.get('resolved')) is not bool:
            raise ValueError('conflict needs id/issue/reason and boolean resolved')
        strings(conflict.get('sources'), 'conflict sources')
        if conflict['resolved'] and not conflict.get('resolution'):
            raise ValueError('resolved conflict needs explicit resolution')
    for request in value.get('input_requests', []):
        if not isinstance(request, dict) or any(not isinstance(request.get(k), str) or not request[k].strip() for k in ('id', 'decision', 'why_user', 'consequence')):
            raise ValueError('input request needs id/decision/why_user/consequence')
        if request.get('wait') not in (True, False) or type(request.get('wait')) is not bool:
            raise ValueError('input request wait must be boolean')
        strings(request.get('dependent_work'), 'dependent_work')
        strings(request.get('independent_work', []), 'independent_work', True)
        strings(request.get('prerequisites', []), 'input prerequisites', True)
        if 'response' in request and (not isinstance(request['response'], str) or not request['response'].strip() or request.get('response_source') != 'user'):
            raise ValueError('response needs nonempty user response and response_source=user; silence is not a response')
        inference = request.get('intent_inference')
        if inference is not None:
            if request.get('category') not in ('intent', 'preference') or request.get('reversible') is not True:
                raise ValueError('intent inference requires reversible intent/preference decision, never authorization')
            if not isinstance(inference, dict) or any(not isinstance(inference.get(k), str) or not inference[k].strip() for k in ('interpretation', 'past_response', 'source', 'original_scope', 'current_fit', 'changed_conditions', 'revisit')):
                raise ValueError('intent inference needs interpretation/past_response/source/original_scope/current_fit/changed_conditions/revisit')
    requests = value.get('input_requests', [])
    request_ids = [r['id'] for r in requests]
    if len(request_ids) != len(set(request_ids)):
        raise ValueError('duplicate input request id')
    known = set(request_ids) | set(value.get('settled_prerequisites', [])) | {f['id'] for f in prerequisites}
    if any(set(r.get('prerequisites', [])) - known for r in requests):
        raise ValueError('unknown prerequisite id; declare pending prerequisite_facts or settled evidence')
    dependencies = {r['id']: set(r.get('prerequisites', [])) & set(request_ids) for r in requests}
    resolved = set()
    while len(resolved) < len(dependencies):
        frontier = {identifier for identifier, prerequisites in dependencies.items() if prerequisites <= resolved} - resolved
        if not frontier:
            raise ValueError('cyclic input prerequisites; reframe the decision tree')
        resolved |= frontier
    for field in ('competence', 'character'):
        items = value.get(field)
        if not isinstance(items, list):
            raise ValueError(f'task needs explicit {field} list (may be empty with a reason)')
        for item in items:
            if not isinstance(item, dict) or any(not isinstance(item.get(k), str) or not item[k].strip() for k in ('property', 'authority', 'preserve', 'adapt', 'check')):
                raise ValueError(f'{field} item needs property/authority/preserve/adapt/check')
            strings(item.get('transfers', []), f'{field} transfer ids', True)
        if not items and not value.get(f'{field}_omitted_reason'):
            raise ValueError(f'empty {field} needs {field}_omitted_reason')
    ids = set()
    for question in value.get('unknowns', []):
        if not isinstance(question, dict) or any(not isinstance(question.get(k), str) or not question[k].strip() for k in ('id', 'property', 'next_evidence', 'stop')):
            raise ValueError('unknown needs id/property/next_evidence/stop')
        strings(question.get('alternatives'), 'unknown alternatives')
        if len(question['alternatives']) < 2:
            raise ValueError('unknown needs at least two competing explanations')
        if question['id'] in ids:
            raise ValueError('duplicate unknown id')
        ids.add(question['id'])
    frontier = value.get('research_frontier', [])
    if not isinstance(frontier, list):
        raise ValueError('research_frontier must be a list')
    frontier_ids = set()
    for lead in frontier:
        if not isinstance(lead, dict) or any(not isinstance(lead.get(k), str) or not lead[k].strip()
                for k in ('id', 'seed', 'quality_cue', 'why', 'next_action', 'bound', 'counterlead')):
            raise ValueError('research lead needs id/seed/quality_cue/why/next_action/bound/counterlead')
        if lead.get('status') not in ('pending', 'inspected', 'deferred', 'blocked'):
            raise ValueError('research lead needs pending/inspected/deferred/blocked status')
        if lead['id'] in frontier_ids:
            raise ValueError('duplicate research lead id')
        frontier_ids.add(lead['id'])
    return value


def decision_basis(task):
    """Fingerprint the conditions that justify a decision, excluding execution IDs."""
    keys = ('scope', 'goal', 'audience', 'surface', 'operation', 'access', 'journey',
            'competence', 'character', 'competence_omitted_reason', 'character_omitted_reason',
            'tags', 'inputs', 'conflicts', 'constraints', 'fidelity', 'capabilities',
            'unknowns', 'permitted_assets', 'access_policy', 'acceptance', 'budget')
    basis = {key: task[key] for key in keys if key in task}
    for axis in ('competence', 'character'):
        if axis in basis:
            basis[axis] = [{key: value for key, value in item.items() if key != 'transfers'} for item in basis[axis]]
    return hashlib.sha256(json.dumps(basis, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def input_status(task):
    requests = task.get('input_requests', [])
    waiting = [r for r in requests if r['wait'] and not r.get('response') and not r.get('intent_inference')]
    settled = set(task.get('settled_prerequisites', [])) | {r['id'] for r in requests if r.get('response') or r.get('intent_inference')}
    frontier = [r for r in requests if not r.get('response') and not r.get('intent_inference') and set(r.get('prerequisites', [])) <= settled]
    return {'waiting': waiting, 'optional_pending': [r for r in requests if not r['wait'] and not r.get('response') and not r.get('intent_inference')],
            'answered': [r for r in requests if r.get('response')],
            'inferred_for_reversible_work': [r for r in requests if not r.get('response') and r.get('intent_inference')],
            'question_batch': [{'id': r['id'], 'decision': r['decision'], 'why_user': r['why_user'], 'consequence': r['consequence']} for r in frontier],
            'deferred_questions': [r['id'] for r in requests if not r.get('response') and not r.get('intent_inference') and r not in frontier],
            'blocked_work': sorted({x for r in waiting for x in r['dependent_work']}),
            'independent_work': sorted({x for r in waiting for x in r.get('independent_work', [])}),
            'limits': 'Requests and response provenance are caller declarations. Do not manufacture a user reply or treat elapsed time, preselection, agent opinion or prior unrelated authorization as an answer.'}


def safe_path(root, relative):
    if not isinstance(relative, str) or not relative.strip() or Path(relative).is_absolute():
        raise ValueError('input path must be relative to project root')
    path = (root / relative).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f'input escapes project root: {relative}')
    return path


def fingerprint(root, files=(), trees=()):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('project root must be a directory')
    entries = []
    for relative in files:
        path = safe_path(root, relative)
        entries.append({'path': relative, 'kind': 'file', 'sha256': rdd.digest(path)})
    for relative in trees:
        path = safe_path(root, relative)
        if not path.is_dir():
            raise ValueError(f'not a directory: {relative}')
        members = []
        for member in sorted(path.rglob('*')):
            if member.is_symlink():
                raise ValueError(f'tree fingerprints require explicit handling of symlink: {member}')
            if member.is_file():
                members.append((member.relative_to(path).as_posix(), rdd.digest(member)))
        encoded = json.dumps(members, ensure_ascii=False, separators=(',', ':')).encode()
        entries.append({'path': relative, 'kind': 'tree', 'sha256': hashlib.sha256(encoded).hexdigest(), 'members': len(members)})
    if not entries:
        raise ValueError('select at least one input file or bounded tree')
    return {'root': str(root), 'entries': entries}


def input_drift(task):
    saved = task.get('inputs')
    if saved is None:
        return [{'reason': 'no project-input fingerprint; compile a selected file/tree manifest before handoff'}]
    if not isinstance(saved, dict) or not isinstance(saved.get('root'), str) or not isinstance(saved.get('entries'), list) or not saved['entries']:
        raise ValueError('inputs need fingerprint root and entries')
    drift = []
    seen = set()
    for item in saved['entries']:
        if not isinstance(item, dict) or item.get('kind') not in ('file', 'tree') or not isinstance(item.get('sha256'), str) or len(item['sha256']) != 64:
            raise ValueError('invalid input fingerprint entry')
        key = (item['path'], item['kind'])
        if key in seen:
            raise ValueError('duplicate input fingerprint')
        seen.add(key)
        try:
            current = fingerprint(saved['root'], [item['path']] if item['kind'] == 'file' else [], [item['path']] if item['kind'] == 'tree' else [])
            if current['entries'][0]['sha256'] != item['sha256']:
                drift.append({'path': item['path'], 'reason': 'selected context changed; inspect and refresh affected decisions'})
        except (OSError, ValueError) as exc:
            drift.append({'path': item['path'], 'reason': str(exc)})
    return drift


def catalog(path=METHODS):
    value = load(path)
    entries = value.get('methods', [])
    seen = set()
    for item in entries:
        for field in ('id', 'mechanism', 'invariant', 'delta', 'probe', 'limit', 'source', 'license', 'conditions'):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f'method needs {field}')
        for field in ('surfaces', 'properties', 'requires'):
            strings(item.get(field), f'method {field}', field == 'requires')
        if item['id'] in seen:
            raise ValueError('duplicate method id')
        seen.add(item['id'])
    if not entries:
        raise ValueError('empty methods catalog')
    return value


def matches(selectors, task):
    """Every declared selector axis must match; no inferred semantic scope."""
    axes = {'scopes': [task['scope']], 'surfaces': [task['surface']],
            'operations': [task['operation']], 'tags': task.get('tags', [])}
    return bool(selectors) and all(set(choices) & set(axes[key]) for key, choices in selectors.items())


def approach_review(task, repair=False):
    """Carry research-before-commitment into planning and builder context."""
    return {
        'status': 'proposed; not evidence that research or experiments ran',
        'module': 'references/discovery.md',
        'goal': task['goal'], 'journey': task['journey'], 'access': task['access'],
        'stage': 'diagnose-and-reconsider' if repair or task['operation'] == 'repair' else 'before-approach-commitment',
        'operation': 'Inspect existing solutions and underlying mechanisms before committing to a consequential approach; investigate causes and structurally similar solutions when results fail.',
        'questions': ['What already supplies the needed behavior, under which conditions?',
                      'Which underlying mechanism matters and what evidence supports it?',
                      'Where could accuracy, runtime, tokens, cost or environment readiness become the bottleneck?',
                      'Which alternative route could remove work rather than optimize it?',
                      'What observation would favor an adaptation, a repair or changing the approach?'],
        'research_review': {'module': 'references/research-improvement.md',
                            'composition': {
                                'objective': task['goal'],
                                'journey': json.loads(json.dumps(task['journey'])),
                                'contributions': list(task.get('contributions', [])),
                                'transfers': list(task.get('transfers', [])),
                                'module': 'references/synthesis.md',
                                'operation': 'Research toward our own coherent system: give each useful resource, concept, codebase or reference a specific contribution and explain how it combines with the others. A source list is not a synthesis.',
                                'assembly': 'Preserve each mechanism and minute difference before grouping. State what stays intact, what is adapted, the connecting contract, dependencies, conflicts and missing pieces. Keep incompatible specialists as conditional alternatives; do not force every retained idea into the build.',
                                'access': 'Choose licensed code reuse, behavioral transfer or independent implementation under the declared access policy. Source-assisted analysis cannot be passed as implementation instructions across a strict clean-room boundary.',
                                'probe': 'Compare the original, adapted and combined mechanisms on a distinguishing case tied to the intended journey. Test consequential interactions and challenger substitutions; record untested combinations explicitly.',
                                'delivery': 'Carry the composition into selected contribution, decision and transfer records, then the producing assignment and artifact checks. Retained ideas may remain deferred with conditions and revisit triggers.',
                                'limits': 'This is an execution assignment, not an inferred composition, an executed test or proof that combining references improves the result.'},
                            'frontier': json.loads(json.dumps(task.get('research_frontier', []))),
                            'iteration': 'When discovery is uncertain or convergent, inspect one bounded lead deeply: explain the seed quality cue, follow concrete dependencies, practitioners, attachments or disagreements, preserve inspected evidence in the existing journal, then revise the next action and counterlead. Recompile the frontier before resuming; preserve the goal and access policy. Do not turn every queue item into shallow bulk enrichment.',
                            'expansion': 'Choose an evidence-grounded neighboring lead and a bounded contrary or neglected branch when useful. Rarity, popularity and source counts do not establish quality. Stop branches that no longer change the decision; retain deferred leads and their reasons.',
                            'scheduling': 'This helper carries resumable state; it schedules no work and edits no automations. Use continuous in-session iteration by default. Recurring execution requires user-authorized scheduling and an actual supported scheduler; keep the objective, permissions and budget stable.',
                            'targets': [{'id': q['id'], 'property': q['property'],
                                         'competing_explanations': list(q['alternatives']),
                                         'next_evidence': q['next_evidence'], 'bound': q['stop']}
                                        for q in task.get('unknowns', [])],
                            'operation': 'For each unresolved target, choose complementary discovery and inspection routes by the evidence needed to distinguish its explanations. Search direct implementations and structurally different mechanisms; follow source lineage and inspect counterevidence. Do not require a provider or discard a contribution because it ranks poorly.',
                            'selection': 'Prioritize the next inspection by whether it could change the approach, expose a critical omission or test a small meaningful difference. For large queues retain an exploration lane and audit low-ranked records; screening labels are revisable, not deletion.',
                            'transfer': 'Link each inspected mechanism, conditions and minute difference to the existing contribution/transfer/check records. Compare original, adapted and combined behavior where interaction could change the intended journey; retain conditional specialists.',
                            'completion': 'Account for targets as supported, contradicted, unresolved or blocked with evidence and the next discriminating observation. A stopped or failed search is not a recovered requirement.',
                            'promotion_check': 'Compare a consequential research-method change on paired held-out decisions and downstream artifact checks, preserving added and missed contributions and whole-investigation costs. Unknown costs stay unknown; provider or report scores do not establish improvement.'},
        'experiment': 'Compare the most promising routes with a bounded discriminating test tied to the complete intended journey. Preserve alternatives and original conditions.',
        'reconsider_when': 'Repeated repairs produce no new evidence, integration cost defeats the benefit, or observed use contradicts passing checks. Revisit framing, cause and evaluator before another patch.',
        'stop_rule': 'Scale discovery to uncertainty and consequence. Reuse current qualified evidence; stop when more search is unlikely to change the next decision. Do not require new research for routine settled work.',
        'limits': 'This packet does not browse, select a winner, enforce execution or certify improvement. Keep source inspection within the declared access policy.'}


def ui_review(task):
    """Provide property-level UI transfer guidance for relevant tasks only."""
    surfaces = {'web', 'website', 'ui', 'native-app', 'android', 'ios', 'mobile', 'desktop'}
    if task['surface'] not in surfaces and not {'ui', 'visual', 'design'}.intersection(task.get('tags', [])):
        return None
    return {'status': 'proposed; image inputs, reviews and rendered output require inspection',
            'module': 'references/ui-continuity.md', 'goal': task['goal'], 'journey': task['journey'],
            'access': task['access'],
            'operation': 'Transfer competence and visual character separately; attach real reference pixels, explore with image models, implement from a selected image and check actual rendered behavior.',
            'anchors': ['well-made shipped references with provenance and property-specific jobs',
                        'Geist utility typography and official Hugeicons unless an explicit applicable requirement differs',
                        'real font assets, component metrics, viewport and density rather than generated lettering'],
            'exploration': 'Give image models freedom over composition and use multiple interpretations when informative; avoid prescribing the whole layout or treating invented content as fact.',
            'review': 'Fresh-context critique of consequential generated candidates and actual coded screens, with readable references and no favored verdict; localize and repair drift before delivery.',
            'limits': 'Guidance is not image generation, independent review, user approval or visual/interaction qualification.'}


def apk_reconstruction_review(task):
    """APK-first comparison contract; no existing iOS counterpart is required."""
    if task['operation'] not in {'reconstruct', 'repair'} or not (
            task['surface'] in {'apk', 'android'} or 'apk-iphone' in task.get('tags', [])):
        return None
    return {
        'status': 'proposed; not evidence of a running reconstruction or fidelity',
        'module': 'references/apk-iphone.md',
        'goal': task['goal'], 'journey': task['journey'], 'access': task['access'],
        'reference': 'The supplied versioned APK and its original Android execution are the behavioral oracle. An existing iOS app and the user\'s personal phone are not prerequisites.',
        'operation': 'Recover original logic, assets and service contracts under the declared access policy; run original Android and reconstructed iOS journeys with equivalent inputs, service state, clocks and histories.',
        'runtime_qualification': 'Before installing, check actual guest ABI support, API level, boot completion and graphics initialization. An available system image or emulator executable is not a working oracle. After ambiguous install transport errors, inspect package-manager completion and the full installed split hash multiset before retrying.',
        'startup_dependencies': 'Trace initialization failures before treating a splash screen as UI evidence. Distinguish missing configuration, native/plugin contracts and external-service failures. Test reversible configuration adaptations through the original SDK path; retain the unmodified baseline and declared external-effect boundary. Do not replace initialization or complete journeys with success stubs.',
        'comparison': ['original entry and default state', 'complete interactions and durable outcomes',
                       'rendering and motion', 'platform adapters and deliberate differences'],
        'encoded_artifacts': 'When present, compare actual decoded bytes, serialization, rendering parameters, validity/refresh timing, lifecycle and error states. Do not substitute an arbitrary code image or assume rotation, signing or scanning from its appearance.',
        'service_boundary': 'Keep complete client flows operational. Isolate only explicitly requested external effects in a stateful test environment shared by both sides; record modified boundaries and unknown service behavior separately.',
        'quote_recovery': 'For quoted transactions, separate transport decoding, catalog values, client calculations and server quote authority. Trace caller/parser and product/event precedence; null, absent and zero are distinct. Bind comparisons to identical selected variants, quantities, identity class, location, currency, clock, promotions and service revision. Inspect displayed fee labels, tips, discounts, rounding, totals, requotes and failure states. Use legitimate captured or sandbox quotes as an independent oracle; controlled formulas qualify only fixture behavior. Do not infer final fees from a base price or arbitrary defaults. A read-like flag on a multiplexed transaction route does not prove absence of side effects; qualify the route before live access under the declared policy.',
        'test_identity': 'When synthetic accounts are requested, use an isolated provider emulator where compatible and local application-profile storage with synthetic identities. Preserve sign-up, verification, sign-in, session refresh, profile changes and account switching; when rapid testing is requested, add isolated password-free persona selection and immediate display-field editing through the actual app state, separate from normal auth-flow comparison; unknown server rules remain unknown. Never send test identities or emulator tokens to production. Qualify actual SDK routing and application-service integration separately from account creation.',
        'access_boundary': 'Binary/source evidence stays analyst-side in strict clean-room mode; independently reviewed behavior crosses the isolated implementer boundary.',
        'limits': 'Missing service data or authority is not solved by a screenshot or client rewrite. Simulator equivalence does not qualify physical performance or universal APK coverage.'}


def failure_review(task, repair=False):
    """Conditional repair guidance; never evidence that an audit ran."""
    triggers = {'reliability', 'compatibility', 'crash', 'offline', 'performance', 'repeated-failure'}
    if not (repair or task['operation'] == 'repair' or triggers.intersection(task.get('tags', []))):
        return None
    return {
        'status': 'proposed; agent must inspect and execute relevant checks',
        'module': 'references/failure-families.md',
        'goal': task['goal'], 'journey': task['journey'], 'access': task['access'],
        'operation': 'Bind the failure to the actual artifact/run, identify the broken assumption, inspect consequential siblings, change the producing path and verify completion/persistence.',
        'candidate_families': ['behavior-contract-coverage', 'resource-lifetime-capacity',
                               'lifecycle-representation', 'dependency-necessity',
                               'timing-work-amplification', 'durable-state-completion'],
        'record': ['observed counterexample and evidence', 'mechanism or competing hypotheses',
                   'producing operation and change', 'sibling coverage and unknowns',
                   'discriminating check and actual effective configuration', 'scope and revisit condition'],
        'limits': 'Families are hypotheses; no tools ran and no cause, coverage or success is established. Keep private evidence within its permitted boundary. Scale checks to the actual consequence.'}


def investigate(task, methods):
    plans = []
    for question in task.get('unknowns', []):
        candidates, blocked = [], []
        for method in methods['methods']:
            if task['surface'] not in method['surfaces'] and '*' not in method['surfaces']:
                continue
            if question['property'] not in method['properties']:
                continue
            missing = sorted(set(method['requires']) - set(task.get('capabilities', [])))
            proposed = dict(method, missing_capabilities=missing,
                            applicability='candidate; inspect conditions before choosing')
            (blocked if missing else candidates).append(proposed)
        plans.append(dict(question, candidates=candidates, unavailable=blocked,
                          status='requires-selection' if candidates else 'needs-new-method-or-access'))
    return {'scope': task['scope'], 'goal': task['goal'], 'journey': task['journey'],
            'access': task['access'], 'investigation': plans,
            'human_input': input_status(task), 'approach_review': approach_review(task),
            'ui_review': ui_review(task), 'failure_review': failure_review(task),
            'apk_reconstruction_review': apk_reconstruction_review(task),
            'stop_rule': 'Stop each probe at its stated evidence or bound; unknown is not recovered. Stop discovery when further search is unlikely to change the next decision; retain unresolved alternatives.',
            'limits': ['No tools installed or executed; capabilities are caller declarations, not verified receipts.',
                       'Method matches use exact surface/property labels, not semantic fit or optimal ranking.',
                       'Strict clean-room plans are analyst-side; exports and access enforcement are separate.']}


def descendants(records, roots):
    affected = set(roots)
    for record in records:  # links always point backward; one chronological pass suffices
        deps = record['data'].get('links', []) + record['data'].get('depends_on', [])
        if any(x in affected for x in deps):
            affected.add(record['id'])
    return affected


def impact(records, store, changed=()):
    by_id = {r['id']: r for r in records}
    unknown = set(changed) - set(by_id)
    if unknown:
        raise ValueError(f'unknown changed ids: {sorted(unknown)}')
    roots, reasons = set(changed), []
    for record in records:
        data = record['data']
        if record['kind'] == 'evidence' and 'local_path' in data:
            try:
                actual = rdd.digest(Path(store).parent / data['local_path'])
                if actual != data['sha256']:
                    roots.add(record['id'])
                    reasons.append({'id': record['id'], 'reason': 'file hash drift'})
            except rdd.JournalError as exc:
                roots.add(record['id'])
                reasons.append({'id': record['id'], 'reason': str(exc)})
        if record['kind'] == 'change':
            roots.update(data['links'])
            reasons.append({'id': record['id'], 'reason': data['reason'], 'scope': data['scope']})
    affected = descendants(records, roots)
    return {'roots': sorted(roots), 'affected': [r['id'] for r in records if r['id'] in affected],
            'reasons': reasons, 'limits': 'Only declared links/dependencies and captured file changes. Undeclared or newly added dependencies need inspection. Change records invalidate their linked historic chains; reobserve into fresh records.'}


def closure(records, identifiers):
    by_id = {r['id']: r for r in records}
    needed = set(identifiers)
    pending = list(needed)
    while pending:
        identifier = pending.pop()
        if identifier not in by_id:
            raise ValueError(f'unknown id: {identifier}')
        for dep in by_id[identifier]['data'].get('links', []) + by_id[identifier]['data'].get('depends_on', []):
            if dep not in needed:
                needed.add(dep)
                pending.append(dep)
    return [r for r in records if r['id'] in needed]


def compile_context(task, records, store, purpose='implement'):
    if purpose not in ('implement', 'repair'):
        raise ValueError('compile purpose must be implement or repair')
    by_id = {r['id']: r for r in records}
    selected = task.get('contributions', [])
    for identifier in selected:
        if identifier not in by_id or by_id[identifier]['kind'] != 'contribution':
            raise ValueError(f'not a contribution: {identifier}')
    stale = set(impact(records, store)['affected'])
    decisions, lessons, review_lessons = {}, [], []
    for record in records:
        data = record['data']
        if record['kind'] == 'decision' and data.get('task_scope') == task['scope']:
            for link in data.get('links', []):
                if by_id[link]['kind'] == 'contribution':
                    decisions[link] = record
        if record['kind'] == 'lesson':
            if matches(data.get('applies_to', {}), task):
                lessons.append(record)
            elif not data.get('applies_to'):
                review_lessons.append(record['id'])
    blockers, chosen = [], []
    blockers += [{'id': task['scope'], **item} for item in input_drift(task)]
    blockers += [{'id': c['id'], 'reason': 'unresolved synthesis conflict', 'issue': c['issue']} for c in task.get('conflicts', []) if not c['resolved']]
    for request in input_status(task)['waiting']:
        blockers.append({'id': request['id'], 'reason': 'required user input unresolved', 'dependent_work': request['dependent_work']})
    for identifier in selected:
        decision = decisions.get(identifier)
        if identifier in stale or (decision and decision['id'] in stale):
            blockers.append({'id': identifier, 'reason': 'affected by changed evidence/dependency; refresh into new records'})
        elif not decision or decision['data']['status'] != 'adopted':
            blockers.append({'id': identifier, 'reason': 'needs current adopted decision for exact task_scope'})
        elif decision['data'].get('context_sha256') != decision_basis(task):
            blockers.append({'id': identifier, 'reason': 'decision does not pin current task conditions; inspect and append revised decision'})
        else:
            chosen += [identifier, decision['id']]
    transfers = []
    requested = task.get('transfers', [])
    for identifier in requested:
        if identifier not in by_id or by_id[identifier]['kind'] != 'transfer':
            raise ValueError(f'not a transfer: {identifier}')
        record = by_id[identifier]
        linked = [x for x in record['data'].get('links', []) if by_id[x]['kind'] == 'contribution']
        if record['data'].get('task_scope') != task['scope'] or not set(linked) <= set(selected):
            blockers.append({'id': identifier, 'reason': 'transfer scope or contributions differ from task'})
        elif identifier in stale:
            blockers.append({'id': identifier, 'reason': 'transfer depends on changed evidence'})
        elif any(not decisions.get(c) or decisions[c]['id'] not in record['data'].get('depends_on', []) for c in linked):
            blockers.append({'id': identifier, 'reason': 'transfer does not pin current decision ids in depends_on'})
        else:
            transfers.append(record)
            chosen.append(identifier)
    for identifier in selected:
        if not any(identifier in t['data'].get('links', []) for t in transfers):
            blockers.append({'id': identifier, 'reason': 'no selected transfer contract for this task'})
    corrections = []
    for lesson in lessons:
        data = lesson['data']
        targets = data.get('targets', [])
        acknowledgments = [t['id'] for t in transfers if lesson['id'] in t['data'].get('depends_on', [])]
        affected = descendants(records, targets)
        relevant = [t for t in transfers if not targets or set(t['data'].get('links', []) + t['data'].get('depends_on', [])) & affected]
        applications = []
        for transfer in relevant:
            application = transfer['data'].get('correction_applications', {}).get(lesson['id'])
            if lesson['id'] not in transfer['data'].get('depends_on', []) or not isinstance(application, dict) or any(not isinstance(application.get(k), str) or not application[k].strip() for k in ('operation', 'change', 'check', 'limits')):
                blockers.append({'id': transfer['id'], 'reason': 'affected transfer lacks actionable correction application', 'lesson': lesson['id']})
            else:
                applications.append({'transfer': transfer['id'], **application})
        corrections.append({'record': lesson, 'targeted_impact': sorted(descendants(records, targets)),
                            'received_by_transfers': acknowledgments, 'applications': applications,
                            'implemented': 'not established', 'demonstrated': 'not established'})
        chosen.append(lesson['id'])
        if not acknowledgments:
            blockers.append({'id': lesson['id'], 'reason': 'applicable correction not acknowledged in selected transfer depends_on'})
    checks = [r for r in records if r['kind'] == 'check' and any(t['id'] in r['data'].get('links', []) for t in transfers)]
    required_reruns = []
    for transfer in transfers:
        related = [r for r in checks if transfer['id'] in r['data'].get('links', [])]
        if related and related[-1]['data']['outcome'] in ('failed', 'blocked'):
            rerun = {'transfer': transfer['id'], 'failed_check': related[-1]['id'],
                     'required': 'Repair producing operation and rerun the declared check; repair readiness is not delivery readiness.'}
            required_reruns.append(rerun)
            if purpose != 'repair':
                blockers.append({'id': transfer['id'], 'reason': 'latest declared check failed or blocked; repair or replace contract before handoff'})
    chosen += [r['id'] for r in checks]
    alternatives = [r for r in records if r['kind'] == 'contribution' and r['id'] not in selected]
    packet = {'scope': task['scope'], 'purpose': purpose, 'required_reruns': required_reruns, 'task': task, 'ready_for_handoff': not blockers,
              'human_input': input_status(task),
              'approach_review': approach_review(task, repair=purpose == 'repair' or bool(required_reruns)),
              'ui_review': ui_review(task),
              'apk_reconstruction_review': apk_reconstruction_review(task),
              'failure_review': failure_review(task, repair=purpose == 'repair' or bool(required_reruns)),
              'blockers': blockers, 'records': closure(records, chosen), 'corrections': corrections,
              'checks': checks, 'retained_alternative_ids': [r['id'] for r in alternatives],
              'unscoped_lesson_ids_for_review': review_lessons,
              'limits': ['Readiness means declared handoff completeness, not implementation success or semantic approval.',
                         'Competence/character contracts are supplied judgments; inspect their authority and conflict resolution.',
                         'All retained alternatives remain in the journal; query them when selected context is inadequate.']}
    packet['journal_sha256'] = rdd.digest(Path(store))
    packet['task_sha256'] = hashlib.sha256(json.dumps(task, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    packet['decision_context_sha256'] = decision_basis(task)
    if task['access'] == 'strict-clean-room':
        packet['ready_for_handoff'] = False
        packet['blockers'].append({'id': task['scope'], 'code': 'analyst-provenance', 'reason': 'analyst packet contains source provenance; use reviewed specification export and verified isolated implementer'})
    return packet


def assess(task, records, store):
    """Trace requested properties to current contracts and observed check evidence.

    Reports declared coverage, never semantic truth or universal equivalence.
    """
    packet = compile_context(task, records, store)
    by_id = {r['id']: r for r in records}
    stale = set(impact(records, store)['affected'])
    selected = set(task.get('transfers', []))
    coverage = []
    correction_gaps = []
    for correction in packet['corrections']:
        lesson_id = correction['record']['id']
        for application in correction['applications']:
            checks = [r for r in records if r['kind'] == 'check' and application['transfer'] in r['data'].get('links', []) and lesson_id in r['data'].get('links', [])]
            check = checks[-1] if checks else None
            evidence = [by_id[e] for e in check['data'].get('links', []) if by_id[e]['kind'] == 'evidence'] if check else []
            if not check or check['data']['outcome'] != 'passed' or check['id'] in stale or input_drift({'inputs': check['data'].get('artifact_inputs')}) or not any(e['data']['basis'] == 'observed' and e['id'] not in stale and e['data'].get('local_path') for e in evidence):
                correction_gaps.append({'lesson': lesson_id, 'transfer': application['transfer'], 'reason': 'correction application lacks current observed passed check'})
    for axis in ('competence', 'character'):
        for item in task[axis]:
            findings = []
            links = item.get('transfers', [])
            if not links:
                findings.append('property has no explicit transfer mapping')
            for identifier in links:
                if identifier not in selected:
                    findings.append(f'{identifier}: not a selected current transfer')
                    continue
                checks = [r for r in records if r['kind'] == 'check' and identifier in r['data'].get('links', [])]
                check = checks[-1] if checks else None
                if not check or check['data']['outcome'] != 'passed' or check['id'] in stale:
                    findings.append(f'{identifier}: no current passed check')
                    continue
                if input_drift({'inputs': check['data'].get('artifact_inputs')}):
                    findings.append(f'{identifier}: checked artifact snapshot is missing or changed')
                evidence = [by_id[e] for e in check['data'].get('links', []) if by_id[e]['kind'] == 'evidence']
                if not any(e['data']['basis'] == 'observed' and e['id'] not in stale and e['data'].get('local_path') for e in evidence):
                    findings.append(f'{identifier}: check lacks captured observed evidence')
            coverage.append({'axis': axis, 'property': item['property'], 'transfers': links,
                             'declared_coverage': not findings, 'gaps': findings})
    property_blockers = [b for b in packet['blockers'] if b.get('code') != 'analyst-provenance']
    property_ready = not property_blockers and bool(coverage) and all(c['declared_coverage'] for c in coverage) and not correction_gaps
    access = access_review(task, records, store)
    return {'scope': task['scope'], 'handoff_blockers': packet['blockers'], 'property_review_blockers': property_blockers, 'coverage': coverage,
            'ready_for_property_review': property_ready, 'access_review': access,
            'correction_gaps': correction_gaps,
            'ready_for_review': property_ready and access['ready'],
            'limits': 'Coverage checks declarations, provenance, selected contracts and evidence freshness. Inspect evidence and full journey to judge meaning; this is not automatic quality certification.'}



def access_review(task, records, store):
    """Verify captured mechanical boundary receipts, not semantic independence."""
    limits = 'Mechanical receipt review only. Image contents/history, model prior knowledge, semantic independence, asset rights and worker behavior require substantive review; a captured receipt is not cryptographic attestation.'
    if task['access'] != 'strict-clean-room':
        return {'ready': True, 'mode': 'source-assisted', 'gaps': [], 'limits': limits}
    gaps = []
    config = task.get('clean_room', {})
    if not isinstance(config, dict):
        return {'ready': False, 'mode': 'strict-clean-room', 'gaps': ['clean_room must be an object'], 'limits': limits}
    by_id = {r['id']: r for r in records}
    stale = set(impact(records, store)['affected'])
    captures = {}
    asset_declared = bool(config.get('assets_evidence') or config.get('assets_root'))
    for field in ('specification_evidence', 'receipt_evidence', *(['assets_evidence'] if asset_declared else [])):
        item = by_id.get(config.get(field))
        if not item or item['kind'] != 'evidence' or item['data'].get('basis') != 'observed' or not item['data'].get('local_path') or item['id'] in stale:
            gaps.append(field + ': needs fresh observed captured evidence in this journal')
            continue
        try:
            captures[field] = load(Path(store).parent / item['data']['local_path'])
        except (OSError, ValueError) as exc:
            gaps.append(field + ': unreadable capture: ' + str(exc))
    for field in ('image_review', 'worker_review'):
        declaration = config.get(field)
        if not isinstance(declaration, dict) or declaration.get('reviewed') is not True or any(not isinstance(declaration.get(k), str) or not declaration[k].strip() for k in ('reviewer', 'declaration', 'limits')):
            gaps.append(field + ': needs reviewed=true and reviewer/declaration/limits')
    spec, receipt = captures.get('specification_evidence'), captures.get('receipt_evidence')
    if spec is not None:
        try:
            review_export(spec)
            if spec['scope'] != task['scope'] or spec['goal'] != task['goal'] or spec['audience'] != task['audience'] or spec['journey'] != task['journey']:
                gaps.append('specification scope/goal/audience/journey differ from current task')
        except (ValueError, TypeError, KeyError) as exc:
            gaps.append('specification review: ' + str(exc))
    if receipt is not None:
        if not isinstance(receipt, dict):
            gaps.append('receipt must be an object')
        else:
            image = receipt.get('image', '')
            if not isinstance(image, str) or len(image) != 71 or not image.startswith('sha256:') or any(c not in '0123456789abcdef' for c in image[7:]):
                gaps.append('receipt lacks pinned image SHA256 identity')
            image_review = config.get('image_review')
            if not isinstance(image_review, dict) or image_review.get('image') != image:
                gaps.append('image_review image differs from receipt image')
            if spec is not None:
                digest = hashlib.sha256(json.dumps(spec, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                if receipt.get('specification_sha256') != digest:
                    gaps.append('receipt specification_sha256 differs from reviewed specification')
            if receipt.get('boundary_probes_passed') is not True or receipt.get('worker_executed') is not True or type(receipt.get('worker_exit')) is not int or receipt['worker_exit'] != 0:
                gaps.append('receipt needs passed boundary probes and executed worker exit 0')
            approved = {}
            if receipt.get('asset_inventory') or receipt.get('asset_manifest_sha256') or asset_declared:
                try:
                    manifest = captures.get('assets_evidence')
                    root = config.get('assets_root')
                    if not manifest or not isinstance(root, str) or not root.strip():
                        raise ValueError('assets need fresh captured manifest and assets_root')
                    asset_root = Path(root) if Path(root).is_absolute() else Path(store).parent / root
                    approved = assets.snapshot(manifest, asset_root, task['scope'])
                    if receipt.get('asset_scope') != task['scope'] or receipt.get('asset_manifest_sha256') != assets.identity(manifest) or receipt.get('asset_inventory') != assets.inventory(approved):
                        raise ValueError('receipt assets differ from current approved manifest/bytes/scope')
                except (OSError, ValueError, TypeError) as exc:
                    gaps.append('asset review: ' + str(exc))
            declared_output = config.get('output_directory')
            output = receipt.get('output_directory')
            if not isinstance(output, str) or not output.strip() or not isinstance(declared_output, str) or not declared_output.strip():
                gaps.append('clean_room and receipt need output_directory')
            else:
                root = Path(store).parent
                destination = Path(output) if Path(output).is_absolute() else root / output
                declared = Path(declared_output) if Path(declared_output).is_absolute() else root / declared_output
                if destination.resolve() != declared.resolve():
                    gaps.append('receipt output_directory differs from declared current artifact')
                try:
                    if destination.is_symlink() or not destination.is_dir():
                        raise ValueError('output must be an ordinary directory')
                    inventory = receipt.get('output_inventory')
                    if not isinstance(inventory, list) or not inventory or len(inventory) > 1000:
                        raise ValueError('output inventory must contain 1..1000 files')
                    expected = {}
                    for entry in inventory:
                        name = entry.get('path') if isinstance(entry, dict) else None
                        if not isinstance(name, str) or not name or Path(name).is_absolute() or '..' in Path(name).parts or name in expected:
                            raise ValueError('invalid or duplicate output inventory path')
                        expected[name] = entry.get('sha256')
                    actual = {}
                    total_entries = 0
                    total_bytes = 0
                    for path in destination.rglob('*'):
                        total_entries += 1
                        if total_entries > 2000:
                            raise ValueError('output exceeds bounded traversal size')
                        if path.is_symlink() or (not path.is_file() and not path.is_dir()):
                            raise ValueError('output contains symlink or special file')
                        if path.is_file():
                            size = path.stat().st_size
                            total_bytes += size
                            if size > 50 * 1024 * 1024 or len(actual) >= 1000 or total_bytes > 200 * 1024 * 1024:
                                raise ValueError('output exceeds bounded inventory size')
                            actual[str(path.relative_to(destination))] = rdd.digest(path)
                    if actual != expected:
                        raise ValueError('output inventory differs from current artifact files/hashes')
                    if approved:
                        allowed_assets = {'assets/' + e['path']: e['sha256'] for e in assets.inventory(approved)}
                        for name, digest in actual.items():
                            if name.startswith('assets/') and allowed_assets.get(name) != digest:
                                raise ValueError('delivered asset differs from approved whole file')
                except (OSError, ValueError) as exc:
                    gaps.append('output review: ' + str(exc))
    return {'ready': not gaps, 'mode': 'strict-clean-room', 'gaps': gaps, 'limits': limits}


def review_export(spec):
    """Allowlist behavioral fields; this is a review aid, not an isolation claim."""
    allowed = {'scope', 'goal', 'audience', 'journey', 'behaviors', 'unknowns', 'acceptance', 'review'}
    if not isinstance(spec, dict) or set(spec) - allowed:
        raise ValueError('export has fields outside behavioral allowlist')
    for key in ('scope', 'goal', 'audience'):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            raise ValueError(f'export needs {key}')
    journey = spec.get('journey')
    if not isinstance(journey, dict) or set(journey) != {'entry', 'default', 'action', 'outcome', 'reset'} or any(not isinstance(v, str) or not v.strip() for v in journey.values()):
        raise ValueError('export journey must contain behavioral entry/default/action/outcome/reset')
    for key in ('behaviors', 'unknowns', 'acceptance'):
        strings(spec.get(key), key, key == 'unknowns')
    review = spec.get('review')
    if not isinstance(review, dict) or set(review) != {'reviewer', 'implementation_independent', 'source_free', 'asset_rights', 'limits'} or not isinstance(review['reviewer'], str) or not review['reviewer'].strip() or not isinstance(review['limits'], str) or not review['limits'].strip():
        raise ValueError('export requires explicit review identity and limits')
    if any(review[k] is not True for k in ('implementation_independent', 'source_free', 'asset_rights')):
        raise ValueError('export review assertions must be true')
    # Reject common obvious provenance bypasses, still require substantive human/agent review.
    for key in allowed - {'review'}:
        text = json.dumps(spec.get(key, '')).casefold()
        if any(token in text for token in ('http://', 'https://', 'file://', 'local_path', 'sha256', '```', '../')):
            raise ValueError(f'export {key} contains source/link/code markers requiring removal')
    return {'specification': spec, 'review_status': 'declared reviewed; semantic independence not mechanically proven',
            'isolation_verified': False, 'next': 'Deliver only specification to an access-constrained fresh implementer. Check file/tool/network/retrieval boundaries and record actual denial receipts separately.'}


def seed(store, methods):
    """Retain research mechanisms as candidates, never as adoption decisions."""
    records, _ = rdd.read_records(store, allow_missing=True)
    by_id = {r['id']: r for r in records}
    pending = []
    for method in methods['methods']:
        prefix = 'research:' + method['id']
        batch = [
            {'id': prefix + ':reference', 'kind': 'reference', 'data': {
                'locator': method['source'], 'job': method['mechanism'],
                'inspection': 'Distilled from prior source inspection documented in the package catalog; upstream execution and current availability not established.',
                'license_observation': method['license']}},
            {'id': prefix + ':evidence', 'kind': 'evidence', 'data': {
                'links': [prefix + ':reference'], 'claim': method['mechanism'],
                'basis': 'documented', 'conditions': method['conditions'],
                'limits': method['limit']}},
            {'id': prefix + ':contribution', 'kind': 'contribution', 'data': {
                'links': [prefix + ':evidence'], 'property': method['invariant'],
                'conditions': method['conditions'], 'delta': method['delta'], 'test': method['probe'],
                'surfaces': method['surfaces'], 'properties': method['properties'],
                'requires': method['requires'], 'limits': method['limit']}}
        ]
        for item in batch:
            if item['id'] in by_id:
                if by_id[item['id']] != item:
                    raise ValueError(f'seed revision differs for {item["id"]}; preserve original and import updated mechanism with a new id')
                continue
            rdd.validate(item, by_id, Path(store))
            by_id[item['id']] = item
            pending.append(item)
    for item in pending:
        rdd.append(store, item)
    return {'added': len(pending), 'status': 'retained candidates only; task-scoped adoption and transfer contracts still required'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    plan = commands.add_parser('plan', help='propose conditional investigation methods; executes no tools')
    plan.add_argument('--task', required=True, type=Path)
    plan.add_argument('--catalog', type=Path, default=METHODS)
    context = commands.add_parser('compile', help='compile task-scoped decisions, transfers, corrections and blockers')
    context.add_argument('store', type=Path)
    context.add_argument('--task', type=Path, required=True)
    context.add_argument('--purpose', choices=('implement', 'repair'), default='implement', help='repair retains failed checks and required reruns; does not waive provenance, decision, input or access blockers')
    assessment = commands.add_parser('assess', help='trace declared competence/character to current transfers and captured check evidence')
    assessment.add_argument('store', type=Path)
    assessment.add_argument('--task', type=Path, required=True)
    change = commands.add_parser('impact', help='inspect hash drift and downstream declared dependencies')
    change.add_argument('store', type=Path)
    change.add_argument('--changed', action='append', default=[])
    export = commands.add_parser('review-export', help='validate declared behavioral export; does not establish isolation')
    export.add_argument('spec', type=Path)
    snapshot = commands.add_parser('fingerprint', help='hash selected context files and bounded directory inventories')
    snapshot.add_argument('--root', type=Path, required=True)
    snapshot.add_argument('--file', action='append', default=[])
    snapshot.add_argument('--tree', action='append', default=[])
    retain = commands.add_parser('seed', help='retain conditional research catalog in a journal; adopts nothing')
    retain.add_argument('store', type=Path)
    retain.add_argument('--catalog', type=Path, default=METHODS)
    basis = commands.add_parser('basis', help='hash decision conditions to pin in adopted records')
    basis.add_argument('--task', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'basis':
            result = {'context_sha256': decision_basis(task_spec(load(args.task)))}
        elif args.command == 'seed':
            result = seed(args.store, catalog(args.catalog))
        elif args.command == 'fingerprint':
            result = fingerprint(args.root, args.file, args.tree)
        elif args.command == 'plan':
            result = investigate(task_spec(load(args.task)), catalog(args.catalog))
        elif args.command == 'review-export':
            result = review_export(load(args.spec))
        else:
            records, _ = rdd.read_records(args.store, verify_files=False)
            if args.command == 'impact':
                result = impact(records, args.store, args.changed)
            else:
                task = task_spec(load(args.task))
                result = assess(task, records, args.store) if args.command == 'assess' else compile_context(task, records, args.store, args.purpose)
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        if args.command == 'compile' and not result['ready_for_handoff']:
            return 2
        if args.command == 'assess' and not result['ready_for_review']:
            return 2
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
