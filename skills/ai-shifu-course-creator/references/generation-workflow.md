# Generation Workflow

## Generation

Generate a runnable Teaching Prompt for each lesson.

### Teaching Pattern Baseline

Apply the mode-independent patterns and constraints in `pedagogy.md#teaching-patterns`, `pedagogy.md#cognitive-techniques`, `pedagogy.md#variable-strategy`, `pedagogy.md#interaction-design`, and `pedagogy.md#visual-text-coordination`, then apply the selected cross-artifact profile from `delivery-modes.md`.

Apply the normalized content constraints through `pedagogy.md#authoring-constraints`; Generation never reads legacy phase-specific constraint wrappers.

Consume the normalized Course Design Intake interaction policy only after it passes `data-contracts.md#interaction-policy`. Apply its teaching effect and substitution from `pedagogy.md#interaction-policy-precedence`; Generation does not reinterpret the modes or purposes. Whenever that policy calls for an interaction, apply `pedagogy.md#interaction-design` before writing the standalone interaction line required by [Prompt Contracts](prompt-contracts.md).

### Single-Lesson Generation Strategy

Required anchors per lesson:

1. Opening paragraph with the teaching-start function required by the structural-metadata rule in [Prompt Contracts](prompt-contracts.md) — not a copied chapter / lesson title or directory label.
2. Opening objective plus slide-style visual cover.
3. Evidence-chain explanation.
4. The interaction slot or non-interactive substitute required by `pedagogy.md#interaction-policy-precedence`, with visible instructional value.
5. At least one reusable deliverable.
6. Lesson close with summary or decision checkpoint.

Optional modules: viewpoint calibration, misconception correction, dual deliverables (understanding + action), cross-lesson bridge sentence, additional visual-text reinforcement blocks.

### Slide-Only Generation Override

When `delivery_mode` is `pure_slides`, Generation applies `delivery-modes.md#pure-slides`; that owner defines every replacement to the standard teaching baseline.

### Outputs

Return `data-contracts.md#generation-output`; `lesson_teaching_prompts` remains an array even when the route generates exactly one lesson, and each item follows `data-contracts.md#lesson-schema`.

Generation output is terminal only for an explicitly artifact-only route. When the selected route creates or changes a platform course, continue through any required course-level finalization and the routed platform write; do not report the Generation handoff as a completed course mutation.

### Validation

Run `review-checklist.md#generation-validation` before returning any lesson.

### Working with Author-Provided Images

Route every supplied or changed lesson image through [Image Assets](image-assets.md). Continue only after its validated handoff, which preserves an already-valid platform resource or uploads an unresolved one.
