#!/usr/bin/env python3
"""Independent property comparisons with hashed evidence and three-valued outcomes.

Packets must be produced by a reviewed observer. This validates evidence binding,
not the truth of arbitrary observer declarations. Pillow is optional for pixels.
"""
import argparse
import hashlib
import io
import json
import math
from pathlib import Path
import sys

from offline_worker import strict_json

MISSING = object()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def field(value, path):
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return MISSING
        value = value[key]
    return value


def bound_file(root, evidence):
    name = evidence['path']
    if not isinstance(name, str) or not name:
        raise ValueError('evidence path must be nonempty')
    relative = Path(name)
    if relative.is_absolute() or '..' in relative.parts:
        raise ValueError('evidence path escapes root')
    root = Path(root)
    if root.is_symlink():
        raise ValueError('evidence root must not be a symlink')
    # macOS /var itself is a system symlink. Resolve the selected root, then
    # reject links inside that root; unrelated ancestors are not evidence.
    root = root.resolve(strict=True)
    path = root/relative
    current = path
    while current != root:
        if current.is_symlink():
            raise ValueError('evidence must be an ordinary non-symlink file')
        current = current.parent
    if not path.is_file():
        raise ValueError('evidence must be an ordinary non-symlink file')
    if path.stat().st_size > 33554432:
        raise ValueError('evidence exceeds byte limit')
    with path.open('rb') as stream:
        data = stream.read(33554433)
    if len(data) > 33554432:
        raise ValueError('evidence exceeds byte limit')
    if hashlib.sha256(data).hexdigest() != evidence['sha256']:
        raise ValueError('stale or changed evidence file')
    return data


def packet(value):
    for key in ('run_id', 'artifact_sha256', 'contract_sha256', 'fixture', 'journey'):
        if not value.get(key):
            raise ValueError('packet needs '+key)
    seen = set()
    last = -math.inf
    for frame in value.get('observations', []):
        if frame.get('run_id') != value['run_id']:
            raise ValueError('mixed trajectory run identities')
        if not isinstance(frame.get('id'), str) or frame['id'] in seen:
            raise ValueError('unique observation identifiers required')
        seen.add(frame['id'])
        timestamp = frame.get('time')
        if type(timestamp) not in (int, float) or not math.isfinite(timestamp) or timestamp < last:
            raise ValueError('ordered finite observation timestamps required')
        bounds = frame.get('time_bounds')
        if bounds is not None:
            if not isinstance(bounds, list) or len(bounds) != 2 or any(type(v) not in (int, float) or not math.isfinite(v) for v in bounds) or not bounds[0] <= timestamp <= bounds[1]:
                raise ValueError('time bounds must be finite and contain the observation time')
        last = timestamp
    return {f['id']: f for f in value.get('observations', [])}


def result(identifier, status, reason, **details):
    return dict(id=identifier, status=status, reason=reason, **details)


def validate_contract(contract):
    """Reject invalid evaluation rules even when their evidence is missing."""
    properties = contract.get('properties', [])
    if not isinstance(properties, list) or not properties or len(properties) > 1000:
        raise ValueError('nonempty bounded property set required')
    seen = set()
    def rectangle(value):
        return isinstance(value, list) and len(value) == 4 and all(type(x) is int for x in value) and 0 <= value[0] < value[2] and 0 <= value[1] < value[3]
    def number(value):
        return type(value) in (int, float) and math.isfinite(value)
    for rule in properties:
        if not isinstance(rule, dict) or not isinstance(rule.get('id'), str) or not rule['id'] or rule['id'] in seen:
            raise ValueError('unique nonempty property identifiers required')
        seen.add(rule['id'])
        kind = rule.get('kind')
        if kind not in ('state', 'pixels', 'duration', 'trajectory'):
            raise ValueError('unknown property kind')
        if kind != 'trajectory':
            if any(not isinstance(rule.get(key, rule.get('observation')), str) or not rule.get(key, rule.get('observation')) for key in ('reference_observation', 'candidate_observation')):
                raise ValueError('property needs reference and candidate observation identifiers')
        if kind == 'state':
            if not isinstance(rule.get('path'), list) or not rule['path'] or any(not isinstance(k, str) or not k for k in rule['path']):
                raise ValueError('state path must be nonempty string keys')
            if rule.get('operator', 'equals') not in ('equals', 'not_equals', 'within'):
                raise ValueError('unsupported state operator')
            if rule.get('operator') == 'within' and (not number(rule.get('tolerance')) or rule['tolerance'] < 0):
                raise ValueError('numeric comparison needs finite nonnegative tolerance')
        if kind == 'duration':
            if not isinstance(rule.get('start'), str) or not rule['start'] or not number(rule.get('tolerance')) or rule['tolerance'] < 0:
                raise ValueError('invalid duration contract')
        if kind == 'pixels':
            tolerance, ratio = rule.get('channel_tolerance', 0), rule.get('max_changed_ratio', 0)
            if type(tolerance) is not int or not 0 <= tolerance <= 255 or not number(ratio) or not 0 <= ratio <= 1:
                raise ValueError('pixel tolerance out of bounds')
            for key in ('reference_crop', 'candidate_crop', 'region'):
                if key in rule and not rectangle(rule[key]):
                    raise ValueError('invalid '+key)
            if not isinstance(rule.get('masks', []), list):
                raise ValueError('masks must be a list')
            for mask in rule.get('masks', []):
                if not isinstance(mask, dict) or not isinstance(mask.get('reason'), str) or not mask['reason'] or not rectangle(mask.get('rect')):
                    raise ValueError('mask needs rectangle and reason')
        if kind == 'trajectory':
            routes = rule.get('allowed')
            if routes is not None and (not isinstance(routes, list) or not routes or any(not isinstance(route, list) or any(not isinstance(v, str) or not v for v in route) for route in routes)):
                raise ValueError('explicit complete alternative trajectories required')
            if not isinstance(rule.get('forbidden', []), list) or any(not isinstance(v, str) or not v for v in rule.get('forbidden', [])):
                raise ValueError('forbidden observations must be identifiers')
    return properties


def pixels(left, right, rule, reference_root, candidate_root):
    from PIL import Image, ImageChops, ImageDraw
    payloads = [bound_file(reference_root, left['image']), bound_file(candidate_root, right['image'])]
    images = []
    for i, payload in enumerate(payloads):
        # Decode the very bytes whose hash was checked, not a second path read.
        with Image.open(io.BytesIO(payload)) as source:
            if source.width*source.height > 32000000:
                raise ValueError('image geometry exceeds bounds')
            source.load()
            image = source.convert('RGBA')
        crop = rule.get('reference_crop' if i == 0 else 'candidate_crop')
        if crop:
            if len(crop) != 4 or any(type(x) is not int for x in crop) or not 0 <= crop[0] < crop[2] <= image.width or not 0 <= crop[1] < crop[3] <= image.height:
                raise ValueError('invalid explicit crop')
            image = image.crop(crop)
        images.append(image)
    if images[0].size != images[1].size:
        return 'failed', 'geometry_mismatch', dict(reference_size=images[0].size, candidate_size=images[1].size)
    width, height = images[0].size
    region = rule.get('region', [0, 0, width, height])
    if len(region) != 4 or any(type(x) is not int for x in region) or not 0 <= region[0] < region[2] <= width or not 0 <= region[1] < region[3] <= height:
        raise ValueError('invalid comparison region')
    tolerance = rule.get('channel_tolerance', 0)
    ratio_limit = rule.get('max_changed_ratio', 0)
    if type(tolerance) is not int or not 0 <= tolerance <= 255 or type(ratio_limit) not in (int, float) or not 0 <= ratio_limit <= 1:
        raise ValueError('pixel tolerance out of bounds')
    masks = rule.get('masks', [])
    for mask in masks:
        rect = mask.get('rect', [])
        if not mask.get('reason') or len(rect) != 4 or any(type(x) is not int for x in rect) or not 0 <= rect[0] < rect[2] <= width or not 0 <= rect[1] < rect[3] <= height:
            raise ValueError('mask needs bounded rectangle and reason')
    # C-backed channel operations avoid an interpreted loop over every phone
    # pixel. Include alpha explicitly; visual equality must not hide its change.
    channels = ImageChops.difference(*images).split()
    maximum = channels[0]
    for channel in channels[1:]:
        maximum = ImageChops.lighter(maximum, channel)
    changed = maximum.point([255 if value > tolerance else 0 for value in range(256)])
    included = Image.new('L', (width, height), 0)
    draw = ImageDraw.Draw(included)
    draw.rectangle([region[0], region[1], region[2]-1, region[3]-1], fill=255)
    for mask in masks:
        x1, y1, x2, y2 = mask['rect']
        draw.rectangle([x1, y1, x2-1, y2-1], fill=0)
    total = included.histogram()[255]
    ignored = (region[2]-region[0])*(region[3]-region[1])-total
    changes = ImageChops.multiply(changed, included).histogram()[255]
    if not total:
        raise ValueError('mask removes entire property region')
    ratio = changes/total
    return ('passed' if ratio <= ratio_limit else 'failed'), 'region_pixel_difference', dict(changed=changes, compared=total, ignored=ignored, ratio=ratio, limit=ratio_limit)


def compare(contract, reference, candidate, reference_root, candidate_root):
    properties = validate_contract(contract)
    expected_contract = canonical(contract)
    a, b = packet(reference), packet(candidate)
    if any(p['contract_sha256'] != expected_contract for p in (reference, candidate)):
        raise ValueError('evidence uses another property contract')
    if any(reference[k] != candidate[k] for k in ('fixture', 'journey')):
        raise ValueError('reference/candidate starting conditions are not equivalent')
    outcomes = []
    for rule in properties:
        identifier, kind = rule['id'], rule['kind']
        ref_id = rule.get('reference_observation', rule.get('observation'))
        cand_id = rule.get('candidate_observation', rule.get('observation'))
        left, right = a.get(ref_id), b.get(cand_id)
        if kind != 'trajectory' and (left is None or right is None):
            outcomes.append(result(identifier, 'not_tested', 'missing_observation'))
            continue
        if kind == 'state':
            path = rule['path']
            if not isinstance(path, list) or not path or any(not isinstance(k, str) for k in path):
                raise ValueError('state path must be nonempty string keys')
            expected, actual = field(left.get('state', {}), path), field(right.get('state', {}), path)
            if expected is MISSING or actual is MISSING:
                outcomes.append(result(identifier, 'not_tested', 'missing_state_field'))
                continue
            expected = rule.get('expected', expected)
            operator = rule.get('operator', 'equals')
            if operator == 'equals':
                passed = type(expected) == type(actual) and expected == actual
            elif operator == 'not_equals':
                passed = type(expected) != type(actual) or expected != actual
            elif operator == 'within':
                tolerance = rule.get('tolerance')
                if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance < 0 or type(actual) not in (int, float) or type(expected) not in (int, float) or not math.isfinite(actual) or not math.isfinite(expected):
                    raise ValueError('numeric comparison needs finite tolerance and numbers')
                passed = abs(actual-expected) <= tolerance
            else:
                raise ValueError('unsupported state operator')
            outcomes.append(result(identifier, 'passed' if passed else 'failed', 'state_assertion', expected=expected, actual=actual))
        elif kind == 'pixels':
            if not left.get('image') or not right.get('image'):
                outcomes.append(result(identifier, 'not_tested', 'missing_image'))
                continue
            try:
                status, reason, details = pixels(left, right, rule, reference_root, candidate_root)
                outcomes.append(result(identifier, status, reason, **details))
            except (OSError, ValueError, ImportError) as error:
                outcomes.append(result(identifier, 'not_tested', 'unusable_image_evidence', detail=str(error)))
        elif kind == 'duration':
            start = rule['start']
            if start not in a or start not in b or not reference.get('timestamp_basis') or reference.get('timestamp_basis') != candidate.get('timestamp_basis'):
                outcomes.append(result(identifier, 'not_tested', 'missing_or_incompatible_clock_basis'))
                continue
            expected, actual = left['time']-a[start]['time'], right['time']-b[start]['time']
            tolerance = rule['tolerance']
            if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or tolerance < 0 or min(actual, expected) < 0:
                raise ValueError('invalid duration contract')
            frames = (a[start], left, b[start], right)
            if any('time_bounds' in frame for frame in frames):
                bounds = [frame.get('time_bounds', [frame['time'], frame['time']]) for frame in frames]
                reference_duration = [bounds[1][0]-bounds[0][1], bounds[1][1]-bounds[0][0]]
                candidate_duration = [bounds[3][0]-bounds[2][1], bounds[3][1]-bounds[2][0]]
                if min(reference_duration[0], candidate_duration[0]) < 0:
                    outcomes.append(result(identifier, 'not_tested', 'uncertain_event_order',
                        expected_bounds=reference_duration, actual_bounds=candidate_duration, tolerance=tolerance))
                    continue
                delta = [candidate_duration[0]-reference_duration[1], candidate_duration[1]-reference_duration[0]]
                nearest = 0 if delta[0] <= 0 <= delta[1] else min(abs(v) for v in delta)
                furthest = max(abs(v) for v in delta)
                status = 'passed' if furthest <= tolerance else 'failed' if nearest > tolerance else 'not_tested'
                outcomes.append(result(identifier, status, 'bounded_duration_difference',
                    expected=expected, actual=actual, expected_bounds=reference_duration,
                    actual_bounds=candidate_duration, difference_bounds=delta, tolerance=tolerance))
            else:
                outcomes.append(result(identifier, 'passed' if abs(actual-expected) <= tolerance else 'failed', 'duration_difference', expected=expected, actual=actual, tolerance=tolerance))
        elif kind == 'trajectory':
            actual = [f['id'] for f in candidate['observations']]
            alternatives = rule.get('allowed', [[f['id'] for f in reference['observations']]])
            if not isinstance(alternatives, list) or not alternatives or any(not isinstance(route, list) or any(not isinstance(v, str) for v in route) for route in alternatives):
                raise ValueError('explicit complete alternative trajectories required')
            forbidden = set(rule.get('forbidden', []))
            passed = actual in alternatives and not forbidden.intersection(actual)
            outcomes.append(result(identifier, 'passed' if passed else 'failed', 'complete_trajectory', expected=alternatives, actual=actual))
        else:
            raise ValueError('unknown property kind')
    status = 'failed' if any(p['status'] == 'failed' for p in outcomes) else 'not_tested' if any(p['status'] == 'not_tested' for p in outcomes) else 'passed'
    return dict(status=status, contract_sha256=expected_contract, reference_run=reference['run_id'], candidate_run=candidate['run_id'],
                reference_artifact=reference['artifact_sha256'], candidate_artifact=candidate['artifact_sha256'], properties=outcomes,
                limits='Observer declarations need independent review. These properties do not establish unobserved behavior or universal equivalence.')


def repair_export(report, review):
    if review.get('approved') is not True or not review.get('reviewer') or review.get('report_sha256') != canonical(report):
        raise ValueError('repair export requires explicit review of the current report hash')
    return dict(contract_sha256=report['contract_sha256'], candidate_artifact=report['candidate_artifact'],
                counterexamples=[dict(property=p['id'], reason=p['reason'], expected=p.get('expected'), actual=p.get('actual'),
                                     discrepancy={k: v for k, v in p.items() if k not in ('id', 'status', 'reason')},
                                     instruction='Preserve this externally evaluated property; rerun the reviewed case after repair.')
                                 for p in report['properties'] if p['status'] == 'failed'],
                unresolved=[p['id'] for p in report['properties'] if p['status'] == 'not_tested'], review=review,
                limits='Review must remove source-shaped or private values; approval is a declaration, not semantic leakage detection.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--candidate', type=Path)
    parser.add_argument('--repair-report', type=Path, help='export counterexamples from an independently reviewed report')
    parser.add_argument('--review', type=Path, help='approval bound to the canonical current report hash')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        read = lambda p: strict_json(p.read_text())
        if args.repair_report:
            if not args.review or any((args.contract, args.reference, args.candidate)):
                raise ValueError('repair export needs --repair-report and --review only')
            report = repair_export(read(args.repair_report), read(args.review))
        else:
            if not all((args.contract, args.reference, args.candidate)) or args.review:
                raise ValueError('comparison needs --contract, --reference and --candidate')
            report = compare(read(args.contract), read(args.reference), read(args.candidate), args.reference.parent, args.candidate.parent)
        with args.output.open('x') as stream:
            json.dump(report, stream, indent=2, allow_nan=False)
        return 0 if args.repair_report or report['status'] == 'passed' else 2
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('error: '+str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
