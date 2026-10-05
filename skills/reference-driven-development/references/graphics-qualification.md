# Qualify graphics replacements across every boundary

A backend can work directly while a consumer's dispatch and compatibility layers
still route around it. Qualify direct backend behavior, guest API dispatch and
transport, surfaces and presentation, and the full application journey separately.
A passing boundary does not qualify the next.

## Choose candidates by mechanism

The pinned [gfxstream dispatch](https://github.com/google/gfxstream/blob/07ee40efb0e7037a9a9b7fe59071e7c4997e7cbe/host/gl/OpenGLESDispatch/GLESv1Dispatch.cpp)
selects its statically linked GLES1 translator first. Its
[EGL path](https://github.com/google/gfxstream/blob/07ee40efb0e7037a9a9b7fe59071e7c4997e7cbe/host/gl/glestranslator/egl/egl_imp.cpp)
creates version-specific translator contexts. Selecting another underlying
library therefore does not prove that the translator was bypassed. Source
inspection does not identify an installed binary's exact revision.

| Candidate | Job | Qualification needed |
| --- | --- | --- |
| [ANGLE ES1](https://github.com/google/angle/blob/main/doc/ES1Status.md) | Fixed-function support above a modern backend | Feature gaps, guest dispatch, sharing, resource lifetime and presentation |
| Guest ANGLE with Vulkan transport | Move interpretation into the guest | Guest ABI/OS, Vulkan driver and transport, loader and display integration |
| [GL4ES](https://github.com/ptitSeb/gl4es/tree/ec16bedd8819c475326f4f1a3063772c6d986e06) | Fixed-function shader generation and texture environments | ES1 ABI, fixed-point adaptation, lifecycle and extensions |
| Guest software rendering | Independent simple control path | Actual API coverage, precision, performance and presentation |

Inspect actual exports and behavior. A fixed-point wrapper forwarding to an
underlying fixed API may fail when the backend supports only float entry points.
Preserve upstream licenses and attribution; GL4ES is MIT. Check the exact revision
and rights before reuse. These are candidates, not installed or universally
qualified dependencies.

## Design discriminators that reject plausible errors

Use unrelated authored inputs, an unshared owned context and independent expected
outputs. Keep a known-good neighboring operation. Test both output and state.

- Contrast unit-zero state before and after configuring another texture unit.
- Use visibly different textures, patterns and reversed coordinates. Different
  rows are necessary to discriminate vertical coordinate errors.
- Separate server-active texture state from client-active coordinate arrays.
- Prime queried state with contrasting values before testing setters. An inherited
  matching value does not establish that a setter works.
- Predict RGB and alpha separately, including transparent RGB and non-neutral
  colors. Visual plausibility is weaker than independently derived pixels.
- Cover nonzero first indices, interleaved strides, VBO/EBO offsets and updates.
- Exercise conversion directly: a backend accepting fixed-point arrays can bypass
  the CPU converter while still producing correct draws.
- Check null outputs, negative queries, cardinalities, guards and error state.

Keep raw numeric words, declared representation, units and decoded values.
Convert fixed-point quantities without corrupting enum-valued arguments. Compile
ABI-facing adapters with implicit declarations as errors. Check prototypes and
required headers; loading an export is not calling it.

A full-frame oracle is stronger than a few sample pixels when transferring to a
new boundary. Native success codes establish lifecycle/error outcomes only;
independent output checks establish the declared image property. Record which
branch the control actually exercised.

## Preserve context and routing

Use explicit underlying library handles to prevent compatibility exports from
resolving recursively. Avoid changing the caller's current context during
initialization; some libraries create one as a side effect. Verify current
context, display and draw/read surfaces before and after initialization, drawing,
readback and teardown. A configuration flag needs observed effective behavior.

Do not infer backend version from the requested context version. Drivers may
upgrade requests. Inspect the actual version and relevant documented controls,
such as [ANGLE's context upgrade extension](https://chromium.googlesource.com/angle/angle/+/refs/heads/main/extensions/EGL_ANGLE_create_context_backwards_compatible.txt).
Guest API version and underlying transport version are separate observations.

For interception, qualify direct imports and procedure-resolver results, multiple
contexts and threads, context retirement and window recreation. Preserve original
calling conventions and resolver semantics. Restoring patched bytes does not
restore mutated GL state. Retire adapters only when ongoing execution restoration
or process termination is demonstrated. Successful normal teardown does not
establish recovery from lost contexts or partial setup failure.

Track context ownership at the layer that creates and destroys it. Keep resource
creation, routing, presentation and cleanup in one coherent contract. Check
failure branches separately; a comment describing cleanup is not executed proof.

## Bind the executed artifact and complete journey

Record source, compiler, headers, build commands, executed library hashes and
actual configuration. A later byte-identical rebuild proves reproducibility,
not a retrospectively captured original build receipt. Preserve rejected
candidates and their negative evidence.

For windows, test entry, input, background, foreground, resize, exit and reopen.
Compare fresh captured output with independent expectations and require owned
resource cleanup. Count memory and timing across repetitions. Thread sharing,
context loss and deferred destruction need their own cases.

Diagnostic capture failure is distinct from application failure. A readback path
must not crash the target merely because the observer cannot capture its current
surface. Keep observer error and target outcome separate.

When a service stalls startup, inspect the ordinary completion/error path first.
Normal dismissal may permit local work; compare an intervention with an
unmodified control before claiming it necessary. Derive ABI and error constants
from the actual platform, retain callbacks for their native lifetime, and verify
restoration separately. Never invent successful saves or rewards.

An observation timeout does not prove a live operation ended. Check process
identity and in-flight work before extending or replacing observation. Guest
instruction time and host wall time can diverge; physical-device performance
needs actual device evidence. Bounded controls do not establish general graphics
conformance or complete application fidelity.
