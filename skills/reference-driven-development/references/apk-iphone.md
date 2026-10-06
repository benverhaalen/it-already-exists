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

Useful mechanism references include [touchHLE](https://github.com/touchHLE/touchHLE) for platform-framework replacement and explicit compatibility coverage, [libhybris](https://github.com/libhybris/libhybris) for Android Bionic boundary adaptation on Linux, [UTM](https://github.com/utmapp/UTM) for QEMU-based iOS execution and interpreter/JIT tradeoffs, and [ANGLE](https://github.com/google/angle) for graphics translation. These are conditional source leads, not integrated dependencies or demonstrated APK-to-iPhone solutions. Check the exact revision, component license and supported APIs before reuse.

## Make improvements transfer across apps

Separate portable platform adapters from app-specific fixes. A reusable repair needs a trigger, observed contract, affected operation, independent control, actual-app result, fallback, rollback and version conditions. An offline modification changes behavior; retain the original comparison baseline and identify which properties are intentionally adapted. Never fabricate successful persistence, rewards or server responses merely to avoid an error dialog.

Qualify a varied owned corpus: managed UI, JNI/native rendering, audio, persistence, concurrency, graphics state and lifecycle, followed by mixed engines and external services. Compare Android and iPhone using normal inputs, captures and durable-state checks. Measure cold setup, additional app-specific work, diagnostic iterations and physical performance separately. Progress means broader supported contracts and less repeated intervention; passing a metadata fixture does not establish runtime coverage.

For RDD, preserve the running reference's screens, state transitions and interaction evidence with provenance. Source-assisted work may use inspected code and assets within its authorized scope. Strict independent implementation receives reviewed behavioral specifications through an actual access boundary; the execution analyst's APK, code and complete dependency report are not automatically safe exports.
