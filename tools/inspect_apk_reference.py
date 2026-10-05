#!/usr/bin/env python3
"""Compatibility entry point; canonical APK intake ships with the portable skill."""
import importlib.util
from pathlib import Path
import sys

_location = Path(__file__).resolve().parents[1] / 'skills/reference-driven-development/scripts/apk_intake.py'
_spec = importlib.util.spec_from_file_location('rdd_apk_intake', _location)
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
# Preserve the existing analyst API as well as the command-line entry point.
globals().update({name: value for name, value in vars(_module).items() if not name.startswith('_')})

if __name__ == '__main__':
    sys.exit(main())
