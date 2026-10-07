#!/usr/bin/env python3
"""Report exact JSON state changes without copying field values into the receipt."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path

MAX_BYTES = 16 * 1024 * 1024
MAX_NODES = 100_000
MAX_DEPTH = 128


def digest(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True,
                     separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def validate(value, depth=0, budget=None):
    if budget is None:
        budget = [MAX_NODES]
    budget[0] -= 1
    if depth > MAX_DEPTH or budget[0] < 0:
        raise ValueError("JSON state exceeds traversal limits")
    if type(value) is dict:
        if any(type(k) is not str for k in value):
            raise ValueError("Object keys must be strings")
        children = value.values()
    elif type(value) is list:
        children = value
    elif type(value) in (str, int, bool, type(None)):
        children = ()
    elif type(value) is float and math.isfinite(value):
        children = ()
    else:
        raise ValueError("Unsupported JSON value")
    for child in children:
        validate(child, depth + 1, budget)


def compare_states(before, after):
    validate(before)
    validate(after)
    changes = []

    def record(pointer, kind, old=None, new=None):
        item = {"pointer": pointer, "kind": kind}
        if kind != "added":
            item["before_sha256"] = digest(old)
        if kind != "removed":
            item["after_sha256"] = digest(new)
        changes.append(item)

    def walk(a, b, pointer):
        if type(a) is not type(b):
            record(pointer, "type_changed", a, b)
        elif type(a) is dict:
            for key in sorted(set(a) | set(b)):
                child = pointer + "/" + key.replace("~", "~0").replace("/", "~1")
                if key not in a:
                    record(child, "added", new=b[key])
                elif key not in b:
                    record(child, "removed", old=a[key])
                else:
                    walk(a[key], b[key], child)
        elif type(a) is list:
            # A length change can shift identities; do not pretend indices align.
            if len(a) != len(b):
                record(pointer, "array_length_changed", a, b)
            else:
                for index, (old, new) in enumerate(zip(a, b)):
                    walk(old, new, pointer + "/" + str(index))
        elif digest(a) != digest(b):
            record(pointer, "value_changed", a, b)

    walk(before, after, "")
    return {"schema_version": 1, "equal": not changes,
            "before_sha256": digest(before), "after_sha256": digest(after),
            "changes": changes,
            "limits": "Exact JSON types and values; no protocol normalization, ignored fields, or authorization of mutations. Pointers and hashes can still be sensitive."}


def read_state(path):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Duplicate object key")
            result[key] = value
        return result

    with Path(path).open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("JSON input exceeds byte limit")
    value = json.loads(raw, object_pairs_hook=unique,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON number")))
    validate(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--before", required=True)
    parser.add_argument("--after", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        result = compare_states(read_state(args.before), read_state(args.after))
        # Refuse to overwrite evidence or either source input.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2, allow_nan=False)
            stream.write("\n")
    except (OSError, ValueError, RecursionError):
        parser.exit(2, "State comparison failed; check input validity, limits and unused output path.\n")
    print(json.dumps({"equal": result["equal"], "change_count": len(result["changes"])}))
    return 0 if result["equal"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
