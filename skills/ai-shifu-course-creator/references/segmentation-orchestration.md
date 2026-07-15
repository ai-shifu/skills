# Segmentation and Orchestration

## Segmentation

Turn messy course source material into a reliable intermediate structure for downstream lesson generation.

### Workflow

See `pedagogy.md#segmentation-methodology` for the full methodology (cleanup, immutable-block marking, semantic segmentation, lesson-boundary proposal, source linking). Apply a normalized `authoring_constraints.lesson_granularity` value when proposing lesson boundaries; explicit chapter and lesson targets remain authoritative.

### Outputs

Return `data-contracts.md#segmentation-output`. The schema owns every handoff field and signal meaning; `pedagogy.md#segmentation-methodology` owns how source material is divided and how source-supported signals are derived.

### Validation

Run `review-checklist.md#segmentation-validation`. Do not advance to lesson cuts until every observable check passes or fallback output records the unresolved uncertainty.

---

## Orchestration

**Role**: end-to-end authoring orchestrator for Path A. Orchestration calls Segmentation and Generation internally, then performs the cross-lesson work that those phases cannot — course index, global variable table, and mandatory gating. On a platform-bound course mutation, this authoring result remains an intermediate handoff rather than the terminal course result.

### Workflow

1. Normalize source ordering and merge input material.
2. Run Segmentation for cleanup and semantic segmentation, applying normalized authoring constraints through `pedagogy.md#authoring-constraints`.
3. Finalize lesson cuts from Segmentation's boundary candidates (one core question each).
4. Run `generation-workflow.md` to generate per-lesson Teaching Prompts.
5. Build course index and global variable table.
6. Recompute only failed lessons through strict gating.

### Mandatory Gates

Run `review-checklist.md#orchestration-validation`. Recompute lessons that fail any observable gate; do not partially pass.

### Rerun Rules

- Recompute only impacted lessons.
- Recompute dependency-linked lessons when shared variables change.
- Recompute full course only when global source order changes.

### Failure Handling

When `execution_mode` from `data-contracts.md#course-design-controls` is `fallback`, Orchestration:

- Delivers coarse lesson drafts first; continues with best-effort generation instead of stopping.
- Marks uncertain spans explicitly on `course_index` entries.
- Emits a `rerun_plan` listing lessons that need recompute and why.

Fallback field shapes per `data-contracts.md#fallback-output-extensions`.

### Outputs

Return `data-contracts.md#orchestration-output`; preservation rules remain in `markdownflow.md#preservation`.

### Validation

Run `review-checklist.md#orchestration-validation`; that checklist defines the observable completion gate.
