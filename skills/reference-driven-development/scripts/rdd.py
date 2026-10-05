#!/usr/bin/env python3
"""Optional, single-writer JSONL evidence journal. History is never overwritten.

Structural checks and file hashes do not establish semantic truth or independence.
Use one writer at a time; this helper provides no concurrent-writer isolation.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

REQUIRED = {
    "reference": ("locator", "job", "inspection"),
    "evidence": ("claim", "basis", "conditions"),
    "contribution": ("property", "conditions", "delta", "test"),
    "decision": ("status", "conditions", "reason", "revisit"),
    "transfer": ("invariant", "adaptation", "artifact", "check_plan"),
    "check": ("method", "outcome", "result", "limits"),
    "lesson": ("lesson", "scope", "validation", "revisit"),
    "change": ("reason", "scope", "revisit"),
}
TARGETS = {
    "evidence": "reference", "contribution": "evidence",
    "decision": "contribution", "transfer": "contribution",
    "check": "transfer", "lesson": "check",
}
ENUMS = {
    "evidence": ("basis", {"observed", "documented", "inferred", "proposed"}),
    "decision": ("status", {"candidate", "adopted", "challenger", "deferred", "contradicted"}),
    "check": ("outcome", {"passed", "failed", "blocked", "not-run"}),
}


class JournalError(ValueError):
    """Invalid record, journal, or captured file."""


def reject_constant(value):
    raise JournalError(f"non-JSON numeric constant: {value}")


def digest(path):
    try:
        with path.open("rb") as stream:
            result = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                result.update(chunk)
            return result.hexdigest()
    except OSError as exc:
        raise JournalError(f"cannot read evidence file {path}: {exc}") from exc


def validate(record, previous, store, capture=False, verify_files=True):
    if not isinstance(record, dict):
        raise JournalError("record must be an object")
    identifier, kind, data = (record.get(key) for key in ("id", "kind", "data"))
    if not isinstance(identifier, str) or not identifier.strip():
        raise JournalError("id must be a nonempty string")
    if identifier in previous:
        raise JournalError(f"duplicate id: {identifier}")
    if not isinstance(kind, str) or kind not in REQUIRED:
        raise JournalError(f"unknown kind: {kind!r}")
    if not isinstance(data, dict):
        raise JournalError(f"{identifier}: data must be an object")
    for field in REQUIRED[kind]:
        value = data.get(field)
        if value is None or value == "" or value == [] or value == {} or (
            isinstance(value, str) and not value.strip()
        ):
            raise JournalError(f"{identifier}: missing or empty {field}")
    if kind in ENUMS:
        field, choices = ENUMS[kind]
        if not isinstance(data[field], str) or data[field] not in choices:
            raise JournalError(f"{identifier}: invalid {field}")
    links = data.get("links", [])
    if not isinstance(links, list) or any(not isinstance(link, str) for link in links):
        raise JournalError(f"{identifier}: links must be a list of ids")
    if len(set(links)) != len(links):
        raise JournalError(f"{identifier}: duplicate links")
    for link in links:
        if link not in previous:
            raise JournalError(f"{identifier}: link is not an existing id: {link}")
    for field in ("depends_on", "targets"):
        values = data.get(field, [])
        if not isinstance(values, list) or any(not isinstance(v, str) or v not in previous for v in values):
            raise JournalError(f"{identifier}: {field} must contain existing ids")
        if len(values) != len(set(values)):
            raise JournalError(f"{identifier}: duplicate {field}")
    if kind == "change" and not links:
        raise JournalError(f"{identifier}: change needs affected record links")
    if "task_scope" in data and (not isinstance(data["task_scope"], str) or not data["task_scope"].strip()):
        raise JournalError(f"{identifier}: task_scope must be a nonempty string")
    if "applies_to" in data:
        selectors = data["applies_to"]
        if not isinstance(selectors, dict) or not selectors:
            raise JournalError(f"{identifier}: applies_to must be a nonempty selector object")
        for key, values in selectors.items():
            if key not in {"scopes", "surfaces", "operations", "tags"} or not isinstance(values, list) or not values or any(not isinstance(v, str) or not v.strip() for v in values):
                raise JournalError(f"{identifier}: invalid applies_to selector {key}")
    if kind in TARGETS:
        count = sum(previous[link]["kind"] == TARGETS[kind] for link in links)
        if count < 1 or (kind == "decision" and count != 1):
            raise JournalError(f"{identifier}: needs {'exactly one' if kind == 'decision' else 'at least one'} {TARGETS[kind]} link")
    if kind == "evidence" and "local_path" in data:
        local = data["local_path"]
        if not isinstance(local, str) or not local.strip() or Path(local).is_absolute():
            raise JournalError(f"{identifier}: local_path must be relative to the journal parent")
        saved = data.get("sha256")
        if saved is not None and (not isinstance(saved, str) or len(saved) != 64 or any(c not in '0123456789abcdef' for c in saved)):
            raise JournalError(f"{identifier}: invalid sha256")
        if capture or verify_files:
            actual = digest(store.parent / local)
            if saved is not None and saved != actual:
                raise JournalError(f"{identifier}: evidence hash drift for {local}")
            if capture:
                data["sha256"] = actual
        if not capture and saved is None:
            raise JournalError(f"{identifier}: missing sha256 for local_path")
    elif kind == "evidence" and "sha256" in data:
        raise JournalError(f"{identifier}: sha256 requires local_path")
    return record


def read_records(store, allow_missing=False, verify_files=True):
    store = Path(store)
    try:
        raw = store.read_bytes()
    except FileNotFoundError:
        if allow_missing:
            return [], b""
        raise JournalError(f"journal does not exist: {store}")
    try:
        lines = raw.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise JournalError("journal is not UTF-8") from exc
    records, previous = [], {}
    for number, line in enumerate(lines, 1):
        try:
            record = json.loads(line, parse_constant=reject_constant)
            validate(record, previous, store, verify_files=verify_files)
        except (ValueError, TypeError) as exc:
            raise JournalError(f"line {number}: {exc}") from exc
        previous[record["id"]] = record
        records.append(record)
    return records, raw


def append(store, record, allow_drift=False):
    store = Path(store)
    records, raw = read_records(store, allow_missing=True, verify_files=not allow_drift)
    # Copy through JSON so capturing a hash does not mutate the caller's object.
    record = json.loads(json.dumps(record, allow_nan=False))
    validate(record, {item["id"]: item for item in records}, store, capture=True)
    payload = json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n"
    if raw and not raw.endswith(b"\n"):
        payload = "\n" + payload
    # All validation precedes opening for append. One writer is required.
    with store.open("ab") as stream:
        stream.write(payload.encode("utf-8"))
        stream.flush()
        os.fsync(stream.fileno())
    return record


def query(records, term=None, kind=None, neglected=False, task_scope=None):
    latest, transferred = {}, set()
    by_id = {record["id"]: record for record in records}
    for record in records:
        links = record["data"].get("links", [])
        if task_scope is not None and record['kind'] in ('decision', 'transfer') and record['data'].get('task_scope') != task_scope:
            continue
        if record["kind"] == "decision":
            for link in links:
                if by_id[link]["kind"] == "contribution":
                    latest[link] = record["data"]["status"]
        elif record["kind"] == "transfer":
            transferred.update(link for link in links if by_id[link]["kind"] == "contribution")
    for record in records:
        if kind and record["kind"] != kind:
            continue
        if neglected and (record["kind"] != "contribution" or (
            latest.get(record["id"]) == "adopted" and record["id"] in transferred
        )):
            continue
        if term and term.casefold() not in json.dumps(record, ensure_ascii=False).casefold():
            continue
        yield record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    add = commands.add_parser("append", help="validate then append one record")
    add.add_argument("store", type=Path)
    add.add_argument("--record", type=Path, required=True)
    add.add_argument("--allow-drift", action="store_true", help="explicit recovery: keep historical hashes and append after old files changed; new local evidence is still verified")
    check = commands.add_parser("check", help="check structure, links, and captured file hashes")
    check.add_argument("store", type=Path)
    find = commands.add_parser("query", help="case-insensitive lexical search; no semantic ranking")
    find.add_argument("store", type=Path)
    find.add_argument("--term")
    find.add_argument("--kind", choices=REQUIRED)
    find.add_argument("--neglected", action="store_true", help="contributions without an adopted latest decision or without a transfer")
    find.add_argument("--task-scope", help="scope decision/transfer status used by --neglected; records remain discoverable")
    args = parser.parse_args(argv)
    try:
        if args.command == "append":
            with args.record.open(encoding="utf-8") as stream:
                record = json.load(stream, parse_constant=reject_constant)
            result = append(args.store, record, allow_drift=args.allow_drift)
            print(json.dumps(result, ensure_ascii=False))
        else:
            records, _ = read_records(args.store)
            if args.command == "check":
                print(f"OK: {len(records)} records; structure, links, and file hashes checked")
            else:
                for record in query(records, args.term, args.kind, args.neglected, args.task_scope):
                    print(json.dumps(record, ensure_ascii=False))
    except (OSError, ValueError, TypeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
