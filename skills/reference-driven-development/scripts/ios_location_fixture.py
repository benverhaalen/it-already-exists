#!/usr/bin/env python3
"""Run a command with a fresh location trajectory on an explicit owned simulator."""
import argparse
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import uuid


def coordinate(value):
    try:
        lat, lon = map(float, value.split(","))
    except ValueError as error:
        raise argparse.ArgumentTypeError("Use latitude,longitude") from error
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise argparse.ArgumentTypeError("Coordinate is outside geographic bounds")
    return lat, lon


def trajectory_speed(start, end, timeout):
    """Keep the interpolated path alive beyond the bounded test duration."""
    lat1, lat2 = map(math.radians, (start[0], end[0]))
    dlat = lat2 - lat1
    dlon = math.radians(end[1] - start[1])
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    distance = 6371000 * 2 * math.asin(math.sqrt(min(1, max(0, a))))
    if distance < 1:
        raise ValueError("Choose two waypoints at least one meter apart")
    return distance / (timeout + 60)


def run_command(command, timeout, log):
    with log.open("wb") as output:
        process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            return process.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            raise


def run_fixture(device, bundle, start, end, timeout, command, output, grant=False,
                invoke=subprocess.run, execute=run_command):
    speed = trajectory_speed(start, end, timeout)
    output.mkdir(parents=True, exist_ok=False)
    receipt = {"device": device, "simulated": True, "start": list(start), "end": list(end),
               "speed_meters_per_second": speed, "timeout_seconds": timeout,
               "permission_grant_requested": grant, "test_exit": None,
               "trajectory_started": False, "cleanup_succeeded": False,
               "limits": "Fixture lifecycle only; inspect native fixes and actual journey assertions separately. No network isolation is provided."}
    attempted = False

    def sim(*args):
        result = invoke(["xcrun", "simctl", *args], capture_output=True, text=True, check=False, timeout=15)
        if result.returncode:
            raise RuntimeError(f"simctl {args[0]} failed with exit {result.returncode}")
        return result.stdout

    try:
        devices = json.loads(sim("list", "devices", "--json"))
        matches = [item for group in devices["devices"].values() for item in group if item["udid"] == device]
        if len(matches) != 1 or matches[0]["state"] != "Booted":
            raise ValueError("Explicit simulator UUID must identify one booted device")
        if grant:
            sim("privacy", device, "grant", "location", bundle)
        attempted = True
        sim("location", device, "start", f"--speed={speed:.12g}", "--interval=1",
            f"{start[0]},{start[1]}", f"{end[0]},{end[1]}")
        receipt["trajectory_started"] = True
        receipt["test_exit"] = execute(command, timeout, output / "command.log")
    except Exception as error:
        receipt["error_type"] = type(error).__name__
    finally:
        if attempted:
            try:
                sim("location", device, "clear")
                receipt["cleanup_succeeded"] = True
            except Exception as error:
                receipt["cleanup_error_type"] = type(error).__name__
        receipt["fixture_command_passed"] = (receipt["test_exit"] == 0 and receipt["cleanup_succeeded"])
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--device", required=True, help="UUID of a task-owned booted simulator")
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--start", type=coordinate, required=True)
    parser.add_argument("--end", type=coordinate, required=True)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--grant-location", action="store_true", help="Explicitly grant in-use permission; grant persists afterward")
    parser.add_argument("--output", type=Path, required=True, help="New private evidence directory")
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        uuid.UUID(args.device)
    except ValueError:
        parser.error("--device must be an explicit simulator UUID")
    if not 1 <= args.timeout <= 3600:
        parser.error("--timeout must be between 1 and 3600 seconds")
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("Supply a test command after --")
    receipt = run_fixture(args.device, args.bundle, args.start, args.end, args.timeout,
                          command, args.output, args.grant_location)
    print(json.dumps(receipt))
    return 0 if receipt["fixture_command_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
