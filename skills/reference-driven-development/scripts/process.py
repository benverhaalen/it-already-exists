"""Bounded local process primitive. This is not an access sandbox."""
import os
from pathlib import Path
import selectors
import signal
import subprocess
import time


def run(argv, cwd, timeout=30, max_bytes=4194304, env=None, stdin_path=None):
    if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or '\x00' in a for a in argv):
        raise ValueError('command must be an argv list')
    if not 0 < timeout <= 3600 or not 0 < max_bytes <= 67108864:
        raise ValueError('process bounds out of range')
    start = time.monotonic()
    # A regular input file avoids blocking while writing a large prompt into a
    # pipe. The caller owns and validates this file; no shell is involved.
    with (Path(stdin_path).open('rb') if stdin_path else open(os.devnull, 'rb')) as source:
        child = subprocess.Popen(argv, cwd=Path(cwd), env=env, stdin=source,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    chunks = {'stdout': bytearray(), 'stderr': bytearray()}
    status = 'completed'
    selector = selectors.DefaultSelector()
    selector.register(child.stdout, selectors.EVENT_READ, 'stdout')
    selector.register(child.stderr, selectors.EVENT_READ, 'stderr')
    try:
        while selector.get_map():
            if time.monotonic() - start >= timeout:
                status = 'timeout'
                break
            for key, _ in selector.select(min(.1, max(0, timeout - (time.monotonic() - start)))):
                data = os.read(key.fileobj.fileno(), 65536)
                if not data:
                    selector.unregister(key.fileobj)
                    continue
                remaining = max_bytes - sum(len(v) for v in chunks.values())
                chunks[key.data].extend(data[:remaining])
                if len(data) > remaining:
                    status = 'output_limit'
                    break
            if status != 'completed':
                break
        if status == 'completed':
            try:
                child.wait(timeout=max(.001, timeout - (time.monotonic() - start)))
            except subprocess.TimeoutExpired:
                status = 'timeout'
    finally:
        # Also kill descendants after successful parent exit: detached background
        # work must not cross an attempt boundary within this process group.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()
        selector.close()
        child.stdout.close()
        child.stderr.close()
    return dict(status=status, exit_code=child.returncode, elapsed=time.monotonic()-start,
                **{k: bytes(v) for k, v in chunks.items()})
