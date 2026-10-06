# Observation and reverse engineering

Choose evidence channels for the property being inferred, not merely for convenient access.

| Reference | Useful evidence | Limit |
| --- | --- | --- |
| Website or native app | Rendered states, DOM/accessibility, actions, network, persistence | One path misses history, permissions, and failures |
| Source or binary | Resources, dependencies, static paths, runtime traces | Code existence does not establish reachable behavior |
| API, CLI, file format | Inputs/outputs, errors, ordering, streaming, round trips | Finite cases do not establish full equivalence |
| Screenshots, video, manual | Layout, visible sequence, stated rules | Passive evidence cannot answer every interactive question |
| Audio, game, physical interface | Signals, frames, timing, device observation | Observer and hardware can alter measurements |

Record version, environment, role, preceding actions, locale, viewport/device, and relevant state. Link actual captures or reproducible observations. Preserve missing evidence and hypotheses instead of inventing internals.

For Android archive acquisition from a product name, use [APK acquisition](apk-acquisition.md) to resolve identity and an explicit build before bounded intake.

First establish acquisition readiness: access, reset/replay, observation reliability, and known perturbations. Completed input and completed capture are different events. A stale image, failed capture, or unchanged observer cannot prove an unchanged product. Verify freshness and inspect actual output. Do not execute untrusted code merely because it is a reference.

Use discriminating probes: history changes, delayed response, failure, retry, duplicate input, role changes, restart, and state restoration. For example, a draft visible after navigation might be volatile memory; restart or storage inspection separates it from durable recovery. Probe what distinguishes candidate explanations, rather than collecting many similar screenshots.

Narrow static and runtime investigation around unresolved behavior. Combine them when each resolves the other's blind spots. Record truncation, inaccessible paths, timing distortion, and compatibility substitutions. Cached observations need validity conditions; environment changes can invalidate them.

For adaptation, preserve the useful mechanism under the target brief. For reconstruction, define the comparison surface, permitted tolerances, reference version, and unobserved cases explicitly. Appearance, behavior, state, performance, and timing can disagree; measure them separately. Never infer perfect fidelity from build success or a few matched screens.

The bundled scripts/apk_intake.py supports bounded static APK metadata; [observation sessions](observation-sessions.md) supports explicitly selected task-owned installed Android apps. Provisioning, installation and specialized recovery need separately qualified domain tools. In it-already-exists, the legacy Android recorder and runtime-observation documents offer additional optional acquisition support. The skill alone neither controls all reference surfaces nor recovers inaccessible behavior.

For concrete tool candidates, search the [conditional reverse-engineering catalog](reverse-engineering-catalog.md) by unresolved mechanism. Load only the relevant section; preserve its limitations and historical cutoff.

When observation requires a compatibility repair, qualify creation, dispatch,
state and teardown as one execution contract. Restoring hook bytes cannot undo
a changed graphics context. Keep the adapter present until the observed process
has ended unless restoration of ongoing execution is independently qualified.
When replacing unavailable services, preserve the caller's completion/error
semantics; first investigate whether normal error dismissal already supplies a
usable route. Compare an intervention with an unmodified control before calling
it necessary. Use [graphics qualification](graphics-qualification.md) to separate backend behavior from dispatch, lifecycle and presentation.

For repeatable binary ports, distinguish the reusable runtime contract from the
application-specific adapter. Inventory executable architecture, bytecode,
framework calls, graphics/audio, storage, lifecycle and external services before
choosing execution, translation or reconstruction per subsystem. Reuse qualified
implementations first; retain missing contracts with exact signatures and
reproducible cases. A fix becomes reusable only with its operating conditions and
regression evidence, not because one application launches. Research unresolved
mechanisms rather than repeating discovery for already qualified components.

If modifications are requested, retain an immutable reference and a separately
versioned mod specification: intended behavior change, affected layer, baseline
hash, patch/adaptation, preserved invariants and rollback. Resource replacement,
bytecode changes, native patches and host adapters have different failure modes;
choose the least invasive layer that actually produces the desired behavior.
Keep compatibility repairs separate from intentional changes in the comparison
oracle. Check both the requested change and neighboring behavior, including save
compatibility and reopen. An iPhone host adaptation is not itself a modified
Android APK; qualify each requested output on its actual platform. Strict
clean-room boundaries still apply when selected; source-assisted mod work does
not establish an independent implementation.
