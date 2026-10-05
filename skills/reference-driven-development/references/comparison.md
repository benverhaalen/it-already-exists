# Independent comparison and repair evidence

Use `scripts/comparison.py` to evaluate separately reviewed appearance, state,
trajectory and duration properties. The evaluator lives outside the implementer
boundary. Keep the contract fixed during implementation repair; if the intended
behavior changes, review a new contract rather than loosening a failing rule.

The evaluator accepts generic packets. For the Android session adapter,
`scripts/observation_packet.py` supplies a reviewed, integrity-bound producer.
It checks actual APK bytes against installed digests, completed consecutive
attempts, exact action sequences, post-input probes, capture identity and fresh
stability evidence. Arbitrary generic packets still need an independently
inspected observer/build receipt. Neither path is cryptographic device
attestation or certification of complete reconstruction.

## Android journal handoff

Run the producer outside the implementation boundary. The analyst reviews the
complete journey and declarative state projections, then supplies a selection:

```json
{
  "fixture": "counter cleared and launched",
  "journey": "increment",
  "milestones": [{
    "id": "incremented", "attempt_id": "ACTUAL_COMPLETED_ATTEMPT",
    "operation": "act", "actions": [{"kind": "tap", "x": 540, "y": 421}],
    "state": {"count": {
      "probe": "count", "kind": "android-preference-int", "name": "count"
    }}
  }]
}
```

The selection must include every intervening attempt from its first to last
milestone; failed or uncertain attempts cannot be hidden inside a passing
trajectory. Setup before the selected journey remains bound by the full journal
hash. Starting-condition meaning and the journey's coverage require review.
State projections support `text`, `json` with a list of object keys in `path`,
and `android-preference-int` with an exact `name`. Only the last successful
post-input probe vector supplies state. Missing or ambiguous data fails export;
no arbitrary extraction code runs. Review text/JSON exports for private data.

The review contains `approved: true`, `reviewer`, and four current digests:
`journal_sha256` of exact `events.jsonl` bytes; `config_sha256` of the session's
sorted JSON configuration using Python's default separators; and
`contract_sha256` and `selection_sha256` using `comparison.canonical`.
Any appended journal data requires a new review. Keep reviews and raw journals
private; declaration of approval alone does not enforce reviewer independence.

```sh
python3 /path/to/skill/scripts/observation_packet.py \
  --session /private/observed-session --config /private/session-config.json \
  --contract /private/contract.json --selection /private/selection.json \
  --review /private/evidence-review.json --apk /private/installed.apk \
  --output /private/new-evidence-bundle
```

Repeat `--apk` for all installed splits. For a single APK, artifact identity is
its byte SHA256; for multiple APKs it is `comparison.canonical` of an object
containing `apk_sha256s` sorted lexicographically. The new bundle contains
`packet.json` and the selected checked captures; raw probe outputs stay outside.
All stability frames are hash-checked, including frames not exported. The
producer verifies the configured policy instead of weakening it. State and
capture times remain separate: sequential readings are not atomic, and host
capture completion is not guest presentation time. The comparator can consume
the bundle directly; the implementer receives only separately reviewed behavior
and counterexamples.

## Install and execute

State, trajectory and timing comparisons use the standard library. Install the
optional dependency in the chosen Python environment for image checks:

```sh
python3 -m pip install -r /path/to/skill/scripts/requirements-comparison.txt
python3 /path/to/skill/scripts/comparison.py \
  --contract /private/contract.json --reference /private/original/packet.json \
  --candidate /private/candidate/packet.json --output /private/report.json
```

Output must be new. Exit 0 means all declared properties passed; 2 means a
property failed or was not tested; 1 means invalid inputs or an output error.
Missing evidence, unavailable Pillow, changed image bytes or undecodable images
produce `not_tested`, never a pass. Invalid contracts are rejected even if the
corresponding observation is absent. One failure keeps the overall result failed
while preserving any properties that remain untested.

## Evidence packets and contracts

Each packet contains `run_id`, `artifact_sha256`, `contract_sha256`, `fixture`,
`journey`, optional `timestamp_basis` and `observations`. Contract identity is
`comparison.canonical(contract)`: SHA256 of sorted compact JSON with nonfinite
numbers forbidden. Original and candidate use the same contract, fixture and
journey, but distinct run/build identities. Every observation has a unique `id`,
the packet's `run_id`, and a finite ordered `time`; optional `state` is an object
and `image` has `path` and `sha256`. Image paths are relative to that packet's
directory. Links inside the evidence root, traversal and files over 32 MiB are
rejected. Do not put these private packets or captures in the public package.

An example contract:

```json
{
  "properties": [
    {"id": "persistence", "kind": "state", "observation": "reopened",
     "path": ["count"], "operator": "equals"},
    {"id": "button", "kind": "pixels", "observation": "initial",
     "region": [20, 40, 120, 80], "channel_tolerance": 0,
     "max_changed_ratio": 0},
    {"id": "route", "kind": "trajectory",
     "allowed": [["initial", "incremented", "reopened"]]},
    {"id": "duration", "kind": "duration", "start": "initial",
     "observation": "reopened", "tolerance": 0.1}
  ]
}
```

Use `reference_observation` and `candidate_observation` for intentional frame
alignment instead of `observation`. State paths default to the original's value;
`expected` supplies a reviewed target for adaptation. Equality preserves types,
so `true` cannot masquerade as count `1`. Other operators are `not_equals` and
numeric `within` with finite nonnegative `tolerance`.

Pixel properties compare RGBA channel differences without rescaling. Crops are
explicit `reference_crop` and `candidate_crop`; region and rectangle bounds use
exclusive right/bottom edges. Geometry mismatch fails. A `masks` entry requires
`rect` and a reviewable `reason`; overlapping masks count only once, and masking
the entire region makes evidence unusable. Thresholds need repeated original
observations and seeded-defect calibration; no automatic calibration is supplied.
Keep critical regions separate so global averages cannot hide a broken control.
Raw channel thresholds are not a perceptual, antialias-aware or expert taste
judgment. C-backed [Pillow channel operations](https://pillow.readthedocs.io/en/stable/reference/ImageChops.html)
avoid interpreting a Python loop for every phone pixel; alpha remains included.

Trajectory rules match a complete allowed observation sequence, with optional
`forbidden` IDs. They cannot pass by combining milestones from different branches.
Duration uses within-run differences, not equal absolute clocks, and requires the
same declared timestamp basis. Host observation completion is not device frame
presentation time; compare those measurements only for the property they measure.

## Reviewed counterexamples

The reviewer supplies `approved: true`, `reviewer` and `report_sha256` computed
with `comparison.canonical(report)`. Review the actual current report and remove
private or source-shaped state values before permitting strict handoff.

```sh
python3 /path/to/skill/scripts/comparison.py \
  --repair-report /private/report.json --review /private/review.json \
  --output /private/reviewed-repair.json
```

The export retains contract/build identity, failed-property discrepancies and
unresolved property IDs. Approval does not make unresolved checks pass or prove
semantic independence. Only this reviewed behavioral evidence may cross the
strict boundary; original captures, source context and evaluator internals stay
outside unless separately permitted. Rebuild, rerun and compare after repair.

The hosted adapter can import this report with its hash-bound review and separately
reviewed behavioral guidance into an existing submitted coding loop. See
[persistent repair](coding-loop.md#reviewed-external-repair) for delivered-byte
binding, fixed contracts and durable budget preservation.

## Timing uncertainty

An observation may carry `time_bounds: [earliest, latest]` in the same declared
clock as `time`. Both endpoints must be finite and contain that observation’s
point timestamp. The duration evaluator subtracts endpoint bounds, retaining the
full possible reference and candidate durations. It passes only if every possible
difference lies within the fixed tolerance; fails if no possible difference fits;
otherwise returns `not_tested`. Overlapping bounds that cannot establish event
order also return `not_tested`. Equal midpoint estimates cannot hide uncertainty.
Absent bounds retain the original point-time comparison, but absence does not
prove a physical measurement exact.

For recorded visible transitions, use [video timeline inspection and reviewed
export](video-timeline.md). It preserves actual decoded presentation timestamps
and adjacent-frame brackets instead of assuming constant frame rate. This
supports comparisons of the specified visible events. Device input receipt and
physical display presentation require their own synchronized measurement path.
