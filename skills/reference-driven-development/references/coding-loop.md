# Persistent independent coding loop

`scripts/coding_loop.py` extends the one-shot worker with durable source files,
action/observation history, reviewed command selection and resume. For local
inference, run it inside the separately qualified offline container; it is not a host sandbox. Include
its sibling `offline_worker.py`, `assets.py` and `process.py` in the image.
Tests exercise compiler failure and repair with scripted inference. Reviewed
external repair transport retains sources, history and spent budgets. Hosted
inference, runtime isolation and end-to-end fidelity need their own qualification;
a scripted test is not evidence of model quality or arbitrary reconstruction.

## Producing operation

Supply the independently reviewed behavioral specification, image-local backend
argv, reviewed local weights and a complete policy. The model sees the full
specification, current managed UTF-8 sources, prior actions and observations, and
the available command catalog. It chooses one JSON action per generation:

```json
{"action":"edit","files":[{"path":"app.py","content":"count = 0\n"}],"delete":[]}
```

Other actions are `{"action":"command","command":"build"}` and
`{"action":"submit"}`. Edits replace whole files; deletion names existing
managed files. Commands select exact reviewed argv, without model-authored shell
strings or substitutions. The catalog may provide build, test, runtime smoke
checks, or inspection tools. Those commands can execute generated code: their
access is enforced by the outer boundary, not by catalog membership. Review
toolchain and runtime dependencies before the run; no automatic downloads occur.

A policy example:

```json
{
  "commands": {"build": ["python3", "-m", "py_compile", "app.py"]},
  "max_steps": 30,
  "total_seconds": 1800,
  "step_seconds": 120,
  "max_output_bytes": 1048576,
  "max_context_bytes": 8388608,
  "max_files": 100,
  "max_content_bytes": 2097152
}
```

```sh
python3 /opt/rdd/coding_loop.py --root /work/implementation \
  --spec /spec/specification.json --model /models/reviewed.gguf \
  --backend /opt/rdd/backend.json --policy /opt/rdd/loop-policy.json
```

Use this command as the worker command in `cleanroom.py`; that adapter pins the
image, exports the reviewed spec, probes the boundary and records delivered files.
Do not mount the analyst repository, original app source, raw evidence journal,
or evaluator into the image. The loop's project is `/work/implementation/project`.
Its `loop.json` contains full accepted actions and observations, including source
contents. Keep that implementation-side record private.

## Lifecycle and evidence

Each generation reserves its maximum allowed runtime and spends a step before
launch. Finished steps refund unused time; interrupted steps retain the
reservation. Inference and command execution share the step allowance. Both
pipes are bounded; commands retain partial diagnostics with explicit timeout or
output-limit status. Command diagnostics are capped at the smaller of the output
budget and one eighth of the context-byte budget. Process-group cleanup does not
prevent a hostile child from escaping its group; the outer container lifecycle
must terminate remaining processes.

Use `--resume` only with the same root and inputs. The spec, policy and backend
are content-bound; weights are bound by path/size/mtime metadata, so model-content
identity still requires the separately reviewed image/model receipt. An uncertain
edit or command is never automatically replayed. Inspect the partial project and
actual process state, then create a new reviewed handoff; automatic reconciliation
is not supplied yet. The current outer Docker adapter exports partial files but
does not automatically re-import a prior project for resumed containers.

Full context remains available until its explicit byte bound. Overflow stops the
loop instead of silently summarizing away evidence. Retain the durable record and
construct a scoped, reviewed continuation when necessary. Automated semantic
condensation and repeated-no-progress detection are not supplied yet.

`submitted` means a nonempty managed source artifact was offered to the external
evaluator. Its digest describes managed UTF-8 source contents, not built APK
bytes. Compile checks, model statements and worker-authored tests do not establish
reference fidelity. Bind the actual delivered build into observation packets and
run the independent property contract. Return only reviewed behavioral
counterexamples through the reviewed persistent repair handoff below.
The separate approved-asset manifest identity is also bound when supplied; the
managed-source digest remains distinct from binary asset and delivered-build hashes.

## Reviewed assets in a persistent run

Both coding-loop and hosted-worker CLIs accept `--asset-manifest` and
`--asset-root`. Use the existing reviewed image/font/audio manifest shape from
[clean-room boundaries](clean-room.md). A new handoff snapshots every listed
whole file, verifies scope, format header and original hash, and copies only those
bytes into `root/project/assets/<manifest path>`. The original asset directory is
never a command mount or inference input. Rights and semantic source-independence
still require review; format/header checks do not certify either. Supply required
license and attribution notices in the reviewed delivery requirements.

Direct asset context contains approved relative paths, kinds, sizes and hashes,
not binary contents. Reviewed command diagnostics can still print asset content
into later history; review that catalog for the intended information boundary.
This is asset availability for construction, not automatic multimodal vision
input. Reserve the case-insensitive top-level `assets` namespace against
generated edits and deletion; inconsistent directory casing in the manifest is
rejected for portability. Approved assets consume the existing file/content
budgets alongside managed UTF-8 sources. They are not decoded as source files.

On resume or repair, supply the same manifest but omit `--asset-root`: validate
the persistent copies, with no dependence on the original folder and no silent
restoration. Manifest changes require a fresh handoff. Checks before inference,
action acceptance, commands, submission and repair reject missing/changed files,
extra entries, namespace case aliases and links. A command that changes approved
assets leaves an uncertain operation and cannot automatically replay. Submitted
runs are checked too, before their early return. Hash verification rereads the
bounded assets; its cost is not yet benchmarked on large asset sets.

The hosted Docker runner overlays those run-owned copies at `/work/assets` with
a separate read-only bind mount and excludes recursive host mounts. Before
inference it qualifies this actual nested layout: all bytes readable with matching
hashes; append, unlink, creation and directory rename denied. General boundary
and nested-asset qualification are preflight work outside the loop's step/time
budget, with separate bounded execution. Generic/local callbacks have drift
detection only unless their surrounding boundary separately enforces read-only
access; filesystem modes alone do not establish that protection.

Qualify asset transport by reading approved bytes, checking inventory hashes,
submitting, removing the original folder and resuming from retained copies.
Require nested write, deletion, creation and rename denials plus confirmed
container cleanup. This tests transport and lifecycle, not visual judgment,
rendered font identity or end-to-end fidelity.

The loop borrows small linear actions, persistent feedback and budgets from the
inspected [mini-swe-agent](https://github.com/SWE-agent/mini-swe-agent) mechanism,
and durable action/result grouping from
[OpenHands SDK](https://github.com/OpenHands/software-agent-sdk). It independently
implements the narrow operations above; neither reference's full capabilities nor
their performance claims have been reproduced. Loop metadata is writable by the
same container user as generated code, so it is diagnostic state, not tamper-proof
independent evidence. External receipts and acceptance remain outside that user.

## Reviewed external repair

The hosted adapter accepts `--resume` with all four repair arguments:
`--repair-report`, `--repair-review`, `--repair-guidance` and
`--candidate-artifact`. The artifact is a relative path inside the implementation
project. The report must describe failed or unresolved properties; its explicit
review binds the canonical report hash. Guidance contains `scope`, a list of
observable `behaviors`, and the same behavioral review declarations used by
`workflow.py review-export`. Keep reference source and raw observation files out
of both the guidance and exported discrepancies. Declaration validation cannot
prove semantic independence.

`scripts/repair.py` re-derives exported feedback from the reviewed report. Before
accepting a new repair, the loop verifies unchanged submitted managed sources and
the delivered file’s actual SHA-256 against the candidate artifact in that report.
The first repair binds the comparison contract; later repairs must retain it.
The original specification and policy remain bound. Guidance explicitly correcting
a prior implementation assumption supplements the specification in full history.
Only feedback and guidance enter model context; the full report remains broker-side.

Acceptance is persisted before inference. An identical accepted handoff can resume
a safe inference failure without duplicating feedback or rechecking an artifact
already rebuilt during that repair. It never resets steps or spent time. An
uncertain edit or command still blocks automatic resume. Submission remains a
candidate: independently install, observe and compare the rebuilt bytes before
claiming a successful repair.
