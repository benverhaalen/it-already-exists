# Recover an observable runtime by testing its assumptions

When a reference will not run, treat the failure as a question about a particular layer. A black screen is an outcome; it is not a diagnosis. The purpose of recovery is to obtain trustworthy behavior to study, with every environmental change attached to that evidence.

## Find the unmet assumption

Map the path from launch to the missing result. Determine whether the process starts, required libraries load, initialization advances, a surface exists, a frame is submitted, and the visible target responds. Use the least invasive evidence available: bounded commands, service state, logs, timestamps, captures, and operational thread snapshots within the selected access profile.

At the stalled step, state the assumption in plain language. Examples:

- An old SDK expects a device-metadata call to return a nonempty value.
- A startup flow assumes a retired endpoint will respond before it can show its UI.
- A rendering client assumes its graphics-service request will complete.
- An emulator launcher assumes the default guest architecture is suitable for the supplied native library.

Distinguish those explanations from facts. A repeated sleeping stack can locate a wait without proving why it persists. A black capture might contain no app frame, a frame hidden by a system dialog, or a capture failure. These possibilities require different tests.

Check whether a suspected failure signal also occurs during normal operation. A rendering thread can legitimately sleep between requested frames. Compare successive presentation timestamps, current surface/context validity, the visible view hierarchy, and actual captured pixels before changing the renderer. Advancing timestamps establish presentation activity, not meaningful image content; a large view does not establish occlusion without its visibility, background, alpha, and contents. Retire an explanation when the new evidence contradicts it, and update the next experiment accordingly.

When a launcher wraps another engine, compare the requested setting, the wrapper's effective configuration, and the final engine arguments. An override passed directly to the engine can leave the wrapper's resource bookkeeping unchanged. Reconcile the values at the layer that owns them, then inspect the generated configuration before interpreting the next run.

For a crash, match the process and timestamp to its faulting thread and call stack. Compare nearby warnings with a run that progressed further: a warning shared by both runs may be incidental. Test the explanation supported by the failing call, rather than treating the last printed line as its cause.

## Build the smallest discriminating experiment

Write down four things before changing the environment:

1. **Evidence:** what was actually observed, and where it is recorded.
2. **Hypothesis:** the missing assumption that could explain it.
3. **Intervention:** the smallest permitted change that tests that assumption.
4. **Prediction:** the specific execution or visible change expected if the hypothesis is useful.

For a missing metadata value, a narrow adapter at a public framework boundary can supply a documented placeholder and log whether the target actually requests it. For a retired service, an authorized offline fixture could supply an independently specified response. For a graphics wait, test another renderer while preserving the guest and input. These are candidate mechanisms; each needs its own observed result.

Prefer a supported setting or compatible guest image when it supplies the prerequisite. Instrumentation is useful when it creates a more discriminating experiment. Do not substitute for application decisions such as reward outcomes or navigation merely to make a screenshot appear. That would change the behavior being measured.

Test the measuring instrument and the target separately. If a state query returns impossible values, first establish that the query works in that environment; it is not reliable evidence that the target set impossible state. A tiny independently authored control can test the disputed capability with known inputs and predicted outputs. For graphics, an isolated, unshared offscreen context can test clear, drawing and texturing without reading or modifying the target's resources. Require actual output checks and acknowledged cleanup. A passing simple control narrows the diagnosis; it does not validate the target's full rendering history or window surface.

Match the control to the disputed operation. Successfully setting a value or drawing an image does not establish that querying the state back works: setters, rendering and queries can follow different compatibility paths. Set independently chosen values, query them into owned sentinel buffers, compare with predicted results, and inspect errors only in the control's owned context. Include a nearby operation expected to work so a local defect can be distinguished from a broken test setup.

Trace the phase where a dependency is consumed. A steady rendering loop can repeatedly use values calculated during initialization without querying them again. If a short steady-state trace cannot explain the failure, preserve the current state and observe one prepared startup before the suspected initialization calls. Record the actual covered interval. Reaching an event cap before the desired boundary is a partial observation, not a failed launch and not authorization to launch again. Keep repeated-call counts separately from representative argument samples when repetition would exhaust the useful trace budget.

Keep the source package unchanged, preserve initial state, and record interventions separately. The selected clean-room access profile still applies: a runtime problem does not authorize implementation agents to inspect original application code. If deeper analysis is necessary, keep its access and exports separately constrained.

If an intervention changes networking or device access, identify how commands, captures, and rollback reach the target first. Preserve that observer/control channel while changing the application-facing capability. Afterward, read the actual interface, route, or service state relevant to the hypothesis; a saved setting or accepted console command does not prove the intended network effect. If observation disappears, record the result as unknown until the channel is recovered.

## Verify the repair at two levels

First verify the local mechanism: the adapter was installed, the real target called it, and the observed wait or downstream state changed. Then verify the actual goal: the original target becomes visible, accepts input, and completes the selected journey.

For an adapter, test both the corrected case and the untouched fallback with owned inputs before applying it to the target. Unknown state must remain unknown: invalidate inferred state after unsupported operations instead of fabricating an answer. Bind an intervention to its declared process, context and interval, stop substitutions at the chosen boundary, and separately acknowledge removal of hooks. A successful isolated correction is still not proof that it repairs the target's visible failure.

Report these independently. Removing one startup dependency can reveal the next missing dependency. A later wait or newly submitted buffer is evidence of progress, not proof that the application now works. Keep failed and partial results; they prevent another agent from repeating the same uninformative attempt.

Do not automatically turn a successful compatibility intervention into a fidelity baseline. A synthetic identifier can alter identity-dependent behavior. Disabled networking can alter default content. Virtual-clock changes invalidate ordinary wall-clock timing comparisons. Mark the affected properties and obtain a suitable baseline before making claims about them.

## Recheck the constraint when the standard route fails

Separate the user's requirement from the chosen method. “Run this binary” does not necessarily require a standard emulator UI, hardware virtualization, a particular guest image, or a particular host-process architecture.

Build a small compatibility map: host instruction set, translator or emulator engine, guest board and OS, app native ABI, graphics backend, and external prerequisites. Identify which link actually lacks support. A negative result for one combination does not rule out all combinations.

Inspect actual shipped artifacts and supported options alongside documentation. A distribution may include lower-level engines that its default launcher does not expose. Conversely, a familiar product name or open-source repository does not prove the required CPU, graphics, or native-bridge capability. Verify provenance, architecture, dependencies, and an actual bounded execution before relying on an alternative.

Probe structurally similar mechanisms when direct options converge: compatibility shims, virtual peripherals, protocol fixtures, software CPU translation, alternate graphics implementations, and controlled clocks. Choose by the missing capability, not by novelty. Measure host resource costs and stop a branch when another repetition is unlikely to change the next decision.

Validate an observation tool in its actual execution environment. A probe that parses in the host's current language runtime can fail in an older embedded interpreter before collecting anything. Distinguish tool compilation, attachment, completed observation, and detachment. Repair the probe's compatibility first; its parser error says nothing about the target's behavior.

## Record the lesson so it changes the next attempt

A useful lesson is conditional and executable as a workflow:

> When an app's startup repeatedly waits at a platform boundary, identify the expected input, test a minimal documented substitute within the access scope, and require both a changed execution trace and a usable interaction before calling recovery complete.

“Try more emulators” or “use instrumentation” is too broad. Save the triggering symptom, evidence, tested intervention, prediction, observed limit, rollback, and next discriminating test in the target's private workspace. Transfer only the general method here. Use the [runtime-observation workflow](runtime-observation.md) to keep readiness and fidelity claims aligned with the evidence.
