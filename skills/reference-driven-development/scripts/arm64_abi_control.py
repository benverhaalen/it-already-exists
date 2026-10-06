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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--clang', help='Optional matching engine clang executable')
    args = parser.parse_args()
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise SystemExit("This control requires native Apple Silicon macOS and Xcode.")
    fixtures = Path(__file__).resolve().parent / "fixtures" / "arm64_abi"
    compiler = [args.clang] if args.clang else ["xcrun", "clang"]
    mac_sdk = run(["xcrun", "--sdk", "macosx", "--show-sdk-path"]).strip()
    ios_sdk = run(["xcrun", "--sdk", "iphonesimulator", "--show-sdk-path"]).strip()
    with tempfile.TemporaryDirectory(prefix="rdd-abi-control-") as scratch:
        scratch = Path(scratch)
        android = scratch / "android.s"
        darwin = scratch / "darwin.s"
        run(compiler + ["-target", "aarch64-linux-android", "-O2", "-Werror", "-S",
             str(fixtures / "stack-prefix.c"), "-o", str(android)])
        run(compiler + ["-isysroot", ios_sdk, "-target",
             "arm64-apple-ios17.0-simulator", "-O2", "-Werror", "-S",
             str(fixtures / "stack-prefix.c"), "-o", str(darwin)])
        executable = scratch / "control"
        run(compiler + ["-isysroot", mac_sdk, "-O2", "-Werror",
             str(fixtures / "bridge-control.c"), str(fixtures / "bridge-control.S"),
             "-o", str(executable)])
        result = run([str(executable)]).strip()
        mixed = scratch / "mixed-control"
        run(compiler + ["-isysroot", mac_sdk, "-O2", "-Werror",
             str(fixtures / "mixed-control.c"), str(fixtures / "mixed-control.S"),
             "-o", str(mixed)])
        mixed_result = run([str(mixed)]).strip()
        print(json.dumps({
            "scope": "owned scalar and mixed controls; native macOS execution, iOS compiler comparison",
            "result": result,
            "mixed_result": mixed_result,
            "compiler": run(compiler + ["--version"]).splitlines()[0],
            "android_assembly": android.read_text(),
            "ios_assembly": darwin.read_text(),
            "limits": ["not a general trampoline generator", "not an original app call",
                       "no physical iPhone execution", "no aggregate, variadic or callback coverage"],
        }, indent=2))


if __name__ == "__main__":
    main()
