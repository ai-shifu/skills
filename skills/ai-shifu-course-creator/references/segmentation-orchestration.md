# Segmentation and Orchestration

## Segmentation

Turn messy course source material into a reliable intermediate structure for downstream lesson generation.

### Segmentation Methodology

#### Objective

Produce stable lesson-oriented semantic segments from noisy source material while preserving immutable artifacts.

#### Core Rules

1. Preserve source order unless explicit ordering hints are provided.
2. Keep code blocks, image files, and table blocks immutable.
3. Segment by semantic shift, not heading depth alone.
4. Keep each lesson candidate centered on one teachable question.
5. Attach source spans to every segment.

#### Failure Handling

If structure is weak, output a fallback segmentation, mark uncertain spans, and provide focused rerun hints using the fields in [data-contracts.md#segmentation-fallback-fields](data-contracts.md#segmentation-fallback-fields).

### Outputs

Produce a segment list that conforms to [data-contracts.md#segment-schema](data-contracts.md#segment-schema), including its canonical [segment types](data-contracts.md#segment-types) and [transfer signals](data-contracts.md#transfer-signals), plus lesson boundary candidates with one core question each.

### Validation

- Segment output covers all valid source spans in traceable order.
- Every segment passes [data-contracts.md#segment-schema](data-contracts.md#segment-schema).
- The preservation and one-core-question rules in [Core Rules](#core-rules) pass; immutable assets also satisfy [markdownflow.md#preservation](markdownflow.md#preservation).

---

## Orchestration

**Role**: end-to-end orchestrator for Path A. Orchestration calls Segmentation and Generation internally, then performs the cross-lesson work that those phases cannot — course index, global variable table, and mandatory gating.

### Workflow

1. Normalize source ordering and merge input material.
2. Run Segmentation for cleanup and semantic segmentation.
3. Finalize lesson cuts from Segmentation's boundary candidates (one core question each).
4. Run Generation to generate per-lesson Teaching Prompts.
5. Build course index and global variable table.
6. Recompute only failed lessons through strict gating.

### Mandatory Gates

All gates must pass before Orchestration declares lessons complete:

- **Syntax / runtime gates** (violation → Prompt fails to run): preservation of code, images, and required source spans per `markdownflow.md#preservation`; no unresolved placeholders and no learner-answer variable references without a variable-backed interaction and metadata contract; `?[]` on standalone lines; deterministic blocks used only for truly fixed content per `markdownflow.md#deterministic-blocks`; every image URL must be on the `res.ai-shifu.cn` domain — fixed images wrapped in a single-line deterministic block, HTML-view images expressed as instruction-style directives with the `(必须原样保留)` URL phrase per `markdownflow.md#images`.
- **Pedagogical gates** (violation → teaching quality fails): one core question per lesson, the policy-resolved teaching loop, and delivery-mode visual-text behavior — all per `pedagogy.md#interaction-policy-precedence`, `pedagogy.md#lesson-loop`, `pedagogy.md#interaction-design`, `pedagogy.md#variable-strategy`, and `pedagogy.md#visual-text-coordination`. At this phase, verify the resulting placements and substitutions rather than redefining policy semantics. Also enforce the five-interaction maximum, distinct branching for viewpoint/path interactions or explicit `require_branching_feedback`, and an immediate feedback or visible instructional effect for every other interaction.

Recompute lessons that fail any gate; do not partially-pass.

### Rerun Rules

- Recompute only impacted lessons.
- Recompute dependency-linked lessons when shared variables change.
- Recompute full course only when global source order changes.

### Failure Handling

Under fallback mode (see `authoring-controls.md#execution-modes`), Orchestration:

- Delivers coarse lesson drafts first; continues with best-effort generation instead of stopping.
- Marks uncertain spans explicitly on `course_index` entries.
- Emits a `rerun_plan` listing lessons that need recompute and why.

Fallback field shapes per `data-contracts.md#fallback-output-extensions`.

### Outputs

See `data-contracts.md#output-contract` for the Teaching Prompts, course index, and global variable table schemas; preservation rules per `markdownflow.md#preservation`.

### Validation

- All artifacts present per `data-contracts.md#output-contract`.
- Fallback outputs include explicit uncertainty markers and rerun hints.
- All Mandatory Gates above pass.
