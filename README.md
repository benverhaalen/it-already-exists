# it-already-exists

Build software from useful parts of existing work.

Give your coding agent a goal. The agent finds references, studies their useful details, builds the result, and checks it.
You can also supply apps, websites, source code, images, or recordings.

Keep what works. Change what your project needs. Combine references with a clear purpose.

## Start here

1. Describe the result, its users, and its constraints.
2. Install the [reference-driven factory](docs/factory-installation.md) for Claude Code or Codex.
3. Use the [process](docs/architecture.md) to guide research and implementation.
4. Check the complete user journey, including errors and saved state.
5. Use the [repair guide](docs/failure-recovery.md) when results fail.

For app inspection, see the [runtime observation guide](docs/runtime-observation.md).
For independent implementation, see the [access boundaries](docs/surfaces.md).

## Status

The factory includes the RDD skill, pinned procedures, project controls, and Python tools for research, observation, comparison, and repair.
Automatic reconstruction of arbitrary apps is not complete.

Keep private source files, captures, and credentials outside this repository.

Project code and text use the [MIT license](LICENSE). Bundled assets retain their [original licenses](THIRD_PARTY_NOTICES.md).
