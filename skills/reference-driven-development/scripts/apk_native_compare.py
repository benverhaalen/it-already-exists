#!/usr/bin/env python3
"""Compare two apk_native_profile.py reports without conflating runtime
compatibility with application equivalence.

Matching ABI/machine word size, matching toolchain-derived library sets or
even an identical declared ABI never proves two APKs are the same
application: shared SDKs and engines routinely produce byte-identical
non-app libraries (engine runtimes, codecs) across unrelated apps. Only an
identical SHA256 of a library's actual decoded bytes is artifact identity
for that library; only an identical whole-APK input SHA256 is artifact
identity for the whole package. This module never emits an "equivalent
application" verdict; it classifies each matched library and leaves
unqualified semantic equivalence to a human reviewing actual application
artifact evidence.
"""
import argparse
import json
import re
from pathlib import Path
import sys

MARKERS = ('bits', 'machine', 'little_endian')


def _digest(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("missing or invalid SHA256 evidence")
    return value


def _marker(record):
    elf = record.get('elf')
    return tuple(elf[key] for key in MARKERS) if elf else None


def _index(profile):
    """Group library records by (declared_abi, library file name)."""
    grouped = {}
    for record in profile['libraries']:
        key = (record['declared_abi'], Path(record['entry']).name)
        grouped.setdefault(key, []).append(record)
    return grouped


def compare(reference, candidate):
    if reference.get('schema_version') != 1 or candidate.get('schema_version') != 1:
        raise ValueError('unsupported native-profile schema_version')
    _digest(reference["input"]["sha256"])
    _digest(candidate["input"]["sha256"])
    for report in (reference, candidate):
        for record in report["libraries"]:
            if record["status"] == "inspected":
                _digest(record.get("sha256"))
                if not record.get("elf") or any(k not in record["elf"] for k in MARKERS):
                    raise ValueError("inspected library has incomplete ELF evidence")
    ref_index, cand_index = _index(reference), _index(candidate)
    libraries = []
    for key in sorted(set(ref_index) | set(cand_index)):
        declared_abi, name = key
        ref_records, cand_records = ref_index.get(key, []), cand_index.get(key, [])
        if not ref_records:
            for record in cand_records:
                libraries.append({'declared_abi': declared_abi, 'name': name,
                                  'candidate_entry': record['entry'], 'reference_entry': None,
                                  'classification': 'candidate_only'})
            continue
        if not cand_records:
            for record in ref_records:
                libraries.append({'declared_abi': declared_abi, 'name': name,
                                  'reference_entry': record['entry'], 'candidate_entry': None,
                                  'classification': 'reference_only'})
            continue
        for ref_record in ref_records:
            for cand_record in cand_records:
                entry = {'declared_abi': declared_abi, 'name': name,
                         'reference_entry': ref_record['entry'], 'candidate_entry': cand_record['entry']}
                if ref_record['status'] != 'inspected' or cand_record['status'] != 'inspected':
                    entry['classification'] = 'uncompared'
                    entry['reason'] = (f"reference status={ref_record['status']!r}, "
                                       f"candidate status={cand_record['status']!r}")
                elif ref_record['sha256'] == cand_record['sha256']:
                    entry['classification'] = 'identical_bytes'
                elif _marker(ref_record) == _marker(cand_record):
                    entry['classification'] = 'runtime_marker_match_bytes_differ'
                    entry['note'] = ('Same ISA/word-size/endianness only; shared toolchains or engines '
                                      'commonly produce this across unrelated applications. Not artifact '
                                      'identity and not evidence of application equivalence.')
                else:
                    entry['classification'] = 'runtime_marker_mismatch'
                libraries.append(entry)
    counts = {}
    for entry in libraries:
        counts[entry['classification']] = counts.get(entry['classification'], 0) + 1
    ref_sha, cand_sha = reference['input']['sha256'], candidate['input']['sha256']
    any_runtime_clue_only = counts.get('runtime_marker_match_bytes_differ', 0) > 0
    any_mismatch = bool(counts.get('runtime_marker_mismatch') or counts.get('reference_only') or
                        counts.get('candidate_only'))
    all_identical = bool(libraries) and all(e['classification'] == 'identical_bytes' for e in libraries)
    return {
        'schema_version': 1,
        'reference_id': reference['reference_id'], 'candidate_id': candidate['reference_id'],
        'input_identity': {'reference_sha256': ref_sha, 'candidate_sha256': cand_sha,
                            'identical_input_bytes': ref_sha == cand_sha},
        'libraries': libraries,
        'classification_counts': counts,
        'verdict': {
            'exact_whole_apk_identity': ref_sha == cand_sha,
            'all_compared_libraries_identical_bytes': all_identical,
            'runtime_compatibility_clues_only': any_runtime_clue_only and not all_identical,
            'mismatches_present': any_mismatch,
            'application_equivalence': 'not_evaluated_by_this_tool',
        },
        'limits': ['Compares only native ELF libraries this profiler inspected; DEX, assets, resources, '
                   'manifest and signing identity are untouched and may still differ or match independently.',
                   'A "runtime_marker_match_bytes_differ" library only shows shared ISA/word-size/endianness; '
                   'it is a toolchain/engine compatibility clue, never application identity or equivalence.',
                   'Matching every compared native library does not establish whole-application equivalence; '
                   'treat it as partial evidence requiring actual full-artifact hashes or behavioral comparison.',
                   'Uninspected (budget-skipped, duplicate-path or invalid) libraries on either side cannot '
                   'be compared and are reported as "uncompared", not as a match or mismatch.'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path, help='apk_native_profile.py JSON for the reference APK')
    parser.add_argument('candidate', type=Path, help='apk_native_profile.py JSON for the candidate APK')
    parser.add_argument('--output', type=Path, required=True, help='Fresh JSON path')
    args = parser.parse_args()
    try:
        reference = json.loads(args.reference.read_text(encoding='utf-8'))
        candidate = json.loads(args.candidate.read_text(encoding='utf-8'))
        result = compare(reference, candidate)
        with args.output.open('x', encoding='utf-8') as output:
            json.dump(result, output, indent=2)
            output.write('\n')
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        print(f'Native profile comparison blocked: {exc}', file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
