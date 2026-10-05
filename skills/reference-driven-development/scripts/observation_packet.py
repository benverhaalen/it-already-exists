#!/usr/bin/env python3
"""Export reviewed Android journal evidence for independent comparison.

Integrity binding is not device attestation. Keep this outside the implementer.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile
import xml.etree.ElementTree as ET

from comparison import bound_file, canonical, validate_contract
from offline_worker import strict_json


def read(path, limit=67108864):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('ordinary input file required')
    with path.open('rb') as stream:
        data = stream.read(limit+1)
    if len(data) > limit:
        raise ValueError('input exceeds byte limit')
    return data


def sha(data):
    return hashlib.sha256(data).hexdigest()


def apk_hash(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError('ordinary APK file required')
    digest, total = hashlib.sha256(), 0
    with path.open('rb') as stream:
        while chunk := stream.read(1048576):
            total += len(chunk)
            if total > 1073741824:
                raise ValueError('APK exceeds byte limit')
            digest.update(chunk)
    return digest.hexdigest()


def extract(actual, rule):
    """Small reviewed data projections; never execute observer-supplied code."""
    kind = rule['kind']
    if kind == 'text':
        return actual
    if kind == 'json':
        value = strict_json(actual)
        path = rule.get('path')
        if not isinstance(path, list) or not path or any(not isinstance(k, str) for k in path):
            raise ValueError('JSON projection needs string keys')
        for key in path:
            if not isinstance(value, dict) or key not in value:
                raise ValueError('missing JSON projection')
            value = value[key]
        return value
    if kind == 'android-preference-int':
        # Android preferences are plain XML; forbid expansion and ambiguity.
        if '<!DOCTYPE' in actual.upper() or '<!ENTITY' in actual.upper():
            raise ValueError('XML declarations forbidden')
        root = ET.fromstring(actual)
        matches = [e for e in root if e.tag == 'int' and e.get('name') == rule.get('name')]
        if root.tag != 'map' or len(matches) != 1:
            raise ValueError('unique integer preference required')
        return int(matches[0].attrib['value'])
    raise ValueError('unsupported state projection')


def prepare(session, config, contract, selection, review, apks):
    validate_contract(contract)
    raw = read(Path(session)/'events.jsonl')
    identity = sha(json.dumps(config, sort_keys=True).encode())
    binding = dict(journal_sha256=sha(raw), config_sha256=identity,
                   contract_sha256=canonical(contract), selection_sha256=canonical(selection))
    if review.get('approved') is not True or not isinstance(review.get('reviewer'), str) or not review['reviewer']:
        raise ValueError('independent evidence review required')
    if any(review.get(k) != v for k, v in binding.items()):
        raise ValueError('review does not bind current evidence and selection')
    if not apks or len(apks) > 64:
        raise ValueError('all installed APKs required')
    hashes = sorted(apk_hash(p) for p in apks)
    if hashes != sorted(config.get('apk_sha256s', [])):
        raise ValueError('supplied APK bytes differ from qualified configuration')
    lines = raw.decode().splitlines()
    if not lines or len(lines) > 20000:
        raise ValueError('bounded nonempty journal required')
    events = [strict_json(line) for line in lines]
    run = events[0]['session_id']
    groups, order = {}, []
    previous = -math.inf
    for event in events:
        stamp = event.get('monotonic')
        if event.get('session_id') != run or type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp < previous:
            raise ValueError('mixed session or unordered journal')
        previous = stamp
        aid = event.get('attempt_id')
        if not isinstance(aid, str) or not aid:
            raise ValueError('attempt identity missing')
        if aid not in groups:
            order.append(aid)
            groups[aid] = []
        elif order[-1] != aid:
            raise ValueError('interleaved attempt histories')
        groups[aid].append(event)
    milestones = selection.get('milestones')
    if not isinstance(milestones, list) or not milestones or len(milestones) > 1000:
        raise ValueError('complete bounded milestone selection required')
    chosen = [m['attempt_id'] for m in milestones]
    if len(set(chosen)) != len(chosen) or any(a not in groups for a in chosen):
        raise ValueError('unique existing attempts required')
    indices = [order.index(a) for a in chosen]
    if indices != list(range(indices[0], indices[0]+len(indices))):
        raise ValueError('journey cannot omit or reorder intervening attempts')
    if len({m['id'] for m in milestones}) != len(milestones) or any(not isinstance(m['id'], str) or not m['id'] for m in milestones):
        raise ValueError('unique nonempty milestone IDs required')
    for key in ('fixture', 'journey'):
        if not isinstance(selection.get(key), str) or not selection[key]:
            raise ValueError('reviewed starting conditions and journey required')
    observations, images = [], {}
    for milestone in milestones:
        history = groups[milestone['attempt_id']]
        end = history[-1]
        if history[0]['kind'] != 'attempt_started' or end['kind'] != 'attempt_completed' or any(e['kind'] in ('attempt_failed', 'attempt_completed', 'attempt_started') for e in history[1:-1]):
            raise ValueError('selected attempt must have one successful complete history')
        if end['operation'] != milestone['operation'] or history[0]['operation'] != end['operation']:
            raise ValueError('milestone operation mismatch')
        state = end['state']
        if state.get('session_id') != run or state.get('config_sha256') != identity or state.get('qualified') is not True or state.get('uncertain_mutation') is not None:
            raise ValueError('unqualified or uncertain completed observation')
        if sorted(state['environment'].get('apk_sha256s', [])) != hashes:
            raise ValueError('observed installed APK differs from supplied bytes')
        actions = [e['action'] for e in history if e['kind'] == 'input_acknowledged']
        if actions != milestone.get('actions', []):
            raise ValueError('observed action sequence differs from reviewed journey')
        last_input = max((i for i, e in enumerate(history) if e['kind'] == 'input_acknowledged'), default=-1)
        polls = [e for e in history[last_input+1:] if e['kind'] == 'probes']
        if not polls or not polls[-1]['outcomes'] or any(o.get('status') != 'passed' for o in polls[-1]['outcomes']):
            raise ValueError('successful post-input probes required')
        probe = polls[-1]
        outcomes = probe['outcomes']
        if len({o['id'] for o in outcomes}) != len(outcomes):
            raise ValueError('duplicate probe identities')
        projected = {}
        for name, rule in milestone.get('state', {}).items():
            found = [o for o in outcomes if o['id'] == rule['probe']]
            if len(found) != 1:
                raise ValueError('state projection requires final post-input probe')
            projected[name] = extract(found[0]['actual'], rule)
        capture = state['capture']
        frames = [e for e in history if e['kind'] == 'capture']
        if not frames or any(frames[-1].get(k) != v for k, v in capture.items()) or frames[-1]['monotonic'] < probe['monotonic']:
            raise ValueError('final state and capture are not fresh matching evidence')
        required = capture['required_stability']
        operation = end['operation']
        profile = actions[-1]['kind']+'-after' if operation == 'act' and actions else {
            'reset': 'reset-after', 'qualify': 'qualify', 'capture': 'capture', 'reconcile': 'reconcile'}.get(operation)
        if capture['capture_policy'] != profile:
            raise ValueError('capture policy does not match completed operation')
        configured = config.get('capture_stability_overrides', {}).get(capture['capture_policy'], config.get('capture_stability', 1))
        if type(required) is not int or required < 1 or required != configured:
            raise ValueError('invalid capture stability')
        if required > 1:
            stable = [e for e in history if e['kind'] == 'capture_stability']
            tail = frames[-required:]
            if not stable or len(tail) != required or stable[-1]['capture_ids'] != [e['capture_id'] for e in tail] or stable[-1]['required_stability'] != required or stable[-1]['capture_policy'] != capture['capture_policy'] or any(e['sha256'] != capture['sha256'] or e['monotonic'] < probe['monotonic'] for e in tail):
                raise ValueError('fresh consecutive stability evidence missing')
            for frame in tail:
                bound_file(session, frame)
        if capture['path'] != capture['capture_id']+'.png' or Path(capture['path']).name != capture['path']:
            raise ValueError('session capture filename identity mismatch')
        payload = bound_file(session, capture)
        images[capture['path']] = payload
        observations.append(dict(id=milestone['id'], run_id=run, time=frames[-1]['monotonic'], state=projected,
                                 image=dict(path=capture['path'], sha256=capture['sha256']),
                                 attempt_id=milestone['attempt_id'], capture_id=capture['capture_id'],
                                 state_time=probe['monotonic'], capture_policy=capture['capture_policy']))
    value = dict(run_id=run, artifact_sha256=hashes[0] if len(hashes) == 1 else canonical(dict(apk_sha256s=hashes)),
                 apk_sha256s=hashes, contract_sha256=canonical(contract), fixture=selection['fixture'],
                 journey=selection['journey'], timestamp_basis='host_monotonic_seconds', observations=observations,
                 provenance=dict(**binding, reviewer=review['reviewer'], review_sha256=canonical(review)),
                 limits=['Observer journal is integrity-bound, not cryptographic device attestation.',
                         'State probes and captures are sequential, not an atomic snapshot.',
                         'Host capture completion does not measure guest presentation time.',
                         'Semantic projection and starting conditions require independent review.'])
    return value, images


def publish(output, packet, images):
    output = Path(output)
    if output.exists() or output.is_symlink():
        raise ValueError('output must be new')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix='.rdd-packet-', dir=output.parent))
    try:
        for name, data in images.items():
            path = temporary/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        (temporary/'packet.json').write_text(json.dumps(packet, indent=2, allow_nan=False)+'\n')
        # Refuse an existing output even if another producer created it meanwhile.
        output.mkdir()
        for path in temporary.iterdir():
            shutil.move(str(path), output/path.name)
    finally:
        shutil.rmtree(temporary)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('session', 'config', 'contract', 'selection', 'review', 'output'):
        parser.add_argument('--'+key, required=True)
    parser.add_argument('--apk', action='append', required=True)
    args = parser.parse_args()
    try:
        values = [strict_json(read(getattr(args, key)).decode()) for key in ('config', 'contract', 'selection', 'review')]
        value, images = prepare(args.session, *values, args.apk)
        publish(args.output, value, images)
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError) as error:
        parser.exit(1, str(error)+'\n')


if __name__ == '__main__':
    main()
