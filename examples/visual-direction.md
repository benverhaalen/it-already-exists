# Worked example: transferring visual taste

Illustrative proposal, not an observation from a named product or a generated design.

## The user's intent

Build a place for designers to save inspiration and retrieve it when starting a project. The user supplies no references. The agent seeks examples for capture, retrieval, collection browsing and keyboard navigation, guided by the intended audience and existing project.

Suppose the first investigation leaves a consequential question about retrieval. The agent shows two rough views with the same saved items: one organizes them into project boards, and one surfaces them through search with previews. It asks: "You're starting a kitchen redesign and want to find what you've saved. Would either of these get you to the right material? You can point to useful parts, reject both, or tell me what you'd expect instead."

The user replies: "Neither. Usually I remember what something looked like, but not what I called it, and I don't want to organize boards."

That correction changes the problem definition. The agent deprioritizes manual organization and investigates references that support recognition through images and lightweight narrowing. It does not infer that the user rejects all search or always prefers large images. A candidate visual browsing direction must now make saved material recognizable, and the resulting prototype must let the user test that expectation. The next useful interaction can be a revised artifact rather than another question.

The investigation should establish which concrete properties support recognition and retrieval. Keep annotated full-screen images and detail crops so the builder can inspect the visual relationships; a list of color and spacing values loses too much context. Any visual direction remains provisional until it serves this task.

## From visual evidence to a coherent direction

| Property to investigate in the reference | Possible target decision if confirmed | Inspect in the actual target |
| --- | --- | --- |
| One clear focal point with quieter supporting metadata | Give the collection title and content imagery priority; keep counts and timestamps subordinate | What draws the eye first at the normal viewport and with realistic content? |
| Related alignment and spacing across sections | Establish shared edges and a small spacing scale suited to the existing layout | Are titles, controls and content aligned? Does a long title break the relationship? |
| Deliberate image proportions and cropping | Define content-aware crop behavior and a meaningful fallback | Do portrait, landscape, missing and low-resolution images still compose well? |
| A consistent relationship between type size, weight, width and line length | Choose available typefaces and hierarchy as a system | Inspect wrapping, readable density, awkward breaks and hierarchy on both target viewports |
| Restrained feedback during state changes | Keep content stable during filtering and communicate loading locally | Observe the transition under delay; check motion and retained focus |

A complementary reference contributes a filtering mechanism. Its original colors, typography and panel density need not transfer. Reconcile its controls with the chosen visual system, and preserve the useful behavior through adaptation.

## Application and judgment

The coding agent receives the selected direction, relevant reference images, decisions and representative content cases before implementing the collection browser. It then captures and uses the actual result at normal and narrow widths, including long labels, empty results, loading and errors.

Some properties admit objective checks: clipping, overlap, focus order, retained position and agreed layout relationships. Others need visual judgment: balance, emphasis, rhythm and whether the direction suits this audience. A passing geometry check cannot settle those questions.

When uncertain, compare two concrete versions that differ in the disputed choice while keeping the task and content constant. Review the running flow as well as screenshots. If feedback contradicts the initial interpretation, update the direction and its dependent decisions rather than adding isolated styling fixes.
