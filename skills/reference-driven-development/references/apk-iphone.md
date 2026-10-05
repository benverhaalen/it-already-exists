# APK execution on iPhone and reference transfer

The intended journey is package intake → usable Android oracle → selected execution route → iPhone build → matched complete journeys → reference transfer or modification. Preserve this full goal when testing one component. Current bundled tools qualify metadata and Android observation; they do not convert arbitrary APKs or provide a general iPhone runtime.

## Inspect the actual native contract

Install `scripts/requirements-native-profile.txt` in a task-owned Python environment, then run:

```sh
python3 /path/to/skill/scripts/apk_native_profile.py /private/input.apk --output /private/native-profile.json
```

The helper uses [pyelftools](https://github.com/eliben/pyelftools) 0.33, a public-domain ELF parser, rather than duplicating its binary-format machinery. It reads bounded payloads in memory, checks program/section table bounds and cumulative parser reads, and traverses dynamic program headers so stripped files remain inspectable. Reports include payload hashes, ELF machine and word size, ABI-label agreement, DT_NEEDED, SONAME, and dependency candidates within each declared ABI. It records malformed, ambiguous and budget-skipped entries separately. No target payloads are executed or extracted.

Use [Android's ABI contract](https://developer.android.com/ndk/guides/abis) and the [ELF loading](https://gabi.xinuos.com/elf/07-pheader.html) and [dynamic linking](https://gabi.xinuos.com/elf/08-dynamic.html) specifications to interpret the results. Matching ARM64 instruction sets does not establish matching Android/iOS calling, loader, library or operating-system contracts. Presence of DEX alongside native code preserves both workstreams. Static dependencies omit dynamic loads, JNI/Java calls, direct syscalls, hidden payloads, external splits and server behavior.

## Compare execution routes by required contracts

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
