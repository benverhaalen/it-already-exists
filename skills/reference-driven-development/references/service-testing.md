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

## Bundled request guard

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
