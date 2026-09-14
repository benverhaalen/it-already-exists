# Understanding a design decision

Proposed standard for reference analysis in `it-already-exists`. The purpose is to support useful design debates and transfer decisions, not to invent the original team's motives.

## The level we need

For a consequential choice, the system should explain: who is trying to do what, under which conditions, why this mechanism might help, what alternatives it competes with, what it costs, and what would change the recommendation.

A reference is useful in a design debate when it supports an argument that can be challenged. Naming a successful product or describing a beautiful screen does not establish that its choices fit another product.

## Depth of understanding

| Level | Question answered | Useful output | What remains missing |
| --- | --- | --- | --- |
| 1. Description | What is there? | Layout, text, controls, assets, spacing and visual examples | Behavior and purpose |
| 2. Behavior | What happens, under which inputs and histories? | Interaction sequence, states, timing, persistence and errors | Whether that behavior serves this audience |
| 3. Context and mechanism | What problem could this solve, for whom, under what conditions? | User goal, relevant constraints and a causal hypothesis connecting the choice to an effect | The original team's intent and evidence that the effect actually occurs |
| 4. Alternatives and tradeoffs | Why favor this choice over another in this context? | Competing options, criteria, benefits, costs, assumptions and evidence | Whether the same tradeoff applies in the new product |
| 5. Transfer and revision | What should our product preserve or change, and what would overturn that decision? | A contextual recommendation, explicit adaptations and a discriminating experiment or artifact comparison | Results of that experiment and broader generalization |

Levels 3–5 are the useful target for design debates, supported by levels 1–2. Scale the effort to the decision. Existing typography conventions may settle a small component change; a new navigation model deserves deeper comparison.

These are levels of analytical depth, not increasing certainty. A sophisticated explanation can be unsupported. A modest observation can be well established.

## Evidence status is a separate axis

| Status | What it establishes | What it does not establish |
| --- | --- | --- |
| Observed | This behavior or appearance occurred in recorded conditions | Motive, effectiveness for users, or behavior in untested conditions |
| Documented rationale | An identified source says the choice had a particular purpose | That the purpose was achieved, or that the statement covers the exact observed version |
| Inferred mechanism | A reasoned explanation connects the choice to an expected effect | That the original team used this reasoning or that the effect is real |
| Evaluated effect | A specified comparison found an outcome for a sample and conditions | Universal effectiveness or automatic transfer to a different audience |
| Proposed adaptation | The new project chooses a change for stated reasons | A verified improvement before the target is built and evaluated |

Keep contradictory evidence, missing observations and changes of context visible. Designer intent, actual behavior, user outcomes and our recommendation are different claims and can disagree.

## What context to capture

Start with the user's task and conditions, then add dimensions that could change the choice:

- Who: experience, accessibility needs, frequency of use, and relevant roles.
- Task: intended outcome, urgency, complexity, and how often it repeats.
- Interaction: device, input method, screen space, attention and surrounding workflow.
- State and content: data volume, content variability, collaboration, connectivity and operation timing.
- Consequences: reversibility, recovery cost, privacy, visibility to others and potential confusion.
- Constraints: platform conventions, existing architecture, business requirements and operational limits.
- Product direction: desired character, density, visual hierarchy, vocabulary and continuity with nearby features.

Do not fill every dimension with guesses. Record known facts, relevant unknowns and the assumptions the recommendation depends on. Existing production choices may reflect legacy constraints or business objectives that the new product does not share.

## Record a decision as an argument

1. State the design question and the user's desired outcome.
2. Link the reference observations and any actual rationale sources.
3. Explain the proposed mechanism and its conditions of applicability.
4. Compare plausible alternatives using criteria derived from this product's audience and constraints.
5. Make the tradeoff explicit, including what gets worse or becomes more costly.
6. Select what to preserve, adapt or omit; label independently generated ideas.
7. State what evidence would change the choice and how to obtain it.
8. Link the implementation and evaluation when they exist.

The output should be a concise argument with relevant visual or interaction evidence. An unexplained score, a product name, or a confident story about its designers is insufficient.

## Example: automatic saving versus explicit submission

Hypothetical example; no claim is made about a named product.

Description: the reference has no Save button. Behavior: editing is followed by an indicator; a separate reload experiment is needed to establish persistence.

Context hypothesis: frequent edits to private work make interruption and recovery important. Automatic saving might reduce repeated manual actions and preserve work, provided the user can understand save status and recover from mistakes.

Tradeoff: automatic saving adds synchronization, status and recovery requirements. Explicit saving gives a clear commit point but adds an action and leaves unsaved-work cases to handle.

Transfer: a publishing product contains two operations with different consequences. Preserve private drafts automatically if that suits the data policy; use explicit submission to make material visible to an audience. The useful borrowed principle is continuity of work. Removing every explicit action would discard the relevant context.

Evidence that could change the recommendation: users misunderstand draft versus published state, a retention policy forbids local draft storage, or disconnected editing is common enough to require a different synchronization design. Evaluate the actual workflow under these conditions.

## Implication for the 3% principle

Understand the mechanism and its important conditions before choosing the deliberate change. Preserve the part that serves the new user goal. A small visual change can substantially alter behavior; a substantial visual adaptation can preserve the useful mechanism. The amount of surface resemblance is not the quality criterion.
