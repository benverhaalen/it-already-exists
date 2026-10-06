# APK execution on iPhone and reference transfer

The intended journey is package intake → usable Android oracle → selected execution route → iPhone build → matched complete journeys → reference transfer or modification. Preserve this full goal when testing one component. Current bundled tools qualify metadata and Android observation; they do not convert arbitrary APKs or provide a general iPhone runtime.

The supplied versioned APK and its Android execution are the primary reference.
Do not require an existing iOS counterpart or the user's personal phone to
reconstruct it. Use task-owned Android execution and iOS simulators for iterative
comparison; physical iPhone checks qualify device-specific behavior later.
Recover original assets, logic and protocols within the declared access policy.
Judge fidelity against complete Android journeys, not an imagined native design.

### Keep location fixtures alive through the journey

Location permission, a fresh native fix, and the resulting application route are
separate requirements. A simulator with granted permission can still leave the
original client waiting when its simulated trajectory has ended. Preserve both
manual selection and location-selected entry paths; do not require a manual city
selector when the original client legitimately opens the nearby catalog.

Use `scripts/ios_location_fixture.py` around a bounded test command on an explicit
task-owned booted simulator. Pass `--device` with its UUID, `--bundle`, two nearby
coordinates via `--start` and `--end`, a `--timeout`, and a new private `--output`
directory, followed by `--` and the test command. The helper starts one fresh
interpolated path whose calculated duration exceeds the test timeout, then clears
that path on command success, failure or timeout. It writes the command log and
a separate lifecycle receipt. A failed cleanup cannot produce a passing receipt.
It does not restart a failed command or select another device.

Use repeated `--require-log-text` arguments for actual selected-test execution
and consequential transition witnesses, in addition to checking the process
exit. Some test tools return success when a misspelled selector executes zero
tests. The helper requires every supplied literal witness in the command log;
it inspects at most 16 MiB and does not store witness text in the receipt. These
markers are evidence handles, not independent proof: inspect the assertions and
actual test result that produce them.

Use `--capture-failure` to save `failure.png` from that selected simulator after
an unsuccessful command, missing witness, or cleanup failure. Capture happens
after fixture cleanup; it is a diagnostic observation, not the exact failure
instant or proof of its cause. Capture failure is recorded separately and cannot
change the test outcome. Screens can contain private data; keep this output
private and inspect it before sharing. A clipboard or permission dialog can block
a test without establishing an application hang. Handle a known dialog specifically
in the UI driver; do not accept arbitrary system alerts. See Apple's
[interruption-handler guidance](https://developer.apple.com/videos/play/wwdc2020/10220/).
Host process-group termination does not guarantee that simulator test runners or
applications stopped; inspect their actual state before starting another run.

Existing simulator location scenarios are replaced; use a dedicated device and
do not run competing fixtures on it. Permission remains unchanged unless
`--grant-location` is explicit. That option persists the in-use grant after the
test and can mask the normal permission-request experience; test permission
prompting, denial and reduced accuracy separately. Keep fixture coordinates and
command output private when they contain user or application data. This helper
provides no network isolation.

The helper was exercised around an original frontend's location-selected catalog,
dated offer and guest restriction journey on an iOS simulator. Separately check
the actual native permission and fresh fix, codec preservation and app transition;
the wrapper's zero command exit does not establish those properties by itself.
Physical-device location, event streams, background/return, permission changes
and all product states remain independent qualifications. Its lifecycle tests
cover failed and timed-out commands, failed trajectory startup, failed cleanup
and refusal to mutate a shutdown device.

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

Before registering a native plugin, compare platform-specific configuration and
identity validation as well as its channel codec. A matching API can still reject
Android configuration. Inspect the selected SDK product's actual dependency graph;
a package manifest can mention networking products that are absent from the linked
closure, while component auto-registration can activate products that are present.
Qualify the built closure and initialization paths before relying on isolation.

For Firebase Core 12.19.0, the bundled opt-in
`scripts/fixtures/firebase_core/android-app-id.patch` adds Android v1 IDs to the
existing iOS validator without replacing the ID or weakening its remaining format
checks. It is pinned to firebase-ios-sdk revision
`27eaab3918e0bf78711cf1abf240577176326432`. Check and apply from that repository
root, then define `RDD_ANDROID_FIREBASE_ID` only in the FirebaseCore C target.
The accompanying Apache 2.0 license applies to the upstream source patch.
`registry-control.m` supplies a synthetic native control: both platform IDs must
validate, a malformed ID must fail, actual SDK configuration must retain the ID,
data-collection state must change, and deletion must empty the registry. Run it
in an empty task-owned app with only FirebaseCore and its required dependencies;
observe the deletion callback separately from the function result. These native
controls passed on an ARM64 iOS simulator. They do not qualify authentication,
Installations, service authority, other SDK versions, or full application startup.
Changing a local validator does not grant an Android identity iOS backend authority.

When a compiled caller omits the failed channel name, trace the host dispatch
boundary before guessing plugins. The pinned Flutter overlay
`scripts/fixtures/flutter_abi/ios-channel-trace.patch` logs only missing channel
names when the process environment has `RDD_TRACE_MISSING_CHANNELS=1`; it does
not log payloads or change replies. Apply from the same Flutter engine root as
`flutter-tonic.patch` and retain `TONIC-LICENSE`, which matches the Flutter source
license. With simulator launch, pass the variable as
`SIMCTL_CHILD_RDD_TRACE_MISSING_CHANNELS=1`. The linked overlay has identified
missing channels during original Android snapshot startup on an iOS simulator.
Missing does not mean fatal: correlate names and timing with the actual failed
journey, then inspect codec, method, state, error and service contracts. Leave
unknown calls as explicit gaps. Keep tracing off for normal use.

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

## Preserve service SDK behavior across platform hosts

Prefer an inspected native SDK and matching channel codec when both platforms
already implement the same service. Reusing listeners, query evaluation, cache
and durable state can remove a large custom reimplementation. Match the APK's
actual codec tags, field order, enums and argument counts; the newest plugin can
be incompatible with the original compiled client. Keep SDK API changes separate
from the client's wire contract.

Use the offline [wire inspector](flutter-wire.md) when a Flutter boundary loses
type identity or fails decoding. It retains tags and absolute byte offsets;
Boolean, integer and floating-point values remain distinct. Declare custom
single-value wrappers only after inspecting the exact generated codec. Qualify
the diagnostic against upstream-generated vectors before using it to blame the
application. A nested value's alignment depends on the complete message; copying
a separately encoded double can corrupt an otherwise plausible fixture.

For local Firestore tests, [LocalFirestoreSettings.h](../scripts/fixtures/firebase_firestore/LocalFirestoreSettings.h)
requires a numeric loopback host and valid port and disables TLS for the emulator.
Apply it before native instance construction or access. Inspect every construction
path, including codec readers that can construct a service instance independently
of the main plugin factory. Check cached instances and additional databases too.
The pinned native SDK's emulator convenience method changes its host but does not
by itself disable TLS; inspect actual settings rather than assuming that behavior.

The authored [local-control.m](../scripts/fixtures/firebase_firestore/local-control.m)
was built with Firebase Apple SDK 12.19.0 and executed in an iOS simulator against
an owned Firestore emulator. It checks rejected external/DNS hosts, IPv6 settings,
absence of Auth/App Check/Installations classes in the selected runtime, and a
local write, server read and server-confirmed listener with a large integer.
Compile it with the adjacent header and the native Core/Firestore SDK targets.
Its synthetic Android app ID requires the opt-in Core validator adaptation in
[android-app-id.patch](../scripts/fixtures/firebase_core/android-app-id.patch)
and `RDD_ANDROID_FIREBASE_ID`; stock Core rejects that identity. The recorded
control used that adapted Core build.
Use a local `demo-rdd-accounts` project on `127.0.0.1:8082`; the fixture writes only
`compatibilityControls/native-ios`. Original APK service adapters need separate
codec and journey qualification. IPv6 connectivity is not tested by this control.

This is a service endpoint adapter, not process isolation. Auth, App Check,
Installations, telemetry and payments may establish their own connections.
Selecting only interop protocol targets does not include their concrete providers;
verify the linked closure and actual runtime before relying on that distinction.
Preserve original wire identities separately from deliberate local service
authority changes. Provider configuration is not attestation, and a local test
token is not a production credential. Do not register an uncontrolled production
provider or fabricate an authorized result to bypass initialization.

Reference mechanisms: [native SDK target definitions](https://github.com/firebase/firebase-ios-sdk/blob/12.19.0/Package.swift),
[Firestore emulator configuration](https://firebase.google.com/docs/emulator-suite/connect_firestore),
and [FlutterFire's versioned service plugins](https://github.com/firebase/flutterfire).
Native fixture success does not establish whole-app fidelity or universal APK
compatibility.

### Check connections made during SDK construction

Do not assume initialization only stores configuration. In inspected Stripe
Apple SDK 26.9.0, constructing `STPAPIClient` invokes fraud telemetry before the
Flutter initialization method returns. Disable `advancedFraudSignalsEnabled`
before client construction in the deliberate local test mode. Analytics has a
separate test condition; disabling fraud signals alone does not disable it.
Inspect [the constructor](https://github.com/stripe/stripe-ios/blob/26.9.0/StripeCore/StripeCore/Source/API%20Bindings/STPAPIClient.swift),
[telemetry eligibility](https://github.com/stripe/stripe-ios/blob/26.9.0/StripeCore/StripeCore/Source/Telemetry/STPTelemetryClient.swift)
and [analytics eligibility](https://github.com/stripe/stripe-ios/blob/26.9.0/StripeCore/StripeCore/Source/Analytics/STPAnalyticsClient.swift).

The authored [local-startup-control.swift](../scripts/fixtures/stripe_core/local-startup-control.swift)
was built with Swift 5 mode, Flutter and StripeCore 26.9.0 and run in an iOS
simulator. Call `RDDStripeHost.registerMessenger` with an owned Flutter messenger.
It checks native configuration, disabled telemetry and analytics, and rejection
of external and local requests by this client's injected transport. It sets the
SDK's process-wide `UITesting` environment flag and uses an inert synthetic key;
run it only in a test host. Its JSON channel accepts startup configuration and
explicitly rejects other payment operations and unqualified 3DS configuration.
It is a bounded startup fixture, not a working purchase adapter or process-wide
network sandbox. Qualify the original client codec and each later payment journey
separately. Keep deliberate telemetry suppression distinct from faithful recording.

## Qualify SDK traffic beyond collection consent

Collection consent is not a network boundary. Datadog iOS 3.16.0 uses a NOP
writer for denied consent, but its default clock provider separately starts
NTP synchronization. Features can also request a writer that bypasses consent.
Inspect the [clock provider](https://github.com/DataDog/dd-sdk-ios/blob/3.16.0/DatadogCore/Sources/Core/Context/ServerOffsetPublisher.swift),
[writer selection](https://github.com/DataDog/dd-sdk-ios/blob/3.16.0/DatadogCore/Sources/Core/Storage/FeatureStorage.swift)
and [core transport construction](https://github.com/DataDog/dd-sdk-ios/blob/3.16.0/DatadogCore/Sources/Datadog.swift).
For a deliberate local test policy, replace both the upload transport and clock
provider before initializing the native core. Retain actual SDK state and feature
registration; do not reply with fabricated initialization success.

The authored [local-transport.swift](../scripts/fixtures/datadog_core/local-transport.swift)
adds an explicit configuration method inside the DatadogCore source target.
Add [crash-control.swift](../scripts/fixtures/datadog_core/crash-control.swift)
inside DatadogCrashReporting and
[startup-control.swift](../scripts/fixtures/datadog_core/startup-control.swift)
inside the Flutter test host. These exact fixture bytes were compiled with
Datadog iOS 3.16.0, KSCrash 2.5.1, DictionaryCoder 1.2.0 and Swift 5 language mode.
The [Flutter plugin patch](../scripts/fixtures/datadog_core/flutter-local-startup.patch)
applies to pub package datadog_flutter_plugin 3.7.0. In a test host, call
`RDDDatadogHost.qualifyNativeConfiguration()` before registering the upstream
`DatadogSdkPlugin` with its Flutter registrar. Apply the patch from the package
root with `patch -p1 --fuzz=0`; retain the upstream Apache license. The patch
requires the pristine `DatadogSdkPlugin.swift` SHA-256
`cf41acefa6e0365ba8ef24aa980511b4bbdf4722ebd409aba686628514beb3ce`.
Check that digest before applying the zero-context patch.

Simulator checks passed for rejection of external and loopback requests through
this configuration's HTTP factory, local clock offset, actual initialized core
with denied consent, and actual registered crash-reporting feature. The plugin
preserves its core configuration mappings and native crash initialization while
using an inert token, local environment and denied consent for the test policy.
It registers upstream logs and RUM channels; their complete behavior and crash
capture/recovery are not qualified by these initialization checks. The transport
is deliberately unavailable, not a successful mock uploader. This policy changes
telemetry behavior and is not a process-wide sandbox or an arbitrary APK adapter.

## Make improvements transfer across apps

Separate portable platform adapters from app-specific fixes. A reusable repair needs a trigger, observed contract, affected operation, independent control, actual-app result, fallback, rollback and version conditions. An offline modification changes behavior; retain the original comparison baseline and identify which properties are intentionally adapted. Never fabricate successful persistence, rewards or server responses merely to avoid an error dialog.

Qualify a varied owned corpus: managed UI, JNI/native rendering, audio, persistence, concurrency, graphics state and lifecycle, followed by mixed engines and external services. Compare Android and iPhone using normal inputs, captures and durable-state checks. Measure cold setup, additional app-specific work, diagnostic iterations and physical performance separately. Progress means broader supported contracts and less repeated intervention; passing a metadata fixture does not establish runtime coverage.

For RDD, preserve the running reference's screens, state transitions and interaction evidence with provenance. Source-assisted work may use inspected code and assets within its authorized scope. Strict independent implementation receives reviewed behavioral specifications through an actual access boundary; the execution analyst's APK, code and complete dependency report are not automatically safe exports.


### Preserve directory contracts across platforms

An Android AOT frontend still sends Android plugin channel names when running
inside an iOS host. Installing only the iOS plugin does not cover that wire
contract. Inspect the actual generated request and reply envelopes before
mapping the underlying operation to native storage.

The authored [directory adapter](../scripts/fixtures/path_provider/android-ios-directories.swift)
uses the Android `PathProviderApi` channel names for four no-argument operations.
It follows the inspected `path_provider_android` 2.2.22 standard-codec single-item
reply envelope and `path_provider_foundation` 2.4.4 iOS directory mapping:
documents, application support, and caches. Temporary and application-cache
requests share the caches directory, as these inspected plugins do. Directories
are created through native Foundation APIs before returning their real paths.

Compile the fixture in a Flutter iOS host and call
`RDDPathProviderHost.registerMessenger` with the running engine messenger. Its
native control writes, reads and removes a unique file in each directory, checks
container membership, and checks the cache alias and documents/support
separation. These exact fixture bytes compiled and passed those controls in an
iOS simulator; an original Android frontend then called documents, temporary
and support operations through the adapter and advanced to its populated
selection screen. A follow-on image cache still required its SQLite plugin.

This is bounded directory compatibility, not full persistence qualification.
Absolute Android paths, preexisting data migration, backup policy, protected
files, app groups and shared/external storage remain separate transfer questions.
The fixture does not register Android external-storage channels. Inspect actual
consumers and compare persistent state across relaunch; do not substitute an iOS
sandbox path for shared storage without testing its intended property.

Sources: [Android plugin](https://github.com/flutter/packages/tree/path_provider_android-v2.2.22/packages/path_provider/path_provider_android),
[iOS plugin](https://github.com/flutter/packages/tree/path_provider_foundation-v2.4.4/packages/path_provider/path_provider_foundation).
Upstream BSD attribution accompanies the fixture. Plugin versions establish the
inspected contracts; they do not prove an arbitrary APK used those versions.


### Reuse the real database implementation

When an original frontend calls `com.tekartik.sqflite`, first compare the
upstream Android and Darwin method contracts. A storage path adapter does not
supply database operations. Prefer the actual native SQLite implementation to
mock query results: cache metadata, transactions and persistent state depend on
its behavior.

The authored [native control](../scripts/fixtures/sqflite/RDDSQLiteControl.m)
was compiled against the Darwin native sources from `sqflite_darwin` 2.4.4.
Acquire the [upstream archive](https://pub.dev/api/archives/sqflite_darwin-2.4.4.tar.gz)
and verify SHA-256
`dbdda396f975f74d611ffd3e6fb280ee3ee4cd2319b89278533f427e0140cf0b`.
This native-source qualification does not imply that its newer Dart package
constraints fit an older application's toolchain or prove the APK's version.

For the qualified manual host, place the Darwin native sources in
`SQLitePlugin` beside the control, retain both upstream licenses, link
`libsqlite3.tbd`, and apply the accompanying Foundation import patch when no
Pod prefix header supplies it. Bundle the upstream privacy manifest in a
separate resource bundle to avoid collisions with other plugins' manifests.
Register `SqflitePlugin` with the engine registrar. The control executes before
engine startup and plugin registration. Run it only in a dedicated qualification
launch and require its returned Boolean to pass; normal launches should not run
the disposable probe. It waits synchronously with a timeout per operation, so
slow storage can cause launch watchdog failures. Do not block an active
application thread to run it during normal use. The direct probe uses a separate
plugin instance and does not exercise the engine messenger itself; retain the
subsequent real frontend calls as separate integration evidence.

The simulator control passed request and success-envelope codec round trips,
disk-backed open/insert/query, integer/text/blob/null preservation, transaction
rollback, close/reopen persistence, a native missing-table error, and deletion.
An original Android frontend subsequently issued actual query and insert calls
through the registered native plugin and reached a populated image-bearing
selection screen. Image delivery separately used reviewed cached source bytes;
SQLite alone does not establish image or whole-screen fidelity.

Error-envelope transport, batch operations, cursor paging, transaction IDs,
concurrent callers, process restart, migrations and preexisting Android database
files remain unqualified. The control uses a disposable database and tests a
bounded contract, not arbitrary schemas. Keep actual-app transition evidence
alongside controls; successful startup is not evidence that all database users
work. Upstream implementation: [sqflite Darwin](https://github.com/tekartik/sqflite/tree/master/sqflite_darwin).
