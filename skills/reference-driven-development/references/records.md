# Durable evidence and retrieval

Reuse existing project notes. Keep a compact brief for outcome, constraints with reasons, state, assumptions, evidence locations, and next action. Store private evidence outside the distributable skill and public repository. Do not impose separate documents when a linked project note suffices.

For sustained investigations, retain reference metadata, raw evidence, atomic contributions, reversible decisions, transfer contracts, actual checks, and conditional lessons. Use stable identities and versioned links. Compact summaries are retrieval views, not the sole surviving knowledge. Save evidence before compression or retries; test recovery after a fresh context.

## Optional deterministic journal

`scripts/rdd.py` is a Python standard-library helper for append-only JSONL records. It checks structure, typed provenance links, and optional local-file hashes. It does not perform research, judge truth, capture a product, enforce isolation, or establish semantic coverage.

```sh
python3 /path/to/reference-driven-development/scripts/rdd.py append /private/project/records.jsonl --record /private/project/new-record.json
python3 /path/to/reference-driven-development/scripts/rdd.py check /private/project/records.jsonl
python3 /path/to/reference-driven-development/scripts/rdd.py query /private/project/records.jsonl --term restart --kind contribution
python3 /path/to/reference-driven-development/scripts/rdd.py query /private/project/records.jsonl --neglected
```

Each record has unique `id`, `kind`, and object `data`. `data.links` lists already existing record IDs. Required nonempty fields:

| Kind | Fields | Required linked kinds |
| --- | --- | --- |
| reference | locator, job, inspection | none |
| evidence | claim, basis, conditions | at least one reference |
| contribution | property, conditions, delta, test | at least one evidence |
| decision | status, conditions, reason, revisit | exactly one contribution |
| transfer | invariant, adaptation, artifact, check_plan | at least one contribution |
| check | method, outcome, result, limits | at least one transfer |
| lesson | lesson, scope, validation, revisit | at least one check |

Evidence basis: `observed`, `documented`, `inferred`, `proposed`. Decision status: `candidate`, `adopted`, `challenger`, `deferred`, `contradicted`. Check outcome: `passed`, `failed`, `blocked`, `not-run`. Recording a proposed check as passed is an evidence error the schema cannot detect.

An evidence record may include `local_path` (relative to the journal directory) and `sha256`. Append computes its hash and rejects an incorrect supplied hash; check detects missing or changed files. Remote locators are not fetched or verified.

Append validates the existing journal and new record before writing, rejecting duplicate IDs and broken provenance. Use one coordinator writer; concurrent writers are unsupported. Append revisions rather than editing history. Latest linked decision in journal order determines current status.

`--neglected` finds contributions whose latest status is not adopted or which have no transfer. It surfaces a queue, not proof that every idea has been recovered. Term queries are lexical, not semantic. Inspect originals, conditions, and contradictions before acting on results; retained files alone do not establish useful retrieval.
