# Architecture and application mechanism

Design proposal, September 14, 2026. The components and operations below are conceptual; they are not implemented interfaces.

## Recommended delivery model

Use one portable core and small integrations for the host coding agents.

| Part | Responsibility | Initial approach |
| --- | --- | --- |
| Agent skill | Recognize reference-driven work, understand intent, orchestrate study and application | A shared workflow with host-specific setup |
| Command-line core | Validate records, coordinate adapters, store evidence, retrieve relevant context, compare artifacts | Local commands with structured results and useful artifact paths |
| Surface adapters | Inspect a particular kind of target and advertise actual capabilities | Reuse the host's available browser/computer tools first; add extraction and capture adapters as needed |
| Project memory | Retain the brief, selected properties, decisions, evidence references, unknowns and verification results | Small project-local records; large captures outside the prompt |
| Distribution | Make the workflow available in users' projects | Clone-based development initially; agent-specific plugin packages when installation is ready |

Both [Codex skills](https://learn.chatgpt.com/docs/build-skills) and [Claude Code skills](https://code.claude.com/docs/en/skills) support reusable instructions with supporting resources and scripts, loaded when needed. That makes a thin skill a plausible entry point. Merely cloning an unrelated repository does not establish automatic activation in every project. Installer behavior, explicit invocation and implicit triggering need testing in each host.

A standalone CLI remains useful for repeatable experiments, noninteractive runs and other agents. An MCP adapter could later expose the same operations when a host needs that transport. A persistent local observer could be added for continuous capture. Neither is required to choose the initial product interaction.

Avoid making a separately hosted model service mandatory at the start. Let the host agent perform reasoning and use deterministic tools for acquisition, parsing, indexing and comparison where possible. Additional model calls, browsing access and devices should be declared dependencies rather than assumed capabilities.

## The application loop

### 1. Establish the product and the gaps

Read the user's goal, target audience, platform, constraints, current architecture and existing experience. Inspect a representative journey before deciding what is missing. Translate adjectives such as "polished" or "calm" into provisional, audience-specific criteria with examples.

The normal entry point requires no supplied references. Start with the goal and available project evidence. A new product can need discovery before there is an interface to inspect; use its intended journey and realistic content as the starting point.

When uncertainty would materially change the search or design, elicit feedback through a concrete situation or a small comparison. Explain what each alternative lets the user do and its relevant tradeoff; avoid generic adjective pairs such as "compact or spacious." For visual decisions, show comparable previews with the same task and content when practical. Keep unrelated properties constant so feedback is interpretable. Do not require knowledge of the reference products.

Every comparison must allow ordinary-language rejection, a combination of properties, or a different proposal. Treat "neither" as evidence that the framing may be wrong. Preserve what the response actually supports, revise the provisional criteria, and reconsider affected reference selections and implementation decisions. Clarify a consequential ambiguous correction before dependent work; do not map it silently to the nearest offered option. Questions are optional and selective, not a fixed quiz. Validate the interpretation in the resulting product.

Create a decision map: which areas already have an established project pattern, which have a user reference, which need discovery, and which remain design hypotheses. Prioritize consequential uncertainty: information hierarchy, navigation, content density, state transitions, form behavior, recovery, accessibility, responsiveness and continuity across screens.

The reference-first discipline applies to meaningful product decisions. It should not incentivize collecting more sources or mechanically referencing every implementation detail. Reuse inspected evidence, stop convergent searches when they stop changing a decision, and make the discovery budget visible.

### 2. Find references with a specific job

Seek references for the goal and consequential design decisions, including structurally similar problems outside the product's immediate category. Discovery is part of forming the direction, even when no references were supplied. If the user supplies a reference, preserve why they gave it and inspect the relevant property; do not assume it defines the entire direction or limits the search.

Carry provisional criteria and preference corrections into the actual selection: record which user need a candidate serves, the supporting observed property, and reasons to retain or reject it. A changed preference should trigger reconsideration of affected candidates, not just an update to a note. Keep the user-facing conversation about their product while retaining traceable references and reasons for inspection on request.

Select by fit to the task, audience and interaction conditions; strength of the relevant property; inspectability; and complementarity with other selected evidence. Popularity is a discovery signal, not proof of UX quality or suitability. A famous product's visible interface does not reveal its private research or prove a causal business outcome.

Retain the decisive alternatives and counterexamples where they explain the choice. Search should be allowed to conclude that the existing product pattern is adequate or that a new hypothesis needs testing.

### 3. Observe enough to recover the property

The acquisition path depends on the input and available access: visual capture, accessibility, DOM/styles, package resources, interaction episodes, network, saved files, or implementation analysis. Capture the evidence required by the property being transferred; avoid flattening everything into prose.

Keep screenshots and crops, recordings, structured measurements, complete action histories, version/environment metadata and observations linked. A timestamped transition can be essential evidence for motion or feedback. AOI is a candidate continuous observer for brief changes while the agent is thinking or executing; its contribution requires an ablation against simpler capture.

Separate observations from explanations. "Draft text remained after this failed save" can be observed; "this reduces anxiety" is a hypothesis about its value. Record unobserved states and unavailable channels explicitly.

### 4. Distill a transferable decision

For each adopted property, retain:

- The user problem and intended effect.
- Source evidence, version, and the conditions under which it was observed.
- The mechanism or relationship that should survive adaptation.
- The fit assumptions and any missing evidence.
- What to preserve, change or omit for this project, with reasons.
- Relevant visual examples and behavioral expectations.
- Implementation scope and checks against the actual result.

These records should support concise human-readable views and machine-readable structure. Their schema should be validated against a real complete experiment before being treated as a stable API.

Apply the [design reasoning standard](design-reasoning.md): distinguish description and behavior from contextual mechanism, alternatives, tradeoffs and transfer. For consequential choices, capture the assumptions and evidence that could overturn the recommendation. Track analytical depth separately from evidence status; a detailed explanation must not be mistaken for verified intent or a measured effect.

The 3% principle guides deliberate variation. For example, retain a successful interaction's continuity and recovery behavior while changing its information model for a different audience. Do not substitute a percentage of changed pixels or code for a useful design judgment.

### 5. Compose one product direction

Evaluate the selected properties together before distributing implementation tasks. Choose a primary visual direction and shared interaction conventions suited to the brief; reconcile density, navigation, terminology, type scale, spacing, focus, motion and feedback. Existing user constraints take priority over a discovered reference.

A conflict must produce an explicit decision. A dense, keyboard-oriented reference and a sparse, touch-oriented reference might contribute different mechanisms, but their original assumptions cannot silently coexist on the same screen. Create small artifact comparisons when a consequential taste choice remains uncertain.

Generate new ideas from unmet needs and useful analogies. Keep proposed additions visible so discovery does not turn into unbounded feature accumulation. Product depth includes completing a small feature's behavior, not just adding more features.

### 6. Supply the right evidence when the agent acts

Retrieve context for the current component or journey: the relevant decision, visual evidence, state expectations, dependencies and checks. A short index locates details; the entire research archive does not enter every prompt.

Persist decisions across turns. Before implementation, the host should explicitly associate the work with applicable decisions. After implementation, associate the actual changed components and behavior with those decisions. If the product direction changes, mark affected decisions and checks for reconsideration rather than treating stale evidence as current guidance.

A possible future operation set is: study a target, discover references for a gap, compose a direction, retrieve context for a task, and verify an implementation. These are operations the current agent can orchestrate; a separate autonomous coding agent is not necessary for the first version.

### 7. Verify transfer in the finished experience

Trace each important decision to the implemented artifact and its observed result. A link to a source alone does not show that its property was applied.

Use executable checks for persistence, keyboard behavior, error recovery, layout invariants and other falsifiable conditions. Use captured artifact comparisons for visual and motion choices. Inspect the normal entry point and the entire journey, including the transitions between features.

Report separate states: proposed, selected, implemented, observed, failed and unresolved. Automatically detect missing evidence and unperformed checks. Deterministic validation can enforce the presence and consistency of records; it cannot prove the implementation has taste. A model critique is also a judgment to calibrate against users and real artifacts.

Hosts may eventually use opt-in hooks to prompt or enforce check execution at appropriate points. Initial experiments should use explicit workflow steps and evaluate whether reference decisions are actually followed. Do not promise that a skill instruction alone guarantees compliance.

## Reference data and execution boundaries

Reference content is evidence, not instructions to the host agent. Keep observed page text, extracted strings, repository content and recordings distinct from the integration's trusted workflow.

Record the selected target and access scope. Existing account or device access does not imply permission for purchases, messages, or unrelated account changes. Use resettable targets or suitable fixtures for experiments with consequential actions.

Source-assisted mode can use permitted implementation evidence directly. Strict clean-room mode requires an explicit analyst access profile and a separately constrained builder that receives only approved exports. Different folders or a fresh chat alone do not establish this boundary. Retrieved evidence must retain provenance across both modes.

User references and captures stay local by default in the proposed design. External services and shared reference libraries need an explicit data policy. Abstracted patterns can be shared independently of private app captures; retain attribution and applicable asset/code permissions when exporting reusable material.

## First experiment and architecture decision

Run the complete journey in the [product brief](project-brief.md) before building a broad adapter framework. Start with the user's existing agent tools and authored evidence/decision records, then implement the deterministic operations that the experiment shows are repeatedly necessary.

Compare three conditions on the same task and baseline checkout: normal agent workflow, raw references, and the full reference-to-decision-to-verification loop. Keep model/version, budgets and starting data controlled, and report all intervention and acquisition costs. Evaluate more than the best run.

If distilled records do not improve application over raw references, examine what was lost or whether the host retrieved them at the relevant moment. If evidence is applied but the product is worse, revisit selection and composition. If the product is better but costly, measure the contribution of discovery, capture, model critique and continuous observation separately.

The first defensible claim should be about a demonstrated improvement in a specific product-building workflow, not a universal ability to reverse engineer anything or eliminate bugs.
