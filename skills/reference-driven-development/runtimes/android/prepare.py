#!/usr/bin/env python3
"""Prepare a source-free API35 compiler context from already downloaded inputs.

No downloading, SDK license acceptance, target sources, or Docker execution.
"""
import argparse
import hashlib
import json
import io
from pathlib import Path, PurePosixPath
import shutil
import stat
import tempfile
import zipfile

BUILD_TOOLS_SHA256 = 'bd3a4966912eb8b30ed0d00b0cda6b6543b949d5ffe00bea54c04c81e1561d88'
PLATFORM_SHA256 = '4566663c3876e022b4fa4ced8c8697c4ab1688267f090114fd92d027b32e619b'


def prepare(archive, platform, destination):
    destination = Path(destination).absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError('context destination must be fresh')
    inputs = []
    for path, expected, maximum in ((Path(archive), BUILD_TOOLS_SHA256, 70*1024**2),
                                    (Path(platform), PLATFORM_SHA256, 50*1024**2)):
        if path.is_symlink() or not path.is_file() or path.stat().st_size > maximum:
            raise ValueError('bounded ordinary dependency files required')
        data = path.read_bytes()
        if len(data) > maximum or hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('dependency does not match the reviewed API35 qualification version')
        inputs.append(data)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='rdd-android-context-', dir=destination.parent) as temp:
        root = Path(temp)/'context'; root.mkdir()
        sdk = root/'sdk/build-tools/35.0.0'; sdk.mkdir(parents=True)
        # Hash-qualified archive still gets explicit path/type/size checks.
        with zipfile.ZipFile(io.BytesIO(inputs[0])) as z:
            seen = set(); total = 0
            for info in z.infolist():
                name = PurePosixPath(info.filename)
                mode = info.external_attr >> 16
                if (name.is_absolute() or '..' in name.parts or '\\' in info.filename
                        or not name.parts or name.parts[0] != 'android-15'
                        or info.filename in seen or stat.S_ISLNK(mode)):
                    raise ValueError('unsafe compiler archive entry')
                seen.add(info.filename); total += info.file_size
                if len(seen) > 2000 or total > 250*1024**2:
                    raise ValueError('compiler archive exceeds bounds')
                target = sdk.joinpath(*name.parts[1:])
                if info.is_dir(): target.mkdir(parents=True, exist_ok=True)
                else:
                    if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                        raise ValueError('nonregular compiler archive entry')
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(z.read(info))
                    target.chmod(0o755 if mode & 0o111 else 0o644)
        jar = root/'sdk/platforms/android-35/android.jar'; jar.parent.mkdir(parents=True)
        jar.write_bytes(inputs[1])
        shutil.copyfile(Path(__file__).with_name('Dockerfile'), root/'Dockerfile')
        inventory = [{'path': str(p.relative_to(root)), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
                     for p in sorted(root.rglob('*')) if p.is_file()]
        receipt = {'build_tools_sha256': BUILD_TOOLS_SHA256, 'platform_sha256': PLATFORM_SHA256,
                   'files': inventory, 'scope': 'compiler dependencies only; no target sources supplied'}
        (root/'context-receipt.json').write_text(json.dumps(receipt, indent=2)+'\n')
        root.rename(destination)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--platform-jar', required=True, type=Path)
    parser.add_argument('--destination', required=True, type=Path)
    args = parser.parse_args()
    receipt = prepare(args.archive, args.platform_jar, args.destination)
    print(json.dumps({'destination': str(args.destination), 'files': len(receipt['files']),
                      'scope': receipt['scope']}))
