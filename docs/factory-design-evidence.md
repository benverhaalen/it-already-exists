# Evidence behind the factory proposal

This is a condensed design rationale for [factory evolution](factory-evolution.md).
The research inspected the existing helpers and dependent primary-source leads.
It does not demonstrate an implemented integration or a speed, cost or fidelity
advantage. Each numbered layer below follows a question raised by the preceding
finding; counting sources is not an effectiveness measure.

## From research context to consequential investigation

| Layer | Inspected mechanism and limitation | Question or decision it changes |
| --- | --- | --- |
| 1 | [STORM question generation](https://github.com/stanford-oval/storm/blob/fb951af7744dab086e34962e9bc6fe878e145f83/knowledge_storm/storm_wiki/modules/knowledge_curation.py) uses a bounded dialogue while retaining richer search material separately | Retaining a source does not mean the next question consumed it; keep recoverable evidence and explicit projections |
| 2 | [MemGPT](https://arxiv.org/html/2310.08560v2) couples bounded context with external recall; retrieval can still miss relevant messages | Preserve original responses and qualify retrieval/application, rather than trusting a mutable preference summary |
| 3 | [Doyle's truth maintenance](https://www.ijcai.org/Proceedings/79-1/Papers/004.pdf) retains supports and absence conditions; belief status is not truth | Keep reasons, exceptions and dependencies so a correction can reopen conclusions without becoming universal |
| 4 | [Reiter's diagnosis](https://cse.sc.edu/~MGV/csce580f12/gradPres/reiter-diagnosis.pdf) selects disconfirming observations; a measurement can introduce new diagnoses | A discriminator must permit an explanation outside the initial candidate list |
| 5 | [Dewey's inquiry](https://brocku.ca/MeadProject/Dewey/Dewey_1910a/Dewey_1910_f.html) makes locating the difficulty investigative | Preserve the outcome while changing the explanation and route; small contextual differences can defeat an analogy |
| 6 | [Modern Bayesian experimental design](https://arxiv.org/html/2302.14545v2) distinguishes utilities and sequential decisions; within-model information gain can miss model failure | Select research by the decision it can change; do not invent calibrated numerical utility for arbitrary product questions |
| 7 | [Experimental design with discrepancy](https://arxiv.org/html/2304.07949) separates information efficiency from mismatch detection | Distinguish questions that rank known alternatives from questions that challenge the frame |
| 8 | [ASReview's consuming selection code](https://github.com/asreview/asreview/blob/79d568212b2b0a78f9fd7be3c5117dfb890489f9/asreview/models/queriers.py) shows why a named mixed-ranking policy needs behavioral inspection | Test the actual exploration operation and admitted source pool; configuration and uniqueness checks do not establish coverage |
| 9 | [GEPA's candidate selector](https://github.com/gepa-ai/gepa/blob/462e437a09be67d2acb59564cc0ea59132f5777c/src/gepa/strategies/candidate_selector.py) and engine use evaluated traces and case-level Pareto candidates | Retain conditional method specialists; separate learning feedback from later promotion evidence |
| 10 | [Adaptive holdout reuse](https://proceedings.neurips.cc/paper_files/paper/2015/file/bad5f33780c42f2588878a9d07405083-Paper.pdf) requires explicit statistical conditions and exposure control | A repeatedly consulted final evaluator becomes development feedback; track exposure rather than asserting independence |
| 11 | [MT-Bench judge analysis](https://arxiv.org/html/2306.05685v4) tests order, verbosity and reasoning failures | Calibrate critics on subtle failures, inspect references first and use actual execution; agreement alone does not establish quality |
| 12 | [AI Agents That Matter](https://arxiv.org/html/2407.01502v1) distinguishes downstream cost and generality from model proxies | Compare complete journeys, including failed attempts, environment state and human repair, on tasks matching the claim |

The adopted connection is an extension of existing research episodes: parent
finding, consequential question, actual inspection, scoped conclusion and changed
consumer. Offline method learning remains conditional. Neither a fixed exploration
ratio nor a source-count quota is adopted. Conceptual papers provide hypotheses
and constraints, not measured factory gains.

## From early use to safe continued construction

| Layer | Inspected mechanism and limitation | Question or decision it changes |
| --- | --- | --- |
| 1 | Existing full acceptance covers the whole current objective; preview declarations do not demonstrate use | Add nonterminal readiness without weakening the full obligation set |
| 2 | [Unreal chunking](https://dev.epicgames.com/documentation/en-us/unreal-engine/cooking-and-chunking?application_version=4.27) follows primary and secondary asset dependencies | A usable journey needs its prerequisites; a menu or progress percentage is insufficient |
| 3 | [Nix generations](https://nix.dev/manual/nix/2.32/package-management/profiles) separate immutable builds from atomic activation | Keep stable and development artifacts separate with one authoritative release descriptor |
| 4 | [SQLite WAL](https://sqlite.org/wal.html) provides bounded snapshot/concurrency behavior | Artifact immutability does not protect mutable data, backups or cross-host use |
| 5 | [Prisma expand/contract](https://www.prisma.io/docs/guides/database/data-migration) separates coexistence and migration | Qualify semantic backfill and retirement; old code can misinterpret new data even when storage remains readable |
| 6 | [PostgreSQL isolation](https://www.postgresql.org/docs/current/transaction-iso.html) distinguishes snapshots from serializable invariants | Enforce invariants at the real transaction boundary, including appropriate retries |
| 7 | [DBOS checkpoint ownership](https://docs.dbos.dev/explanations/concurrent-executions) fences its own checkpoint writes | Reuse durable execution when recovery warrants it; identify its actual effect boundary |
| 8 | [Temporal activity semantics](https://docs.temporal.io/activity-definition) and [DBOS steps](https://docs.dbos.dev/python/tutorials/workflow-tutorial) expose retry boundaries | A durable runtime does not make arbitrary external effects exactly once; use receiver idempotency or reconciliation |
| 9 | [Bazel Skyframe](https://bazel.build/reference/skyframe) requires registered inputs for sound incrementality | Reuse completely captured results; hidden reads require wider invalidation |
| 10 | [miniAdapton](https://arxiv.org/html/1609.05337v1) recomputes demanded affected results through its mutation interfaces | Prioritize the usable closure without claiming arbitrary model judgments have incremental consistency |
| 11 | [Git expected-old reference updates](https://git-scm.com/docs/git-update-ref.html) reject stale writes; multiple refs have reader caveats | Promotion needs target-level freshness and a coherent descriptor, not just a journal lock |
| 12 | [Debezium outbox routing](https://debezium.io/documentation/reference/stable/transformations/outbox-event-router.html) uses stored identities and ordering keys | Reconcile committed effects with lost publication/replies; do not require Kafka for local products |
| 13 | [Temporal message passing](https://docs.temporal.io/develop/typescript/workflows/message-passing) distinguishes queued signals, processed updates and handler lifecycle | A captured correction is not an adopted correction; connect its authority to actual promotion and continuing work |

The last question needs a host/project experiment: can correction and cancellation
actually revoke stale effect authority at the target? Until that route is qualified,
the adapter must report its unsupported boundary. The full older Adapton paper was
not available during this inspection; the complete miniAdapton implementation was
read instead. Its guarantees are restricted to its tracked computation model.

## From proof to a practical semantic core

This chain asks whether an existing language, shared representation or small
custom language would improve actual factory decisions. Runtime authority,
representation and proof tooling are separate choices.

| Layer | Inspected mechanism and limitation | Question or decision it changes |
| --- | --- | --- |
| 1 | [Lean proof validation](https://lean-lang.org/doc/reference/latest/ValidatingProofs/) distinguishes valid derivation from statement meaning and transitive assumptions | Keep source-grounded obligations outside the producer's editable acceptance target |
| 2 | [Comparator's pinned comparison](https://github.com/leanprover/comparator/blob/ca04cfc72b550331658ec314bf47685281bfd4bf/Comparator/Compare.lean) checks declaration dependencies; allowed definition holes relax value equality | Protect the contract's definition closure and inspect escape hatches, not just theorem names |
| 3 | [TLA+ refinement](https://lamport.azurewebsites.net/tla/tutorial/session11-1.html) defines explicit mappings between models | Separate intent-to-contract review, model refinement and actual runtime correspondence |
| 4 | [TLC's successor exploration](https://github.com/tlaplus/tlaplus/blob/94d0c5070852b37b801bb8998c436383ab7ee37b/tlatools/org.lamport.tlatools/src/tlc2/tool/ModelChecker.java) follows configured actions, constraints and checking paths | Preserve finite bounds, fairness and progress scope rather than claiming an unbounded implementation proof |
| 5 | [PObserve's log bridge](https://github.com/p-org/P/blob/260da928f67569ca7a8c0039a02d0bad7cde6096/Docs/docs/advanced/pobserve/logparser.md) needs a parser; the inspected example drops unsupported/malformed shapes | Qualify actual event completeness, identity and ordering; this example is not a universal PObserve defect |
| 6 | [Dafny's assumption auditor](https://github.com/dafny-lang/dafny/blob/5f717bf447b19d38cad1b69b1bf9a9f102feccfb/Source/DafnyCore/Auditor/Assumption.cs) exposes external contracts and verification exemptions | Source contracts reduce drift but need explicit external and compiler boundaries |
| 7 | [Z3's query semantics](https://microsoft.github.io/z3guide/docs/logic/basiccommands/) expose sat, unsat and unknown | Check assumption feasibility and reachable positive cases; contradictory assumptions can make an implication vacuous |
| 8 | [Hypothesis stateful execution](https://github.com/HypothesisWorks/hypothesis/blob/82fa40ada6bc83480a746890a40bb3d708ba8f03/hypothesis/src/hypothesis/stateful.py) exercises real adapters and shrinks sampled counterexamples | Test correction/retry/recovery sequences against existing Python before deciding a replacement language is necessary |
| 9 | [MLIR's verifier](https://github.com/llvm/llvm-project/blob/ce2a4984a3f43327a2b7c40baa74907bc10eb899/mlir/lib/IR/Verifier.cpp) checks structural and dialect invariants | Preserve meaningful typed nodes through adapters; well-formedness alone does not prove semantic lowering |
| 10 | [XLA architecture](https://openxla.org/xla/architecture) optimizes operations in a defined numerical domain | Give the controllable factory core explicit operation semantics while leaving discovery and taste open-ended |
| 11 | [StableHLO semantics](https://github.com/openxla/stablehlo/blob/ac08895509c616ed5a11a1b31ef96ff28c6a1e90/docs/spec.md) include implementation-defined calls and numerical ordering limits | Represent unsupported, unknown and externally assumed boundaries without upgrading them into verified outcomes |
| 12 | [Alive2 translation validation](https://github.com/AliveToolkit/alive2/blob/5d0eb277235b73f71000501c3a4f5ab9b2586915/README.md) checks individual transformations with bounded support | Consider independent checks of produced adapter operations before attempting a universally verified compiler |
| 13 | [CUE validation](https://github.com/cue-lang/cue/blob/a4f52c2332e4b8749cb40efc3550b0aaf10e60d1/cue/types.go) permits incomplete values by default; Concrete/Final strengthen different checks | Distinguish provisional interpretation, complete executable input and conflicting requirements; compare against ordinary typed records |
| 14 | [Cedar's Lean semantics](https://github.com/cedar-policy/cedar-spec/blob/6d7fb269d5eec6ce4ae1d4aff9794feba0c0d5a9/cedar-lean/Cedar/Spec/Authorizer.lean) and differential tests connect a narrow policy model to an implementation | A small authoritative decision language is a serious alternative; the surrounding runtime must enforce its decisions |
| 15 | [AWS formal engineering abstract](https://repositum.tuwien.at/handle/20.500.12708/219530?mode=full) describes a portfolio of models, tests, faults and trace checks | Reuse one scoped property across suitable tools instead of forcing every domain through one language |
| 16 | [LPIPS research](https://openaccess.thecvf.com/content_cvpr_2018/papers/Zhang_The_Unreasonable_Effectiveness_CVPR_2018_paper.pdf) targets perceptual similarity, not quality assessment | Similarity can diagnose faithful reconstruction; taste and interaction need actual artifacts and judgment |
| 17 | [Aria/HHL](https://arxiv.org/html/2607.06341v1) describes hook/workflow syntax lowered to Python while a general agent solves whole proof obligations | Keep a small stable acceptance/effect core and replaceable capable generators; custom syntax must earn its additional cost |

Compare existing typed records plus an explicit interpreter, an executable
Lean-embedded admission/acceptance model, and a restricted custom representation
on the same correction-versus-promotion journey. Python can retain journal and
effect adapters in all three. Check actual rejection, runtime correspondence,
diagnostic quality and whole-task cost. Cedar supports taking the custom-language
case seriously; it does not establish that a factory DSL will outperform Python.
Lean need not be only an external checker.

No proof replay, compiler integration, solver campaign or comparative prototype
was run. The AWS source was a one-page talk abstract, not a full engineering
evaluation. Aria's campaign results remain author-reported; its compiler source
was not inspected. Neither supports a measured product-factory superiority claim.

## UI references have concrete jobs

The UI process begins with actual human-designed reference pixels and early
image-led system exploration. The following mechanisms support realization and
verification; none chooses the visual direction or proves taste.

| Reference | Job in the producing path | Required boundary |
| --- | --- | --- |
| Native Codex and [CLI image inputs](https://learn.chatgpt.com/docs/developer-commands?surface=cli) | Carry reference images into generation, critique and implementation; Claude can hand off through the installed CLI | Actual images and outputs must be available on that invocation; a permission flag is not evidence of tool capability |
| [assistant-ui](https://github.com/assistant-ui/assistant-ui) | Investigate mature task behavior such as reader-aware chat scrolling | Transfer only relevant observed behavior; a screenshot does not establish it |
| [Argos](https://github.com/argos-ci/argos) | Study baseline eligibility and rejection rather than accepting every new screenshot | Match state, scope and accepted baseline; automated comparison does not decide taste |
| [Storybook portable stories](https://storybook.js.org/docs/api/portable-stories) | Reuse representative component states and interaction examples | Restore the real application context for complete-journey verification |
| [Playwright screenshots](https://playwright.dev/docs/screenshots) | Capture coded renders at controlled viewport/device scale | Fonts, content and state must be real and stable; CSS-scale equality is not behavioral or sensory equality |
| [Superdesign's pinned model-design guidance](https://github.com/superdesigndev/superdesign-skill/blob/f9f05cd988c247dce6c072eaf9ac6b162f2ffc4b/skills/superdesign/references/design-with-your-model.md) | Preserve a selected draft identity, branch deliberate alternatives and route real image references | Transfer those mechanisms without requiring its hosted service or adopting unrelated workflow policies |
| [CDP font realization](https://chromedevtools.github.io/devtools-protocol/tot/CSS/#method-getPlatformFontsForNode) | Inspect actual fonts used for representative text nodes, alongside font files and geometry | Chromium-specific glyph/font reporting needs browser qualification; it does not establish typography rights or all visual fidelity |

The discriminating UI trial implements two meaningfully different surfaces from
one early system, with realistic long, empty and error states. Fresh critics see
the original references, system studies and actual renders, without a preferred
verdict. Check shared character and correct task-specific variation, plus the
normal complete interaction journey. Pixel fidelity to an already-drifted
generated image cannot establish fidelity to the original reference.

## Source reuse and scope

This proposal transfers mechanisms, not implementation code. Inspected STORM and
GEPA snapshots carry MIT licenses; ASReview carries Apache-2.0. DBOS and Temporal
license inspection was not a pinned package qualification. Papers and documentation
are not assumed to grant an implementation or asset license. Any later code reuse
must preserve the relevant pinned license, notices and attribution. Strict
clean-room construction instead requires an enforced analyst/builder boundary
and approved behavioral exports.

Inspected language snapshots carry Apache-2.0 for Comparator, XLA, StableHLO, CUE
and Cedar; MIT for TLA+, P, Dafny and Alive2; MPL-2.0 for Hypothesis; BSD-2-Clause
for LPIPS; and Apache-2.0 with LLVM exceptions for MLIR. These source identities
are research pins, not a tested compatible dependency set. No upstream runtime
code is copied into this proposal.

The source audit identifies plausible connections and actual current-helper gaps.
Complete integrated implementation, host qualification and matched whole-task
effectiveness trials remain separate work.
