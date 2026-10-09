# Retained analysis and behavioral evidence

Use this module when repeated analysis costs time/context, static graphs leave
uncertain execution paths, or reconstruction claims depend on collected evidence.
It complements the existing journal and workflow; it does not replace them.

## Preserve evidence while shrinking the view

Use `scripts/analysis_reuse.py` before repeating an immutable analyzer query.
Declare an explicit artifact, operation, parameters, provider/version/settings,
and effects. The helper refuses live, mutable, implicit-cursor or unqualified
queries. Those declarations need inspection of the actual provider; this helper
cannot discover hidden dependencies. For document/address-dependent operations,
include those identities in parameters. Also include any external dependencies,
tool configuration, engine version and relevant environment in the profile.

Run `lookup` with the same binding. A miss calls for fresh analysis; a hit returns
a retained evidence ID, not the full payload. Run `view` with that ID and a JSON
pointer/page to examine a focused portion. Views retain the parent's source,
basis, conditions and limitations and reject artifact/profile drift. Views default to at most 20 items and 64 KiB of encoded output. An oversized
view is refused rather than silently truncated; use a smaller page, a deeper
collection or an explicitly qualified provider summary. Keep the full parent.

Example query (authored fixture; adapt to the actual provider):

```json
{"provider_profile":{"provider":"analyzer","version":"1","settings":{"mode":"strict"}},"operation":"xrefs","parameters":{"document":"target","address":"0x10"},"effects":{"immutable":true,"mutates_artifact":false,"depends_on_live_state":false,"depends_on_implicit_cursor":false}}
```

The evidence file declares `basis` (observed/documented/inferred), `source`,
`conditions`, and an explicit `limitations` string list. Run from a private task
workspace; analysis may contain proprietary or sensitive material.

```sh
python scripts/analysis_reuse.py lookup --store retained --artifact target.bin --query query.json
python scripts/analysis_reuse.py retain --store retained --artifact target.bin --query query.json --result analysis.json --evidence evidence.json
python scripts/analysis_reuse.py view --store retained --artifact target.bin --query query.json --id EVIDENCE_ID --pointer /rows --limit 20
```

Link the retained ID and local parent path in the existing evidence journal. The
helper keeps immutable content-addressed parents and a single-writer query index.
It does not schedule analyzers, authenticate evidence or support concurrent writes.

## Compare execution, including its intermediate boundaries

Start with cheap static analysis. Retain unresolved edges instead of treating a
missing indirect call as proof of no path. Instrument uncertain boundaries on
the original, then compare the reconstruction under the same inputs/time/service
fixture. Normalize legitimate platform differences explicitly in the collector;
never sort away event order or discard required state to obtain a pass.

`scripts/behavioral_evidence.py compare original.json candidate.json --output comparison.json`
requires matching `case`, `environment` (shared controlled scenario identity),
`inputs_sha256`, nonempty ordered `events` containing `boundary` and phase-entry
`state`, plus `final_state`. It catches reordered calls even when final state is
identical. Preserve original and candidate platform/build identities in separate
capture provenance. Exact JSON comparison only covers those supplied boundaries;
choose measurements and tolerances appropriate to audio, graphics and time.

For an unknown that requires behavioral proof, bind it to a fixed nonempty set of
required cases and a qualified environment. The `closure` command checks each
local receipt's SHA-256, obligation/case/environment, observed original basis,
executed-verifier declaration, pass status and event/final-state equality. Missing
cases, inferred original authority, stale receipts and swapped contexts remain
unresolved. Inspect the actual capture and execution receipts before supplying
those declarations. This is structural qualification, not independent truth or
full product equivalence. Use the existing workflow to track dependencies and
remaining unknowns.

Closure packet shape:

```json
{"obligations":[{"id":"persist","environment":"controlled-v1","required_cases":["reopen","cancel"],"receipts":[{"case":"reopen","file":"results/reopen.json","sha256":"ACTUAL_FILE_SHA256"}]}]}
```

Each comparison receipt also declares `obligation`, `original_basis:"observed"`
and `verifier_executed:true`, backed by inspected execution evidence. Run
`python scripts/behavioral_evidence.py closure obligations.json --root private-task`.
Unresolved closure or failed comparison exits 1; malformed inputs exit 2.

## Evaluate adoption

Before crediting speed/cost/fidelity gains, use the existing reconstruction trial
helper on paired fixed cases and held-out connected journeys. Include stale
provider settings, wrong fixture, same-final-state/wrong-order, omitted negative
cases and corrupted retained evidence. Measure calls, returned bytes, time and
model costs separately. Keep failures and missing observations in the denominator.
Reverse the adaptation if it hides cases or costs more than fresh targeted work.

## References and scope

Mechanisms inspected in [REA](https://github.com/morluto/rea) at
`8c96baab80dc258d31ca1632d761fffb11dbaaae`: retained analysis views, artifact/provider
cache binding and authority-qualified obligations. Source contracts were tested;
provider integration and universal fidelity were not demonstrated. The helpers
here are project-authored adaptations; no upstream source is bundled.

[DX-Ball reconstruction](https://github.com/N0zoM1z0/dx-ball) at
`3142ddbc0d6f92d91b1aaf9f279b3314590c98c2` supplies the original-binary oracle,
ordered boundary and evaluator-corruption mechanisms. Its source was inspected;
its target suite was not executed here. Both references use MIT licenses.
[angr CFG analysis](https://docs.angr.io/en/latest/analyses/cfg.html) supplies the
static-versus-contextual investigation tradeoff; unresolved targets remain possible.
[decomp-permuter](https://github.com/simonlindholm/decomp-permuter) and
[asm-differ](https://github.com/simonlindholm/asm-differ) are conditional leads for
same-platform compilation matching, not cross-platform semantic equivalence.
