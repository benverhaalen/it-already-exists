# Product brief

Updated September 14, 2026. This document distinguishes the intended product from untested architecture proposals.

## Intended outcome

Help people using Claude Code or Codex build polished, deep, coherent products inside their existing projects. The system should give coding agents concrete access to qualities that are difficult to communicate with generic instructions: taste, hierarchy, nuance, interaction detail, recovery, and completeness across real user journeys.

Reverse engineering is the means of learning from a reference. Applying what was learned to the user's product is the central outcome. Full reconstruction remains available when requested.

## Confirmed scope and preferences

- Name and repository: `it-already-exists`, private during development.
- Primary interface: the coding agent the user already uses in their project. Avoid a dedicated frontend initially.
- Normal entry: the user's product goal and project context. The agent actively seeks references; the user need not provide any. Optional supplied references and discovered references can include websites, APKs, installed desktop applications, executables, recordings, repositories, APIs, and other observable surfaces.
- Preference discovery: concrete situations or comparable previews when an answer would change a consequential decision. Avoid vague adjective pairs and forced binaries. Users can reject the framing, combine properties, or describe an alternative in ordinary language without knowing the reference products.
- Default: adapt the best relevant properties into a coherent original product. Exact reconstruction is an explicit alternative.
- Creative principle: a Virgil Abloh-style 3% rule—start with an existing solution and make a deliberate change. No literal change-percentage metric is intended.
- The system must help generate ideas as well as inspect existing examples.
- Preserve separate strict clean-room and source-assisted workflows for reconstruction.
- Initial resources: one builder, limited GPU access. Prefer existing inspection tools and selective use of the user's coding agent over a mandatory second inference service.

## Product behavior

Discovery drives design from the user's goal, rather than waiting for a supplied reference or an already implemented quality gap. Form provisional criteria from the audience, task and project, seek useful examples, and refine both the criteria and search from feedback. Ask only questions that can change a decision; this is a conversation, not an onboarding questionnaire.

A reference can contribute a visual direction, interaction pattern, product capability, implementation mechanism, or evaluation example. Establish its job before transferring it. A user-supplied reference has stronger evidence of the user's intent than an independently discovered one, but that does not imply the user likes every property of it.

Understand choices in context well enough to support a design debate: identify the user problem, conditions, alternatives, tradeoffs and what would change the recommendation. Keep observed behavior, documented rationale, inferred mechanisms and evaluated effects distinct. See the [design reasoning standard](design-reasoning.md).

For substantive product decisions, look for relevant existing evidence and expose unsupported choices. Reuse already approved project patterns when they answer the question. Scale new discovery to the uncertainty and consequence of a decision; a fresh search for every line of code would not serve the product outcome.

Resolve multiple references into one system: a consistent navigation model, vocabulary, hierarchy, type and spacing relationships, motion behavior, and state conventions. Retain intentional variation when it serves a different task or mode. The agent should be able to explain both the adopted property and its adaptation.

Ideas can arise from a pattern transferred across domains, a conflict between reference assumptions and the new audience, or a capability gap no reference resolves. Record those as proposals with a reason and a practical comparison, rather than claiming an invented feature was observed elsewhere.

## Representative user journey

Proposed first complete demonstration:

1. A person opens Claude Code or Codex in an existing, working project with a simple collection-and-editor workflow.
2. They describe the goal: help designers save inspiration and retrieve it for a project. No reference is supplied. The initial state is the project's normal entry screen, not an isolated demo component.
3. The integration reads the project context and seeks references for capture, retrieval, editing and recovery. If an important preference remains unclear, it offers a concrete comparison using the user's task and realistic content. The person can choose, combine, reject both, or correct the premise. That response changes the selection criteria and affected search; it does not become a universal taste label.
4. It produces a small set of evidence-linked decisions, reconciles them with the existing product language, and makes the required context available to the coding agent.
5. The coding agent implements the full workflow: open, select, edit, invalid input, correction, save, navigation, and durable result. Delayed and failed saves, keyboard use, narrow layout and return navigation are included where applicable.
6. Verification runs the experience and checks whether the selected qualities survived. It distinguishes implemented behavior, actual observations, subjective judgments and unresolved questions.
7. The person reviews the result in their normal app preview, with a concise account of what changed and why. They can correct a taste choice without restating the whole brief.

This proposed demonstration tests discovery without supplied references, preference correction, transfer and application together. It must include a correction that rejects the agent's initial framing, with the revised criteria visibly affecting the result. Also test the optional supplied-reference path. A subsequent native app or APK case tests whether the shared representation extends beyond browser references.

## Success and credibility

Compare the same project task with the same model and budget under: the normal coding workflow; references supplied directly; and references processed through this proposed mechanism. Measure actual user-journey completion, relevant edge cases, consistency, and human interventions. Report wall time and cost, including discovery and capture.

Evaluate goal-only discovery separately from transferring a fixed reference set. Use the same initial brief and feedback access across conditions, and count the cost of preference questions. A useful result should reflect a user's correction, including rejection of the offered options, without requiring them to name replacement references. Keep these discovery and correction claims separate from gains due to better reference distillation.

Evaluate taste with blinded comparisons of the running artifacts by people representative of the audience. Use measurable layout, timing and behavior checks as supporting evidence. Retain disagreements and failure cases. Exact-reconstruction evaluations use explicit reference comparisons; adaptation evaluations judge the target brief and transferred properties, since a successful adaptation may intentionally look different.

No measured gain, general taste evaluator, working adapter, enforced information boundary, or demonstrated reconstruction is claimed at this stage.
