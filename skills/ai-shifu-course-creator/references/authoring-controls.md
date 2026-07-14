# Authoring Controls

Read this file for every Segmentation, Orchestration, Generation, or Optimization task. It selects cross-phase controls and routes each concern to its single owner; it does not redefine those owners' rules.

## Input Compatibility Normalization

Before selecting an execution mode or running Course Design Intake, normalize legacy authoring inputs exactly once through `data-contracts.md#input-compatibility-normalization`. After normalization, a route that runs Course Design Intake receives `authoring_run_controls`, `authoring_constraints`, and other canonical context fields. A Segmentation-only route receives canonical `execution_mode`, the applicable structure target, `authoring_constraints`, and other canonical context fields directly; it does not require or synthesize `authoring_run_controls`. No downstream route receives legacy wrappers.

Consume the normalization result and any reported conflict or unsupported-field outcome exactly as returned by that owner; do not reinterpret it here.

## Execution Modes

- **Standard mode** is the default when input quality supports the complete phase contract and successful normalization did not explicitly produce `execution_mode: fallback`.
- **Fallback mode** applies only after normalization succeeds, when non-conflicting input is incomplete or low quality, or when compatibility normalization explicitly produces `execution_mode: fallback`; produce coarse but schema-valid output, mark uncertainty, and provide focused rerun hints.

Unresolved normalization conflicts and unsupported legacy members stop before execution-mode selection with the targeted outcome returned by Data Contracts; they never select fallback mode.

Record the selection as `execution_mode: standard|fallback`. A Segmentation-only route consumes that field directly. A route that runs Course Design Intake merges it with the intake result into the canonical `authoring_run_controls` object defined by `data-contracts.md#course-design-controls`. Fallback output adds only the fields in `data-contracts.md#fallback-output-extensions`.

## Cross-File Concept Routing

| Concern | Single owner or owner split |
|---|---|
| Output language and canonical human-facing terms | [Output Language](session-controls.md#output-language) and [Canonical Term Translation Table](session-controls.md#canonical-term-translation-table) |
| Input, handoff, and output shapes | [Data Contracts](data-contracts.md) |
| MarkdownFlow syntax and runtime behavior | [MarkdownFlow Spec](markdownflow.md) |
| Mode-independent teaching design | [Pedagogy](pedagogy.md) |
| Standard versus pure-slide cross-artifact behavior | [Delivery Modes](delivery-modes.md) |
| Course Prompt base template | [Course Prompt](course-prompt.md) |
| Author-provided asset inspection, upload, and embedding | [Image Assets](image-assets.md) |
| Cross-artifact red lines | [Prompt Contracts](prompt-contracts.md) |
| Observable phase and finalization checks | [Review Checklist](review-checklist.md) |

## Authoring Control Inputs

- `course_author_name`, `course_profile`, `delivery_constraints`, and `authoring_constraints` provide author, course, and content-generation context.
- `interaction_policy`, `delivery_mode`, and `listen_mode_enabled` are normalized by Course Design Intake.
- `execution_mode` is selected here before the active phase runs; it becomes part of `authoring_run_controls` only when the route also runs Course Design Intake.
- `target_language` is resolved through `session-controls.md#output-language`.

Field shapes, compatibility mappings, and enums are authoritative in `data-contracts.md#input-compatibility-normalization`, `data-contracts.md#course-design-controls`, and `data-contracts.md#authoring-constraints`.
