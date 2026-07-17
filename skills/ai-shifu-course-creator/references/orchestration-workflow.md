# Orchestration Workflow

Drive Segmentation and Teaching Prompt generation, then produce the cross-lesson course index and global variable table. This file coordinates phases; it does not redefine their rules.

## Required References

- `language-policy.md`
- `authoring-mode.md#mode-selection`
- `data-contracts.md#output-contract`
- `data-contracts.md#variable-table`
- `data-contracts.md#orchestration-fallback-fields`
- `segmentation-workflow.md`
- `teaching-prompt.md`
- `pedagogy.md`

## Workflow

1. Normalize source ordering and merge the input material.
2. Run Segmentation and retain its traceable segments and lesson-boundary candidates.
3. Finalize lesson cuts with one core question per lesson.
4. Run Teaching Prompt generation for each lesson.
5. Build `course_index` and `global_variable_table` from the completed lesson set.
6. Apply the gates below. Rerun the phase that owns each failed output rather than treating every failure as a lesson-only generation failure.
7. After every affected Segmentation and Teaching Prompt rerun passes, rebuild both `course_index` and `global_variable_table`, then reapply the gates. Block handoff while any gate still fails.

## Mandatory Gates

- Verify syntax and runtime results through the requirements loaded by `teaching-prompt.md`.
- Verify every learner-answer variable against `data-contracts.md#variable-table`.
- Verify the selected teaching loop, interaction effects, variable-persistence decisions, and delivery-mode behavior against `pedagogy.md`.
- Require Segmentation's preservation validation to pass.
- Verify every required interaction effect and branch against `pedagogy.md#interaction-design`.

Do not partially pass a phase or lesson.

## Rerun Rules

- When a preservation, traceability, or lesson-boundary gate fails, rerun Segmentation for the affected source scope, then rerun every Teaching Prompt affected by the changed segments or lesson cuts.
- When a Teaching Prompt authoring or runtime gate fails, rerun only the affected lesson and any dependency-linked lessons.
- After a rerun changes lesson boundaries, variables, or their consumers, rebuild both cross-lesson outputs from the passing lesson set; never hand off a stale `course_index` or `global_variable_table`.
- Recompute the full course only when global source order changes. If an owning phase cannot pass after its focused rerun, stop and report the blocking gate instead of handing off partial outputs.

## Fallback Handling

Under fallback mode, deliver coarse lesson drafts, mark uncertain `course_index` entries, and emit the `rerun_plan` defined in `data-contracts.md#orchestration-fallback-fields`. Keep best-effort work separate from artifacts that passed all gates.

## Outputs

Produce `lesson_teaching_prompts`, `course_index`, and `global_variable_table` exactly as defined in `data-contracts.md#output-contract`.

Keep these as structured phase-handoff data. When a local course directory is materialized, follow the closed artifact set owned by `cli/course-directory-spec.md`.

## Validation

- All three Orchestration outputs are present and mutually consistent.
- Every lesson passes the Mandatory Gates.
- Fallback outputs include the required uncertainty and rerun fields.
