# Segmentation and Orchestration

## Segmentation

Turn messy course source material into a reliable intermediate structure for downstream lesson generation.

### Workflow

See `pedagogy.md#segmentation-methodology` for the full methodology (cleanup, immutable-block marking, semantic segmentation, lesson-boundary proposal, source linking).

### Outputs

Segment list per `data-contracts.md#segment-schema` (each segment carries id, type, core point, preservation flag, source span, and transfer signals), plus lesson boundary candidates with one core question each.

### Validation

- Segment output covers all valid source spans in traceable order.
- `transfer_signals` object populated and usable downstream (schema per `data-contracts.md#segment-schema`).
- Preservation, one-core-question, and information-fidelity constraints pass — see `markdownflow.md#preservation` and `pedagogy.md#lesson-loop`.

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

- **Syntax / runtime gates** (violation → script fails to run): preservation of code, images, and required source spans per `markdownflow.md#preservation`; no unresolved placeholders and no learner-answer variable references without a variable-backed interaction and metadata contract; `?[]` on standalone lines; deterministic blocks used only for truly fixed content per `markdownflow.md#deterministic-blocks`; every image URL must be on the `res.ai-shifu.cn` domain — fixed images wrapped in a single-line deterministic block, HTML-view images expressed as instruction-style directives with the `(必须原样保留)` URL phrase per `markdownflow.md#images`.
- **Pedagogical gates** (violation → teaching quality fails): one core question per lesson, the interaction-policy-specific minimum teaching loop, and visual-text pairing — all per `pedagogy.md#interaction-policy-precedence`, `#lesson-loop`, `#interaction-design`, `#variable-strategy`, and `#visual-text-coordination`. Under `enabled`, require only the placements implied by the selected purposes, then enforce max five interactions per lesson, variable-collection pacing, viewpoint branching where applicable, and a visible instructional effect for every interaction. Under `disabled`, or an `enabled` lesson to which no selected purpose applies, use the non-interactive loop and do not fail the lesson for missing interactions. Under `unspecified`, apply the existing pedagogical gates unchanged.

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
