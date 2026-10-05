# Hosted independent implementation

Use hosted frontier inference as the primary capable implementation route when
an existing authorized subscription is available. Local weights are optional;
clean-room access does not depend on where the model runs.

`scripts/frontier_worker.py` separates a trusted host broker from generated-code
execution. The broker sends only the reviewed behavioral specification, managed
implementation sources, diagnostic history and exact reviewed command catalog.
When reviewed assets are supplied, it also sends their bounded relative inventory;
the original asset root and binary contents are absent from that direct asset
context. Command diagnostics still enter model history, so reviewed commands may
deliberately expose asset content; this route does not filter that content.
Each generation is a fresh tool-free Claude print invocation. The model selects
the same edit/command/submit actions as the persistent coding loop. The host
writes bounded generated UTF-8 files; each command runs in a fresh offline Docker
container with only that implementation project mounted. Broker state,
credentials, evaluator files, reference evidence and the analyst repository are
outside the mount. The container receives no inference credentials or network.
Approved image/font/audio files are copied into that project and protected by a
separate read-only `/work/assets` mount, qualified against the actual nested layout.

## Qualified transport and limits

The current adapter uses existing Claude Pro/Max authentication, rejects API
authentication and supplies no API-key or paid-service fallback. It qualifies
Claude Code `2.1.286`, hashes the installed executable, and binds the exact model
into resume identity. Safe mode, restricted mode, no built-in tools, empty strict
MCP configuration, disabled skills, empty settings sources, replacement system
prompt and disabled session persistence are explicit invocation controls. It does
not resume the analyst conversation. Stock built-in plugin identifiers may appear
in initialization; custom plugin paths are rejected.

Initialization must report empty tools, MCP servers and skills and the approved
model. Tool-use content, server-tool usage, unknown lifecycle events, failure,
multiple results, duplicate JSON keys, malformed/truncated or oversized actions
are rejected. Thinking-token progress telemetry is discarded. The event checks
detect protocol drift; they do not sandbox the trusted CLI itself. Changing the
CLI version or profile requires a fresh review, not blindly updating a version
string. The caller still reviews specification meaning and source leakage.

Qualify inference, command isolation, build, installation, observation and repair
as separate boundaries. Test allowed project writes and denied host-file, socket,
credential and network access with independently chosen probes. Compare state,
trajectory, appearance and timing separately; matching settled pixels cannot
establish animation or latency equivalence. Retain protocol rejections in history.
A safe resume must preserve reviewed feedback and spent budgets.

Sol/Astra and other providers can use the same inference/execution split, but
their harness adapters are not qualified here. A fresh Codex chat or disabled
shell tool alone does not establish no retrieval or filesystem access. Inspect
and qualify its full supported control surface before adding it. Do not silently
fall back to the source-bearing host agent.

## Invocation and receipts

For Android builds, see the [source-free compiler recipe](../runtimes/android/README.md).
Provision a reviewed local image with Node for boundary probes and the intended
build tools; pin the full image ID. No automatic pulls or build-tool installation
occur. Supply the existing `workflow.py review-export` behavioral review shape
and the complete [coding-loop policy](coding-loop.md).

```sh
python3 /path/to/skill/scripts/frontier_worker.py \
  --spec /private/reviewed-specification.json \
  --policy /private/reviewed-loop-policy.json \
  --root /private/new-implementation-run \
  --image sha256:FULL_REVIEWED_IMAGE_ID \
  --model claude-opus-5-5
```

The loop's project is `root/project`; its host-only lifecycle record remains
`root/loop.json`. `root/broker-receipt.json` records harness/model/image identity,
request/response hashes, reported usage and completed command cleanup. Attempts
are persisted before inference; rejected responses retain their status and
unknown usage. Successful command receipts are saved by the next inference or
terminal cleanup. Resume preserves previous receipts and full loop feedback.
Interruption can still leave an uncertain operation; do not automatically replay
it. Receipts are diagnostics, not signed evidence or an independent fidelity
oracle. CLI cost estimates/token counts are not proof of subscription billing or
remaining allowance.

For a new run with reviewed whole assets, append `--asset-manifest
/private/approved-assets.json --asset-root /private/approved-originals`. On resume
and repair retain the same `--asset-manifest` and omit `--asset-root`; stored copies
are verified without rereading or restoring originals. Manifest identity and
the nested asset boundary participate in resume identity. Command receipts record
asset read-only protection, and `asset_qualification` records the real read/hash
and denied append/unlink/create/rename probes. See the [persistent asset lifecycle
and qualification limits](coding-loop.md#reviewed-assets-in-a-persistent-run).

Containers are unprivileged, use read-only root, dropped capabilities, no network
and bounded resources. Removal is confirmed after every command, including
timeout. The project directory is made writable for the container UID; use a
private task-owned run location. Loop state is not mounted into generated-code
execution. The broker process, Docker daemon and supported CLI are trusted;
model pretraining and image purity remain separate review questions.

The generic loop now accepts separate inference and command-runner interfaces;
hosted mode refuses a missing command runner and does not require a dummy model
file. Only the supplied adapter qualifies the operational access controls—an
arbitrary callback is not automatically a clean-room boundary. Generated outputs
remain untrusted for host execution. Observe the actual delivered build against
the independent property contract and return reviewed behavioral counterexamples.

The mechanism transfers explicit minimal actions and bounded persistent feedback
from the inspected mini-swe-agent workflow, with separation of model requests
from execution permissions. CLI controls follow the actual installed help and
[Claude CLI reference](https://code.claude.com/docs/en/cli-reference). Tool
inventory and actual fixture runs supply the qualification beyond documentation.

For a persistent repair of a submitted candidate, use the same inputs and root:

```sh
python3 /path/to/skill/scripts/frontier_worker.py \
  --spec /private/reviewed-specification.json \
  --policy /private/reviewed-loop-policy.json \
  --root /private/existing-implementation-run \
  --image sha256:FULL_REVIEWED_IMAGE_ID \
  --model claude-opus-5-5 --resume \
  --repair-report /private/external-report.json \
  --repair-review /private/report-review.json \
  --repair-guidance /private/behavioral-guidance.json \
  --candidate-artifact candidate.apk
```

See [repair bindings and lifecycle](coding-loop.md#reviewed-external-repair).
The original contract remains outside the worker’s execution mount; exported
feedback names its fixed hash and the actual delivered build’s hash. Preserve
old build snapshots and independently collected observation packets.
