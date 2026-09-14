#!/usr/bin/env python3
"""Record explicit input/capture events against a task-local Android emulator.

Every action carries an emulator serial. Captures preserve raw pixels, monotonic
host times and an action trace; no timing normalization is silently applied.
"""
import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


def adb(serial, *args, binary=False, timeout=30, container=None, executable='adb'):
    prefix=['docker','exec',container] if container else []
    result=subprocess.run([*prefix,executable,'-s',serial,*args],capture_output=True,timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace')[-1500:])
    return result.stdout if binary else result.stdout.decode(errors='replace').strip()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--serial',required=True)
    p.add_argument('--container',help='Optional task-local Docker container holding the emulator')
    p.add_argument('--adb',default='adb',help='ADB executable on the selected host/container')
    p.add_argument('--capture-method',choices=['exec-out','pull'],default='exec-out',
                   help='Use pull with old Android images that do not support exec-out')
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--label',required=True)
    p.add_argument('--timeout',type=float,default=30,
                   help='Positive timeout in seconds for each external command (default: 30)')
    sub=p.add_subparsers(dest='action',required=True)
    sub.add_parser('capture')
    tap=sub.add_parser('tap');tap.add_argument('x',type=int);tap.add_argument('y',type=int)
    swipe=sub.add_parser('swipe')
    for field in ['x1','y1','x2','y2','duration_ms']:swipe.add_argument(field,type=int)
    sub.add_parser('back')
    args=p.parse_args()
    if not 0 < args.timeout < float('inf'):
        p.error('timeout must be a finite positive number')
    if args.action=='swipe' and args.duration_ms<=0:
        p.error('duration must be positive')
    def device(*values,**kwargs):
        return adb(args.serial,*values,container=args.container,executable=args.adb,
                   timeout=args.timeout,**kwargs)
    if not args.serial.startswith('emulator-'):
        p.error('This experiment recorder only operates on an explicit Android emulator.')
    args.output.mkdir(parents=True,exist_ok=True)
    event=dict(version=1,event_id=time.time_ns(),serial=args.serial,container=args.container,label=args.label,action=args.action,
               utc=datetime.now(timezone.utc).isoformat(),started_monotonic=time.monotonic(),
               command_timeout_seconds=args.timeout)
    def record(stage):
        with (args.output/'events.jsonl').open('a') as f:
            f.write(json.dumps(dict(event,stage=stage))+'\n')
    record('started')
    step='validate_emulator'
    try:
        if device('shell','getprop','ro.kernel.qemu')!='1':
            raise RuntimeError('Selected device did not identify itself as an emulator')
        perform_action(args,device,event,record)
    except (OSError,RuntimeError,subprocess.SubprocessError) as error:
        event.update(failed_monotonic=time.monotonic(),failed_step=event.get('pending_step',step),
                     error_type=type(error).__name__,error=str(error)[-1500:])
        record('failed')
        print(json.dumps(event,indent=2),file=sys.stderr)
        return 1
    return 0


def perform_action(args,device,event,record):
    def pending(step):
        event['pending_step']=step
        record('step_started')
    command=None
    if args.action=='tap':command=['input','tap',str(args.x),str(args.y)]
    if args.action=='swipe':
        command=['input','swipe',*[str(getattr(args,k)) for k in ['x1','y1','x2','y2','duration_ms']]]
    if args.action=='back':command=['input','keyevent','4']
    if command:
        event['command']=command
        record('input_requested')
        pending('input')
        event['response']=device('shell',*command)
        event['input_completed_monotonic']=time.monotonic()
        record('input_completed')
    event['capture_started_monotonic']=time.monotonic()
    record('capture_started')
    if args.capture_method=='exec-out':
        pending('screencap')
        png=device('exec-out','screencap','-p',binary=True)
    else:
        capture_id=f'it-already-exists-{time.time_ns()}.png'
        remote=f'/data/local/tmp/{capture_id}'
        pending('screencap')
        device('shell','screencap','-p',remote)
        with tempfile.TemporaryDirectory(prefix='reference-capture-') as folder:
            local=Path(folder)/capture_id
            pending('pull_capture')
            if args.container:
                intermediate=f'/tmp/{capture_id}'
                device('pull',remote,intermediate)
                pending('copy_from_container')
                subprocess.run(['docker','cp',f'{args.container}:{intermediate}',str(local)],
                               check=True,capture_output=True,timeout=args.timeout)
                pending('remove_container_copy')
                subprocess.run(['docker','exec',args.container,'rm',intermediate],
                               check=True,capture_output=True,timeout=args.timeout)
            else:
                device('pull',remote,str(local))
            png=local.read_bytes()
        pending('remove_guest_copy')
        device('shell','rm',remote)
    pending('validate_png')
    if not png.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('Android screencap did not produce PNG bytes')
    name=f'{time.time_ns()}-{args.action}.png'
    pending('save_capture')
    (args.output/name).write_bytes(png)
    event.update(capture_finished_monotonic=time.monotonic(),screenshot=name,
                 screenshot_sha256=hashlib.sha256(png).hexdigest(),
                 timing_scope='host elapsed times; software emulation may run slower than original intended playback')
    event.pop('pending_step',None)
    record('complete')
    print(json.dumps(event,indent=2))

if __name__=='__main__':sys.exit(main())
