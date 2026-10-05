# Diagnose and repair recurring failures

Use this module after a material defect, disappointing observed use, repeated repair, or before a consequential compatibility/reconstruction delivery. The agent owns triage and verification; ask the user only for information or actions unavailable through authorized evidence. Scale the investigation to consequence and uncertainty rather than running every check on every task.

## Classify the broken assumption

A symptom can belong to several families. Keep alternatives until a discriminating observation separates them. The following are search handles, not diagnoses or an exhaustive taxonomy.

| Family | Broken assumption | Evidence and next check |
| --- | --- | --- |
| Behavior/contract coverage | A reachable choice, callback or platform operation is supported | Inventory actual entry points and signatures; distinguish declared, reached, implemented and demonstrated. Exercise completion, cancellation, defaults and error branches. Count unsupported behavior even when it does not crash. |
| Resource lifetime/capacity | Temporary work is released, ownership survives handoff and capacity remains available | Measure live resources and high-water marks across repeated complete journeys, resets and background/foreground. Inspect growth after warmup, double release, stale handles and failure under bounded capacity. Pooling or collection needs an ownership oracle, not just lower memory. |
| Lifecycle/representation | State, units, encoding, context and ordering are preserved at a boundary | Test resize, suspend/resume, reconnect, cancellation and resource creation/destruction. Preserve raw values and effective configuration. An observer/capture failure is distinct from an artifact failure. |
| Dependency necessity | A service or external prerequisite is essential to the user's local result | Trace which action requests it and how failure affects outcome/persistence. Separate optional telemetry, reviews and cloud backup from required behavior. Adapt the proven optional/decline path; never invent success, rewards or a successful save. |
| Timing/work amplification | Work occurs at the intended cadence without needless copies, retries or recomputation | Attribute time and cost to stages, include tail latency and cold/warm behavior. Distinguish processing time, presentation cadence and semantic time. A faster rewrite must retain an independent outcome/timing oracle. |
| Durable state/completion | Useful output survives completion, reopening and interruption | Follow entry → work → finish → return → reopen. Verify persisted output and error recovery, including partial writes and retry ambiguity. A displayed success message is not durable success. |

For software these boundaries include API/JNI/ABI, callbacks, storage and graphics. For documents they include fonts/media, conversion and save/reopen; for agent workflows, tool coverage, context lifetime, handoffs, approvals and interrupted runs. Transfer the broken assumption and test, rather than imposing software vocabulary on another domain.

## Make the family inspectable

Bind each counterexample to the artifact/build, effective environment, prior state, triggering action, failing boundary and observed outcome. Add only relevant measurements: resource counts, last calls, state transitions, timings or persistence receipts. Keep rotated/raw evidence and distinguish candidate stack addresses from a verified call stack. Capture the first causal failure when available; the last log line alone is not its cause. Correlate user feedback with the right run before attributing it.

Once a cause is supported, search for sibling operations sharing its contract, allocator, dependency or state transition. Prioritize reachable consequential siblings; retain untested ones as unknown. Inspect available implementations and documentation for the missing mechanism when necessary. A patch to one caller is not evidence that the family is fixed.

Change the actual producing path. Reproduce the counterexample, preserve nearby working behavior, and verify through completion/persistence as appropriate. Diagnostic failures should be reported separately from the operation under test; recovery must not silently hide true output failures. Freeze the executed revision and effective options. If a test restarts an artifact and drops experimental options, its results qualify the actual options only.

## Feed improvement back without exporting private artifacts

Keep hot-path diagnostics bounded: counters or sampled summaries for repeated
events, detailed first failures and relevant state changes. Measure observer
overhead before attributing a slowdown to the target. Preserve raw error values
without assigning an unverified meaning. For storage adapters, exercise short
writes, interrupted operations, partial failure and zero progress; retain the
completed count and failure rather than reporting synthetic success. A completed
write or flush is not proof of crash-safe durability or a successful full save.

Write a scoped lesson in the existing journal: observed failure, supported mechanism or unresolved hypothesis, adopted change, sibling coverage, producing operation, discriminating check, limits and revisit condition. Attach it to the repair transfer so the compiled implementation context carries the correction. Retain project-specific evidence privately; portable guidance receives only abstract mechanisms and authored examples. Validate a broader claim on fresh cases before calling it general effectiveness.

## Reuse runtime contracts and keep application changes separate

For binary ports, inventory architecture, bytecode, frameworks, graphics, audio,
storage, lifecycle and external services. Select execution, translation or
reconstruction per subsystem. Reuse a qualified runtime contract before writing
an application-specific adapter. Record missing signatures and regression cases.
Research unfamiliar mechanisms; reuse the evidence for already qualified ones.
Qualification applies to the tested platform, configuration and access policy.

## Make modifications reviewable and reversible

Keep an immutable original and a separate, versioned modification specification.
Record the intended change, affected layer, input hashes, patch, preserved behavior
and rollback route. Asset changes, bytecode edits, native patches and host adapters
need different tools and checks. Select the least invasive layer that produces the
intended result.

Keep compatibility repairs separate from intentional behavior changes. Preserve
the original behavior oracle for the former. Define the intended differences for
the latter. Test nearby behavior, completion, save and reopen after each change.
A host adaptation does not establish that a modified APK was produced or tested.

## Maintain the shared process

After a useful finding, update the operation or guidance that controls the next
attempt. Keep project names, private artifacts and target-specific examples out
of these updates. Describe the mechanism, its conditions, its test and its limits.
Review each coherent change, run the relevant checks, commit it and push it to the
shared repository. Do not include unrelated pending work in that commit.
