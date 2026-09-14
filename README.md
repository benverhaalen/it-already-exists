# it-already-exists

**Give your coding agent a reference for what good looks like.**

You want to build a production app with Claude Code or Codex. Someone has already built the interaction you need: a thoughtful onboarding flow, a useful empty state, a search experience that remembers where you were, an editor that handles mistakes gracefully.

There is a lot to learn from the details of existing products. Your agent needs a way to inspect those details, understand which ones matter for your users, and carry them into what it builds.

`it-already-exists` is being designed to do that inside the project you are already working on. Give your agent a website, an APK, a recording, or an app on your computer. It should study your references, find others where the product needs more depth, and turn the useful parts into precise guidance for design, implementation, and verification.

The goal is a product with coherent taste, considered interactions, and fewer overlooked details—with less handholding.

## The idea

Start from things that already work. Understand what makes them work. Make deliberate changes for the product you are building.

The inspiration is the Virgil Abloh-style 3% rule: preserve the strength of something familiar and change it with purpose. Here, that is a creative principle rather than a numerical similarity target.

Combine references by the jobs they do: one might establish visual direction, another a navigation pattern, another recovery from an error. Resolve those choices into one product language, then inspect whether the implementation actually carries them through.

Study each choice in context: who it serves, what problem it addresses, which alternatives it competes with, and what would make it wrong for this project. Distinguish what the product demonstrates from documented design rationale and our own hypotheses.

## Intended experience

From your existing project, tell your coding agent something like:

> Use this app's editor as a reference. I like how it feels complete without being crowded. Find useful references for the parts we are missing and apply them to our product.

The proposed workflow is:

1. Understand your audience, product, constraints, and what each reference means to you.
2. Inspect supplied references and discover additional ones for specific gaps.
3. Extract evidence: appearance, interaction, state, timing, data, and edge cases.
4. Explain what to retain, what to adapt, and why it fits this project.
5. Give the coding agent focused implementation guidance and relevant evidence as it works.
6. Exercise the finished experience, find missing details, and repair them.

Default: adapt useful properties into a coherent original product. Faithful reconstruction is available as a separate intended mode, with strict clean-room and source-assisted workflows kept distinct.

## Status

Early development. This repository contains the product design, a generic Android observation recorder, and a runtime-observation workflow. The general analysis pipeline and installable agent integration remain unfinished.

The recommended starting shape is a command-line core with small Claude Code and Codex skill integrations. The existing coding agent is the main interface; a dedicated frontend is not part of the initial plan. Packaging and implementation details remain proposals until tested.

References can reveal good solutions, but they do not establish that those solutions fit a different audience or guarantee bug-free software. That is why application and verification are part of the product.

Target-specific experiments live outside this repository. Only reusable tools, abstracted process lessons, and synthetic examples belong here. See the [runtime-observation workflow](docs/runtime-observation.md) for acquisition readiness, evidence limits, and failure recovery.

## Design documents

- [Product brief](docs/project-brief.md)
- [Architecture and application mechanism](docs/architecture.md)
- [Understanding design choices in context](docs/design-reasoning.md)
- [Supported surface ambitions and evidence limits](docs/surfaces.md)
- [Runtime observation and evidence](docs/runtime-observation.md)
- [Compatibility recovery and testing constraints](docs/compatibility-recovery.md)
- [Worked example: preserving a draft through failure](examples/reference-to-implementation.md)
- [Worked example: transferring visual taste](examples/visual-direction.md)

## Android observation recorder

With an already running, task-owned emulator and ADB installed:

```sh
python3 tools/capture_android_reference.py \
  --serial emulator-5554 --output /path/to/private-evidence \
  --label initial-state capture
```

Use `--capture-method pull` for older ADB implementations and `--timeout 60` for a slower runtime. The JSON-lines journal distinguishes a completed input from a completed capture; failed operations record the last attempted step. Host elapsed time is not original-device animation timing.

If Android capture stalls, `--capture-method console` uses the emulator's own screenshot command. This requires a native emulator on the same host; it does not support containers or remote emulator hosts. The recorder verifies both the console acknowledgment and a fresh PNG, records the observer and hash, and retains failed attempts. Inspect the image before deciding whether another input is needed.
