#!/usr/bin/env python3
"""Verify one local Android HTTP fixture against previously captured bytes."""
import argparse
import hashlib
import json
import re
import subprocess

HEADER_LIMIT = 16384
BODY_LIMIT = 16 * 1024 * 1024


def response_matches(raw, expected_bytes, expected_sha256):
    if len(raw) > HEADER_LIMIT + expected_bytes:
        raise ValueError("Response exceeds bound")
    headers, separator, body = raw.partition(b"\r\n\r\n")
    if not separator or len(headers) + 4 > HEADER_LIMIT:
        raise ValueError("Missing or excessive HTTP headers")
    lines = headers.split(b"\r\n")
    if not re.fullmatch(rb"HTTP/1\.[01] 200(?: .*)?", lines[0]):
        raise ValueError("Fixture did not return HTTP 200")
    fields = {}
    for line in lines[1:]:
        key, colon, value = line.partition(b":")
        if not colon:
            raise ValueError("Malformed HTTP header")
        key = key.strip().lower()
        if key in fields:
            raise ValueError("Duplicate HTTP header")
        fields[key] = value.strip()
    if b"transfer-encoding" in fields:
        raise ValueError("Transfer encoding is outside this probe contract")
    length = fields.get(b"content-length", b"")
    if not re.fullmatch(rb"[0-9]{1,10}", length) or int(length) != expected_bytes:
        raise ValueError("Content length differs from captured reference")
    if len(body) != expected_bytes or hashlib.sha256(body).hexdigest() != expected_sha256:
        raise ValueError("Response bytes differ from captured reference")
    return {"bytes": len(body), "sha256": expected_sha256}


def probe(adb, serial, host, port, path, expected_bytes, expected_sha256,
          timeout=15, invoke=subprocess.run):
    if not re.fullmatch(r"emulator-[0-9]+", serial):
        raise ValueError("Select a task-owned emulator serial")
    if host not in {"127.0.0.1", "10.0.2.2"}:
        raise ValueError("Only guest loopback or the Android emulator host alias is allowed")
    if type(port) is not int or not 1 <= port <= 65535:
        raise ValueError("Invalid local port")
    if not re.fullmatch(r"/[A-Za-z0-9._~/-]{1,1023}", path):
        raise ValueError("Supply an ASCII fixture path without queries or credentials")
    if type(expected_bytes) is not int or not 0 <= expected_bytes <= BODY_LIMIT:
        raise ValueError("Expected body exceeds probe bound")
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or not 1 <= timeout <= 60:
        raise ValueError("Supply a SHA-256 digest and bounded timeout")
    # All shell tokens are fixed or validated above. Cap output in the guest;
    # cap+1 detects an oversized response rather than accepting its prefix.
    cap = HEADER_LIMIT + expected_bytes
    command = (f"toybox nc -q 2 -w 5 -W 5 {host} {port} | "
               f"toybox head -c {cap + 1}")
    request = f"GET {path} HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n".encode("ascii")
    r = invoke([adb, "-s", serial, "shell", "-T", command], input=request,
               capture_output=True, timeout=timeout, check=False)
    if r.returncode:
        raise ValueError("Android fixture command failed")
    result = response_matches(r.stdout, expected_bytes, expected_sha256)
    result.update({"endpoint_host": host, "endpoint_port": port,
                   "limits": "One local GET and exact body bytes; not app behavior, network isolation or universal endpoint coverage."})
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adb", default="adb")
    p.add_argument("--serial", required=True)
    p.add_argument("--host", choices=["127.0.0.1", "10.0.2.2"], required=True)
    p.add_argument("--port", type=int, required=True)
    p.add_argument("--path", required=True)
    p.add_argument("--expected-bytes", type=int, required=True)
    p.add_argument("--expected-sha256", required=True)
    p.add_argument("--timeout", type=int, default=15)
    a = p.parse_args()
    try:
        result = probe(a.adb, a.serial, a.host, a.port, a.path,
                       a.expected_bytes, a.expected_sha256, a.timeout)
    except (ValueError, subprocess.TimeoutExpired, OSError) as error:
        print(json.dumps({"passed": False, "error_type": type(error).__name__,
                          "reason": str(error) if isinstance(error, ValueError) else "Command unavailable or timed out"}))
        return 1
    print(json.dumps({"passed": True, **result}))
    print("RDD_HTTP_BYTES_MATCH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
