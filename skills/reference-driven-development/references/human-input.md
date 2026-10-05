# Human input that changes consequential decisions

The product should reduce the user's research, reference discovery, repeated explanation, technical selection and quality-repair burden. The agent owns those tasks. Human input is useful where it contributes information or authority the agent cannot establish, not as a ceremony after every stage.

## Recover intent before asking

Read the relevant conversation and project decisions first. Separate outcome, hard constraints, preferences, examples, tentative proposals and methods. Preserve why a response mattered, its original task/conditions and its evidential strength. A reference supplied for density does not authorize its entire visual language. A local negative correction is not a permanent universal prohibition.

Reuse a prior response when the current decision shares its relevant conditions, nothing consequential contradicts it, and its purpose is clear. Act directly on explicit requirements and established decisions within their scope. Infer reversible implementation choices from consistent prior preferences when fit is strong; expose a consequential inference briefly and retain a revisit trigger. Record that it is an inference, not a newly supplied user answer. A changed audience, platform, task, risk or competing response can make the old answer insufficient.

Use `input_requests[].intent_inference` in the task contract to retain `interpretation`, actual `past_response`, its `source`, `original_scope`, `current_fit`, `changed_conditions` and `revisit`. Only reversible `category: intent` or `preference` requests with `reversible: true` may use this route. The helper checks declaration shape, not whether the interpretation is faithful. Do not invent the source or quote. Inspect it before relying on it. Explicit authorization should be carried from the original authorized scope; inference cannot manufacture missing permission.

## When to wait

Wait for required input when plausible interpretations materially change the outcome and evidence cannot resolve which the user wants; when a consequential taste choice needs their judgment; when only they know a necessary constraint; or when the next action lacks authorization. Explain the decision and why their input changes it. Ask for missing information, not for permission already supplied.

A required answer blocks only its dependent work. Continue independent research, diagnostics, reversible preparation and concretization. Never treat silence, elapsed time, a preselected option, critic agreement or an agent-written assumption as consent. For permission-dependent actions, finish the authorized preparation first so the user reviews a concrete result.

Do not wait for routine implementation methods, publicly inspectable facts, choosing among equivalent tools, reversible low-impact refinements, or decisions already supported by applicable prior responses. Optional questions can remain open while work continues under a disclosed reversible assumption; unresolved required choices cannot.

## Minimize separate interruptions

Maintain a small unresolved-decision queue. Resolve inspectable questions yourself first, identify dependencies, then bundle related questions in one concise interaction at the next consequential branch. `plan` and `compile` emit one `question_batch`, blocked work and independent work. The host may split it when one answer determines whether the remaining questions matter; do not overwhelm the user with a questionnaire.

Ask at the level that resolves several downstream choices: intended task or reference-property authority before individual component details. Use concrete comparisons with comparable task/content when taste matters. Permit rejection of the framing, combinations and ordinary-language corrections. A binary choice must not erase those possibilities. Avoid requiring the user to research references, name libraries or prescribe technical architecture.

After an answer, update the affected selection/contract and dependents once. Retain the answer's meaning so later screens do not ask again. Do not expand it to unrelated work. If a new question repeats an old one, identify the changed condition that makes asking worthwhile.

## Evaluate the burden alongside the result

For later user-chosen evaluations, consider separate interruption count, repeated questions already answered, time preparing answers, required domain knowledge, avoidable corrections, and total time to an accepted result. Few questions with wrong hidden assumptions are not success; many confirmations that prevent the agent taking responsibility are not success either. Preserve audience fit, behavior, character and authorized scope while reducing avoidable human work.

If repeated corrections persist, investigate retrieval, misinterpreted intent, wrong authority, reference gaps, production drift and evaluator mismatch before requesting more preferences. The human should provide consequential intent and judgment; the system should carry those decisions into the product.

## Dependency frontier

For intertwined consequential choices, identify prerequisites before asking. Resolve inspectable facts yourself. Batch only questions whose prerequisites are settled; after replies, recompute the frontier. A higher-level answer may eliminate several downstream questions. Do not turn this into exhaustive interviewing: the agent owns routine technical decisions, and prior scoped intent can support reversible work. Required unresolved decisions still block dependent work.

The helper accepts request `prerequisites` and task `settled_prerequisites`. It emits answerable `question_batch` and `deferred_questions`; settlement is a caller declaration that needs evidence. Cyclic or permanently inaccessible prerequisites require reframing, not silent assumption.
