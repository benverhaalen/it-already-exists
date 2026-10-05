# Surface-specific evidence preservation

Read when a document, recording, audio stream or physical interface is consequential to the result. These are conditional methods distilled from inspected OSS, not installed adapters or demonstrated reconstructions. Pin the original input and tool/configuration identity, preserve errors and omissions, and choose a probe that distinguishes the unresolved property. Use the host's available domain tools or build a bounded adapter when justified.

## Documents: structure and appearance are separate evidence

[Docling](https://github.com/docling-project/docling/tree/d6f03078ad364108df3e7e82e8f0dcc3fd7f39ea) and [docling-core](https://github.com/docling-project/docling-core/tree/61ab797b904eb68f79eb6229f021b3747099dec6), inspected at September 30 revisions, expose conversion status, errors, hierarchy and provenance. Relevant code includes Docling's `docling/datamodel/document.py` and core's `types/doc/common/reference.py`, `types/doc/items/table/table_data.py` and hierarchical document iteration. Both declare MIT licenses at these revisions; model dependencies have their own terms.

The producing operation is: hash the original; convert with recorded versions/options and bounded resources; retain native blocks, relationships, page/bounding-box spans and table coordinates beside conversion status; compare consequential reading order, merged cells and image placement against rendered pages; then formulate independently phrased requirements. Flattened Markdown can be useful retrieval text, but cannot replace structure or rendered evidence. Confidence and parse success do not certify visual fidelity. Preserve unsupported objects, OCR ambiguity and conversion failures as unknowns.

For controlled editing, inspect [python-docx](https://github.com/python-openxml/python-docx/tree/e45454602b53e8e572b179ccf1c91093ec9f4ed7), June 16, 2025, MIT. `src/docx/text/paragraph.py` shows that assigning paragraph text removes run formatting. `src/docx/document.py` documents that top-level paragraph/table lists omit certain revision and nested structures. These small differences directly affect an edit that looks superficially correct.

Inventory relevant native objects, styles, relationships, nesting and revisions; render the baseline; edit the smallest intended boundary; save a fresh artifact; reopen and render it; compare intended changes and unintended formatting, pagination, links and relationship loss. Use a narrow discriminating fixture or actual authorized artifact when evaluation is in scope. This library does not supply a renderer or preserve every OOXML byte by contract. Do not treat save success as a round-trip verdict.

## Recordings: preserve the actual time basis

[PyAV](https://github.com/PyAV-Org/PyAV/tree/b618b2d9802cb8c4ac368ff97fc2873de05aab89), September 30, BSD-3-Clause, distinguishes integer presentation timestamps and rational time bases in `docs/api/time.rst`; `av/container/input.py` explains seek behavior. Average frame rate and frame index cannot establish exact times in variable-rate media.

The [bounded video timeline helper](video-timeline.md) now inspects actual frame PTS and exports reviewed visible-transition brackets; it does not qualify device input latency.

Hash the recording; inventory streams and time bases; identify the relevant interval; seek to an earlier keyframe and decode forward; retain actual frame/audio timestamps and the decoding recipe. Compare a relevant sequential decode with the seek-forward result when relying on exact timing. Surface missing timestamps, discontinuities, dropped frames and synchronization uncertainty. Media time does not establish input latency, host/guest clock correspondence or capture completeness. A recording supports observed sequences; unseen interaction rules remain unresolved.

## Physical interfaces: decoded labels need raw measurements

[libsigrok](https://github.com/sigrokproject/libsigrok/tree/0bc2487778e660f4d3116729b6f4aee2b1996bb0), November 20, 2025, GPL-3.0-or-later, preserves session/sample/channel metadata in `src/session_file.c`. [libsigrokdecode](https://github.com/sigrokproject/libsigrokdecode/tree/71f451443029322d57376214c330b518efd84f88), October 1, 2024, supplies protocol decoders; inspect exact file terms, since the UART decoder header and repository COPYING differ in their stated licensing scope.

Within authorized safe measurement access, record device identity, channels, calibrated clock assumptions, trigger, stimulus and capture-loss evidence. Preserve raw sample intervals and versioned decoder parameters. Tie each interpreted event to those intervals and compare known framing against actual edges. The inspected UART decoder requires a sample rate, can fall back on its sampling-point parameter, and includes a dummy expected-parity value in a marked incomplete branch. Never promote such a fallback or placeholder into an observed device fact. Missing clock information, framing errors and disagreement are evidence to investigate.

Sampling metadata is not a calibration certificate; a plausible decoded packet is not physical equivalence. Missing hardware, safe stimulus or loss information is a precise capability/evidence gap, not permission to infer it from a simulation.

## Transfer boundary

Keep raw source-bearing native structures, recordings and hardware captures analyst-side when their content is restricted. Export only independently reviewed observable behavior, content/layout requirements and separately permitted data assets. Domain tools and their outputs do not automatically qualify as clean-room implementer inputs. Record a selected method as a contribution and transfer contract; use its producing operation and check in the actual task, rather than treating this reference list as proof of application.
