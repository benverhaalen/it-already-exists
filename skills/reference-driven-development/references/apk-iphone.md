# APK execution on iPhone and reference transfer

The intended journey is package intake → usable Android oracle → selected execution route → iPhone build → matched complete journeys → reference transfer or modification. Preserve this full goal when testing one component. Current bundled tools qualify metadata and Android observation; they do not convert arbitrary APKs or provide a general iPhone runtime.

The supplied versioned APK and its Android execution are the primary reference.
Do not require an existing iOS counterpart or the user's personal phone to
reconstruct it. Use task-owned Android execution and iOS simulators for iterative
comparison; physical iPhone checks qualify device-specific behavior later.
Recover original assets, logic and protocols within the declared access policy.
Judge fidelity against complete Android journeys, not an imagined native design.

For encoded artifacts such as QR codes, recover the actual payload-producing
path. Compare decoded bytes, serialization, encoding/error-correction settings,
geometry, colors, refresh/expiration timing, caching, background/return and
redemption outcomes. A matching-looking code alone proves little. Do not assume
that a code rotates, carries a signature or is scanned for every product type.
Distinguish data delivered by a service from data constructed by the client;
preserve the observed division and unresolved questions. Where external effects
must be isolated, feed both clients equivalent service state and preserve the
entire client flow; see [service testing](service-testing.md). A test namespace
is a declared external-state difference, not permission to alter the renderer
or replace purchase/redemption with canned success.

## Inspect the actual native contract

Install `scripts/requirements-native-profile.txt` in a task-owned Python environment, then run:

```sh
python3 /path/to/skill/scripts/apk_native_profile.py /private/input.apk --output /private/native-profile.json
```

The helper uses [pyelftools](https://github.com/eliben/pyelftools) 0.33, a public-domain ELF parser, rather than duplicating its binary-format machinery. It reads bounded payloads in memory, checks program/section table bounds and cumulative parser reads, and traverses dynamic program headers so stripped files remain inspectable. Reports include payload hashes, ELF machine and word size, ABI-label agreement, DT_NEEDED, SONAME, and dependency candidates within each declared ABI. It records malformed, ambiguous and budget-skipped entries separately. No target payloads are executed or extracted.

Use [Android's ABI contract](https://developer.android.com/ndk/guides/abis) and the [ELF loading](https://gabi.xinuos.com/elf/07-pheader.html) and [dynamic linking](https://gabi.xinuos.com/elf/08-dynamic.html) specifications to interpret the results. Matching ARM64 instruction sets does not establish matching Android/iOS calling, loader, library or operating-system contracts. Presence of DEX alongside native code preserves both workstreams. Static dependencies omit dynamic loads, JNI/Java calls, direct syscalls, hidden payloads, external splits and server behavior.

To compare a reference decompile's native profile against a candidate's, run `scripts/apk_native_compare.py reference.json candidate.json --output comparison.json`. It classifies each matched library as `identical_bytes` (actual SHA256 match), `runtime_marker_match_bytes_differ` (same ISA/word-size/endianness only), `runtime_marker_mismatch`, `uncompared` (one or both sides uninspected), or `reference_only`/`candidate_only`. Shared Flutter engine builds, Dart snapshot formats and ISAs routinely produce `runtime_marker_match_bytes_differ` across unrelated applications; the report always sets `verdict.application_equivalence` to `not_evaluated_by_this_tool` and never declares two APKs the same application from runtime clues alone. Treat `identical_bytes` across every compared native library as partial evidence only — DEX, assets, manifest and signing identity still need their own comparison before claiming artifact equivalence.

## Compare execution routes by required contracts

Qualify the observation runtime before investing in the app route: actual guest
ABI support, API level, completed boot and graphics initialization. A downloadable
system image and a shipped emulator binary do not prove a compatible launch.
Use crash stacks to separate CPU, loader and graphics failures; inspect a working
upstream or owned setup for a discriminating adaptation. After an ambiguous
installation transport error, inspect the actual package-manager result and
complete installed split hash multiset before repeating installation.

Treat startup as part of the full journey. Capture plugin/configuration inputs
without exposing credentials, distinguish absent configuration from a platform
adapter failure, and inspect the original dependency's validation contract.
Test reversible configuration changes through the original SDK path under the
declared external-effect controls. A constructed SDK or displayed first frame
does not establish payment, service or complete-app fidelity. Preserve the
unmodified reference and the exact adaptation; do not return success from
initialization just to get past the splash screen.

Keep candidate routes until evidence discriminates them:

- Original native logic with a compatibility host: inspect loader/relocation, CPU, Bionic, JNI, threading, clock, graphics, audio, filesystem and lifecycle requirements. Qualify each adapter with owned discriminating controls, then actual app journeys. Unknown calls must remain explicit gaps rather than success-returning stubs.
- Managed Android execution: inspect reachable DEX/framework/service use. A native-library shim does not supply Activity, Binder, resources, rendering widgets or the Java runtime.
- Full-system execution: assess guest OS and device support plus iOS interpreter/JIT availability, graphics, memory, latency and distribution. A simulator run does not establish physical iPhone feasibility.
- Source recovery or independent reconstruction: preserve the behavioral oracle and compare complete outcomes. Agent-written cross-language code can reduce construction effort; it cannot recover unobserved behavior or absent server state by itself.

For qualified ARM64 Dart ELF snapshots with identity file/virtual mappings,
`scripts/dart_aot_macho_pack.py input.so /private/new-output` emits unchanged
snapshot bytes, Mach-O assembly with the four Flutter snapshot exports, and a geometry receipt. It refuses unsupported
layouts and existing output directories. Link with the receipt's segment
permissions and check the actual instruction-to-writable-storage distance before
execution. Dart snapshots can address writable BSS relative to their instruction
image; embedding the entire payload in a read-only executable segment can fault
during VM initialization. This packer qualifies bounded storage geometry only.
It does not provide a matching VM, resolve Android/iOS ABI differences, implement
Flutter native bindings or plugins, or establish physical-device compatibility.

For engine-based apps, inspect the matching engine and the actual plugin
registrant before reproducing generic Android APIs. Reuse existing iOS engine
and plugin implementations where their message codecs, results, errors and timing
match the original caller. Android-specific compiled branches and FFI calling
conventions remain separate obligations. A matching runtime version or available
iOS SDK is evidence for an experiment, not proof that the original app will run.

Test VM loading before application execution. Match snapshot format, product
flags, pointer compression and compiled platform ABI separately. The official
[engine configuration](https://github.com/flutter/flutter/blob/78fc3012e45889657f72359b005af7beac47ba3d/engine/src/flutter/tools/gn)
enables compressed pointers for Android ARM64 but excludes iOS because of address
space reservation constraints. Platform metadata changes do not convert this
object layout. A VM mismatch requires a matching runtime or a qualified snapshot
transformation; suppressing its diagnostic is insufficient. Inspect initialization
order too: this revision invokes Dart plugin registration before resolving the
application entrypoint, so a deliberately missing entrypoint alone does not
prevent plugin execution. Use a source-verified initialization-only probe or an
enforced service boundary before running an unfamiliar snapshot.

Qualify native calls separately from VM loading. Apple's ARM64 ABI packs some
stack arguments more tightly than Android's ABI. Inspect the actual dispatcher's
converted C types, including the receiver, before calculating register and stack
locations; argument count alone does not prove a mismatch. Adjacent 32-bit stack
arguments are a discriminating control. Run `scripts/arm64_abi_control.py` on
Apple Silicon with Xcode to compare compiler output and execute an owned
Android-layout caller against a Darwin callee with and without a static bridge.
The fixtures detect incorrect argument values, compare a static scalar bridge
with a compiler-generated bridge, and exercise mixed integer, pointer, boolean
and floating-point registers, stack spills and floating-point returns. Use
`--clang /path/to/engine/clang` to test the actual engine compiler too. These
controls do not provide a general bridge, load an APK, or establish iPhone
execution. Extend controls to callbacks, aggregates and variadic calls before
relying on wider coverage.
Use [Apple's ARM64 ABI rules](https://developer.apple.com/documentation/xcode/writing-arm64-code-for-apple-platforms)
and the matching runtime's generated signatures to select actual adaptations.
For nonvariadic scalar dispatchers, investigate Clang's
[`ms_abi` attribute](https://clang.llvm.org/docs/AttributeReference.html#ms-abi)
as a static adapter: the inspected
[LLVM ARM64 implementation](https://github.com/llvm/llvm-project/blob/8c7a2ce01a77c96028fe2c8566f65c45ad9408d3/llvm/lib/Target/AArch64/AArch64CallingConvention.td)
uses the common AAPCS argument layout for that convention. Annotate only the
incoming foreign boundary; keep host implementation calls native. This is a
conditional mechanism for qualified signatures, not permission to treat all
Windows, Android and Darwin ABIs as interchangeable. Variadic conventions differ.

Keep an experimental convention adapter opt-in and compile-time guarded to its
qualified host, architecture and converted argument/return types. Check both a
working foreign-layout call and intentional rejection of unsupported signatures.
Then compile the runtime's complete binding-registration translation unit with
its actual generated flags and the proposed overlay; a hand-picked dispatcher
can pass while another registered signature fails. Keep this check outside a
live build's source and output graph. A registration compile qualifies signature
coverage only; separately verify linked function addresses, original guest calls,
callbacks and complete behavior before expanding compatibility claims.

The bundled source overlays in `scripts/fixtures/flutter_abi/` preserve this
experimental route. They are pinned to Flutter revision
`78fc3012e45889657f72359b005af7beac47ba3d` and Dart SDK revision
`2da4111d8d0cbf2a83c0662251508f017000da8a`. Apply `flutter-tonic.patch` from
`engine/src/flutter` and `dart-snapshot.patch` from the nested Dart SDK root,
using `git apply --check` before applying. Preserve the accompanying upstream
BSD notices; the repository's MIT license does not replace them.

Enable `dart_use_compressed_pointers=true rdd_android_snapshot_abi=true
rdd_android_ffi_abi=true` through the engine's GN arguments for an ARM64 iOS
simulator release build. The first overlay selects the original Android snapshot
target contract while retaining the Darwin host implementation. The second
adapts Tonic's incoming scalar/pointer dispatcher boundary and rejects wider
converted signatures. Both default off. These are source overlays, not a complete
engine installer: acquire the pinned dependencies, qualify the compiler, and
resolve host toolchain prerequisites separately.

The overlays have been checked against pristine pinned sources and linked into
a simulator engine. Original Android snapshot initialization and retained
lifecycle/accessibility/frame callbacks have executed in that engine. Those
callbacks do not establish outgoing scene FFI, plugin compatibility, rendered
application UI, physical-device execution or universal APK support. Obfuscated
Dart class names can defeat name-based diagnostics; use actual retained engine
entrypoints for initialization probes and preserve separate app-journey checks.

For controlled service tests, `dart-loopback.patch` applies after the snapshot
overlay in the pinned Dart SDK root. Enable `rdd_test_loopback_only=true` through
GN. It guards the Darwin Dart IO TCP connect paths, bind destinations, UDP sends,
message peers and DNS resolution; only numeric loopback destinations are allowed.
`localhost` is resolved locally without DNS, Unix socket traffic is denied, and
reverse DNS is denied. This is an intentional test boundary, not original network
behavior. Keep live reviewed reads in the host-controlled mirror.

Actual linked simulator controls have verified asynchronous and synchronous
external TCP denial, non-local DNS/reverse-DNS denial, external UDP denial,
local UDP delivery, numeric localhost lookup and Unix message-send denial.
Other guarded bind and peer cases still need runtime controls. This patch covers
Dart IO only: native plugins, foreign libraries, inherited sockets and operating
system services require separate qualification. Do not register an external SDK
or claim process isolation from these checks. Preserve normal local service
contracts instead of fabricating successful plugin responses to bypass startup.

Useful mechanism references include [touchHLE](https://github.com/touchHLE/touchHLE) for platform-framework replacement and explicit compatibility coverage, [libhybris](https://github.com/libhybris/libhybris) for Android Bionic boundary adaptation on Linux, [UTM](https://github.com/utmapp/UTM) for QEMU-based iOS execution and interpreter/JIT tradeoffs, and [ANGLE](https://github.com/google/angle) for graphics translation. These are conditional source leads, not integrated dependencies or demonstrated APK-to-iPhone solutions. Check the exact revision, component license and supported APIs before reuse.

## Make improvements transfer across apps

Separate portable platform adapters from app-specific fixes. A reusable repair needs a trigger, observed contract, affected operation, independent control, actual-app result, fallback, rollback and version conditions. An offline modification changes behavior; retain the original comparison baseline and identify which properties are intentionally adapted. Never fabricate successful persistence, rewards or server responses merely to avoid an error dialog.

Qualify a varied owned corpus: managed UI, JNI/native rendering, audio, persistence, concurrency, graphics state and lifecycle, followed by mixed engines and external services. Compare Android and iPhone using normal inputs, captures and durable-state checks. Measure cold setup, additional app-specific work, diagnostic iterations and physical performance separately. Progress means broader supported contracts and less repeated intervention; passing a metadata fixture does not establish runtime coverage.

For RDD, preserve the running reference's screens, state transitions and interaction evidence with provenance. Source-assisted work may use inspected code and assets within its authorized scope. Strict independent implementation receives reviewed behavioral specifications through an actual access boundary; the execution analyst's APK, code and complete dependency report are not automatically safe exports.
