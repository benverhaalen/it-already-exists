# Project-owned controls and development feedback

Use `scripts/project_controls.py` when a project needs a reproducible route that
a fresh consumer can drive. Keep the product, its services and its data in that
project. This helper supplies inspected file identities, an explicit feature map,
bounded command execution, serial ownership, recovery evidence and declared
dependency invalidation. It does not provide a universal UI driver or establish
an independent oracle.

The native lead can run `inspect` and `generate` before acquiring a driver.
An empty scaffold records the missing driver and oracle. This avoids requiring
an already-qualified driver to explain that one is missing. Acquire the missing
project-specific controls, then generate a new reviewed manifest; do not label
guessed package scripts or successful process launch as qualified behavior.

## Normal route

Commands below use an installed skill path; replace the script path with the
actual installed location and the project path with the selected project.

```sh
python3 /path/to/reference-driven-development/scripts/project_controls.py inspect --root /path/to/project --source-root src
python3 /path/to/reference-driven-development/scripts/project_controls.py generate --root /path/to/project --blueprint /path/to/reviewed-blueprint.json
python3 /path/to/reference-driven-development/scripts/project_controls.py doctor --root /path/to/project
python3 /path/to/reference-driven-development/scripts/project_controls.py run --root /path/to/project --feature edit-and-save --class maintenance
```

Generation creates `.rdd/project-controls/manifest.json` and its adjacent guide.
The manifest contains the exact helper command array, project identity, manifest
path and evidence location. Give a cold consumer those generated files and the
project. They can doctor, drive every named feature, inspect durable state and
clean up using the declared route. Existing manifests are never overwritten.
For intentional regeneration, choose a new `--output` path inside
`.rdd/project-controls/`, inspect the changed map and use `--manifest` explicitly.

Inspect the normal entry, default state, alternate required entries and recent
user-facing churn before selecting the map. Each feature names:

- `id`, `entry`, `default_state` and `prerequisites`, including an empty list
  when there are none.
- `state_observation`, `expected_effect` and `oracle_scope` in concrete terms.
- `route`, an ordered list of declared control IDs.
- Optional `reset_control` and `cleanup_control`, each naming its exact role.

A one-feature cold control proof qualifies that feature's control acquisition.
It does not discharge the other features or the complete user request. A map
cannot prove its own completeness; reconcile it with the original obligations
and current actual entries. A working toolbar cannot stand in for a required
keyboard entry, different default or persistent-state route.

## Blueprint shape

This is a declaration format, not an executable example for an unknown project.
Replace commands and observations after inspecting the actual project.

```json
{
  "source_roots": ["src", "tests", "package.json"],
  "readiness": {
    "driver": "declared",
    "oracle": "missing",
    "gaps": ["independent complete-journey oracle not acquired"]
  },
  "controls": [
    {
      "id": "verify-edit",
      "argv": ["npm", "run", "verify:edit"],
      "cwd": ".",
      "timeout_seconds": 60,
      "max_output_bytes": 1048576,
      "role": "verify",
      "effect": "read-only",
      "classes": ["maintenance", "fix", "forensics"],
      "expected_exit_codes": [0]
    }
  ],
  "features": [
    {
      "id": "edit-and-save",
      "entry": "existing editor control opens the default project",
      "default_state": "saved document reopens with its last committed content",
      "prerequisites": ["isolated project fixture is initialized"],
      "state_observation": "control independently reads the reopened document",
      "expected_effect": "edit is retained after restart and undo remains usable",
      "oracle_scope": "declared control only; independent equivalence is unqualified",
      "route": ["verify-edit"]
    }
  ],
  "development_profile": {
    "kind": "code",
    "feature_roots": {"edit-and-save": ["src/editor"]},
    "allowed_imports": {"edit-and-save": []},
    "shared_invariants": [],
    "diagnostics": [],
    "preview": null
  }
}
```

`source_roots` select the actual freshness scope. Capture all relevant source,
config, assets and test controls; an individual file scope cannot detect an added
file elsewhere. Doctor compares exact bytes and directory additions/deletions.
It excludes `.git` and project-owned `.rdd` state. Missing selected roots, command
working directories and declared diagnostic fixtures are explicit problems.
Symlink source/working paths require a separate qualified adapter and are rejected
here. A moved project needs an intentional new root binding.

Controls require command arrays, a project-relative `cwd`, a bounded timeout,
role, effect and authorized operation classes. There is no shell interpolation.
Supported roles are `launch`, `doctor`, `drive`, `observe`, `verify`, `reset`,
`cleanup` and `diagnostic`; effects are `read-only`, `runtime-state` and
`product-mutation`.

## Authority, serial live state and recovery

Generation writes the control scaffold; it does not run product commands.
Maintenance drives the mapped features and repairs control/documentation drift
through separately reviewed generation. It cannot select `product-mutation`
controls. Fix may select explicitly declared product mutation controls.
Forensics selects read-only observation and diagnostics. Preserve failures and
expected behavior when repairing a product or control; do not rewrite an oracle
to turn a regression into success.

The helper holds one advisory live-owner lease across the route, reset and final
cleanup. Participating consumers of this helper serialize per project. It cannot
fence an unrelated native session or external tool that ignores that lease.
Commands receive `RDD_CONTROL_OWNER`, `RDD_CONTROL_STATE` and
`RDD_CONTROL_PROJECT`. A reset or cleanup must declare
`"ownership": "current-run-only"`; its implementation must check resource
identity before touching it. Use per-owner runtime paths/markers and exact owned
process identities. Never stop a service merely because its name or port matches.
Shared services and final evidence must survive cleanup.

Command arrays are trusted project code, **not an access sandbox**. A command can
perform effects beyond its declaration. The helper detects declared-source drift
after execution, reports it and blocks further fresh-source use; it cannot prevent
or undo an untrusted command's mutation. Review command implementation and its
ownership checks before selecting it. Use a real isolated target/qualified adapter
when the product requires stronger boundaries. Do not place credentials in argv,
stdout, stderr or generated records.

A failed, timed-out or output-limited action preserves unknown target effects,
even if the subprocess is gone. The process primitive stops descendants in its
owned process group; intentionally detached descendants or external services need
their actual project-specific lifecycle controls. A feature failure may execute
its owned reset and final cleanup, records post-reset doctor state, and stops the
route. It does not automatically repeat an action that may already have committed.
Receipts preserve the admitted intent, exact command, source manifest identity,
results, reset/cleanup, source drift and elapsed time. An interrupted admitted
intent or a failed unknown-effect attempt blocks mutating retry. Corrupt evidence
blocks execution instead of disappearing from recovery.

To reconcile, add an inspected read-only `observe` or `verify` control that asserts
the actual target state. It must declare a `reconciliation_scope` and an explicit
`reconciliation_outcome`: `observed-completed`, `observed-not-applied` or
`observed-reset`. Run that selected control with `--reconcile-attempt <intent-id>`.
Only its successful target-specific observation closes the named pending intent;
failure retains the unknown. A generic process check cannot supply this outcome.
The declaration and exit-code assertion still need qualification; this helper does
not infer that an observer is sound or independent.

`clean` means the selected commands completed with their declared exit codes and
no observed selected-source drift. `changed` means an authorized fix changed those
sources and needs review/new controls. `blocked` retains a failed route, stale
source, unavailable driver, unknown prior effect or cleanup failure. These statuses
are not whole-task acceptance. `oracle_verified` always remains false here; the
independent verifier owns acceptance. Declared missing-oracle gaps remain visible
even when a useful bounded route completes.

## Project development profile

For code projects, record feature roots and allowed inward imports alongside the
actual project commands. `allowed_imports` maps a consumer feature to feature IDs
it may depend on. This declaration does not scan or enforce language imports;
use an inspected project-specific compiler/lint/architecture control for that job.
Local helpers may remain duplicated where that keeps feature ownership clear.

`shared_invariants` name true shared schemas, primitives and tokens. Each entry
contains `id`, `kind` (`schema`, `primitive` or `token`), `owner`, `consumers`,
project-relative `sources` and `validator_controls`. A changed shared source
invalidates its inverse consumers; allowed-import inverse edges extend the affected
set. Unmapped source changes conservatively invalidate every declared feature.
Doctor labels this as a declared map, not extracted semantic dependency proof.
Drive every affected consumer after a schema/token change, including client and
server routes where applicable. Demonstrate the actual defect before repair and
the repaired consumer behavior afterward.

`diagnostics` bind exact controls, `positive_fixture` defect paths,
`negative_fixture` valid-exception paths and justified `suppressions`. The helper
checks their presence; it does not infer expected findings from test titles or run
calibration automatically. Run those fixtures through the actual effective
diagnostic configuration and retain positive/negative outcomes. Capture relevant
configuration files in `source_roots`; a changed rule/configuration invalidates
the profile's freshness.

`preview` optionally binds a declared `control`, usable `entry`, actual
`build_ref`, `environment` and `access`. The fields are declarations. Qualify the
actual preview build and have a fresh consumer use that entry and inspect durable
state. A successful local build does not establish preview availability or quality.

Non-code artifacts may use `kind: "non-code"` and only the controls/declarations
that fit their rendering, observation and judgment. No import graph, schema or
preview service is mandatory for them.

This helper uses Unix advisory locking and is qualified by authored local fixtures
on the tested host. Windows locking, arbitrary native UI fidelity, external
service commit fencing and cross-host ownership require their own qualified
adapters. Keep project manifests, captured output and evidence private unless
they are deliberately authored public fixtures.
