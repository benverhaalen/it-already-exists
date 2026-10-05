# Local reference-library fixture

An authored UI fixture for evaluating selection, editing, saving and recovery.
It is not the full product or a production service. No private reference images
or project narratives are included.

```sh
python3 examples/ui-reference-mesh/server.py --database /path/to/private/library.sqlite --port 8765
```

Open `http://127.0.0.1:8765`. The server binds to loopback. Source links are stored
as text, not fetched. SQLite stores committed records; browser local storage
retains drafts separately. Authentication and collaboration are not supplied.

For fault and timing checks, use a new database and browser session:

```sh
python3 examples/ui-reference-mesh/server.py --database /path/to/private/fault-library.sqlite --port 8765 --save-delay 1.5 --fail-first-save
```

The first valid save fails before mutation. Later saves have the declared delay.
These are evaluation faults, not product controls.

## Check the complete journey

- Edit and save through failure. Reload to recover the draft; independently query
  `/api/items` to check that committed state did not change. Retry successfully.
- Start saving snapshot A, then enter B before acknowledgement. A must commit
  while B remains a draft. Reload, recover B, then save it.
- Move collections and search a phrase present only in notes. Preserve query,
  selection context and per-record drafts.
- Reject invalid or credential-bearing URLs without committing them. Correct a
  new record, save, reload and retrieve it through search and its collection.
- In mobile navigation, test forward and reverse Tab boundaries, Escape and
  focus return. Inspect actual desktop/mobile screens and browser errors.

Backend tests cover mutations, conflicts and failure invariants. They do not
establish browser interactions, visual quality, accessibility or deployment safety.
Revision conflicts retain drafts; a full conflict-resolution UI is not supplied.

## Mechanism references

[Excalidraw local data](https://github.com/excalidraw/excalidraw/blob/a9d6507468559406ae242cc79175a93083d04fbe0/excalidraw-app/data/LocalData.ts)
informs the separation of local recovery from acknowledged persistence.
[shadcn sidebar](https://github.com/shadcn-ui/ui/blob/295a1f114a138f23b5dfee0e0c6812394dfeb90c/apps/v4/registry/new-york-v4/ui/sidebar.tsx)
informs distinct desktop navigation and mobile dialog behavior. Both inspected
sources are MIT. The fixture's acknowledgment comparison is an authored
adaptation, not a claim that this exact algorithm exists upstream.

The [component study](design/component-study.html) renders real Geist and
Fraunces assets. Full font and icon notices and provenance are retained.
See the [visual contract](design/contract.md) and [review procedure](design/image-review.md).
