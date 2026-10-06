#!/usr/bin/env python3
"""Qualify an owned Android/Darwin ARM64 stack-layout control on Apple Silicon.

This runs authored code only. It does not load APKs or qualify a full FFI bridge.
"""
import argparse
import json
import platform
import subprocess
import tempfile
from pathlib import Path


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("This control requires native Apple Silicon macOS and Xcode.")
    fixtures = Path(__file__).resolve().parent / "fixtures" / "arm64_abi"
    with tempfile.TemporaryDirectory(prefix="rdd-abi-control-") as scratch:
        scratch = Path(scratch)
        android = scratch / "android.s"
        darwin = scratch / "darwin.s"
        run(["xcrun", "clang", "-target", "aarch64-linux-android", "-O2", "-S",
             str(fixtures / "stack-prefix.c"), "-o", str(android)])
        run(["xcrun", "--sdk", "iphonesimulator", "clang", "-target",
             "arm64-apple-ios17.0-simulator", "-O2", "-S",
             str(fixtures / "stack-prefix.c"), "-o", str(darwin)])
        executable = scratch / "control"
        run(["xcrun", "--sdk", "macosx", "clang", "-O2",
             str(fixtures / "bridge-control.c"), str(fixtures / "bridge-control.S"),
             "-o", str(executable)])
        result = run([str(executable)]).strip()
        print(json.dumps({
            "scope": "owned scalar-prefix control; native macOS execution, iOS compiler comparison",
            "result": result,
            "compiler": run(["xcrun", "clang", "--version"]).splitlines()[0],
            "android_assembly": android.read_text(),
            "ios_assembly": darwin.read_text(),
            "limits": ["not a general trampoline generator", "not an original app call",
                       "no physical iPhone execution", "no floating-point, aggregate or variadic coverage"],
        }, indent=2))


if __name__ == "__main__":
    main()
