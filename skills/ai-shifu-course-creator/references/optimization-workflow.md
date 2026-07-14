# Optimization Workflow

## Optimization

Audit and improve existing Teaching Prompts (and the Course Prompt). This phase is not for writing from scratch.

### When to Use

Use Optimization when existing Teaching Prompts or a Course Prompt need audit and targeted improvement — gap analysis against source, quality upgrades without full rewrites, and lowering runtime failure risk. Not for from-scratch authoring.

### High-Standard Constraints

Apply Optimization audits against the full constraint set:

- Cross-artifact red lines shared by Teaching Prompts and the Course Prompt: `prompt-contracts.md`.
- Pedagogical constraints and issue taxonomy (interaction-policy effects, variable strategy, interaction design, visual-text coordination, lesson loop, information density): `pedagogy.md#interaction-policy-precedence`, `pedagogy.md#variable-strategy`, `pedagogy.md#interaction-design`, `pedagogy.md#visual-text-coordination`, `pedagogy.md#lesson-loop`, and `pedagogy.md#optimization-methodology`.
- Interaction-policy shape and enums: `data-contracts.md#interaction-policy`.
- Delivery-mode behavior across Teaching Prompt and Course Prompt: consume an existing authoring handoff through `delivery-modes.md`; for a focused audit or narrow edit without that handoff, preserve the supplied artifact's mode-dependent structure as defined there.
- Syntax / runtime constraints (preservation, deterministic blocks, variable references): `markdownflow.md`.
- Observable audit checks: `review-checklist.md`.

### Optimization Workflow

1. Define scope (single lesson vs full course); if multiple script versions exist, declare the authoritative one before editing.
2. Build a coverage matrix mapping source points to script coverage.
3. Run the full audit per `review-checklist.md`, classify findings using the issue taxonomy in `pedagogy.md#optimization-methodology`, and apply smallest safe edits first.

### Course Prompt

For end-to-end or full-course finalization, Optimization produces the course-level `course_prompt` artifact. Generate it by filling `course-prompt.md#fillable-template`, applying the selected profile from `delivery-modes.md`, replacing every `XXX`, and preserving every base instruction not explicitly replaced by that profile; do not compose the artifact free-form. A focused audit validates an existing Course Prompt only when the user supplies one and does not synthesize a new course-level artifact from lesson-only source material.

Auto-fill placeholders from the unchanged authoring context carried alongside the phase results (`course_author_name`, `course_profile`, `delivery_constraints`, resolved target language per `session-controls.md#output-language`) and from Segmentation visual cues. The Role must use the course author's real name; if `course_author_name` is missing, ask the author instead of inventing a persona. Apply the normalized profile from `delivery-modes.md`; do not duplicate per-lesson interaction logic or variable collection in the Course Prompt.

### Course Description

For end-to-end or full-course authoring, Optimization also produces `course_description`: a concise learner-facing listing summary based on the course topic, target learners, and concrete outcomes. Use the resolved output language and omit author-side process notes. A focused prompt audit does not create or replace this artifact unless course-level finalization is in scope.

### Outputs

Return `data-contracts.md#optimization-output`. End-to-end or full-course authoring additionally returns `data-contracts.md#final-authoring-output`, including the Course Prompt and course description.

### Validation

Run `review-checklist.md#optimization-validation` and `review-checklist.md#course-prompt`; present any remaining non-blocking gap explicitly.
