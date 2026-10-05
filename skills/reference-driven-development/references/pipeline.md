# End-to-end reference reconstruction

Use this route for a substantial reconstruction or adaptation. The host agent owns the loop and performs the domain work; helpers make intake, provenance, handoffs and recovery repeatable. A helper's successful exit is evidence about that helper, not the original product. Do not substitute a static inventory for an observed journey, or a behavioral specification for the requested implementation.

## Entry and intake

Recover the intended outcome, audience, target version, full scope, comparison tolerances, permitted access and assets. Adaptation versus faithful reconstruction is independent of source-assisted versus strict clean-room access. Define normal entry, default state, a consequential action, outcome and reset. Keep targets and captures in a private workspace outside this distributable repository. The agent maintains task JSON and journal; the user supplies intent rather than administrative forms.

For APKs, use the skill's bounded static intake:

```sh
python3 /path/to/skill/scripts/apk_intake.py /private/target.apk --output /private/intake.json
```

It hashes the input and inspects bounded ZIP metadata without extracting or executing payloads. Its route suggestions are hypotheses grounded in entry names, not recovered behavior. Inspect limits, split candidates and all competing framework clues before selecting tools. Confirm package/version, manifest, signatures and runtime requirements through an appropriate inspected Android tool when needed. An unavailable tool or unrecognized package is a recorded blocker, not permission to invent results.

Before choosing an APK-to-iPhone execution route, read [native compatibility profiling](apk-iphone.md). Run `scripts/apk_native_profile.py` with its optional pinned dependency in a task-owned environment. It examines actual ELF headers and declared dependencies, checks ABI labels, and preserves separate ABI graphs. Use its JSON in the analyst's route decision; do not select a runtime from filenames alone or send binary evidence directly to a strict independent implementer. Dependency candidates require actual loader and platform-contract qualification.

For other inputs use the skill's `scripts/intake.py` with an explicit surface. It preserves local identity or an unfetched locator and proposes observation channels. A URL is not an acquired page; a file extension is not proof of format. Where metadata cannot answer the next question, use the appropriate host tool and capture its actual output. Acquisition adapters are conditional dependencies, not bundled universal control.

Append a reference record and an observed evidence record for the saved report using `rdd.py`. Give the report's evidence `local_path` relative to the journal and retain the original immutable input hash in its conditions. Keep observed metadata, inferred frameworks and unknown behavior separate when creating contributions. Include relevant input files in task fingerprints so later changes cannot silently reuse old decisions.

## Establish usable observation

Read [observation.md](observation.md) and the applicable portable observation module before runtime acquisition. The repository runtime-observation guide contains additional lessons for its legacy recorder; it is not required by the portable session adapter. Prove input identity, compatible environment, responsive control, application readiness, fresh capture and a repeat/reset path separately. Choose channels that can distinguish the unresolved property.

For an explicitly selected installed Android app, [observation-sessions.md](observation-sessions.md)
provides persisted qualification, bounded read-only effect polling, fresh captures
and uncertain-mutation reconciliation. Provisioning and binding installed bytes
to the original input remain separate required receipts.

| Surface | First useful observation | Additional channel when needed | Common false conclusion to avoid |
| --- | --- | --- | --- |
| APK / installed Android | Explicit task-owned serial, actual default screen, one input and resulting fresh capture | Manifest/resources, DEX/native analysis, lifecycle/storage/network, frame sequences | Framework clues or successful install imply visible usable behavior |
| Web | Rendered entry and one complete interaction in the intended session | DOM/accessibility, network/storage, keyboard and responsive views | DOM similarity implies durable state or server equivalence |
| Desktop / iOS | Correct platform runtime, window/accessibility or recording, input/result/reset | Bundle/resources, native instrumentation, saved files, shortcuts/lifecycle | A package or installer is the running application |
| Source / binary | Input identity and a question-led bounded structural query | Actual runtime traces, xrefs/dataflow, interface probes | A recovered function is reachable or decompiler output is original logic |
| API / CLI / protocol | Owned reproducible input, response/output/exit and side effects | Ordering, streaming, reconnect, round trips and persisted state | A recorded response implements arbitrary backend behavior |
| Document / project / database | Format-aware inventory and actual render/read | Controlled edit/export/reopen and relationship queries | One valid file defines the complete format |
| Recording / screenshot / manual | Versioned frames/text/time basis and demonstrated sequence | Seek an interactive reference or independent documentation for hidden rules | Unseen interactions can be derived exactly from pixels |
| Game / audio / creative tool | Frames/signals with input, history and measurement basis | Instrumentation, project files, dynamic/state probes | Observer-distorted timing is original timing |
| Physical / embedded | Identified device, safe measurement channel, stimulus and observed response | Ports/protocol/firmware within access scope | Software simulation establishes physical equivalence |

The Android recorder is an implemented action/capture adapter for an explicit task-owned emulator serial. Physical Android devices require another authorized observation tool; this recorder does not operate them. Other surfaces use available browser, accessibility, format, signal or instrumentation tools; record an exact missing capability when none is available. Never silently swap a different platform/version into the same evidence claim. Passive references can support partial adaptation while faithful reconstruction remains bounded by unobserved behavior. For document hierarchy and round trips, media timestamps, or physical protocol measurements, read [surface-specific methods](surface-methods.md); each has distinct evidence and capability requirements.

## Resolve questions, rather than collect indefinitely

For each consequential unknown retain competing explanations, the next discriminating observation and a stop condition. Use `workflow.py plan --task task.json` to retrieve conditional methods. Read their conditions and the relevant reverse-engineering catalog section. Use deterministic parsing/navigation and persistent bounded queries before expensive model interpretation. Fast semantic models may rank a retained shortlist; they cannot certify correctness or delete alternatives.

Examples of question-to-operation transfer: restart distinguishes volatile from durable state; alternate histories distinguish screens that look identical; asymmetric details distinguish coordinate transforms; a minimal owned fixture distinguishes runtime incompatibility from application logic. Cheap disposable code answers a named uncertainty, preserves its inputs/output and avoids becoming an unreviewed production dependency.

Choose the execution route by the fidelity question and access policy. Binary preservation, compatibility layers and independent reconstruction preserve different things; a fast working port does not establish clean-room independence. Before translating a renderer or rewriting an entire app, establish the original consequential journey and a trustworthy observation channel. A failed control experiment can invalidate the measurement channel even if another screenshot looks plausible. Switch routes when repeated work yields neither distinguishing evidence nor a better artifact.

Record actual captures, environment interventions, coverage/truncation and failed attempts before summarizing. Do not repeat an input after an uncertain mutation until read-only inspection or reset determines whether it completed. Cache only unchanged qualified observations/actions with entry guards and live outcome checks; retain acquisition and replay costs. No complete guarded-replay engine is bundled here.

## Compose and hand off

Use synthesis.md and ui-continuity.md. Preserve separate competence and character contracts: familiar navigation, chat behavior, persistence and recovery alongside the reference's hierarchy, rhythm, typography, motion or interaction details. Give each property an authority, invariant, deliberate adaptation and discriminating check. Retain minute differences and conditional specialists; resolve contradictions rather than averaging them away.

The agent records contributions, task-scoped decisions and pinned transfers in the journal. `workflow.py basis` identifies decision conditions; `fingerprint` identifies selected project inputs. `compile` produces actual implementation context. Inspect it and use it in the producing operation, rather than merely saving it. Repair a failed result through an explicit repair handoff or a revised transfer carrying the original failure and correction; a passing result must not be required before repair can begin. Do not waive stale evidence, input drift or required user decisions to obtain a packet.


In source-assisted mode the host implements the complete requested artifact from that context. Reuse code only with applicable licenses and provenance. In strict mode the analyst packet remains restricted: export independently reviewed observable specifications and permitted assets, then use clean-room.md's qualified execution path. Prefer a capable hosted model through the [source-free broker and isolated commands](frontier-worker.md) when its existing authorized subscription and qualified adapter are available; local inference is an optional route. A reviewed build image is still required. If readiness is missing, retain the full implementation scope and resolve the actual dependency. An online host with original source context cannot become the independent implementer merely by adopting a new role.

Batch answerable consequential questions using human-input.md. Inspect discoverable facts yourself. Reuse prior scoped preferences only for reversible intent choices with current fit and revisit conditions. Wait for unresolved choices that affect dependent work, access or irreversible action; continue independent work. Routine tool selection, research and administrative records should not require user handholding.

For difficult state, concurrency or exact transformation rules, use [formal-methods.md](formal-methods.md). Validate the model against observations, keep the property independent of the repair, and reproduce model counterexamples against the actual artifact. A model pass cannot substitute for the implementation comparison.

## Compare, repair and resume

Read [comparison.md](comparison.md) for the executable multi-property evaluator
and reviewed repair export. Its packets require an independent observer; declared
artifact and state identities alone are insufficient runtime evidence.
For the Android session route, produce each side's packet with
`observation_packet.py` from the actual installed APK files, full session journal,
reviewed consecutive milestone/action selection and explicit probe projections.
Review its four input bindings before export. Use the resulting bundle directly
in the comparator; retain raw journals and captures outside the implementer.
Self-comparison only checks plumbing, not candidate fidelity.

For reconstruction compare the original and candidate under equivalent entry, environment, preceding actions and reset conditions. For adaptation compare against the target journey and the adopted property contracts. Keep appearance, behavior, hidden state, signals, performance and timing separate. Meaningful checks may be rendered comparisons, a state/restart probe, a numerical oracle, a file round trip or expert inspection; do not impose exhaustive automated tests on every property.

Append each actual check with captured observed evidence, limits and `artifact_inputs` from a fingerprint of the checked artifact. `workflow.py assess` detects missing mappings, stale captures and changed artifacts; inspect the meaning of its evidence before claiming success. A check of an earlier artifact cannot certify a later revision.

On failure capture the counterexample, revise the explanation if needed and append a scoped lesson. Its correction application must identify the actual producing operation, change, check and limits, not just acknowledge the lesson. In strict mode pass counterexamples through the reviewed specification boundary, never reference-source patches. The hosted coding loop accepts a reviewed external repair report and behavioral guidance on resume, binding delivered bytes and a fixed contract while preserving its own source history and spent budget; see [persistent repair](coding-loop.md#reviewed-external-repair). Use `impact` for changed evidence and declared dependencies; refresh affected decisions and transfers instead of rewriting history. Recover from the compact task brief, current journal and exact artifacts after a context reset.

## What counts as done

For a user project, stop when the authorized scope and important properties have been implemented and reviewed through their actual artifact paths at the agreed fidelity, with unresolved limits explicit. Access failure, missing runtime, missing worker or unobservable behavior means a precise partial result, not a completed reconstruction. Do not promise equivalence for unspecified or inaccessible cases.

For development of this process itself, focused synthetic checks establish only
the tested mechanics. Completion requires integration and complete runtime
journeys through observation, independent specification, implementation,
comparison and repair, plus qualification of the advertised platform and install
routes. Keep unsupported cases explicit. Even complete demonstrated journeys
cannot establish universal speed, accuracy, fidelity or coverage of every platform.
