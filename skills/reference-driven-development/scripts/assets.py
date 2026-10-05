"""Bounded reviewed non-code assets. Review declarations are not legal certification."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat

KINDS = {'image': {'.png', '.jpg', '.jpeg', '.webp'},
         'font': {'.ttf', '.otf', '.woff', '.woff2'},
         'audio': {'.wav', '.ogg', '.mp3'}}
MAX_FILE = 50 * 1024 * 1024
MAX_TOTAL = 200 * 1024 * 1024


def identity(manifest):
    return hashlib.sha256(json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def review(manifest, scope):
    if not isinstance(manifest, dict) or set(manifest) != {'scope', 'reviewer', 'rights', 'limits', 'files'}:
        raise ValueError('asset manifest needs scope/reviewer/rights/limits/files only')
    if manifest['scope'] != scope or any(not isinstance(manifest[k], str) or not manifest[k].strip() for k in ('scope', 'reviewer', 'rights', 'limits')):
        raise ValueError('asset review scope or declarations invalid')
    files = manifest['files']
    if not isinstance(files, list) or not 1 <= len(files) <= 1000:
        raise ValueError('asset manifest needs 1..1000 files')
    names, directory_spellings = set(), {}
    for entry in files:
        if not isinstance(entry, dict) or set(entry) != {'path', 'sha256', 'kind'}:
            raise ValueError('asset entry needs path/sha256/kind only')
        name = entry['path']
        if (not isinstance(name, str) or not name or len(name) > 220 or PurePosixPath(name).is_absolute() or
                any(p in ('', '.', '..') for p in name.split('/')) or '\\' in name or ':' in name or
                any(ord(c) < 32 for c in name) or name.casefold() in names):
            raise ValueError('invalid or duplicate asset path')
        if not isinstance(entry['kind'], str) or entry['kind'] not in KINDS or PurePosixPath(name).suffix.lower() not in KINDS[entry['kind']]:
            raise ValueError('only reviewed image/font/audio files allowed; no source or archives')
        if not isinstance(entry['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', entry['sha256']):
            raise ValueError('asset needs original sha256')
        names.add(name.casefold())
        for parent in PurePosixPath(name).parents:
            if str(parent) == '.':
                continue
            spelling = str(parent)
            prior = directory_spellings.setdefault(spelling.casefold(), spelling)
            if prior != spelling:
                raise ValueError('asset directory casing must be consistent')
    for name in names:
        if any(str(p) in names for p in PurePosixPath(name).parents):
            raise ValueError('asset file/directory collision')
    return manifest


def read_regular(root, name):
    """Open every component without following links; retain descriptor identity."""
    if not hasattr(os, 'O_NOFOLLOW') or os.open not in os.supports_dir_fd:
        raise ValueError('asset transport requires POSIX descriptor no-follow support')
    root = Path(root).absolute()
    fd = os.open(root.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for component in [*root.parts[1:], *PurePosixPath(name).parts[:-1]]:
            child = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd); fd = child
        file_fd = os.open(PurePosixPath(name).name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        with os.fdopen(file_fd, 'rb') as stream:
            before = os.fstat(stream.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_FILE:
                raise ValueError('asset must be a bounded ordinary file')
            data = stream.read(MAX_FILE + 1)
            after = os.fstat(stream.fileno())
            fields = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if len(data) > MAX_FILE or fields(before) != fields(after) or len(data) != before.st_size:
                raise ValueError('asset changed during bounded snapshot')
            return data
    finally:
        os.close(fd)


def snapshot(manifest, root, scope):
    review(manifest, scope)
    result, total = {}, 0
    for entry in manifest['files']:
        data = read_regular(root, entry['path'])
        if hashlib.sha256(data).hexdigest() != entry['sha256']:
            raise ValueError('asset hash differs from reviewed original: ' + entry['path'])
        # Reject recognizable containers/source disguised behind accepted suffixes.
        # This coarse guard cannot establish semantics or legal independence.
        if data.startswith((b'PK', b'\x7fELF', b'MZ', b'\x1f\x8b', b'#!')):
            raise ValueError('asset contains recognizable archive/executable/source signature')
        suffix = PurePosixPath(entry['path']).suffix.lower()
        signatures = {'.png': data.startswith(b'\x89PNG\r\n\x1a\n'),
                      '.jpg': data.startswith(b'\xff\xd8\xff'), '.jpeg': data.startswith(b'\xff\xd8\xff'),
                      '.webp': data.startswith(b'RIFF') and data[8:12] == b'WEBP',
                      '.wav': data.startswith(b'RIFF') and data[8:12] == b'WAVE',
                      '.ogg': data.startswith(b'OggS'),
                      '.mp3': data.startswith(b'ID3') or (len(data) > 1 and data[0] == 255 and data[1] & 224 == 224),
                      '.ttf': data.startswith(b'\x00\x01\x00\x00'), '.otf': data.startswith(b'OTTO'),
                      '.woff': data.startswith(b'wOFF'), '.woff2': data.startswith(b'wOF2')}
        if not signatures[suffix]:
            raise ValueError('asset header does not match declared non-code format')
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError('assets exceed total byte bound')
        result[entry['path']] = data
    return result


def inventory(files):
    return sorted([{'path': name, 'sha256': hashlib.sha256(data).hexdigest()} for name, data in files.items()], key=lambda e: e['path'])


def verify_tree(manifest, root, scope):
    """Verify a run-owned copy, including undeclared entries, without following links.

    This is host-side drift detection, not a substitute for a read-only command
    mount or protection against a concurrently hostile host process.
    """
    review(manifest, scope)
    root = Path(root).absolute()
    if any(p.is_symlink() for p in (root, *root.parents)) or not root.is_dir():
        raise ValueError('approved asset tree must be an ordinary directory')
    expected_files = {entry['path'] for entry in manifest['files']}
    expected_dirs = {str(parent) for name in expected_files
                     for parent in PurePosixPath(name).parents if str(parent) != '.'}
    found_files, found_dirs = set(), set()
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                path = Path(entry.path)
                relative = path.relative_to(root).as_posix()
                mode = entry.stat(follow_symlinks=False).st_mode
                if stat.S_ISDIR(mode) and relative in expected_dirs:
                    found_dirs.add(relative)
                    pending.append(path)
                elif stat.S_ISREG(mode) and relative in expected_files:
                    found_files.add(relative)
                else:
                    raise ValueError('unexpected, linked or nonordinary approved asset entry: '+relative)
    if found_files != expected_files or found_dirs != expected_dirs:
        raise ValueError('approved asset tree has missing entries')
    return snapshot(manifest, root, scope)
