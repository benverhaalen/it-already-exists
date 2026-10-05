#!/usr/bin/env python3
"""Offline Docker implementer boundary. Image contents require separate review.

No network, host credentials, source mounts or inherited chat are supplied.
The caller must deliver only the reviewed specification to the worker.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import shutil
import tempfile
import uuid
import sys

import workflow
import assets


def invoke(args, timeout=120):
    return subprocess.run(['docker', *args], capture_output=True, text=True, timeout=timeout)


def image_id(image):
    if not image.startswith('sha256:') or len(image) != 71:
        raise ValueError('pin the reviewed local image by full sha256 ID; tags are not accepted')
    result = invoke(['image', 'inspect', image, '--format', '{{.Id}}'])
    if result.returncode or result.stdout.strip() != image:
        raise ValueError('reviewed image is not available locally; no automatic pull')
    return image


def boundary(image, spec_dir, output, name, command, memory='1g', cpus=2, asset_dir=None):
    if not isinstance(memory, str) or not re.fullmatch(r'[1-9][0-9]{0,5}[mg]', memory):
        raise ValueError('memory must be a positive Docker m/g size, such as 32g')
    if not isinstance(cpus, (int, float)) or not math.isfinite(cpus) or not 0 < cpus <= 256:
        raise ValueError('cpus must be a finite number between 0 and 256')
    for path in (spec_dir, output, *([asset_dir] if asset_dir else [])):
        if ',' in str(path):
            raise ValueError('mount path contains unsupported comma')
    return ['run', '--rm', '--pull=never', '--name', name, '--network=none',
            '--read-only', '--cap-drop=ALL', '--security-opt=no-new-privileges',
            '--user=65534:65534', '--pids-limit=128', f'--memory={memory}', f'--cpus={cpus}',
            '--tmpfs=/tmp:rw,nosuid,nodev,size=128m', '--workdir=/work',
            '--env=HOME=/work', '--env=TMPDIR=/tmp',
            '--mount', f'type=bind,src={spec_dir},dst=/spec,readonly',
            '--mount', f'type=bind,src={output},dst=/work',
            *(['--mount', f'type=bind,src={asset_dir},dst=/assets,readonly'] if asset_dir else []), image, *command]


def execute(image, specification, command, timeout, destination=None, memory='1g', cpus=2, asset_manifest=None, asset_root=None):
    image_id(image)
    reviewed = workflow.review_export(specification)['specification']
    if (asset_manifest is None) != (asset_root is None):
        raise ValueError('assets need both reviewed manifest and asset root')
    approved = assets.snapshot(asset_manifest, asset_root, reviewed['scope']) if asset_manifest is not None else {}
    if command and destination is None:
        raise ValueError('worker execution needs a fresh --output directory to preserve artifacts')
    if destination is not None and (destination.exists() or destination.is_symlink()):
        raise ValueError('output destination must not exist')
    with tempfile.TemporaryDirectory(prefix='rdd-cleanroom-') as scratch:
        root = Path(scratch)
        spec_dir, output = root / 'spec', root / 'output'
        spec_dir.mkdir(); output.mkdir()
        spec_dir.chmod(0o755); output.chmod(0o777)
        payload = json.dumps(reviewed, sort_keys=True, ensure_ascii=False).encode()
        (spec_dir / 'specification.json').write_bytes(payload)
        (spec_dir / 'specification.json').chmod(0o444)
        asset_dir = root / 'assets' if approved else None
        if approved:
            asset_dir.mkdir(); asset_dir.chmod(0o755)
            for name, data in approved.items():
                path = asset_dir / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data); path.chmod(0o444)
            for path in asset_dir.rglob('*'):
                if path.is_dir(): path.chmod(0o755)
            (spec_dir / 'assets.json').write_text(json.dumps(asset_manifest, sort_keys=True, ensure_ascii=False))
            (spec_dir / 'assets.json').chmod(0o444)
        # A harmless host canary lies outside both exported mounts.
        canary = root / ('withheld-' + uuid.uuid4().hex)
        canary.write_text('synthetic withheld marker')
        probe = r'''const fs=require('fs'),net=require('net');
const hostPath=process.argv[1];
const readable=fs.readFileSync('/spec/specification.json','utf8');
if(!JSON.parse(readable).goal)process.exit(11);
for(const p of [hostPath,'/var/run/docker.sock']){try{fs.readFileSync(p);process.exit(12)}catch(e){if(e.code!=='ENOENT'&&e.code!=='EACCES')throw e}}
try{fs.writeFileSync('/spec/forbidden','x');process.exit(13)}catch(e){if(!['EROFS','EACCES'].includes(e.code))throw e}
if(fs.existsSync('/spec/assets.json')){
 const m=JSON.parse(fs.readFileSync('/spec/assets.json','utf8'));
 const crypto=require('crypto');
 for(const a of m.files){const bytes=fs.readFileSync('/assets/'+a.path);
 if(crypto.createHash('sha256').update(bytes).digest('hex')!==a.sha256)process.exit(15)}
 try{fs.writeFileSync('/assets/forbidden','x');process.exit(16)}catch(e){if(!['EROFS','EACCES'].includes(e.code))throw e}
}
fs.writeFileSync('/work/allowed.txt','synthetic allowed output');
const s=net.connect({host:'1.1.1.1',port:443});
s.on('connect',()=>process.exit(14));s.on('error',()=>{console.log('boundary probes passed');process.exit(0)});
setTimeout(()=>{s.destroy();console.log('boundary probes passed; network timed out');process.exit(0)},1500);
'''
        name = 'rdd-probe-' + uuid.uuid4().hex
        try:
            result = invoke(boundary(image, spec_dir, output, name, ['node', '-e', probe, str(canary)], memory, cpus, asset_dir), min(timeout, 30))
            if result.returncode:
                raise ValueError('boundary probe failed: ' + result.stderr[-1000:])
            if not (output / 'allowed.txt').exists():
                raise ValueError('allowed output probe did not produce its artifact')
            (output / 'allowed.txt').unlink()
            worker = None
            files = []
            if command:
                name = 'rdd-worker-' + uuid.uuid4().hex
                try:
                    worker = invoke(boundary(image, spec_dir, output, name, command, memory, cpus, asset_dir), timeout)
                except subprocess.TimeoutExpired as exc:
                    stopped = invoke(['rm', '-f', name], 15)
                    if stopped.returncode:
                        raise ValueError('worker timeout; cleanup not confirmed; preserve session for inspection: ' + name)
                    def decoded(value):
                        return value.decode(errors='replace') if isinstance(value, bytes) else value or ''
                    worker = subprocess.CompletedProcess(command, 124, decoded(exc.stdout), decoded(exc.stderr) + '\nWorker timed out; preserved partial output.')
                total_bytes = 0
                for entry_count, path in enumerate(output.rglob('*'), 1):
                    if entry_count > 2000:
                        raise ValueError('output traversal exceeds bounded export size')
                    if path.is_symlink():
                        raise ValueError('worker output contains a symlink; inspect without dereferencing')
                    if path.is_file():
                        size = path.stat().st_size
                        total_bytes += size
                        if size > 50 * 1024 * 1024 or total_bytes > 200 * 1024 * 1024 or len(files) >= 1000:
                            raise ValueError('output file exceeds bounded export size')
                        files.append({'path': str(path.relative_to(output)), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
                    elif not path.is_dir():
                        raise ValueError('worker output contains a special file')
                shutil.copytree(output, destination)
            return {'image': image, 'specification_sha256': hashlib.sha256(payload).hexdigest(),
                    'asset_manifest_sha256': assets.identity(asset_manifest) if asset_manifest is not None else None,
                    'asset_scope': reviewed['scope'] if approved else None, 'asset_inventory': assets.inventory(approved),
                    'resource_limits': {'memory': memory, 'cpus': cpus, 'pids': 128, 'timeout_seconds': timeout},
                    'boundary_probes_passed': True, 'worker_executed': worker is not None,
                    'worker_exit': worker.returncode if worker else None, 'output_inventory': files,
                    'output_directory': str(destination.resolve()) if destination else None,
                    'worker_stdout': worker.stdout if worker else '', 'worker_stderr': worker.stderr if worker else '',
                    'limits': 'Only synthetic file/write/socket/network probes. Image source/history, model training, semantic export independence and worker behavior require review. Outputs are untrusted; inspect before executing. No online model broker or original host context is supplied.'}
        finally:
            # Best-effort removal also covers Docker containers left by a host timeout.
            invoke(['rm', '-f', name], 15)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--spec', required=True, type=Path)
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--memory', default='1g', help='Explicit Docker memory limit; size for reviewed local model, e.g. 32g')
    parser.add_argument('--cpus', type=float, default=2, help='Explicit positive CPU quota, at most 256')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--asset-manifest', type=Path, help='Explicit reviewed permitted non-code asset manifest')
    parser.add_argument('--asset-root', type=Path, help='Private root containing exactly selected source assets; never mounted')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        if not 1 <= args.timeout <= 3600:
            raise ValueError('timeout must be between 1 and 3600 seconds')
        result = execute(args.image, workflow.load(args.spec), args.command, args.timeout, args.output, args.memory, args.cpus, workflow.load(args.asset_manifest) if args.asset_manifest else None, args.asset_root)
        print(json.dumps(result, indent=2))
        return 0 if result['worker_exit'] in (None, 0) else 2
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f'error: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
