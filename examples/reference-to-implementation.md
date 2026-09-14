# Worked example: preserving a draft through failure

Illustrative design example. This is not a finding from an inspected product, an implemented feature, or a test result. All observations below describe evidence a real study would need to collect.

## Product context

A small publishing tool for occasional contributors. The user values an editor that feels calm, complete and forgiving. They supply an editor as a reference; the agent also searches for useful recovery patterns.

## Evidence to acquire

Capture the reference's normal entry and editing sequence, a failed save, a retry, navigation away and return, and restart where relevant. Record what remains visible, what data survives, where focus goes, and whether duplicate input has an additional effect. Associate the observation with a version, account state and environment.

Use the actual reference recording and images in the eventual record. Do not infer durable storage from a toast or an unchanged screenshot.

## Transfer decision

Proposed principle: make the state of the user's work clear and preserve recoverable input through a failed operation.

Hypothesized value: contributors can recover without retyping or wondering whether their work was accepted. Validate the fit with the target workflow; this example does not claim a measured usability effect.

Preserve: continuity of the editing context and a direct recovery action.

Adapt: the publishing tool needs explicit submission, so use clear draft, submitting, submitted and failed states. Choose persistence behavior based on its account and privacy model rather than silently inheriting another app's assumptions.

Omit: collaboration controls and unrelated features when they do not serve this audience.

## Concrete implementation expectations

| Condition | Proposed target behavior | Evidence/check needed |
| --- | --- | --- |
| Invalid input | Explain the problem at the relevant field and preserve other input | Complete the invalid-to-corrected path with pointer and keyboard |
| Submission pending | Show pending state without moving the action or losing editing context | Observe under a controlled delay |
| Submission fails | Preserve the draft, identify the failure, and offer retry | Inject a failure in the target test environment; inspect text and focus |
| Retry | Submit the intended draft once and show the resulting state | Inspect persisted records as well as visible feedback |
| Navigate away and return | Apply the chosen draft retention policy consistently | Repeat the full navigation history |
| Narrow viewport | Preserve hierarchy and access to the recovery action | Use the flow at the target viewport; inspect wrapping and scroll behavior |

These are proposed requirements for this new product. A real record would distinguish which are reference observations, adaptations, and independently proposed improvements.

## Application evidence

Before implementation: provide the coding agent this decision plus the relevant reference clip, the target's existing form conventions, and the chosen data policy.

After implementation: link the actual editor and state-handling changes, record the complete journey, and attach check outcomes. The initial state here is unresolved: no code has been changed and no checks have run.

For taste, inspect whether feedback is legible, calm and consistent with the rest of the product. Compare concrete alternatives if needed. Passing the persistence checks does not establish that judgment.
