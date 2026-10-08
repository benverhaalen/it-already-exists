# Explore once, verify independently, replay often

Load when repeated observation, UI driving or regression checks dominate reconstruction
cost. Use the same principles for non-UI artifacts when legal operations and observable
outcomes can be exposed. This is a researched transfer with a receipt-summary helper,
not an installed universal explorer or native-mobile action compiler.

## First principles and selection rules

A general agent repeatedly pays to interpret state, invent an action, execute it and
judge the result. Separate these jobs where the task permits it. Keep full observation
available outside the compressed decision input; reducing context is useful only while
preserving the distinctions needed for the decision and the verifier.

| Mechanism | Why it can help | Use where | Failure and discriminating check |
| --- | --- | --- | --- |
| Enumerate executable moves; model selects an ID | Converts unconstrained generation into a small choice problem; code supplies selectors and typed values | Ambiguous labels, menu choices, routing among observed alternatives | An omitted move is unreachable. Audit offered versus actually available actions, including virtualized lists and custom controls. Executable does not mean authorized or semantically safe; enforce that at execution |
| Compact task-specific observation | Avoids repeatedly sending entire source trees, DOMs or screenshots | Well-described controls or bounded classification with relevant state exposed | Two different hidden states may look identical. Add history or a targeted probe when they require different next actions; retain original evidence for escalation |
| Read declared option scores directly | Avoids autoregressive answer generation and JSON parsing | Qualified categorical decisions on a model/backend that exposes logits | Verify single-token labels, token-boundary stability and no option collisions. Scores are conditional on offered options; qualify order sensitivity, abstention and held-out errors before using thresholds |
| Reuse an exact inference prefix | Amortizes processing one large state over multiple questions | Several independent criteria over the same unchanged evidence | Require exact token-prefix equality, correct branch positions and isolated cache copies. Include copy/padding costs and compare uncached decisions; an application replay cache is a different mechanism |
| Deterministic routing before inference | Known graph paths need no language judgment | Stable navigation to a known destination, exact recorded operations | Route success may land on the wrong object. Bind object identity, reset state and postconditions; do not merge all URLs or screens with the same shape |
| Compile successful exploration into replay | Amortizes inference and inspection across subsequent runs | Repeated regression journeys on a stable controlled fixture | Discovery success does not establish emitted locator correctness. Replay from reset, require unique targets, preserve assertion semantics and transient negative observations |
| Policy separate from oracle | A model's confident action or DONE answer cannot certify success | Every fidelity claim | Code can implement a weak oracle perfectly. Derive properties independently from the reference; check appearance, hidden state, persistence and timing when consequential |
| Speculate on the next decision | Overlaps inference with settling, reducing serial latency | Read-only decision computation where stale answers can be discarded | Equal decision input is only a reuse condition, not complete state equivalence. Recheck executable target/preconditions after settling; never speculate side effects. Count discarded inference and disable when its cost or serialization dominates |
| Generate legal state sequences and shrink failures | Finds history-dependent defects that a happy path misses; minimizes diagnosis context | Undo, reopen, cancellation, retries, lifecycle and stateful adapters | A wrong transition model misses real behavior. Validate against reference traces, enforce reset and retain external effects; reproduce minimized failures against both artifacts |
| Seed defects into controlled candidates | Tests whether the oracle detects plausible errors rather than merely accepting a good run | Important invariants and visual/behavioral checks | Equivalent or invalid mutants distort scores. Keep survived, uncovered, invalid, skipped and pending cases visible; distinguish timeout detection from precise semantic diagnosis |

A decision model's confidence is relative to the offered choices. It is not calibrated
proof of correctness and cannot repair missing options. Use small models for bounded
proposals after fresh-case qualification; use richer observation and frontier reasoning
when ambiguity, unavailable controls or hidden state defeats that formulation. No local
model download is required by this method.

Compilation pays off when discovery + emission + reset + replay verification + expected
repair cost is less than repeatedly driving the same journeys. Measure that crossover;
short-lived, frequently changing flows may favor direct exploration. A graph shortcut
is useful for reaching a test subject but cannot qualify the interactions it bypasses.
Similarly, an API test can cheaply diagnose semantics without certifying rendered UI.

## Inspected seed and recursive branches

The initial seed was [QuickE2E 0.5.0, revision
98f74b6](https://github.com/dmoka/quicke2e/tree/98f74b6ceb44e8eb68c0bc176e522983639b9521),
inspected October 8, 2026. This includes October work and is not a September-only survey.
Its MIT source separates candidate generation, model selection and code verification.
`src/loop.mjs` compares exact serialized decision inputs before accepting speculative
answers; wide candidate sets use heats with an abstention option instead of silent
truncation. These preserve offered options, not globally optimal choice quality.
`codegen/verify-locators.mjs` measures unique locator binding in a replay walk;
`codegen/codegen.mjs` retains the explorer's visible-text recorder and transient checks.
The replay walker itself handles only fill/click in that inspected path: qualify other
operations separately instead of assuming all emitted operations were measured.

Its [raw launch-task runs](https://github.com/dmoka/quicke2e/blob/98f74b6ceb44e8eb68c0bc176e522983639b9521/bench/results/launch-task.json)
report five runs per arm on one ticket-purchase fixture. The hosted decision arm has a
3.741-second median versus 25.293 seconds for the general agent arm. These are author
measurements, not a reproduced reconstruction benchmark. Reported local zero API cost
excludes hardware, setup and operating cost. Root ran the model-free core/route suite:
49 tests passed using Playwright 1.63.0; no model-driven performance trial was run.

The code inspection opened these subsequent seeds; each has a distinct job:

* **Cheap categorical decisions → token readout, prefix reuse and calibration.**
  QuickE2E's local scorer references SemIf. [SemIf direct scoring, revision
  23cf1f3](https://github.com/TheoLeeCJ/SemIf-OpenJev/blob/23cf1f39fc9534fe81437200959b6dfc7106e45a/src/semif_phase1/direct.py)
  checks exact single-token answer slots, collisions, append-boundary tokenization and
  rejects overlong inputs rather than truncating. Its [MLX serial scorer](https://github.com/TheoLeeCJ/SemIf-OpenJev/blob/23cf1f39fc9534fe81437200959b6dfc7106e45a/src/semif_phase1/mlx_backend.py)
  reuses only an exact token prefix and copies the retained cache before each branch,
  recording copy cost separately. This is inference reuse, not proof that app state is
  unchanged. Its [calibration layer](https://github.com/TheoLeeCJ/SemIf-OpenJev/blob/23cf1f39fc9534fe81437200959b6dfc7106e45a/benchmarks/calibrate.py)
  fits a positive temperature on labeled data with group-disjoint evaluation;
  temperature scaling changes confidence, not the selected argmax or its accuracy.
  Preserve unsupported/soft-label rows outside that calibration claim. MIT; source
  inspected, no model loaded and no latency or decision-quality result reproduced.
* **Replay drift → caching contracts.** [Stagehand cache service, revision
  771f2da](https://github.com/browserbase/stagehand/blob/771f2da06c2b651e7f5200bcaece4721a7c5889c/packages/extension/services/cacheService.ts)
  separates hit, miss, unusable-value and replay-failure paths. Its local HTTP
  integration tests check usage metadata across the wire, rather than inventing token
  savings. In this inspected version key computation and storage are server-side;
  the repository alone does not reveal the complete server cache-key algorithm.
  Transfer observable cache decisions and explicit invalidation, not presumed key
  completeness. MIT; source inspected, suite not run.
* **Browser action space misses native controls → native replay and screenshot
  contracts.** [Maestro Orchestra, revision
  c73b120](https://github.com/mobile-dev-inc/maestro/blob/c73b1202c7c83b9d2e8a60c39ea0ad53039ec507/maestro-orchestra/src/main/java/maestro/orchestra/Orchestra.kt)
  dispatches declarative actions/assertions; [ScreenshotMatch](https://github.com/mobile-dev-inc/maestro/blob/c73b1202c7c83b9d2e8a60c39ea0ad53039ec507/maestro-orchestra/src/main/java/maestro/orchestra/ScreenshotMatch.kt)
  uses the same match metric for its verdict and reported percentage, rejects size
  mismatch and supports region checks through the caller. Its RGB tolerance is not
  our RGBA comparator's metric; transferring thresholds between them would be wrong.
  Use a native driver where qualified; Flutter semantics and canvas remain
  observation questions. Apache-2.0; source inspected, native suite not run.
* **Healing can hide loss → fixed denominator and mutation probes.** The inspected
  [Playwright healer](https://github.com/microsoft/playwright/blob/main/packages/playwright/src/agents/playwright-test-healer.agent.md)
  permits `test.fixme()` when it believes a correct test cannot pass. Useful diagnostic
  tools do not make a skipped requirement satisfied. [Stryker's states and
  metrics](https://stryker-mutator.io/docs/mutation-testing-elements/mutant-states-and-metrics/)
  distinguish survived, uncovered, invalid and ignored mutants; its timeout counts
  as detected. Retain these distinctions and investigate whether important seeded
  errors are actually diagnosed. Do not quietly weaken reference assertions to heal.
* **One passing route misses history → stateful differential exploration.**
  [Hypothesis stateful source, revision
  ca2a4c6](https://github.com/HypothesisWorks/hypothesis/blob/ca2a4c6e3c6b979d9fbb5ef9db614885a736d2aa/hypothesis/src/hypothesis/stateful.py)
  executes initialization, rules with preconditions and repeated invariants.
  [Its documentation](https://github.com/HypothesisWorks/hypothesis/blob/ca2a4c6e3c6b979d9fbb5ef9db614885a736d2aa/hypothesis/docs/stateful.rst)
  demonstrates comparing an implementation to a simple state model and reducing a
  failure to a short reproducible program. For RDD substitute independently observed
  reference behavior where available; a candidate-derived model is not an independent
  oracle. MPL-2.0; source inspected, no runtime claim.

No upstream implementation was copied into the trial helper. Strict clean-room builders
receive reviewed behavioral requirements and counterexamples, not this source-inspection
packet. Follow [clean-room boundaries](clean-room.md) for actual separation.

QuickE2E's own limits matter: no native-mobile adapter, canvas action discovery, general
scroll action or multi-tab flow; opaque-overlay occlusion is not checked by text success.
DOM-semantic success therefore cannot establish screenshot fidelity or universal
reconstruction. Retain the full [comparison](comparison.md) checks and native probes.

## Apply and measure the composition

1. Freeze a representative complete journey, required properties, fixture/reset and
   reference version. Include cases that distinguish plausible wrong implementations.
2. Prefer existing deterministic probes for known boundaries. Explore only the unknown
   route or next action. Preserve critical observations outside any compressed model
   state, and enforce action authority independently of model selection.
3. Compile a passing route where an adapter exists. Independently replay it from reset;
   preserve object identity, unique locators, transient negatives and the same oracle.
   Failures select diagnosis, richer observation or bounded re-exploration, not automatic
   assertion changes. Inspect both the resulting test diff and required-case ledger.
4. Add stateful sequence generation or targeted mutation only where it resolves a real
   fidelity uncertainty. Reproduce minimized discrepancies before repair. Run the fixed
   regression corpus after meaningful changes and retain all unresolved cases.
5. Compare matched fresh cases/repeats: full required-property results, time to first
   useful failure, total completion time, model calls, tokens, paid inference, setup,
   replay and repair. Keep unknowns unknown. A cheaper route that drops a critical
   property fails the intended improvement, even if its aggregate pass rate rises.

`scripts/reconstruction_trials.py` summarizes supplied paired receipts. Its input has
`cases` mapping case IDs to required property ID lists, and `runs` with `case`, `repeat`,
`strategy`, `evidence`, `properties` and `phases`. Property statuses are `pass`, `fail`,
`not_tested` or `skipped`; every required property must remain present. The seven phases
are `research`, `setup`, `build`, `exploration`, `replay`, `verification`, `repair`; each
contains `seconds`, `dollars`, `tokens` as nonnegative numbers or null. Supply explicit
zero for an unused phase and null for unknown cost. Include failed attempts with the
same repeat pairing; do not discard failed discovery or repair before producing receipts.

Run `python scripts/reconstruction_trials.py PRIVATE_TRIALS.json --baseline baseline
--candidate candidate --output PRIVATE_REPORT.json`. It rejects unpaired runs and changed
denominators, reports regressions and new passes individually, preserves unresolved
statuses and includes every supplied attempt's phase costs. Seven synthetic tests
qualify that bookkeeping; neither receipts nor evidence links are independently audited.
The helper cannot detect omitted attempts or establish complete fidelity, significance
or an automatic winning strategy.

Continue seeded research from the actual failure: missing legal actions → driver and
semantic-tree producers; stale replay → identity/precondition and cache contracts;
false pass → oracle mutation and visual occlusion; expensive diagnosis → minimal state
sequences and bounded failure traces. Stop convergent branches when another inspection
is unlikely to change the next experiment. Retain conditional alternatives and minute
differences, with a revisit trigger, rather than forcing every mechanism into every task.
