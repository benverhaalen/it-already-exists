# Executable planning and handoffs

Use `scripts/workflow.py` when an investigation is substantial enough to need repeatable planning, retained decisions or correction reuse. It uses the existing `scripts/rdd.py` journal. Python standard library only; commands do not install tools, call models, operate references or implement a product. The host agent performs those operations using its available capabilities.

## Normal entry and operational loop

Recover the user's goal and existing project. Classify the operation (`adapt`, `reconstruct`, `extend`, `refine`, `repair`, `explore`) and access (`source-assisted`, `strict-clean-room`). Define normal entry/default state, action, meaningful outcome and reset. Inspect current artifacts; missing documentation is not permission to redesign. See human-input.md for consequential uncertainty and ui-continuity.md for UI competence and reference character.

The agent creates and maintains a private task JSON using the fields below; the user supplies intent, not this form. The planning labels are exact retrieval handles, not semantic certification; choose them after understanding the question. Start with relevant questions and evidence, not a mandatory full checklist.

```sh
python3 /path/to/skill/scripts/workflow.py plan --task /private/task.json
python3 /path/to/skill/scripts/workflow.py seed /private/records.jsonl
```

`plan` proposes conditional methods for each unknown, separating available candidates from those lacking declared capabilities. Read each method's conditions, distinguishing delta and failure limits before choosing. The method catalog preserves related alternatives; detailed original research remains in reverse-engineering-catalog.md and ui-continuity.md. `seed` imports reference/evidence/contribution records, adopts nothing, and is idempotent for identical entries. Updated research needs new identifiers, preserving originals. These imported claims describe research mechanisms; actual target observations must be separate evidence records.

Perform chosen investigation through available host tools. Record the actual input/version, observation environment, actions, results, coverage/truncation, and uncertainty. A static recovery is not runtime behavior. Ask a different question or change channel when evidence stops distinguishing alternatives. Follow observation.md for readiness, timing, reset and observer limits.

Append evidence and contributions using `rdd.py append`. For each chosen contribution, append an adopted `decision` with exact `task_scope` and `context_sha256` from `workflow.py basis --task task.json`; its conditions/reason/revisit explain why it applies here. Add a `transfer` with the same scope, contribution links, invariant, adaptation, actual implementation artifact/operation and discriminating check plan. Pin the current adopted decision IDs in transfer `depends_on`; a later decision requires revisiting and replacing affected transfers. Use `depends_on` for explicit decision, evidence, shared-component record and lesson dependencies beyond provenance links. Several references may contribute to one transfer, but each invariant and permitted adaptation must remain identifiable. Use separate transfers where bundling conceals interference.

```sh
python3 /path/to/skill/scripts/workflow.py fingerprint --root /project --file component.py --tree relevant-assets
python3 /path/to/skill/scripts/workflow.py compile /private/records.jsonl --task /private/task.json
python3 /path/to/skill/scripts/workflow.py impact /private/records.jsonl --changed evidence-id
```

Place the fingerprint output under task `inputs`. Select exact files and bounded directories that determine this operation. Tree inventories detect new members as well as changed content; they reject symlinks requiring separate handling. Do not scan whole repositories or private unrelated directories by default. Manifest validity cannot detect undeclared dependencies, external changes or all behavioral effects. Inspect dependency coverage when extending the project.

`compile` emits a focused packet with selected provenance, current task-scoped decisions, transfers, checks, applicable corrections, fingerprints, retained alternative IDs and explicit blockers. Exit 2 means handoff is blocked; 1 means malformed/unreadable input; 0 means declared handoff completeness only. Pass the actual packet to the producing operation. Do not merely archive it. Read its checks and limits before claiming implementation or quality. An empty contribution selection needs an explicit task rationale; it does not establish reference-driven synthesis.

For a failed/blocked result, `compile ... --purpose repair` retains the failed check and emits `required_reruns`; it waives only the latest-check-failure blocker so repair can begin. It never waives stale inputs/provenance, current decision requirements, human input or strict analyst isolation. Final `assess` still requires current successful checks. A revised contract is needed when the intended behavior or decisions change, rather than simply repairing implementation under the same contract.

## Task fields

Required strings: `scope` (stable identifier for this task/conditions), `goal`, `audience`, `surface`, `operation`, `access`. `journey` has string `entry`, `default`, `action`, `outcome`, `reset`. `tags`, `capabilities`, `contributions` and `transfers` are lists of exact strings/IDs. Empty competence or character needs a named omitted reason.

`competence` and `character` are lists of objects with `property`, `authority`, `preserve`, `adapt`, `check`. Authority identifies evidence or an explicit product decision, not merely the name of a famous product. Compile a focused contract after inspecting applicability and conflicts. Facts and intentions are judgments supplied by the host; the helper cannot establish their truth.

`unknowns` contains objects with `id`, exact `property` label, at least two `alternatives`, `next_evidence` and `stop`. Supported catalog handles include `structure`, `assets`, `appearance`, `interaction`, `persistence`, `hidden-state`, `data`, `timing`, `dynamics`, `competence`, `character`, `expert-process`. Surfaces include `web`, `android`, `desktop`, `binary`, `source`, `api`, `cli`, `recording`, `physical`, `game`, `audio`, `document`; unmatched domains require another method rather than a invented match. Capabilities are explicit declarations such as `capture`, `reset` or `dex-analysis`; they do not prove tools are ready.

`input_requests` is optional. Each has `id`, `decision`, `why_user`, `consequence`, boolean `wait`, `dependent_work`, optional `independent_work`. A recorded answer needs nonempty `response` and `response_source: "user"`. Required unresolved requests block handoff, and both plan and compile identify independent work. Agents must not fabricate these declarations or infer consent from silence.

## Changes and corrections

`impact` structurally reads historical records even if local evidence changed, detects missing/changed captured files, and follows declared links/depends_on. It does not rewrite history. A `change` record has `reason`, `scope`, `revisit`, and `links` to invalidated records. Use it for changed source/version or factual dependencies. Linked historic chains remain stale; reobserve into new reference/evidence/contribution records before readopting. Scope is explanatory here: linking shared evidence invalidates all its dependents. A local preference correction belongs in a scoped lesson, not a fabricated global evidence change.

By default `rdd.py append` refuses a journal whose evidence files drifted. Explicit recovery uses `append ... --allow-drift`: old bytes/hashes remain, new evidence is still hashed, and compilation continues blocking affected historic chains. Preserve immutable captures when possible. Structural corruption cannot be bypassed by this option.

A `lesson` still links its triggering check. Add `applies_to` with one or more selector axes: `scopes`, `surfaces`, `operations`, `tags`. Every specified axis must overlap the task; tag alternatives within one axis are OR, not a claimed semantic conjunction. Use an exact task scope for unsettled/local lessons. Free-text `scope` explains boundaries and exceptions; selectors only route them. `targets` identifies affected existing records. Selection does not establish that a lesson is validated.

The compiler injects matching lessons and flags whether selected transfers list them in `depends_on`. Unscoped legacy lessons are surfaced for review, never silently generalized. Acknowledgment proves receipt only: implementation and demonstrated improvement stay unestablished until actual checks support them. Append revised transfer/check records rather than edit original history. Preserve alternative and reversal conditions.

## Clean-room handoffs

A compiled analyst packet includes source provenance and is always blocked from strict implementer handoff. Prepare an independently reviewed behavioral specification instead. `review-export spec.json` allowlists `scope`, `goal`, `audience`, `journey`, `behaviors`, `unknowns`, `acceptance`, `review`. Behavior/acceptance lists are nonempty strings; unknowns may be empty. `review` requires reviewer identity, true assertions for `implementation_independent`, `source_free`, `asset_rights`, and explicit `limits`. It rejects common link/code markers, but semantic leakage can evade those checks.

This command is a specification/review aid; the separate cleanroom.py provides the narrow offline Docker boundary described in clean-room.md. The output explicitly reports `isolation_verified: false`. Use clean-room.md to enforce and inspect a real implementer boundary before claiming strict isolation. Do not pass the full analyst packet, original sources, source-bearing history or provenance links to that implementer.

## Stopping and assurance

Stop a particular investigation when its decision is supported enough for the requested fidelity, its bounded probe expires, or the next required evidence/access is unavailable. Preserve unknowns and smallest unlocking evidence. Do not retry unchanged tools or keep gathering convergent references.

Stop implementation only when requested properties are traced through actual decisions/operations/artifacts and appropriate checks, or report the precise remaining gap. Structural synthetic checks and critical source-informed reasoning establish tested mechanics; they do not establish reconstruction accuracy, taste, speed gains or whole-product quality. Package completion also needs integrated runtime journeys and qualification of advertised execution and installation routes; see pipeline.md.

## Optional question routing

Input requests can declare `prerequisites`; task `settled_prerequisites` records independently resolved factual dependencies. Only answerable questions enter the current batch. Responses remain user-provenanced. Reversible intent/preference reuse can declare `intent_inference` with `interpretation`, `past_response`, `source`, `original_scope`, `current_fit`, `changed_conditions`, `revisit`; it requires request `category` intent/preference and `reversible: true`. This never grants authorization. `conflicts` records id/issue/reason/sources/resolved and a resolution when settled; unresolved conflicts block synthesis.

## Property coverage assessment

Each competence/character property may specify `transfers`, a list of selected transfer IDs. After implementation, run `workflow.py assess records.jsonl --task task.json`. Assessment requires every named property to map to selected current transfers whose latest check passed and links captured observed evidence. Every relied-on check also needs `artifact_inputs`, the fingerprint output for the actual checked files/trees. A missing or changed artifact snapshot cannot certify the current result. It reports missing mappings, failed/missing checks and stale evidence. Exit 2 means review coverage is incomplete. It does not establish that the check discriminates the property, that the evidence is meaningful, or that the complete journey works; inspect those before claiming completion. Omitted property axes require their explicit rationale and do not prove quality.

Transfer IDs within property mappings are execution references and excluded from decision-basis hashing. The underlying property, authority, adaptation and check remain included. Preserve evidence captures immutably and append new records for revisions.

`assess` separates `ready_for_property_review` from `access_review`; combined `ready_for_review` requires both. Strict analyst packets always remain barred from implementer handoff. For final strict assessment, task `clean_room` names `specification_evidence` and `receipt_evidence` IDs for fresh observed captures in this journal, plus `output_directory` for the current output. It also declares `image_review` and `worker_review`, each with `reviewed: true`, reviewer, substantive declaration and limits; image review includes the exact receipt `image` SHA256 identity. Assessment validates the reviewed behavioral export, current scope/goal/journey, receipt specification hash, boundary/worker result and exact current output inventory. Prefer absolute output paths; legacy relative paths resolve against the journal directory. The adapter and assessment bound output to 2,000 entries, 1,000 files, 50 MiB per file and 200 MiB total. These are reviewed mechanical records, not authenticated execution attestation or automatic proof of semantic independence.

## Actionable corrections and factual prerequisites

For each selected transfer affected by a lesson's targets, declare `correction_applications` keyed by lesson ID. Each application needs nonempty `operation`, `change`, `check`, `limits`; pin the lesson in `depends_on`. Compilation rejects receipt without this operation-level plan. With no lesson targets, all selected transfers need an explicit application; qualify scope before sharing broad lessons. Assessment separately requires a passed current check linking the application transfer, lesson and captured observed evidence. That still requires inspection of whether the result demonstrates the intended effect.

Pending factual prerequisites use task `prerequisite_facts` objects with `id`, `evidence` (including the current uncertainty), `next_action`. Unknown prerequisite IDs and cycles are malformed inputs. Mark only inspected facts as settled; a typed declaration cannot establish truth. Goal, audience, journey, property contracts, tags, inputs, conflicts, constraints, fidelity, capabilities, unknowns, permitted assets, access policy, acceptance and budget participate in decision-basis hashing. Update the task with consequential intent changes before deciding again.

Use `rdd.py query ... --neglected --task-scope scope` for scoped candidate retrieval. Without scope, it is a global lexical archive view, not the operational current decision state. Use compilation for that state. Input manifests conservatively block the whole selected handoff on drift; they do not infer an exact component dependency graph. Record shared factual changes and their links when other tasks also depend on them.

## Research and UI operations in compiled context

`investigate` and `compile-context` include `approach_review`, preserving the
complete goal, journey and access policy. It asks for existing mechanisms,
bottlenecks, work-removing alternatives and discriminating tests before a
consequential commitment. Repair context asks for diagnosis and reconsideration.
It neither performs research nor certifies a selected approach.

UI surfaces or explicit UI/visual/design tags also receive `ui_review`: actual
reference image inputs, image-led exploration, font/density anchors, fresh-context
critique and comparison of the rendered complete journey. Non-UI tasks do not
receive those defaults. The agent reads the module and verifies the real
producing calls; a packet field alone is not evidence of execution.


## Optional resumable research frontier

For seeded adaptive discovery, task `research_frontier` is a list of leads with
nonempty `id`, `seed` (existing evidence ID or source locator), `quality_cue`, `why`,
`next_action`, `bound`, `counterlead` and `status` (`pending`, `inspected`, `deferred`
or `blocked`). The agent creates these from inspected context; the user need not
fill a form. Use existing journal records for captures and findings, and project
notes for detailed iteration results. Both planning and compiled builder context
carry the frontier, bounded individual-inspection guidance and scheduling limits.
An empty frontier is valid for settled or small work.

Queue changes alone do not invalidate adopted implementation decisions. If an
inspection changes their factual conditions, update the affected unknowns, inputs
or other decision-basis fields and append changed evidence/decisions as usual.
Frontier validity establishes declared resumable context, not source quality,
completed inspection, scheduler execution or research improvement.
