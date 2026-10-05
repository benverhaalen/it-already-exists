#!/usr/bin/env python3
"""Run compiler probes through the same boundary as generated implementation."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'scripts'))
from frontier_worker import DockerCommands
import workflow

COMMANDS = [['node', '--version'], ['python3', '--version'], ['java', '-version'],
            ['javac', '-version'], ['aapt2', 'version'], ['zipalign', '-h'],
            ['d8', '--version'], ['apksigner', 'version'], ['dpkg-query', '-W']]


def qualify(image, specification, project, receipt_path):
    if project.exists() or project.is_symlink() or receipt_path.exists() or receipt_path.is_symlink():
        raise ValueError('probe project and receipt must be fresh')
    reviewed = workflow.review_export(specification)['specification']
    runner = DockerCommands(image, memory='2g', cpus=2)
    project.mkdir(parents=True)
    receipt = {'image': image, 'status': 'running', 'results': [],
               'limits': 'Compiler and access probes; not APK build or behavioral fidelity.'}
    def save():
        receipt['boundary_receipts'] = runner.receipts
        receipt_path.write_text(json.dumps(receipt, indent=2)+'\n')
    try:
        runner.qualify(reviewed)
        for argv in COMMANDS:
            result = runner.run(argv, project, timeout=45, max_bytes=262144)
            receipt['results'].append({'argv': argv, 'result': {
                key: value.decode(errors='replace') if isinstance(value, bytes) else value
                for key, value in result.items()}})
            accepted = [0, 2] if argv[0] == 'zipalign' else [0]
            if result['status'] != 'completed' or result['exit_code'] not in accepted:
                raise ValueError('tool probe failed: '+argv[0])
            save()
        receipt['status'] = 'passed'
        save()
    except BaseException:
        receipt['status'] = 'failed'
        save()
        raise
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', required=True)
    parser.add_argument('--spec', required=True, type=Path)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--receipt', required=True, type=Path)
    args = parser.parse_args()
    result = qualify(args.image, json.loads(args.spec.read_text()), args.project, args.receipt)
    print(json.dumps({'status': result['status'], 'image': result['image']}))
