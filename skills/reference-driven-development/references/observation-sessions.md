# Task-owned Android observation sessions

`scripts/observation.py` adds a persisted session around an explicitly selected,
already installed Android application. It is an analyst tool, outside the strict
implementer boundary. No device is selected automatically; no APK installation,
emulator provisioning, snapshot restore or UI hierarchy adapter is supplied here.
Those runtime qualification steps remain separate required work.

## Normal entry

The agent creates a private config from inspected runtime facts. This example
uses a task-owned synthetic application with an explicitly exposed read-only
fixture file; arbitrary apps will need their own reviewed observation channels.

```json
{
  "task_owned": true,
  "ownership_reason": "isolated synthetic reconstruction fixture",
  "serial": "emulator-5554",
  "device_kind": "emulator",
  "package": "org.rdd.fixture",
  "component": "org.rdd.fixture/.Main",
  "reset": [{"kind": "stop"}, {"kind": "launch"}],
  "fixture": [{"id": "count", "argv": ["shell", "cat", "/fixture/count"],
               "operator": "equals", "expected": "0"}],
  "probe_wait_seconds": 10,
  "probe_interval": 0.1,
  "probe_stability": 2
}
```

For this example, the fixture app's launch resets count. Force-stop/launch does
not generally reset persistent application state. Define the reset sequence from
actual behavior and confirm it through independent fixture probes. `clear-data`
requires explicit `allow_clear_data: true`; task ownership alone does not enable
it. Do not use implicit state deletion as a substitute for a faithful lifecycle.

```sh
python3 /path/to/skill/scripts/observation.py --config /private/config.json \
  --session /private/session qualify
python3 /path/to/skill/scripts/observation.py --config /private/config.json \
  --session /private/session act --action /private/action.json --effect /private/effect.json
```

An action file is an object such as `{"kind":"tap","x":100,"y":200}`. The
effect file is a nonempty list of independently selected read-only probes, with
the same schema as fixture probes. Supported actions are launch, stop, explicit
clear-data, tap, swipe and back. Coordinates are checked against a new pre-action
capture. This guards geometry bounds, not semantic control identity or movement
between capture and input. Resolve those uncertainties with an appropriate
hierarchy/channel rather than claiming positional input is exact.

Optional `adb` selects the executable and `container` selects an explicit Docker
ADB route. `command_timeout` defaults to 30 seconds. Session configuration is
hash-bound: changing it requires a new session directory. Package version, ABI,
OS and fingerprint drift invalidate qualification. Supply `apk_sha256s`, a list
of independently inspected input hashes for the base APK and every installed
split, to require byte identity too. Qualification asks the selected device for
each installed APK's SHA256 and compares the complete digest multiset before
input. Failure or a mismatch blocks input and invalidates qualification. Hashing
large APKs costs time on every qualification; that cost is not cached away here.
Without this field, qualification establishes package metadata only. Device-query
integrity and acquisition/install receipts still require independent inspection.

## Readiness and uncertainty

Readiness, fixture and expected-effect probes poll read-only queries for at most
`probe_wait_seconds` (0..60). Each query's subprocess deadline is capped by the
remaining wait. `probe_stability` requires consecutive complete matching polls,
not one fleeting match. Timeout, malformed output or transport failure fails the
operation. Query polling is inspired by settled-state observation; it never
reissues the action. Custom shell probes require actual read-only review: the
small command-name filter is not a sandbox or semantic enforcement mechanism.

The retained mechanism is fresh consecutive observations rather than trusting
one pre-wait observation. The inspected
[Maestro implementation](https://github.com/mobile-dev-inc/Maestro/blob/51538ec1d3bb0c5eb84f29fee1687d0ccd2817c7/maestro-client/src/main/java/maestro/Maestro.kt)
applies this to refreshed element bounds after scrolling, with a last-known
position fallback. Our adaptation applies it to reviewed state probes and fails
when stability is unestablished; it does not implement element re-resolution or
that fallback. The delayed-effect and insufficient-stability tests exercise this
specific transfer, not Maestro's complete behavior.

The session persists uncertainty before sending input. A transport acknowledgment
does not establish its effect. Failed expected effects, capture failure or a
crash retain uncertainty, blocking another `act`. Inspect the journal before
choosing `reconcile` (prove the starting fixture) or `reset` (perform the declared
reset and prove that fixture). These are explicit operations, not automatic
retries. A successful unrelated capture cannot clear uncertainty.

Successful operations save fresh uniquely named PNG captures, byte hashes and
an append-only event journal. PNG structure/CRC is checked without a full pixel
decode; the comparator separately decodes image evidence. Time is host monotonic
observation completion, not device frame PTS or an atomic state/image sample.
Probe sequences are not transactional snapshots. Do not infer unavailable timing
or hidden-state properties from them.

When a settled screen is required, optionally set `capture_stability: 2` (1..20)
with `capture_wait_seconds` (default 5, at most 60) and `capture_interval` (default
0.1). Only consecutive newly acquired captures with identical PNG bytes count;
the previous session capture is never reused as the first matching observation.
Every attempt is retained, and the journal identifies the matching capture IDs.
Failure to establish stability fails the operation. This is deliberately an
exact-byte criterion, not perceptual similarity or proof that an animation will
never resume. State readiness alone may precede a window transition. Continuous
motion or signals require timestamped observation and a different property
contract; do not mask them just to make settled-screen qualification pass.

Scope this requirement to the actual observation point. For example,
`capture_stability_overrides: {"stop-after": 1, "launch-before": 1,
"reset-before": 1}` keeps settled app screens strict while recording the
launcher instantaneously during lifecycle transitions. A default whole-screen
settling rule can fail on an animated launcher. Overrides are explicit reviewed
configuration, included in session identity and capture receipts; they never
silently turn a failed stability check into a pass. Supported points are
`qualify`, `capture`, `reconcile`, `reset-before`, `reset-after`, and before/after
each supported action kind. State/effect checks remain required regardless.

Session commands use bounded subprocess output and process-group cleanup.
This is not an OS sandbox, and detached processes can escape a process group.
The session lock prevents concurrent adapter operations within one directory;
it does not reserve a device against other controllers. Keep the device task-owned
and exclude competing input. Full operation budgets and qualified device leases
remain integration work.

## Android guest loopback fixtures

An Android guest's `127.0.0.1` is the guest, not the host. For a task-owned
emulator and local fixture service, `scripts/android_loopback_fixture.py` wraps
one explicit ADB reverse route around a bounded command:

```sh
python3 /path/to/skill/scripts/android_loopback_fixture.py \
  --serial emulator-5560 --device-port 18089 --host-port 8089 \
  --timeout 60 --required-text FLOW_COMPLETED --output /private/new-receipt-dir \
  -- python3 /private/check_cached_response.py
```

The wrapper refuses conflicting routes, borrows matching routes without removing
them, and removes only a route it created. A command failure or missing completion
witness cannot pass. Use a discriminating command that checks the actual response
bytes or app transition; route presence alone does not prove reachability or
fidelity. Keep command logs private. Each ADB operation has a separate 15-second
bound; `--timeout` bounds the test command, not the entire fixture lifecycle.

Run under one exclusive device controller. Identical route replacement by another
controller cannot be distinguished. If route creation times out, inspect the
actual route listing before retrying: the wrapper will not remove an unconfirmed
route. Cleanup failure also requires inspection. This is neither whole-app network
isolation nor authorization to contact production services. See the official
[ADB command reference](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md).


For a cached HTTP object, `scripts/android_http_fixture_probe.py` makes one local
GET and compares the exact body length and SHA-256 with captured reference bytes:

```sh
python3 /path/to/skill/scripts/android_http_fixture_probe.py \
  --serial emulator-5560 --host 10.0.2.2 --port 8089 --path /fixture \
  --expected-bytes 11 --expected-sha256 CAPTURED_SHA256
```

Replace the digest with the actual captured object's SHA-256. This probe uses
Android Toybox `nc` and `head`, caps captured stdout at the expected body plus
16 KiB of headers plus one overflow byte, and bounds the host command. It requires
HTTP 200 and a matching Content-Length; redirects, chunked transfer and duplicate
headers are outside its contract. It emits `RDD_HTTP_BYTES_MATCH` only after exact
comparison. Use that marker with the route wrapper's `--required-text` when testing
an actual reverse route. The wrapper alone proves only route lifecycle.

The guest shell uses `pipefail` so a failed `nc` is not hidden by a successful
output limiter. A nonzero command exit rejects the run even if captured bytes
match. Keep command failure separate from a zero-exit response that fails HTTP
or integrity checks; neither alone identifies the underlying route defect.
Qualify both a known-good local response and a refused local connection on the
selected Android shell before relying on this distinction.

For the standard Android emulator, `10.0.2.2` addresses the host loopback. Compare
that path with guest `127.0.0.1` under the configured reverse route when diagnosing
empty responses. Do not infer a network fix from a newly visible image: memory or
disk caches, different URLs and independent UI transitions can confound it. Keep
source bytes, endpoint settings and the discriminating response receipt together.
The probe does not create routes, refresh remote assets or qualify WebSockets,
TLS, authentication, whole-app egress or native iPhone networking. A local service
can itself contact upstream systems; choose a fixture server that serves captured
bytes without forwarding. Sources: [emulator networking](https://developer.android.com/studio/run/emulator-networking-address),
[Toybox netcat](https://android.googlesource.com/platform/external/toybox/+/refs/heads/main/toys/net/netcat.c).
