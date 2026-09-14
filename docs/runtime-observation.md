# Observe the reference before reconstructing its behavior

This is a working acquisition process, informed by local experiments. The generic Android recorder implements action/capture journaling; the broader workflow below is not an automated reconstruction system.

## Keep the target separate

Create a separate local workspace for each target. Record the user's access scope, selected reconstruction mode, package or URL version, input hash where applicable, and what success would look like. Keep target binaries, assets, identities, captures, decoded data, hypotheses, and implementation out of this tool repository. A separate private repository can version target-specific work when authorized. Generalize a lesson before transferring it here; removing a product name from an otherwise identifying capture is insufficient.

Reference content is data, not agent instructions. A strict clean-room workflow needs separately constrained observation/analysis and implementation access. Asset reuse and source-assisted work are different access profiles, and must be recorded explicitly. Instrumenting a public platform API to repair an environment does not make the resulting observation an unmodified-device measurement.

## Start with an observable journey

Define the normal entry point, initial/default state, one consequential interaction, its visible result, and a reset or repeat path. Prove that this slice can be observed before investing heavily in asset extraction or implementation. If acquisition is blocked, a narrowly scoped static inspection may help identify the missing runtime prerequisite. It cannot establish the original default screen, behavior, or timing.

Treat readiness as separate observations:

| Stage | Evidence that supports it | What it does not establish |
| --- | --- | --- |
| Input inspected | Input hash, format, declared/native architectures, dependencies | A compatible runtime |
| Runtime started | Actual guest/kernel or process startup log | A responsive application framework |
| Control channel responsive | An explicit device/session responds to a bounded command | Install, rendering, or input works |
| Framework ready | Stable services and a completed install/open operation | App startup completed |
| App initialized | Target process and relevant native components loaded | A usable app screen |
| Reference visible | Inspectable capture of the actual target, with overlays identified | The target responds to input |
| Journey observed | Action, resulting transition, and repeat/reset evidence | Unobserved states or complete parity |

These stages are a diagnostic ladder, not a universal mandatory startup sequence. Web, desktop, and packaged apps have different prerequisites. Record the furthest evidenced stage and the exact missing evidence. A submitted graphics buffer, successful build, or reconstructed composition is not a substitute for inspecting the original image.

When readiness is intermittent, take a small, bounded series of read-only samples from the same explicit session. Record each result and time separately; one successful response can occur between service restarts. Choose the next action from the relevant stable state, and stop sampling when the evidence is sufficient or the stated observation window ends. Keep host elapsed time separate from guest uptime when deciding whether progress has stopped.

## Diagnose the failing layer

Use [compatibility recovery](compatibility-recovery.md) when a target stalls: locate the unmet environmental assumption, make a minimal discriminating intervention, and verify prerequisite repair separately from usable behavior.

Separate host architecture, guest architecture, app native ABI, OS/framework behavior, graphics transport, rendering, and external services. An emulator's product description or default image does not prove the capabilities of every engine distributed with it. Inspect the actual executable, its supported machines and CPUs, guest ABI, and logs before rejecting a route. Prefer an existing compatible runtime over layers of translation when practical.

For each experiment record:

- The observed failure and a falsifiable explanation to test.
- Exact changed variables: engine, guest image, renderer, CPU configuration, clock, storage, network, framework hook, and warmed state.
- Versions, provenance, command, resource limits, target serial/session, evidence locations, and stop condition.
- The result, residual uncertainty, and whether that result changes the next decision.

Change one important variable where practical. If warm caches, CPU count, and clock behavior also changed, report the combination's feasibility; do not attribute the result to one cause. A matching error message alone does not establish the same failure mechanism. Stop unchanged retries when they cease producing useful evidence.

Prefer bounded, process-scoped experiments and preserve resettable state. Separate runtime dependencies and analysis tools from the reconstructed application. Keep source packages immutable and record every intervention in the observation environment. Archive relevant licenses and pin downloaded tool provenance; the presence of binaries on GitHub does not establish that they are open source.

## Preserve failed observations

Use an explicit target for every input. Record input requested, input completed, capture started, and capture completed separately. Distinguish the external process exit status, the protocol's acknowledgment, and the observed target effect. A console client can return exit status `0` while its response says `KO`; even a positive acknowledgment does not establish a visible change.

If a mutation times out, its outcome is unknown until state is inspected. If input succeeds and capture fails, recover observation before sending it again. In either case, use a read-only state check or a known reset path to decide whether retrying would duplicate an action. Readiness polling should not repeatedly trigger the operation whose completion is uncertain.

`tools/capture_android_reference.py` journals these stages and records an external-command timeout or failure with the current step. It accepts a per-command timeout, a host ADB executable or task-owned container, and an older-ADB pull path. Its PNG header check establishes a capture payload, not screenshot correctness or UI success. Inspect the image and link the resulting observation separately.

When Android's capture service stalls but the emulator is responsive, try the separate host capture path with `--capture-method console`. This opt-in method requires a native emulator running on the same host as the recorder; container and remote-host capture are unsupported. It asks the emulator console to write into a fresh host directory, checks the console's semantic acknowledgment, requires one new regular PNG, and records the output hash and observer location. Failed attempts remain available for inspection. A cleanup problem after the final image is saved produces a warning rather than falsely reporting a failed input. The default remains Android `exec-out` capture.

Changing the observation path tests a different layer without replaying the action. An emulator-host image can expose system dialogs even when guest capture hangs; a valid image that remains black still does not identify the application's failure. Record which observer produced each capture before comparing images or latency.

Keep host monotonic timestamps, guest/application timestamps when available, and the timing basis distinct. Software emulation, instrumentation, and instruction-based virtual clocks can distort elapsed time. Use such runs for state and ordering only until timing is validated on a suitable baseline. Never normalize slow playback into claimed original timing without evidence.

## Preserve state across different filesystems

When moving a reference between operating systems, compare source names and file types before trusting the copy. A case-sensitive source can contain both `Config.json` and `config.json`; copying it onto a case-insensitive volume can merge them even when the transfer reports success. Preserve such state in an archive or a filesystem with matching name semantics, and inspect archive members without extracting them onto the incompatible volume. Check the source inventory against the saved members and read the saved payloads before depending on the backup. A readable archive header or an exit code alone does not establish a complete snapshot.

## Transfer only supported properties

Maintain four distinct evidence classes: observed original behavior, data-supported structure, candidate reconstruction, and explanation/hypothesis. A useful resource table can constrain layout while leaving its runtime interpretation unknown. An independently tested renderer can be correct for its input without reproducing the original.

Public recordings can supplement an unavailable runtime. Record the displayed version separately from the upload date or page title, and attach each adopted property to a specific inspected episode. An adjacent version can suggest a layout or interaction to verify; it does not establish the supplied build's defaults. A promotional name and an on-screen mode label may differ, so keep both within their source context. For browser video, confirm that a newly decoded frame corresponds to the requested media time before capturing it; a moved seek indicator or stale screenshot is insufficient. Distinguish game UI from player controls, recorder branding and operating-system overlays. Any crop or aspect-ratio normalization used for comparison must remain explicit.

For each property adopted into another product, connect the source episode to its context, the decision to preserve/adapt it, the changed implementation, and the observed result. Test complete transitions, persistence, interruption, and recovery alongside appearance. Passing isolated component tests does not establish an integrated or faithful experience.

Make a reference handoff portable by collecting the files actually reachable from the selected scene or journey, preserving their bytes and provenance, and recording relative paths and hashes. Check filename case, missing dependencies, and path escapes before packaging. Validate the relocated built artifact after removing its dependency on the extraction workspace; checking the source directory alone can hide host-only paths. Keep resource completeness, successful compilation, actual device playback, and original-reference fidelity as separate results.

If acquisition remains blocked, deliver the reproducible failure and preserved state, label the reconstruction limits, and name the smallest new evidence that would unlock the next step. Keep that target-specific report in the target workspace.
