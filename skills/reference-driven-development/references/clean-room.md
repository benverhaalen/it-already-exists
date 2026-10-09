# Strict independent implementation

Use this module before any strict clean-room handoff. Clean-room describes a controlled access process; it is not legal certification or a guarantee about model pretraining.

Declare the access policy first: what analysts may inspect, what implementers may receive, permitted assets and dependencies, and what reference behavior may be queried. Source-assisted work is a separate explicit mode; do not silently switch when isolation is inconvenient.

The analyst produces an implementation-independent behavioral export: inputs, outputs, preconditions, errors, ordering, persistence, timing bounds, observable cases, and uncertainty. Include required public interface names when necessary. Do not export copied code, decompilation, distinctive internal names, source-shaped pseudocode, or unnecessary implementation structure. Avoid both underspecified behavior and overspecified internal designs.

Review the export for source leakage, recognizable copied phrasing, private evidence, and links that bypass the boundary. Record export identity/version, reviewer, allowed material, withheld material, and unresolved observations. Keep restricted provenance on the analyst side; provide permissible evidence sufficient for the implementer's task.

Create an actual access boundary using supported sandbox, container, filesystem permissions, tool permissions, retrieval configuration, and network restrictions. Verify harmless allowed and denied access probes, including indirect source archives, tool outputs, retrieval, and inherited context. Do not fork source-bearing history into the implementer. A new chat, another role, or a different folder is not isolation by itself.

If the harness cannot enforce and demonstrate this boundary, continue analyst/specification work and report the missing boundary. Do not call an accessible same-host implementer clean-room isolated. Preserve the full target scope; uncertainty about access does not justify declaring reconstruction complete.

An independent comparator may observe both implementations and return behavioral counterexamples through reviewed exports. It should not return reference source patches to implementers. Version specifications and counterexamples; replay previously qualified cases after revisions.

Record observable coverage, tolerances, access tests, implementer inputs, and real costs. Passing cases establish those cases, not complete equivalence. Licenses, protected assets, patents, and other legal issues require separate consideration when relevant; this method does not resolve them automatically.

Public skill packages and demonstrations contain reusable instructions and synthetic fixtures. Keep target-specific restricted evidence and source archives outside them.

## Host-sandboxed agent implementers

When an agent CLI runs on the analyst's host under an OS sandbox instead of a
container, deny what the host shares by default, not just the answer directories:
the system temp directories (give each run its own `TMPDIR`), the parent of all run
workspaces (siblings created after a run starts are otherwise readable), harness
memory/session stores and inherited settings. Allow network egress to the model
endpoint only. Verify from inside the boundary with a planted canary in each denied
root, a write to the shared temp path and one ordinary tool call; a run with no
successful tool call is invalid, not a failed attempt. Afterwards scan each transcript
for paths outside the run's own workspace. In one study both the sibling-workspace
and shared-temp paths were open until a transcript review found them; neither showed up
as a failed run.

## Early offline Docker adapter

For hosted frontier inference, use the separately qualified
[hosted implementation adapter](frontier-worker.md). It keeps credentials and
tool-free model requests in a trusted broker and generated-code commands in
project-only offline containers. Local model provisioning is optional. The
offline adapter below remains a separate local-inference route.

`scripts/cleanroom.py` provides a narrow offline boundary for a reviewed local image that includes Node for probes and the intended offline worker/runtime. Pin its full image SHA256 ID; inspect image contents/history separately. No automatic image pull, credentials, original chat, retrieval service or network broker is supplied.

Run without a worker command to check harmless allowed/denied access. With a command, provide a fresh output directory. The helper validates the reviewed behavioral specification, exports it into a read-only `/spec` mount, optionally exports separately reviewed non-code asset snapshots into read-only `/assets`, mounts a fresh `/work`, and runs as an unprivileged user with read-only root, no network, dropped capabilities and bounded process/memory/time resources. It probes allowed specification reads/output writes, denied writes, unavailable host canary/socket and network connection before the worker runs. It preserves ordinary output files and hashes after rejecting symlinks/special files; inspect outputs before execution.

```sh
python3 /path/to/skill/scripts/cleanroom.py --image sha256:REVIEWED_IMAGE_ID --spec /private/reviewed-spec.json
python3 /path/to/skill/scripts/cleanroom.py --image sha256:REVIEWED_IMAGE_ID --spec /private/reviewed-spec.json --output /private/new-output offline-worker /spec/specification.json
```

The image must supply the worker and its inference runtime. The included `scripts/offline_worker.py` provides a bounded implementation entry point, described below; neither helper installs model weights or inference binaries. Hosted inference uses the separate broker adapter above; this adapter itself supplies no remote transport. Do not relax `network=none` merely to make a host harness work. This boundary cannot establish model pretraining independence, image purity, legal status or semantic freedom from copied implementation. It provides a mechanically probed offline execution path, not isolation for every harness.

Establish worker readiness before committing the implementation slice: identify its exact reviewed image/runtime, independent input contract and supported build tools. A boundary-only probe proves no worker capability. Missing worker/runtime is a resumable dependency blocker; retain the completed analyst export and its hash. On worker timeout, the adapter confirms container removal before returning exit 124 and preserves ordinary partial output with hashes. A partial artifact remains incomplete. Inspect a failed cleanup rather than assuming the worker stopped.

## Included independent offline worker

For multi-step source editing and reviewed build/inspection commands, see the
[persistent coding loop](coding-loop.md). Its isolated command lifecycle and
real-model readiness require qualification; the one-shot worker below remains
the asset-aware generation route.

Bake `scripts/offline_worker.py` and its sibling `scripts/assets.py` into the reviewed image with Python, Node for the boundary probes, an offline inference executable and appropriately licensed local model weights. The worker receives only the reviewed mounted specification, supplies a behavioral prompt to a fresh local inference process, and accepts a bounded JSON file map. It rejects duplicate keys, unsafe paths, collisions and oversized responses before writing ordinary source files. It clears inherited backend environment, limits time/output, terminates its process group and never executes generated code. Use it inside the container; it is not a standalone host sandbox.

Configure explicit argv in an image-local `backend.json`. The inspected [September 30 llama.cpp completion documentation](https://github.com/ggml-org/llama.cpp/blob/f7b384c1e5c5b2c5b321a4a7cefea04b15b54cb7/tools/completion/README.md) supports an offline completion process and schema-constrained output. A candidate configuration is:

```json
["/usr/local/bin/llama-completion", "--model", "{model}", "--file", "{prompt}", "--json-schema-file", "{schema}", "--predict", "4096", "--no-conversation", "--no-display-prompt", "--no-context-shift", "--offline", "--log-disable"]
```

This is an inspected CLI contract, not an executed model-quality result. Confirm the actual installed executable, model/template, context capacity and pure-JSON stdout before relying on it. Different models need different prompt/template settings. Do not silently truncate a specification to make it fit; split coherent behavioral slices with dependencies and retained acceptance criteria. Retain prior independently generated files on the implementation side when extending an artifact; include permitted prior work in a separately reviewed behavioral export or explicit worker adaptation rather than mounting the analyst workspace. This first worker produces one bounded source artifact per invocation; it is not an autonomous multi-tool coding agent.

Example invocation after provisioning and reviewing the image:

```sh
python3 /path/to/skill/scripts/cleanroom.py --image sha256:REVIEWED_IMAGE_ID --spec /private/reviewed-spec.json --memory 32g --cpus 8 --timeout 1000 --output /private/new-output python3 /opt/rdd/offline_worker.py --model /models/reviewed.gguf --backend-config /opt/rdd/backend.json --timeout 900
```

Choose resources for actual weights, context, hardware and budget; the sizes above are illustrative. Defaults are 1 GiB and two CPUs, suitable for boundary probes but potentially insufficient for coding models. The outer timeout must exceed the worker timeout. Resource limits are recorded in the boundary receipt. The output and inner worker receipt remain untrusted until the comparator inspects them and the actual requested journey. Invalid/truncated JSON, missing runtime or model failure yields a blocked implementation rather than fabricated files. No model download, fresh real-model execution or actual reconstruction was performed when developing this worker.


## Optional permitted asset transport

Keep the default specification-only boundary when no assets are needed. To preserve authorized images, fonts or audio, create an explicit analyst-side manifest and review each whole file for access scope, rights, source leakage and purpose. The manifest contains only relative exported names and hashes; never put analyst filesystem paths, reference archives, source code, source-bearing project files or URLs in it.

```json
{
  "scope": "target-task-scope",
  "reviewer": "identified reviewer",
  "rights": "Specific permission or ownership supporting these files",
  "limits": "Review scope, exceptions and unresolved legal or semantic questions",
  "files": [
    {"path": "images/logo.png", "sha256": "ORIGINAL_64_LOWERCASE_HEX_DIGEST", "kind": "image"}
  ]
}
```

Supported narrow data kinds are PNG/JPEG/WebP images, TTF/OTF/WOFF/WOFF2 fonts, and WAV/OGG/MP3 audio. SVG, HTML, scripts, compiled code, archives and original APKs are excluded from this initial transport; independently render/regenerate an authorized data asset when appropriate. Header and extension checks reject obvious mismatches but do not fully parse formats, detect hidden source/steganography, certify harmlessness or establish rights. Treat supplied bytes as untrusted data and review their actual meaning. Identified reviewer and rights declarations are declarations, not legal certification.

Pass `--asset-manifest /private/reviewed-assets.json --asset-root /private/approved-assets` to `cleanroom.py` before its worker command. Every manifest path is opened without following symlinks in the root or any descendant component, must be a regular file, and must retain descriptor identity and match its reviewed original hash. The helper snapshots only selected files into an owned temporary directory, capped at 1,000 files, 50 MiB each and 200 MiB total. It mounts that snapshot read-only at `/assets`; the private original root is never mounted. It exports the manifest at `/spec/assets.json` and probes reading its exact bytes and denying asset writes. The outer receipt pins manifest identity, scope and complete permitted inventory.

To use the included worker, add `--asset-manifest /spec/assets.json --asset-root /assets` after its other arguments. The model sees the approved names, kinds and hashes and may return `selected_assets`, an array of exact approved names. The worker copies only those whole reviewed files into delivered `assets/<name>` and instructs generated code to use those relative paths. It reserves the `assets/` output namespace, rejects unapproved selections and duplicates, and applies combined file/byte output bounds before saving any artifact. No generated artifact may depend on the unavailable original `/assets` mount after delivery. The comparator still checks actual code references, rendering and relocated playback. A copied asset establishes delivery, not correct use. Generated code is never executed by this helper.

The worker defaults to 100 output files and 2 MiB of generated-plus-copied contents. Increase `--max-content-bytes` explicitly for justified media requirements, up to the boundary's 200 MiB total cap; receipt files also count against the outer export limits. Model response bytes remain independently capped. Assets too large for declared limits yield a precise blocked result rather than partial silent copies.

For strict `workflow.py assess`, capture the manifest as ordinary observed evidence and set `clean_room.assets_evidence` to its journal ID and `clean_room.assets_root` to the original reviewed root. Assessment requires that evidence to be current, validates scope/review declarations and original file hashes, and matches the boundary receipt's complete exported identities. Canonical delivered `assets/<name>` files must match approved whole-file hashes. Keep both manifest and receipt in the private target workspace; changing source bytes or the reviewed manifest requires new captured evidence and a new handoff. This does not mechanically prove that a custom worker used assets correctly or that its model lacked prior source knowledge.
