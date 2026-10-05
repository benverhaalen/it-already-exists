#!/usr/bin/env python3
"""Bounded, offline reference intake and host-tool observation planning.

Inventories identify inputs, not behavior. Capability declarations are not probes.
No downloads, target execution, archive extraction, or journal mutation occur.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from urllib.parse import urlsplit

SURFACES = ('web', 'desktop', 'binary', 'source', 'api', 'cli', 'recording',
            'physical', 'game', 'audio', 'document', 'android')
ROUTES = {
    'web': ('capture', 'control', 'reset', 'ui-inspection'),
    'desktop': ('capture', 'control', 'reset', 'ui-inspection'),
    'binary': ('binary-analysis', 'capture'),
    'source': ('source-analysis', 'project-inspection'),
    'api': ('function-oracle', 'network-capture', 'reset'),
    'cli': ('function-oracle', 'reset'),
    'recording': ('capture', 'vision'),
    'physical': ('capture', 'control', 'reset'),
    'game': ('trajectory-capture', 'control', 'reset'),
    'audio': ('capture', 'trajectory-capture'),
    'document': ('artifact-inspection',),
    'android': ('package-inspection', 'android-control', 'capture', 'reset'),
}
NEXT = {
    'web': 'Use an authorized browser to capture one fresh rendered/accessibility state, then a meaningful action and reset; preserve viewport, role, history and URL.',
    'desktop': 'Identify platform and an authorized installed/runnable instance; capture windows/accessibility plus one action, persistence and reset. Do not launch an installer merely to inspect it.',
    'binary': 'Inspect format, architecture and resources with static tools first; narrow runtime investigation to unresolved behavior only after execution access and environment are established.',
    'source': 'Inspect entry points, dependencies and relevant call paths; distinguish present code from reachable behavior and select one discriminating runtime question.',
    'api': 'Establish endpoint/version, authorization and safe request scope; record request/response, errors, streaming/order and reset conditions around competing behavioral explanations.',
    'cli': 'Establish authorized invocation and side-effect/reset boundaries; observe inputs, outputs, exit codes, streams and written files for a discriminating case.',
    'recording': 'Inspect timeline, frame/audio timestamps, crops and omissions; annotate visible sequence and hypotheses, then seek an interactive channel for unanswerable questions.',
    'physical': 'Establish device/control access and measurement perturbations; capture synchronized display, control and signal observations with a repeatable reset.',
    'game': 'Establish build, hardware, initial state and deterministic/replay limits; capture synchronized input, frames, audio and trajectories to distinguish state and timing explanations.',
    'audio': 'Establish sample rate, channels, timing, processing chain and playback/measurement conditions; compare raw signal and perceived result for an explicit property.',
    'document': 'Inspect structure, relationships and rendered output using a suitable parser/viewer; where authorized, compare controlled edits and round trips without assuming one sample defines the format.',
    'android': 'Use scripts/apk_intake.py in this skill for bounded static package intake and scripts/observation.py for an explicitly selected, task-owned installed Android session; inspect their help and readiness first. Provisioning, installation, manifest decoding and decompilation require separate domain tools.',
}
HINTS = {
    '.apk': 'android', '.apks': 'android', '.xapk': 'android', '.aab': 'android',
    '.app': 'desktop', '.dmg': 'desktop', '.pkg': 'desktop', '.msi': 'desktop', '.ipa': 'desktop',
    '.exe': 'binary', '.dll': 'binary', '.so': 'binary', '.dylib': 'binary', '.wasm': 'binary',
    '.py': 'source', '.js': 'source', '.ts': 'source', '.tsx': 'source', '.rs': 'source', '.c': 'source', '.go': 'source',
    '.mp4': 'recording', '.mov': 'recording', '.webm': 'recording', '.png': 'recording', '.jpg': 'recording', '.jpeg': 'recording',
    '.wav': 'audio', '.mp3': 'audio', '.flac': 'audio', '.ogg': 'audio',
    '.pdf': 'document', '.docx': 'document', '.xlsx': 'document', '.pptx': 'document', '.json': 'document', '.csv': 'document', '.md': 'document',
}


def digest_json(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def inventory(path, max_entries=2000, max_depth=8, max_file_bytes=16 * 1024 * 1024,
              max_total_bytes=64 * 1024 * 1024):
    """Never follow symlinks; bounded metadata scans and regular-file reads only."""
    if any(type(x) is not int or x < 1 for x in (max_entries, max_depth, max_file_bytes, max_total_bytes)):
        raise ValueError('inventory bounds must be positive integers')
    if not all(hasattr(os, flag) for flag in ('O_DIRECTORY', 'O_NOFOLLOW', 'O_NONBLOCK')) or os.open not in os.supports_dir_fd:
        raise ValueError('safe local inventory requires POSIX no-follow descriptor APIs; use --identity on this host')
    root = Path(os.path.abspath(path))
    # Reject symlink ancestors as well as the selected root; resolve must not silently follow them.
    if any(p.is_symlink() for p in [root, *root.parents]):
        raise ValueError('reference path or ancestor is a symlink; select an explicit physical path')
    entries, omissions, read_bytes = [], [], 0
    if not root.exists():
        raise ValueError('local reference does not exist; use --identity for a non-file reference')

    def visit(current, relative, depth, parent_fd=None, name=None):
        nonlocal read_bytes
        if len(entries) >= max_entries:
            omissions.append({'path': relative, 'reason': 'entry budget exhausted'})
            return
        try:
            info = os.stat(name, dir_fd=parent_fd, follow_symlinks=False) if parent_fd is not None else current.lstat()
        except OSError as exc:
            omissions.append({'path': relative, 'reason': str(exc)})
            return
        entry = {'path': relative, 'size': info.st_size, 'mtime_ns': info.st_mtime_ns}
        entries.append(entry)
        if stat.S_ISLNK(info.st_mode):
            entry['type'] = 'symlink'; entry['content_status'] = 'not followed'
        elif stat.S_ISDIR(info.st_mode):
            entry['type'] = 'directory'
            if depth >= max_depth:
                omissions.append({'path': relative, 'reason': 'depth budget exhausted'})
                return
            directory_fd = None
            try:
                children = []
                directory_fd = os.open(name if parent_fd is not None else current, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent_fd)
                opened = os.fstat(directory_fd)
                if (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino):
                    os.close(directory_fd)
                    directory_fd = None
                    raise OSError('directory changed before inventory')
                with os.scandir(directory_fd) as scan:
                    for child in scan:
                        if len(children) >= max_entries - len(entries):
                            omissions.append({'path': relative, 'reason': 'directory listing budget exhausted; retained subset is not complete'})
                            break
                        children.append(child.name)
                for name in sorted(children):
                    if len(entries) >= max_entries:
                        omissions.append({'path': relative, 'reason': 'entry budget exhausted'})
                        break
                    visit(current / name, name if relative == '.' else relative + '/' + name, depth + 1, directory_fd, name)
            except OSError as exc:
                omissions.append({'path': relative, 'reason': str(exc)})
            finally:
                if directory_fd is not None:
                    os.close(directory_fd)
        elif stat.S_ISREG(info.st_mode):
            entry['type'] = 'file'
            if info.st_size > max_file_bytes or read_bytes + info.st_size > max_total_bytes:
                entry['content_status'] = 'hash omitted: byte budget'
                return
            descriptor = None
            try:
                descriptor = os.open(name if parent_fd is not None else current, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent_fd)
                before = os.fstat(descriptor)
                if not stat.S_ISREG(before.st_mode) or (before.st_dev, before.st_ino) != (info.st_dev, info.st_ino):
                    raise ValueError('input changed before read')
                h = hashlib.sha256(); count = 0
                with os.fdopen(descriptor, 'rb') as stream:
                    descriptor = None
                    while True:
                        chunk = stream.read(min(1024 * 1024, max_file_bytes - count + 1, max_total_bytes - read_bytes + 1))
                        if not chunk:
                            break
                        count += len(chunk); read_bytes += len(chunk)
                        if count > max_file_bytes or read_bytes > max_total_bytes:
                            raise ValueError('input grew beyond byte budget')
                        h.update(chunk)
                    after = os.fstat(stream.fileno())
                if (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                    raise ValueError('input changed during read')
                entry.update(sha256=h.hexdigest(), content_status='hashed')
            except (OSError, ValueError) as exc:
                entry['content_status'] = 'unavailable: ' + str(exc)
            finally:
                if descriptor is not None:
                    os.close(descriptor)
        else:
            entry['type'] = 'special'; entry['content_status'] = 'not read'

    visit(root, '.', 0)
    complete = not omissions and all(e.get('content_status', 'hashed') == 'hashed' for e in entries)
    result = {'root': str(root), 'entries': entries, 'omissions': omissions,
              'complete_content_inventory': complete, 'bytes_read': read_bytes,
              'bounds': dict(max_entries=max_entries, max_depth=max_depth,
                             max_file_bytes=max_file_bytes, max_total_bytes=max_total_bytes)}
    result['inventory_sha256'] = digest_json(result)
    return result


def intake(reference, surface=None, capabilities=(), identity=False, access='source-assisted', scope='reference-intake', **bounds):
    if surface is not None and surface not in SURFACES:
        raise ValueError('unknown surface')
    if access not in ('source-assisted', 'strict-clean-room'):
        raise ValueError('unknown access mode')
    if not isinstance(reference, str) or not reference.strip() or not scope.strip():
        raise ValueError('reference and scope must be nonempty')
    parsed = urlsplit(reference)
    remote = parsed.scheme in ('http', 'https')
    if remote and (not parsed.netloc or parsed.username or parsed.password):
        raise ValueError('URL needs a host and must not contain credentials')
    if identity or remote:
        captured = {'kind': 'identity', 'locator': reference, 'content_acquired': False}
        hint = HINTS.get(Path(parsed.path if remote else reference).suffix.lower()) or ('web' if remote else None)
    else:
        captured = {'kind': 'local', 'locator': str(Path(os.path.abspath(reference))),
                    'inventory': inventory(reference, **bounds)}
        hint = HINTS.get(Path(reference.rstrip('/')).suffix.lower())
        if hint is None and Path(reference).is_dir():
            hint = 'source'  # weak directory hint, never framework detection
    chosen = surface or hint
    platform_limits = []
    if chosen == 'desktop':
        platform_limits = ['Choose macOS AXUIElement, Windows UI Automation, Linux AT-SPI, or available iOS XCUIAutomation by actual target platform; none are included in this helper.', 'iOS packages may require signing, device/build access and authorized automation; a package identity does not establish runnable access.']
    available = sorted(set(capabilities))
    required = list(ROUTES.get(chosen, ()))
    methods = json.loads((Path(__file__).resolve().parents[1] / 'references/methods.json').read_text())['methods']
    candidates = [dict(id=m['id'], mechanism=m['mechanism'], requires=m['requires'],
                       missing=sorted(set(m['requires']) - set(available)), source=m['source'], limit=m['limit'])
                  for m in methods if chosen and (chosen in m['surfaces'] or '*' in m['surfaces'])]
    identifier = 'intake-' + digest_json(captured)[:20]
    return {
        'schema_version': 1, 'reference': captured,
        'surface': {'selected': chosen, 'basis': 'explicit' if surface else 'locator hint' if hint else 'unresolved',
                    'uncertainty': 'A locator/extension does not establish framework, runnable access, or all surfaces; confirm and split mixed references.'},
        'capabilities': {'declared_available': available, 'needed_for_initial_route': required,
                         'missing': sorted(set(required) - set(available)), 'verified': False},
        'platform_limits': platform_limits,
        'next_action': NEXT.get(chosen, 'Inspect the locator context and select the relevant surface/property before choosing tools.'),
        'readiness': {'ready_for_behavioral_observation': False,
                      'questions': ['Which property and comparison fidelity matter, for which audience and complete journey?',
                                    'What version, environment, role, history and measurement conditions apply?',
                                    'Is access authorized, and can input, capture freshness, reset and replay be established?',
                                    'Which competing explanations would the next observation distinguish?',
                                    'In strict mode, which analyst evidence and builder assets are permitted, and what enforced boundary will be used?'],
                      'questions_are_agent_work_first': True},
        'workflow_task_fragment': {'scope': scope, 'surface': chosen, 'access': access, 'capabilities': available},
        'reference_record': {'id': identifier, 'kind': 'reference', 'data': {
            'locator': captured['locator'], 'job': 'input identity and acquisition planning; behavioral property pending',
            'inspection': 'bounded local inventory only' if captured['kind'] == 'local' else 'identity only; not fetched',
            'task_scope': scope}},
        'method_candidates': candidates,
        'limits': ['Not a complete workflow task or an adopted contribution; agent fills intent and contracts from inspected context.',
                   'No target execution, archive extraction, acquisition adapter, semantic inspection or behavioral equivalence claim.',
                   'Hashes describe captured bytes/metadata only; refresh after changes. Truncated inventories cannot prove absence. Directory membership is not an atomic snapshot.',
                   'Local inventory requires POSIX descriptor APIs and a trusted selected root path; it is not a sandbox for hostile filesystem mutation. Identity-only planning works on other hosts.',
                   'Capability names are caller declarations, not successful tool or environment readiness checks.',
                   'Strict-mode output is analyst-side provenance, not an approved builder handoff. Use reviewed specification and enforced isolation.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference')
    parser.add_argument('--surface', choices=SURFACES)
    parser.add_argument('--identity', action='store_true', help='Treat locator as identity only, without local filesystem access')
    parser.add_argument('--capability', action='append', default=[])
    parser.add_argument('--access', choices=('source-assisted', 'strict-clean-room'), default='source-assisted')
    parser.add_argument('--scope', default='reference-intake')
    parser.add_argument('--max-entries', type=int, default=2000)
    parser.add_argument('--max-depth', type=int, default=8)
    parser.add_argument('--max-file-bytes', type=int, default=16 * 1024 * 1024)
    parser.add_argument('--max-total-bytes', type=int, default=64 * 1024 * 1024)
    parser.add_argument('--output', type=Path, help='Fresh JSON output path; never overwrite')
    args = parser.parse_args()
    try:
        result = intake(args.reference, args.surface, args.capability, args.identity, args.access, args.scope,
                        max_entries=args.max_entries, max_depth=args.max_depth,
                        max_file_bytes=args.max_file_bytes, max_total_bytes=args.max_total_bytes)
        encoded = json.dumps(result, indent=2) + '\n'
        if args.output:
            with args.output.open('x', encoding='utf-8') as stream:
                stream.write(encoded)
        else:
            print(encoded, end='')
        return 0
    except (OSError, ValueError) as exc:
        print('intake: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
