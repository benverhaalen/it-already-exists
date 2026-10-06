# Preserve service behavior without production side effects

Separate the client, service contract and external authority. Screens and QR
rendering can match while the issuing ledger, payment processor or venue scanner
remains outside the reconstruction. Do not claim production validity from a
successful local checkout or a visually identical code.

Before running a money-connected reference, define the complete journey:
catalog → current quote → payment outcome → durable order → pass display →
validation → redemption → restart. Include changed prices, cancellation,
payment failure, timeouts, retries, expiration and duplicate redemption. Keep
original and candidate on the same controlled service state during comparison.

Prefer an operator-provided sandbox with legitimate test payment and issuance
credentials. Otherwise use live reviewed read-only discovery alongside an
isolated stateful test service for payment, orders, passes and redemption. That
service needs coherent identifiers, timestamps, failure outcomes and durable
state; a canned successful response is not a backend implementation. Never
create a production pass, consume real credit, redeem a real entitlement or
send a test QR to a real venue scanner. Test codes must use a separate namespace
and test verifier. Preserve the original client journey and appearance while
marking test provenance outside comparison captures.

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

Qualify account creation, duplicate/invalid input, verification, sign-in/out,
refresh, profile updates, switching accounts and restart persistence. Test the
original and candidate against equivalent fixture state. Auth emulation does
not implement the application's profile, wallet, order or entitlement service.
Recover those contracts separately and preserve relations using local IDs.
SDK routing may require source changes or instrumentation when release builds
strip emulator APIs. An emulator account alone is not integrated functionality;
unknown production rules and emulator differences remain explicit limits.

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
