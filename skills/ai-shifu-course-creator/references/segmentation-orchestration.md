# Segmentation and Orchestration

## Segmentation

Turn messy course source material into a reliable intermediate structure for downstream lesson generation.

### Segmentation Methodology

#### Objective

Produce stable lesson-oriented semantic segments from noisy source material while preserving immutable artifacts.

#### Core Rules

1. Preserve source order unless explicit ordering hints are provided.
2. Keep each code block, image reference, and table block as one traceable source span. During Segmentation, apply `optimization-workflow.md#preservation-decisions` and set `preserve_block` before any Generation step; the authority's file location does not defer this decision to the later Optimization phase.
3. Segment by semantic shift, not heading depth alone.
4. Keep each lesson candidate centered on one teachable question.
5. Attach source spans to every segment.

#### Failure Handling

If structure is weak, output a fallback segmentation, mark uncertain spans, and provide focused rerun hints in `resolved_target_language` using the fields in [data-contracts.md#segmentation-fallback-fields](data-contracts.md#segmentation-fallback-fields).

### Outputs

Produce a segment list that conforms to [data-contracts.md#segment-schema](data-contracts.md#segment-schema), including its canonical [segment types](data-contracts.md#segment-types) and [transfer signals](data-contracts.md#transfer-signals), plus lesson boundary candidates with one core question each.

Write `core_point`, human-readable `transfer_signals` values, and each lesson-boundary `core_question` in `resolved_target_language`. Keep segment ids, enum values, source ids and offsets, code, URLs, and exact source quotations unchanged.

### Validation

- Segment output covers all valid source spans in traceable order.
- Every segment passes [data-contracts.md#segment-schema](data-contracts.md#segment-schema).
- The preservation and one-core-question rules in [Core Rules](#core-rules) pass; each immutable span is marked through `data-contracts.md#segment-schema` according to `optimization-workflow.md#preservation-decisions`.

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

- **Syntax / runtime gates** (violation → Prompt fails to run): each Prompt parses and executes according to `markdownflow.md`; every learner-answer variable passes `data-contracts.md#variable-table`; interaction, variable-branch, and image composition pass `generation-workflow.md#markdownflow-authoring`; immutable spans pass `optimization-workflow.md#preservation-decisions`. Verify the observable results through `review-checklist.md` rather than restating those rules here.
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
- Emits a `rerun_plan` listing lessons that need recompute and gives its human-readable `reason` in `resolved_target_language`.

Fallback field shapes per `data-contracts.md#fallback-output-extensions`.

### Outputs

See `data-contracts.md#output-contract` for the Teaching Prompts, course index, and global variable table schemas. Write `course_index[].lesson_title` and `course_index[].core_question` in `resolved_target_language`; keep lesson ids and source-span references stable.

### Validation

- All artifacts present per `data-contracts.md#output-contract`.
- Fallback outputs include explicit uncertainty markers and rerun hints.
- All Mandatory Gates above pass.
