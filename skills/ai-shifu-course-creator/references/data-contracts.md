# Data Contracts

Authoritative source for schemas crossing the skill boundary: input controls, normalized authoring decisions, generated artifacts, intermediate records, and fallback extensions. This file defines shapes and field meanings only; it does not define teaching strategy, runtime syntax, delivery-mode behavior, or language policy.

## Contents

- [Input Contract](#input-contract)
- [Course Design Controls](#course-design-controls)
- [Output Contract](#output-contract)
- [Segmentation Output](#segmentation-output)
- [Generation Output](#generation-output)
- [Orchestration Output](#orchestration-output)
- [Optimization Output](#optimization-output)
- [Final Authoring Output](#final-authoring-output)
- [Segment Schema](#segment-schema)
- [Variable Table](#variable-table)
- [Lesson Schema](#lesson-schema)
- [Fallback Output Extensions](#fallback-output-extensions)

## Input Contract

### Required by Phase

- Segmentation requires a single source document or an explicitly ordered set of topic-aligned documents.
- Generation requires structured segments and lesson cuts from Segmentation, or an equivalent author-supplied lesson plan with traceable source material.
- Orchestration requires the Segmentation and Generation inputs plus normalized Course Design Controls.
- Optimization requires at least one existing Teaching Prompt or Course Prompt. Source material is optional for runtime/syntax review and required for claims about coverage, meaning preservation, or full-course finalization.

### Optional

- Learner persona.
- Lesson granularity preference (`short`, `medium`, `long`).
- Tone constraints.
- Non-negotiable source fragments.
- `course_author_name` (string): the course author's real name for the Course Prompt role.
- `course_profile` object.
- `delivery_constraints` object.
- `interaction_policy` object: normalized Course Design Intake result; see [Interaction Policy](#interaction-policy).
- `execution_mode` (string enum: `standard|fallback`).
- `delivery_mode` (string enum: `standard|pure_slides`).
- `listen_mode_enabled` (boolean).
- `chapter_count_target` (positive integer or `null`).
- `lesson_count_target` (positive integer or `null`).
- `target_language` (BCP-47 recommended, for example `fr-FR`, `ja-JP`, `zh-CN`).
- `authoring_run_controls` (object): normalized phase input using [Course Design Controls](#course-design-controls); workflows consume this object instead of re-reading the six raw control fields it replaces.

Before Course Design Intake, callers may supply `execution_mode`, `delivery_mode`, `listen_mode_enabled`, `chapter_count_target`, `lesson_count_target`, and `interaction_policy` individually. After normalization, replace only those six raw fields with `authoring_run_controls` so consumers cannot observe conflicting control values. Continue carrying `course_material`, `course_author_name`, `course_profile`, `delivery_constraints`, `target_language`, tone constraints, and source constraints as unchanged authoring context alongside phase outputs; control normalization must not discard them.

### Recommended Object Shapes

#### `course_profile`

```json
{
  "audience_level": "beginner|intermediate|advanced",
  "prerequisite_level": "none|basic|strong",
  "lesson_duration_minutes": 12,
  "assessment_mode": "quiz|project|discussion|mixed"
}
```

#### `delivery_constraints`

```json
{
  "platform_limits": ["no_iframe", "markdown_only"],
  "must_cover_topics": ["topic-a", "topic-b"],
  "avoid_topics": ["topic-x"],
  "non_negotiable_fragments": ["required source fragment or code block id"]
}
```

#### Course Design Controls

`authoring_run_controls` is the canonical normalized object passed between phases on routes that run Course Design Intake. Course Design Intake resolves every field except `execution_mode`; Authoring Controls adds that field before Orchestration, Generation, or Optimization begins. A Segmentation-only route consumes its explicit `execution_mode` and structure target directly because delivery and interaction choices do not affect segmentation.

```json
{
  "execution_mode": "standard|fallback",
  "delivery_mode": "standard|pure_slides",
  "listen_mode_enabled": false,
  "chapter_count_target": null,
  "lesson_count_target": null,
  "interaction_policy": {
    "mode": "enabled|disabled|unspecified",
    "purposes": []
  }
}
```

- `execution_mode` is required for an authoring run and must be `standard` or `fallback`.
- `delivery_mode` is required after Course Design Intake and must be `standard` or `pure_slides`.
- `listen_mode_enabled` is required after Course Design Intake and must be `false` when `delivery_mode` is `pure_slides`.
- `chapter_count_target` and `lesson_count_target` are positive integers when explicitly supplied or inferred, otherwise `null`.

#### Interaction Policy

```json
{
  "mode": "enabled|disabled|unspecified",
  "purposes": [
    "learner_context",
    "pre_content_thinking",
    "lesson_end_self_check"
  ]
}
```

The normalized object is schema-valid only when all of these invariants hold:

- `mode` is required and must be exactly `enabled`, `disabled`, or `unspecified`.
- `purposes` is required, duplicate-free, and may contain only `learner_context`, `pre_content_thinking`, and `lesson_end_self_check`.
- `enabled` requires a non-empty `purposes` array; `disabled` and `unspecified` require an empty `purposes` array.

The schema ends at these invariants. Consumers pass the normalized object unchanged.

### Minimal Input Payload Example

```json
{
  "course_material": "long transcript or merged markdown",
  "course_author_name": "Author-provided real name",
  "interaction_policy": {
    "mode": "enabled",
    "purposes": ["learner_context"]
  },
  "execution_mode": "standard",
  "delivery_mode": "standard",
  "listen_mode_enabled": false,
  "chapter_count_target": 2,
  "lesson_count_target": 6,
  "course_profile": {
    "audience_level": "beginner",
    "lesson_duration_minutes": 10,
    "assessment_mode": "project"
  },
  "delivery_constraints": {
    "must_cover_topics": ["core workflow", "failure handling"]
  }
}
```

### Validation Rules

- Input files must be readable text or markdown.
- If multiple files are provided, ordering must be explicit.
- When multilingual content exists, validate `target_language` against `session-controls.md#output-language` before creating artifacts.
- `interaction_policy` must satisfy the mode/purpose invariants above before Generation or Optimization applies pedagogical gates.

## Output Contract

Each phase owns execution; this file owns the exact result that phase adds to the handoff. The handoff retains the unchanged authoring context defined in the Input Contract alongside these phase-owned results. A later phase extends an earlier handoff instead of dropping context or making every earlier phase satisfy the final-course schema.

### Segmentation Output

- `structured_segments_json` (array, required) — non-empty ordered array whose items satisfy [Segment Schema](#segment-schema).
- `preserve_block_index` (array, required) — entries shaped as `{block_id, segment_id, type}`; every entry points to a segment whose `preserve_block` is `true`, and every preserved segment appears once.
- `lesson_cut_candidates` (array, required) — entries shaped as `{lesson_id, segment_ids, core_question}`; `segment_ids` is non-empty and references only known segments, while `core_question` is one concise teachable question.

### Generation Output

- `lesson_teaching_prompts` (array, required) — one item per requested lesson, each satisfying [Lesson Schema](#lesson-schema) and the syntax/runtime behavior in the [MarkdownFlow Spec](markdownflow.md).

### Orchestration Output

- `authoring_run_controls` (object, required) — the schema-valid [Course Design Controls](#course-design-controls) object, carried forward unchanged.
- `lesson_teaching_prompts` (array, required) — complete course array from Generation.
- `course_index` (array, required) — one item per lesson using the schema below.
- `global_variable_table` (array, required) — complete cross-lesson table defined in [Variable Table](#variable-table).

### Optimization Output

- `risk_and_issue_report` (object, required) — `overall_risk` (`low|medium|high`), `blocking_issues` (duplicate-free array of issue-class strings), and `suggestions` (array of non-blocking improvement strings).
- `change_list` (array, required) — zero or more `{issue_class, change}` entries; each records one applied correction, and an audit with no changes returns an empty array.
- `lesson_teaching_prompts` (array, conditional) — required when Optimization rewrites lessons; omitted for report-only review.
- Full-course finalization also returns every field in [Final Authoring Output](#final-authoring-output).

### Final Authoring Output

Required after end-to-end or full-course authoring:

1. `authoring_run_controls` — unchanged normalized controls from Orchestration.
2. `lesson_teaching_prompts` — optimized Teaching Prompts.
3. `course_index` — lesson ordering, core questions, and source mapping.
4. `global_variable_table` — final cross-lesson variable lifecycle.
5. `course_prompt` — runnable course-level system prompt whose content and structure follow the [Course Prompt](course-prompt.md) owner.
6. `course_description` — concise learner-facing SEO/listing description covering the course topic, target learners, and concrete outcomes without author-side workflow notes.

### `course_index` Schema (array, required)

Each item:

- `lesson_id` (string, required)
- `lesson_title` (string, required)
- `core_question` (string, required)
- `source_span_map` (array of `{source_id, start, end}`, required)

### `course_prompt` (string, required)

- Non-empty Markdown string.
- Must satisfy the applicable base-template and delivery-profile contract before handoff.
- Stored as the single course-level prompt artifact; per-lesson content remains in `lesson_teaching_prompts`.

### `course_description` (string, required)

- One concise learner-facing SEO/listing description.
- Base it on the course topic, target learners, and concrete learning outcomes.

### Minimal Structured Artifact Excerpt

This excerpt shows the Final Authoring Output shape while leaving the independently validated `course_prompt` string out of the excerpt.

```json
{
  "authoring_run_controls": {
    "execution_mode": "standard",
    "delivery_mode": "standard",
    "listen_mode_enabled": false,
    "chapter_count_target": 1,
    "lesson_count_target": 1,
    "interaction_policy": {"mode": "enabled", "purposes": ["learner_context"]}
  },
  "lesson_teaching_prompts": [
    {
      "lesson_id": "L01",
      "lesson_title": "Core Loop Setup",
      "teaching_prompt": "Ask the learner for the one goal that should shape course-wide examples.\n---\n?[%{{learner_goal}} ...One-sentence goal]\n---\nThe learner goal is {{learner_goal}}. When the learner goal is UNKNOWN, continue with the default production example; otherwise use a first example that matches it.",
      "used_variables": ["learner_goal"],
      "depends_on_lessons": []
    }
  ],
  "course_index": [
    {
      "lesson_id": "L01",
      "lesson_title": "Core Loop Setup",
      "core_question": "What makes this loop stable in production?",
      "source_span_map": [{"source_id": "doc-1", "start": 120, "end": 286}]
    }
  ],
  "global_variable_table": [
    {
      "name": "learner_goal",
      "collected_in": "L01",
      "used_in": ["L01", "course_prompt"],
      "effect_scope": "cross_lesson"
    }
  ],
  "course_description": "A practical course that helps beginner operators diagnose metric drift, identify likely causes, and choose one concrete fix."
}
```

### Deployment Output

1. `deployed_course_url` — Platform URL of the deployed course.
2. `shifu_bid` — Course BID on the AI-Shifu platform.

#### `deployment_result` (object, optional)

- `shifu_bid` (string, required)
- `deployed_course_url` (string, required)
- `lesson_count` (number, required)
- `status` (string enum: `published|draft`, required)

### Delivery Guarantees

- Stable schema across reruns.
- Deterministic references for lesson ids and source spans.
- Partial rerun support for changed lessons.

## Segment Schema

Each item in the Segmentation output (consumed by Orchestration and Generation):

- `segment_id` (string, required) — stable identifier within the run.
- `segment_type` (string enum, required) — one of `concept` (explanation or definition), `example` (demonstration or walkthrough), `code` (executable or pseudo-code), `image` (image file or source reference), `exercise` (learner action), or `transition` (bridge between ideas).
- `core_point` (string, required) — the single teachable point this segment carries.
- `preserve_block` (boolean, required) — `true` for code, image, table, or required-quote blocks that must reach the lesson verbatim.
- `source_span` (object, required) — traceable source location with `source_id` (string), `start` (non-negative integer, inclusive character offset), and `end` (integer greater than `start`, exclusive character offset). Use the same object shape as entries in `course_index.source_span_map`.
- `transfer_signals` (object, required and non-empty) — include every applicable canonical key below, omit inapplicable keys, and use a non-empty concise string for every included value.

| Key | Field meaning |
|---|---|
| `learner_hook` | Teaching entry point available in the source. |
| `evidence_type` | Form of source evidence. |
| `visual_cue` | Source cue suitable for a slide. |
| `concept_conflict` | Misconception or contradiction to resolve. |
| `boundary_cue` | Validity boundary or exception. |
| `action_cue` | Action the learner can perform. |
| `density_cue` | High-density information that must not be compressed away. |
| `quote_cue` | Quotation that must remain exact. |
| `visual_text_pair_cue` | Required relationship between a visual and explanatory text. |
| `interaction_intent_cue` | Source-supported reason for an interaction. |
| `compare_cue` | Items or states that should be compared. |

## Variable Table

`global_variable_table` is an array. Each item:

- `name` (string, required) — the variable identifier referenced in `{{var}}` / `?[%{{var}} ...]`; it contains only letters, numbers, and underscores, and its human language follows `session-controls.md#output-language`.
- `collected_in` (string, required) — `lesson_id` where the variable is first collected.
- `used_in` (array of strings, required) — every lesson that references the variable through `{{var}}`, plus reserved value `course_prompt` when the Course Prompt artifact references it. Include `collected_in` only if that same lesson also references `{{var}}` after collecting it.
- `effect_scope` (string constant: `cross_lesson`, required).

Only named variables have entries in `global_variable_table`; no-variable interactions have no table entry. Every table entry has `effect_scope: "cross_lesson"`, and `used_in` includes `course_prompt` whenever that artifact references the variable.

## Lesson Schema

Each item in `lesson_teaching_prompts` (Generation per-lesson output):

- `lesson_id` (string, required) — stable, deterministic identifier.
- `lesson_title` (string, required) — concise learner-facing title.
- `teaching_prompt` (string, required) — the per-lesson Teaching Prompt content (written in MarkdownFlow); instructional/directive language only.
- `used_variables` (array of strings, required) — every named variable referenced or collected in this lesson; no-variable interactions are excluded. Cross-check with [Variable Table](#variable-table): each item here must have a matching `global_variable_table` entry, and that entry's `used_in` list must include this lesson when the variable is referenced outside the interaction line. If the Course Prompt references the same variable, `used_in` must also include `course_prompt`.
- `depends_on_lessons` (array of lesson ids, required) — explicit list; empty list if none.

### Minimal Example

```json
{
  "lesson_id": "L03",
  "lesson_title": "Diagnose the Bottleneck",
  "teaching_prompt": "Ask the learner where the system feels slow before naming any cause: CPU, IO, or locks.\n---\n?[CPU bound | IO bound | Lock contention]\n---\nAfter the learner answers, run the matching test first.",
  "used_variables": [],
  "depends_on_lessons": ["L02"]
}
```

## Fallback Output Extensions

When a phase runs under fallback mode, its standard output is augmented with the following fields. Standard-mode output omits these fields entirely; fallback-mode output adds them on top of the standard schema.

### Segmentation fallback fields

Per-segment (extends [Segment Schema](#segment-schema)):

- `uncertainty` (string enum: `low|medium|high`) — confidence on the segment's interpretation.

Top-level addition to the Segmentation output:

- `rerun_hints` (array of strings) — user-facing prompts describing what authoritative input would resolve the uncertainty.

### Orchestration fallback fields

Per-lesson (extends `course_index` items):

- `uncertainty` (string enum: `low|medium|high`).

Top-level addition:

- `rerun_plan` (object, required when any lesson is uncertain):
  - `lessons_to_rerun` (array of lesson ids).
  - `reason` (string) — why the rerun is needed.

### Generation fallback fields

Per-lesson (extends [Lesson Schema](#lesson-schema)):

- `fallback_mode` (boolean) — `true` when this lesson was generated under fallback.
- `assumptions` (array of strings) — assumptions made due to incomplete input.
- `upgrade_notes` (array of strings) — what additional input would upgrade this lesson.

### Optimization fallback fields

Inside `risk_and_issue_report`:

- `coverage_status` (string enum: `complete|partial|unknown_without_source`).

Top-level addition:

- `follow_up` (array of strings) — required inputs to complete a full-coverage audit.
