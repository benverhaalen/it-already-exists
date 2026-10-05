# Reference-driven development

Use one umbrella skill. Load its supporting modules when needed.

## Install

Clone this repository. Copy the complete `skills/reference-driven-development`
folder into your harness's documented skill directory. Preserve all supporting
files. For Codex, use `~/.agents/skills/`. For Claude Code, use `~/.claude/skills/`.
Refresh the harness's skill inventory after installation.

Invoke `$reference-driven-development` with the goal, users and constraints.
Supply references if useful. The agent can also discover them. Installation does
not guarantee automatic selection or tool access.

To build a portable archive:

```sh
python3 tools/package_rdd.py --output /path/to/new-reference-driven-development.zip
```

The builder excludes caches, rejects links and unknown files, and refuses to
replace an existing output. Its manifest records file sizes and hashes.
Hashes establish content identity, not licensing, signatures or live activation.

## Use

The skill connects discovery, observation, synthesis, implementation and repair.
It retains useful differences and deferred alternatives. The agent maintains the
records; the user does not need to fill out internal schemas.

Before a consequential approach, inspect existing solutions, mechanisms,
bottlenecks and work-removing alternatives. When results fail, investigate causes,
test adaptations and reconsider the route. The workflow planner and compiler
carry this guidance into implementation context.

UI work uses real reference images, image-led exploration, precise typography and
component anchors, fresh-context critique and rendered journey checks. See
[UI continuity](../skills/reference-driven-development/references/ui-continuity.md).

Source-assisted work and strict independent implementation are separate access
policies. Strict work needs a verified implementer boundary. A fresh chat alone
is insufficient. See [clean-room boundaries](../skills/reference-driven-development/references/clean-room.md).

## Dependencies and limits

Core records, workflow and intake use Python's standard library. Pixel comparison
needs `scripts/requirements-comparison.txt`. Video inspection needs FFprobe and
FFmpeg. Android observation needs ADB and a qualified runtime. Isolated execution
needs Docker and a separately qualified inference adapter.

Some helpers use Unix facilities. Windows execution and arbitrary harnesses are
not qualified. The skill does not provide universal capture, enforce host tool
permissions or guarantee faithful reconstruction.

Run the tests from the repository root:

```sh
python3 -m unittest discover -s tests -v
```

Tests establish their declared mechanics and fixture behavior. They do not prove
universal speed, model quality, visual taste or arbitrary app equivalence.

## Maintain

Keep one canonical skill folder. Review changes, run relevant checks, commit and
push each coherent improvement. Retain reusable mechanisms and upstream source
attribution. Keep private evidence, source archives, credentials and project
narratives outside this repository.
