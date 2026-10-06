#!/usr/bin/env python3
"""Run a bounded test with one explicit Android-to-host TCP reverse route."""
import argparse
import json
from pathlib import Path
import subprocess

from ios_location_fixture import run_command


def routes(text):
    result = {}
    for line in text.splitlines():
        fields = line.split()
        if not fields:
            continue
        if len(fields) != 3 or fields[1] in result:
            raise ValueError("Ambiguous ADB reverse listing")
        result[fields[1]] = fields[2]
    return result


def run_fixture(adb, serial, device_port, host_port, command, timeout, output,
                invoke=subprocess.run, execute=run_command, required_text=()):
    if not serial.startswith("emulator-") or not serial[9:].isdigit():
        raise ValueError("Select an explicit task-owned emulator serial")
    if any(type(p) is not int or not 1 <= p <= 65535 for p in (device_port, host_port)):
        raise ValueError("Ports must be integers from 1 to 65535")
    if not command or not 1 <= timeout <= 3600:
        raise ValueError("Supply a bounded test command")
    output.mkdir(parents=True, exist_ok=False)
    remote, local = f"tcp:{device_port}", f"tcp:{host_port}"
    receipt = {"serial": serial, "device_endpoint": remote, "host_endpoint": local,
               "created": False, "borrowed": False, "route_verified": False,
               "cleanup_succeeded": False, "test_exit": None, "witnesses_verified": False,
               "limits": "Route lifecycle only; not endpoint reachability, network isolation or app fidelity. Exclude concurrent device controllers."}

    def query(*args):
        r = invoke([adb, "-s", serial, *args], capture_output=True, text=True,
                   timeout=15, check=False)
        if r.returncode:
            raise RuntimeError("ADB command failed")
        return r.stdout

    def listing():
        return routes(query("reverse", "--list"))

    try:
        if query("get-state").strip() != "device":
            raise ValueError("Selected emulator is not online")
        before = listing()
        if remote in before:
            if before[remote] != local:
                raise ValueError("Existing route conflicts; refusing replacement")
            receipt["borrowed"] = True
        else:
            # Never replace a route created by another controller after inspection.
            query("reverse", "--no-rebind", remote, local)
            receipt["created"] = True
        if listing().get(remote) != local:
            raise ValueError("Requested route is not observed")
        receipt["route_verified"] = True
        receipt["test_exit"] = execute(command, timeout, output / "command.log")
        log = (output / "command.log").read_text(errors="replace") if required_text else ""
        receipt["witnesses_verified"] = all(text in log for text in required_text)
    except Exception as error:
        receipt["error_type"] = type(error).__name__
    finally:
        if receipt["created"]:
            try:
                current = listing()
                if remote in current:
                    if current[remote] != local:
                        raise ValueError("Route changed; refusing unrelated cleanup")
                    query("reverse", "--remove", remote)
                if remote in listing():
                    raise ValueError("Created route remains after cleanup")
                receipt["cleanup_succeeded"] = True
            except Exception as error:
                receipt["cleanup_error_type"] = type(error).__name__
        elif receipt["borrowed"]:
            # Borrowed routes remain owned by their creator, even on test failure.
            receipt["cleanup_succeeded"] = True
        receipt["fixture_command_passed"] = (receipt["route_verified"] and
            receipt["test_exit"] == 0 and receipt["cleanup_succeeded"] and receipt["witnesses_verified"])
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--adb", default="adb")
    p.add_argument("--serial", required=True)
    p.add_argument("--device-port", required=True, type=int)
    p.add_argument("--host-port", required=True, type=int)
    p.add_argument("--timeout", type=int, default=300, help="Test command seconds; each ADB setup/cleanup call has a separate 15-second bound")
    p.add_argument("--required-text", action="append", default=[], help="Require a completion witness in the command log; repeatable")
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("command", nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ["--"] else a.command
    try:
        r = run_fixture(a.adb, a.serial, a.device_port, a.host_port,
                        command, a.timeout, a.output, required_text=a.required_text)
    except (ValueError, FileExistsError) as error:
        p.error(str(error))
    print(json.dumps(r))
    return 0 if r["fixture_command_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
