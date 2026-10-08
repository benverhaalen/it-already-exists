# Preserve service behavior without production side effects

Separate the client, service contract and external authority. Screens and QR
rendering can match while the issuing ledger, payment processor or venue scanner
remains outside the reconstruction. Do not claim production validity from a
successful local checkout or a visually identical code.

## Qualify callable transport before business behavior

Use the real native SDK when the original client calls a callable-function
plugin. Recover its channel, argument fields, timeout units, success data and
error envelope first. A JSON endpoint that always returns success does not
preserve those contracts. An HTTP 200 response can contain a callable error;
a response with no data or error is also a failure.

Inspect the actual SDK request before treating its JSON fields as business values.
The [callable protocol](https://firebase.google.com/docs/functions/callable-reference)
encodes 64-bit integers as typed objects with decimal strings. A local fixture
that reads these objects as ordinary integers can reject a valid client request
before any business rule runs. Use [callable_values.py](../scripts/callable_values.py)
to decode nested values with explicit traversal and integer bounds. It preserves
unknown typed maps and returns fresh containers. Its known-wrapper validation is
stricter than SDK coercion; qualify it against captured request shapes. Python
integers retain magnitude, not signedness metadata, so this is not a lossless
wire encoder. This helper's checks qualify decoding only, not fee calculations
or agreement with a production quote.

The authored [native control](../scripts/fixtures/firebase_functions/AppDelegate.swift)
was compiled with Firebase Apple SDK 12.19.0 from revision
`27eaab3918e0bf78711cf1abf240577176326432`. It passed native serialization of an
integer above JavaScript's exact-integer range, Boolean, null and list values;
an HTTP 200 permission error; a malformed response; and three denied endpoint
controls. The loopback fixture recorded exactly the three expected requests.
These checks used no production account, token, payment or business function.

To reproduce, use a dedicated iOS control target with this `@main` source and
the real FirebaseCore and FirebaseFunctions products. Include
[GuardControl.swift](../scripts/fixtures/firebase_functions/GuardControl.swift)
and a copy of the endpoint guard in that control target as well as in the SDK.
The shared source avoids relying on an SDK-internal symbol from another module. Apply the
[SDK patch](../scripts/fixtures/firebase_functions/local-callable.patch) to the
inspected SDK revision and add
[the endpoint guard](../scripts/fixtures/firebase_functions/RDDLocalCallableTransport.swift)
to its `FirebaseFunctions/Sources` directory. Preserve the
[Apache license](../scripts/fixtures/firebase_functions/firebase-ios-sdk-LICENSE).
The patch qualifies the endpoint before token acquisition in callable and
stream entry paths. Only the callable path was exercised by this control.

Start the [local protocol fixture](../scripts/fixtures/firebase_functions/local-callable-server.py)
with `python3 local-callable-server.py --evidence /private/new-requests.jsonl`.
It binds only `127.0.0.1:5006`. Launch the native control with
`RDD_FUNCTIONS_LOCAL_ONLY=1` in its environment; with `simctl launch`, use the
`SIMCTL_CHILD_` prefix. Require the actual `RDD_FUNCTIONS_NATIVE_CONTROL_PASS`
record and inspect the request receipt. The test namespace is
`demo-rdd-accounts`; credentials and headers are not copied into the receipt.
The server supplies protocol controls and explicit errors for unknown business
functions. It does not implement an application's account or purchase rules.

The guard is opt-in and covers the initial SDK endpoint, not redirects or all
native networking. It permits only HTTP on the fixed numeric loopback endpoint
with the test namespace, a region and a bounded function name. It rejects URL
credentials, query strings and fragments. Do not use it as a whole-process
isolation certificate. A native transport PASS and original client request
forwarding establish different properties; keep both records and recover the
real business contract before implementing local account, order or pass state.

The guard control varies one URL property per rejection case instead of
combining several invalid properties in one URL. It passed on native Swift
6.2.4 and in the iOS control: two permitted cases and 22 rejected variants,
including credentials, empty/nonempty queries and fragments, host/port,
namespace, region/function syntax, maximum function length and encoded line
breaks. These are source-level predicate checks with no networking; the three
SDK denied-endpoint calls separately exercise the patched SDK entry path.
Neither check proves redirect containment or whole-process isolation.
The path expression uses strict full-string anchors. A prior trailing-newline
probe was rejected; it did not demonstrate an exploit in the previous guard.

On a Mac with Xcode, run the standalone control from the fixture directory:

```sh
xcrun swiftc -D RDD_CALLABLE_GUARD_STANDALONE \
  RDDLocalCallableTransport.swift GuardControl.swift -o /private/guard-control
RDD_FUNCTIONS_LOCAL_ONLY=1 /private/guard-control
```

Require `RDD_CALLABLE_GUARD_CONTROL_PASS allowed=2 rejected=22 requests=0`.
Do not define the standalone compilation flag in the iOS app target.

Upstream implementation: [Firebase Functions SDK](https://github.com/firebase/firebase-ios-sdk/tree/27eaab3918e0bf78711cf1abf240577176326432/FirebaseFunctions/Sources).

Before running a money-connected reference, define the complete journey:
catalog → current quote → payment outcome → durable order → pass display →
validation → redemption → restart. Include changed prices, cancellation,
payment failure, timeouts, retries, expiration and duplicate redemption. Keep
original and candidate on the same controlled service state during comparison.

Routine comparison and QA should replay captured state locally. Keep any live
catalog refresh in a separate, explicitly enabled producer, with cached assets
and dated provenance. Do not refresh for every launch, retry or test case. Live
requests remain observable to the upstream service; neither read-only access
nor removed telemetry guarantees invisibility. Qualify native SDK egress as
well as the capture helper before claiming no runtime upstream traffic.

For an explicitly requested standalone, interactive test app, move synthetic
identity, private records and permitted business calculations onto the target
device. Keep the original client protocol, including token refresh, query
listeners, typed references and callable result/error envelopes. A local service
running on the development computer does not establish standalone operation;
loopback on a physical device refers to that device. Separate simulator ports
from host fixtures when both share the same network namespace.

Treat live public reads as a separate authorized mode from deterministic replay.
Preserve the reference's actual query clauses: access rules may require filters,
and a changed header or selected location does not prove that the returned
records changed. Key any fallback cache by the complete endpoint and canonical
query, label stale results, and do not substitute cached success for an access
denial. Bound foreground refreshes and avoid repeated upstream reads during
routine QA. HTTP method alone does not establish a read: inspect the operation,
including read-only POST query endpoints.

For a local quote, resolve the selected product, dated inventory and venue rather
than a copied display price. Preserve integer money units, quantity bounds and
inclusive-tax semantics. Mark approximated fees and jurisdictions explicitly;
a rendered total does not establish production price parity or a completed
purchase. Exercise the original screen with changed quantity and missing data.
Then stop the development services and test an ordinary reopen with persisted
identity, selected location, images and private state. Build success, a public
HTTP response and a pure calculation test remain separate evidence from that
complete journey.

Checkpoint the complete local comparison state before relying on a long-running
test session: authentication identities, service records, asset bytes, local
overrides and server policy. Keep credentials and exports private. Record versions,
input hashes and the intended defaults. An export file alone is insufficient:
stop and import the checkpoint, then compare complete record fields, stable account
identity and asset hashes before replaying the original client journey. Check
nested collections as well as top-level records. Keep historical credentials or
session continuity marked unknown when rebuilding an account from profile data.
Compare protocol types as well as values. If import changes JSON representation,
inspect the specific difference against the service contract before accepting it;
do not broadly normalize away missing fields, integer precision or changed types.

Separate restart restoration from changes made by the client after launch. Preserve
before/after state and investigate each changed field; do not ignore an entire user
record merely because some profile updates are expected. Use
`scripts/json_state_delta.py --before /private/before.json --after /private/after.json
--output /private/delta.json` for an exact, type-sensitive JSON comparison. Exit 0
means equal, 1 means differences, and 2 means invalid input or failed output.
The receipt reports RFC 6901 pointers and hashes without copying changed values;
it still belongs in private evidence. Array length changes are reported as a whole
array because positions can shift. The helper does not normalize service types or
authorize changes. Review protocol representation differences separately, and
qualify expected client mutations through the actual operation and readback.

When no checkpoint exists, recover from immutable captures plus explicit recorded
adaptations. Validate the complete plan before writing, refuse to overwrite an
unqualified populated database, and read back every restored record. Do not rerun
live capture scripts as a shortcut or silently replace missing state with defaults.
Label any reconstructed defaults and test their affected client paths separately.
For Firebase fixtures, use the official [emulator import/export mechanism](https://firebase.google.com/docs/emulator-suite/install_and_configure#export_and_import_emulator_data)
and qualify the actual selected versions and services.

Prefer an operator-provided sandbox with legitimate test payment and issuance
credentials. Otherwise use live reviewed read-only discovery alongside an
isolated stateful test service for payment, orders, passes and redemption. That
service needs coherent identifiers, timestamps, failure outcomes and durable
state; a canned successful response is not a backend implementation. Never
create a production pass, consume real credit, redeem a real entitlement or
send a test QR to a real venue scanner. Test codes must use a separate namespace
and test verifier. Preserve the original client journey and appearance while
marking test provenance outside comparison captures.

## Qualify populated state through the original renderer

An empty screen passing does not qualify populated records. Recover the original
query filters, reference types, deserializers and downstream dereferences before
seeding test state. A field accepted as nullable by the parser can still be required
by a later grouping, expiry or rendering operation. Include the metadata used by
those operations even when its name seems unrelated to the visible product type.
Use a crash address or runtime stack to locate the actual requirement; repair the
fixture contract before replacing the screen or suppressing the exception.

Start with the smallest coherent populated fixture, then cover individual and
grouped items, ordinary reopen, partial consumption, completion and expiry.
Use the original client to render those states. Assert the visible count and
navigation, capture the actual screen, and read back durable state after each
transition. A navigation-only probe must remain unqualified for content.
Read back the actual mutation contract instead of assuming which fields consumption
changes. Grouped and single-item views can expose the same content under different
accessibility roles; inspect the tree before classifying a failed assertion as a
rendering defect. Check identifier absence across roles when an item should vanish.
For expiry, distinguish a preset expired fixture from crossing a live timer boundary.
A filtered item can retain its unconsumed record; verify both the UI and durable state.
Before setting the boundary expectation, trace the actual clock source and deadline
constructor. A displayed local time, venue timezone, device timezone and server
instant can differ. Record offsets and date interpretation; a test crossing the
wrong instant cannot establish an expiry defect. Compare an already-expired state
and a live crossing separately, restore exact fixtures, then recheck active content.
Keep clock substitution scoped to testing; do not change original behavior merely
to make an assumed deadline pass.

Decode machine-readable artifacts from screenshots with an independent decoder.
Check the complete payload, identifier membership and endpoint construction,
including schemes added by the client. A displayed code can encode a malformed
URL. Trace local configuration caches too: a service update may reach persistent
storage after the current screen has already used an older value. Verify the
actual encoded result after refresh and ordinary reopen. Capture it twice while the screen is open and again after ordinary reopen;
determine whether it is stable or changes before assuming rotation. Keep test
payloads in a distinct nonredeemable namespace. Encoding fidelity, client state
changes and external verifier acceptance are separate properties.

When the user relaxes a fidelity requirement, narrow that property's acceptance
criteria explicitly. A requested local pricing policy can unblock rendering and
lifecycle tests, but does not qualify reproduction of the upstream pricing policy.
Keep currency units, rounding and jurisdiction inputs explicit in the local rule.

## Recover quote authority as well as its shape

Separate four properties: SDK transport decoding, catalog price, client-side
calculation, and server-authoritative quote. A response accepted by the original
parser establishes its shape, not the price policy. Trace the caller, result
parser, product/event overrides and calculations before interpreting fee fields.
Missing, null and zero values are different; none proves an inheritance rule.

Compare legitimate captured or operator-sandbox quotes under the same variant,
quantity, identity class, location, currency, clock, promotions and service
revision. Cover displayed fee labels, tips, discounts, per-line versus aggregate
rounding, totals, changed-price requotes and failures. Bind each result to that
context and the original screen; a matching total can conceal wrong components.
Use existing `comparison.py` property packets to retain separate outcomes and
missing evidence. A controlled local formula is a diagnostic fixture until an
independent oracle qualifies the rule. Keep unknown fees unavailable rather than
silently substituting zero or a plausible rate.

A quote-only flag on a transaction endpoint is a lead, not evidence of no
side effects. Inspect routing and service behavior within the declared access
policy before calling it live. If the backend rule cannot be observed, record
the exact unresolved inputs and oracle needed; continue qualifying the original
client and other supported journeys without claiming complete checkout parity.

## Cover distinct product journeys

Recover the original product and order variants before selecting comparison
journeys. Bundles, standalone items, admission and reservations may share a
listing while using different availability, option, fee and fulfillment rules.
Preserve these differences in captured records and follow referenced items and
dated inventory. A displayed bundle does not establish a working standalone item.

For each observed variant, exercise selection from the normal entry state and
record the next screen or restriction. Assert its actual content and the return
path, not just that the list disappeared. If a guest reaches an account gate,
qualify that gate and dismissal separately; do not count it as checkout coverage.
Use the controlled identity path to continue the original journey. Track
unobserved variants explicitly rather than substituting a familiar product flow.

## Recover response contracts from compiled clients

Use parser evidence to narrow a fixture before returning success. A service
method name and nearby string labels are leads; trace the original caller,
result extraction, map keys, casts and continuation. Distinguish an empty list
from missing data, null, errors and records with unknown required fields. Test
the real original screen against the fixture, including loading completion and
visible empty-state content. Do not equate an accepted payload with production
business rules. A zero-card account does not qualify payment or checkout.

For ARM64 Dart AOT, `scripts/dart_aot_pool_xrefs.py` finds direct pool loads and
adjacent ADD/LDR loads within supplied, instruction-aligned ELF ranges. Install
`requirements-native-profile.txt`; provide a JSON list of `{ "start": "0x1000",
"end": "0x1010" }` ranges from qualified metadata and a Blutter `pp.txt` dump:

```sh
python scripts/dart_aot_pool_xrefs.py --elf /private/libapp.so \
  --ranges /private/ranges.json --pool /private/pp.txt \
  --slot 0x108 --output /private/new-pool-references.json
```

The output retains source hashes, range bounds, pattern and label. Keep it
private: labels can reveal application or sensitive data. The helper rejects
wrong architectures, overlapping ranges and ranges outside a file-backed
executable segment. It does not discover function boundaries, deserialize
snapshots, infer a response schema or follow control flow. Candidate references
may include data inside a supplied range; absence does not prove no reference.
Tests include register mismatches, nonadjacent loads, range crossings and ELF
boundary failures. Fixed instruction vectors assembled independently with LLVM
check direct/adjacent loads and reject ADDS/SUB; local encoders are not the
only decoding oracle. One compiled-client comparison matched all five selected
references from a Capstone baseline; this is narrow qualification.

[Blutter](https://github.com/worawit/blutter) recovers pool metadata through a
matching Dart runtime. [unflutter's annotator](https://github.com/zboralski/unflutter/blob/main/internal/disasm/annotate.go)
uses the same direct and adjacent pool-load patterns; its broader analysis
tracks register provenance for indirect calls. That broader tool remains a
candidate, not an integrated or validated replacement. This helper was authored
independently and uses explicit existing metadata rather than a new snapshot
parser. Preserve upstream licenses when adopting upstream code.

## Local test identities

When requested, keep synthetic accounts and application profiles entirely in
the controlled environment. Prefer the actual provider's supported emulator
over inventing authentication responses. The MIT-licensed `firebase-tools` project's
[Firebase Authentication emulator](https://firebase.google.com/docs/emulator-suite/connect_auth)
supports account creation, sign-in and local email/SMS verification through
normal SDK contracts. Its unsigned tokens have test authority only. Use a
`demo-` project, explicit loopback binding, and the runtime egress boundary.
Do not route synthetic identities or these tokens to production services.

`scripts/local_auth.py` seeds a synthetic email and display name in an already
running Firebase Auth emulator. It accepts only numeric loopback HTTP endpoints,
disables proxies and redirects, requires `.invalid` email domains, and omits
session tokens from output. Pass a private JSON fixture containing `email`,
`name` and `password`; retain credentials and exported emulator state privately.
The helper does not start the emulator or redirect an APK's SDK calls.

For rapid persona setup, pass `--persona rdd-test-example` with an email/name
fixture. Reusing the ID selects the same local account and updates its name
and email without credential entry. This uses the inspected emulator-only JSON
custom-token contract; it is deliberately a test-control operation. Keep these
controls outside the normal comparison UI, or in a separate test overlay. Wire
the selected local session and profile changes into the app's actual state and
invalidation path. A control script or changed label alone is not in-app
integration. Preserve a separate mode for exercising the real sign-up flow.

When a persona edit spans authentication, a profile store and a local fixture,
snapshot the affected state and use exact field masks. Check stable identity,
credentials and unrelated fields after updating. On failure, attempt each
compensating operation independently; one failed restore must not skip the
others. Read back restored state rather than treating an acknowledgment as
proof. Record the failed stage and each compensation outcome without secrets.
Write a nonempty pending receipt before mutation and save the edit outcome
before refreshing the app session. A failed refresh does not undo an applied
edit. A pending receipt after interruption means unknown state; reconcile it
before retrying. Inject partial-write and compensation failures separately.
This is recovery across stores, not an atomic transaction or proof of the
original account-edit behavior.

On Apple platforms, qualify native session storage before blaming the service
or replacing SDK responses. See [iOS session storage](ios-session-storage.md).
When reusing a compiled cross-platform client, preserve the native plugin
registry's initialization constants as well as its callable channels. The client
may obtain its initial user there before it subscribes to a state stream. A
native signed-in user alone does not prove that the client sees the same session.

Qualify account creation, duplicate/invalid input, verification, sign-in/out,
refresh, profile updates, switching accounts and restart persistence. Test the
original and candidate against equivalent fixture state. Auth emulation does
not implement the application's profile, wallet, order or entitlement service.
Recover those contracts separately and preserve relations using local IDs.
SDK routing may require source changes or instrumentation when release builds
strip emulator APIs. An emulator account alone is not integrated functionality;
unknown production rules and emulator differences remain explicit limits.

Separate callable response data from durable service state. An account-creation
response may parse correctly while the original client still waits for its
profile document or subscription. Inspect the original continuation and its
record references; qualify that the local record exists and reaches the client.
Return success only after required local persistence succeeds. Keep identifiers
test-only and distinguish recovered field types from unknown production rules.

Qualify sign-in through the original credential form before testing restoration;
preloading a native session only tests the returning-user path. Keep synthetic
credentials out of typing logs and clear temporary credential transfer state.

Verify the ordinary returning-user journey without setup shortcuts: finish the
original onboarding, terminate the process, then launch with no reset, persona
seeding or automatic sign-in flags. Require the populated original entry screen
and the same identity in the original account screen across repeated launches.
Check that relaunch does not create another account. Native session-storage
controls alone do not prove this client journey. Test expired sessions, explicit
sign-out and account switching separately; a successful immediate relaunch does
not establish them or persistence after reinstall.

## Bundled request guard (HTTP)

`scripts/service_guard.py` evaluates an exact request fingerprint including
destination, verb, path/query, ordered headers and body digest. Unknown requests
are denied. Reviewed forwarding additionally needs runtime opt-in; protected
hosts and their subdomains override forwarding. Fixture responses stay local.
Changing authentication, headers, query variables or a GraphQL operation
invalidates the permission. This deliberate conservatism requires new review
after legitimate request changes. An empty policy provides no live access.

`scripts/service_guard_mitm.py` supplies the adapter for
[mitmproxy](https://github.com/mitmproxy/mitmproxy), an MIT-licensed proxy.
Its [local-response hook](https://docs.mitmproxy.org/stable/addons/examples/#http-reply-from-proxy)
answers without forwarding the HTTP request. Install the optional pinned
dependency with Python 3.12+ in a task-owned environment:

```sh
python -m pip install -r /path/to/skill/scripts/requirements-service-guard.txt
PYTHONPATH=/path/to/skill/scripts mitmdump \
  -s /path/to/skill/scripts/service_guard_mitm.py \
  --listen-host 127.0.0.1 --listen-port 8080 \
  --set connection_strategy=lazy --set upstream_cert=false \
  --set rawtcp=false --set body_size_limit=1m \
  --set rdd_policy=/private/reviewed-policy.json
```

Policy JSON has `schema_version: 1`, `protected_hosts` and `rules`. Each rule
has a `fingerprint` from `service_guard.fingerprint`. A `forward` rule needs
`read_only_review`, a private evidence reference; a `fixture` rule needs `status`,
`content_type` and bounded `body_base64`. Enable `rdd_live=true` only after
semantics and routing review. GET is not automatically safe, and POST is not
automatically a mutation. A review reference is declared evidence, not a proof
that the named operation lacks side effects. Hashes do not encrypt secrets;
keep policies private and never log complete headers, tokens or payment bodies.

This adapter is not a firewall or a sandbox readiness certificate. It handles
HTTP requests that actually reach it. Lazy connections and disabled upstream
certificate fetching avoid premature upstream contacts; prevent raw traffic,
QUIC, UDP, WebSockets, proxy bypass, alternate interfaces and direct TLS at the
runtime's egress boundary. Configure no bypass rules, production-flow replay or
other forwarding addons. Certificate pinning and native clients require a
separate qualified routing adapter. A system proxy setting alone is insufficient.

Before live access, test the installed runtime with an owned upstream counter:
approved reads arrive; purchase and credit requests do not; unknown destinations,
redirect targets and changed GraphQL bodies are denied; protection survives
restart and failed policy reload. Inspect the original checkout and redemption
journey against the controlled test service. Passing policy fixtures or proxy
checks does not prove a target cannot bypass it or establish server fidelity.

## Transfer typed catalog references

### Follow asset dependencies through detail records

A working listing image does not establish working detail imagery. Trace the
original detail query and cache requests: a separate record, nested array or
gallery may supply different URLs. Inventory those exact leaves and distinguish
image, video and external-link entries. Preserve the original capture, reviewed
source URLs, content types, byte lengths and hashes. Fetch approved assets once
through the qualified acquisition boundary; verify local HTTP responses against
the captured bytes before relying on the original renderer.

Use `scripts/asset_field_transfer.py` for explicit reviewed replacements in JSON,
including Firestore REST wrappers. Each binding has `pointer` (an RFC 6901 JSON
pointer), `expected` (the exact source URL) and `replacement` (the cached URL).
It returns a fresh document and changed-leaf URL hashes; it rejects missing,
stale, duplicate or invalid bindings. It does not discover fields, download
assets, contact services or establish permission. Do not globally replace URL
strings: unrelated links and other occurrences stay unchanged.

```sh
python scripts/asset_field_transfer.py --input /private/captured-fields.json \
  --bindings /private/reviewed-asset-bindings.json --output /private/asset-transfer.json
```

Keep the output private; it contains the transferred document, not just hashes.
Pass only its `document` through the separately qualified local writer. Compare
all unrelated fields before mutation and read back the result. Protect against
concurrent record changes; the pure helper provides no transactional update.
Invalidate the affected original cache when necessary, then inspect the actual
detail images and return journey across ordinary reopens. Successful HTTP or
navigation assertions alone do not establish visible image correctness. Record
unmirrored asset families instead of claiming complete imagery from one screen.

When a permitted reference catalog is replayed in a local Firestore namespace,
use `scripts/firestore_reference_transfer.py` on its REST `fields` object.
It recursively changes only `referenceValue` entries under the explicit source
root. Literal strings, URLs, other-project references and original input stay
intact. Preserve the source capture separately; the output records changed field
paths. It performs no requests and grants no service access.

```sh
python /path/to/skill/scripts/firestore_reference_transfer.py \
  --input /private/source-fields.json --output /private/local-fields.json \
  --source-root 'projects/reference/databases/(default)/documents/' \
  --target-root 'projects/demo-local/databases/(default)/documents/'
```

The output wraps `fields` and `translated_reference_paths`; send only the fields
through a separately qualified local writer. Output files must not already exist.
This is a bounded reference translator, not a complete Firestore schema validator,
a query translator or proof of backend equivalence. Other-project references are
preserved and may remain unusable locally. It supports explicit default-database
roots only. Check that every required referenced record is present. Trace follow-up subcollection and collection-group queries as well; dated offers or inventory overrides may be stored outside their parent records.

Recover actual filters, ordering and cursors from the original query before
mirroring data. A denied broad listing does not establish that a narrower query
is denied; stale summary counts do not establish actual availability. Verify the
original complete screen journey after transfer, including detail records and
refresh. A populated listing alone does not establish accurate products, pricing,
checkout or redemption.

Use `scripts/firestore_dependency_audit.py` on a JSON list of captured REST
records before calling a catalog complete. It retains each typed reference's
source document and field location, reports missing same-project records and
separates external references. Conflicting captures fail rather than quietly
selecting a version. The audit makes no requests and does not authorize reads.
Review each missing record before acquiring it through the qualified boundary.

An active listing may omit an inactive child item that is still referenced by a
sellable bundle. Follow the explicit reference; do not apply the parent's
listing filter to every dependency. Audit again after acquisition, preserve
unavailable records, and compare the original detail journey. Zero missing
typed references does not cover string IDs, subcollection queries, stock,
server-calculated prices, checkout or issued entitlements.
