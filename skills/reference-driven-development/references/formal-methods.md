# Selective formal methods and counterexample repair

Load when a consequential property depends on history, concurrent actions, cancellation, retries, recovery or exact transformations. Keep this conditional: an ordinary layout edit does not need a formal model. These are researched transfers, not installed checker integrations or demonstrated reconstruction improvements.

## What the motivating example establishes

[Boris Cherny's September 22 post](https://x.com/bcherny/status/2102543349102338309) reports using Lean and TLA+ to find SDK defects. His [September 23 clarification](https://x.com/bcherny/status/2102898067133595992) describes modeling difficult subsystems, finding counterexamples, reproducing suspected bugs in code and repairing them. Treat the reported 16 PRs as an author's report, not an independently audited benchmark or whole-codebase proof. The linked reports are discovery evidence; the video and PRs were not independently audited.

## Choose the mechanism by the unresolved question

| Reference | Useful difference | Transfer and limit |
| --- | --- | --- |
| [TLA+ / TLC](https://github.com/tlaplus/tlaplus) | Model state transitions, ordering, safety and liveness separately from production code. | Search difficult interleavings before implementation; finite configurations and environmental assumptions constrain results. A passing run is about the specified model. |
| [P / PeasyAI](https://github.com/p-org/P/tree/260da928f67569ca7a8c0039a02d0bad7cde6096/Src/PeasyAI) | AI generation coupled to compiler/checker feedback and trace-driven repair. Inspected generation.py uses conditional ensemble escalation and heuristic ranking with optional compile checks; p_steps.py preserves checker failure for downstream repair. | Bound retries by information gained. Keep failed checks available to repair without declaring assurance success. Ranking or successful compilation cannot establish that properties are correct. MIT; August 3 pin. |
| [PObserve parser](https://github.com/p-org/P/blob/260da928f67569ca7a8c0039a02d0bad7cde6096/Docs/docs/advanced/pobserve/logparser.md) | Explicit mapping from actual logs to events and monitor partitions. | Maintain an observable-event bridge; audit missing events, identity, order and partitions. A monitor cannot detect behavior omitted by its parser. LockServer test source inspected; no runtime qualification performed. |
| [Coyote replay sample](https://github.com/microsoft/coyote/blob/d8f5c0fb15da70780649abcb3343053bc87cb097/Samples/WebApps/ImageGalleryAspNet/TraceReplayer/Program.cs) | Controls supported concurrent C# execution and replays saved schedules against actual tests. | Prefer reproducible implementation traces where instrumentation fits. Uncontrolled external effects remain outside the schedule. MIT; August 24 pin. |
| [Stateright register example](https://github.com/stateright/stateright/blob/ab8c8be9341505e0f71edbe5dd88ed275bd976a4/examples/single-copy-register.rs) | Actor transition code participates in both checking and runtime; network semantics remain explicit. | Reduce duplicated-model drift where the implementation style fits. Runtime I/O and model bounds still need qualification. MIT; July 2025 pin: older work remains useful. |
| [Lean proof validation](https://github.com/leanprover/reference-manual/blob/4f677697f1f86b7ea817746eba00d339e9f59d68/Manual/ValidatingProofs.lean) | Separates theorem meaning, transitive axioms and proof replay; comparator matches a proof to a separately trusted statement. | Review the intended property before generating proofs; inspect transitive axiom dependencies rather than searching only for literal sorry. Scale independent replay to consequence. Apache-2.0; September 28 pin. |

TLA+ repository availability was checked October 4; do not present its October 2 head as September technology. Qualify and pin a suitable version before use. The other dated pins above were inspected as source references. No upstream code was copied, installed or run.

## Apply the loop to an actual artifact

1. Select a narrow mechanism whose failure matters. Derive candidate properties from the user's goal, reference observations and independently inspected contracts, not just the implementation's current assertions. Separate faithful reference behavior from deliberate product improvements.
2. Capture state variables, actions, forbidden outcomes, progress requirements, reset conditions and environment assumptions. Map each observable event to a capture or implementation boundary. Include timeout, duplication, restart and reordered completion only where plausible.
3. Validate the model against observed traces and at least one distinguishing alternative explanation. Keep unresolved assumptions as unknowns. Review properties independently of the candidate proof/repair so a generated model cannot silently weaken its own goal.
4. Use the smallest appropriate model, controlled scheduler or proof. Record exact tool/version, model/property hashes, configuration, fairness assumptions, explored bounds, resource limit and termination status. Timeout or bounded sampling means incomplete exploration, not success. For proofs inspect statement meaning and permitted axioms; choose stronger replay when warranted.
5. Preserve a counterexample as suspected until reproduced against the actual implementation. If it fails to reproduce, investigate abstraction, event mapping, scheduler and environment; do not automatically dismiss it or patch code to match a wrong model. Shrink the discriminating sequence where useful.
6. Repair through the producing operation while retaining the original property. Recheck the model and the implementation reproduction; revalidate affected ordinary journeys. Review any proposed property weakening as a separate decision.

Use the existing journal: evidence captures retain models, traces and tool output with honest basis and limits; contributions retain mechanism differences; decisions select scoped contracts; checks fingerprint the actual artifact. Send failures through workflow.py compile --purpose repair and record required reruns. The assessor's structural success does not promote a model check to implementation equivalence. In strict clean-room mode the analyst may derive a behavioral model, but only reviewed observable contracts and sanitized counterexamples cross to implementers; source-derived transitions or translated code remain restricted.

## Apply RDD to RDD itself

Promising future bounded targets are stale-evidence handoffs, worker cancellation/export, repair eligibility and access-boundary lifecycle. State properties before inspecting favored fixes: changed inputs cannot retain assurance; failed checks can enable repair without becoming success; cancelled work cannot later publish a valid success receipt. Current helper checks are focused synthetic mechanics, not formal proofs. Do not add a checker campaign or real reconstruction trial under the current stopping rule.

Visual judgment remains an actual rendered/user journey comparison. Formal methods can constrain chat cancellation, streaming order and persistence; they cannot establish that a UI has the reference's character or feels good.
