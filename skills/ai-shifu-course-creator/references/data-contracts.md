# Data Contracts

Authoritative source for all schemas crossing the skill boundary: what comes in (input), what goes out (output), how `resolved_target_language` is derived, and the per-lesson and per-variable shapes.

## Input Contract

### Required

Provide one of:

- A single long transcript or course document.
- A set of topic-aligned documents with intended order.

### Optional

- Learner persona.
- Lesson granularity preference (`short`, `medium`, `long`).
- Tone constraints.
- Non-negotiable source fragments.
- `course_author_name` (string): the course author's real name for the Course
  Prompt role. If absent when a Course Prompt must be generated, ask the author
  instead of inventing a persona name.
- `course_profile` object.
- `delivery_constraints` object.
- `interaction_policy` object: normalized Course Design Intake result; see [Interaction Policy](#interaction-policy).

### Recommended Object Shapes

#### `course_profile`

```json
{
  "audience_level": "beginner|intermediate|advanced",
  "prerequisite_level": "none|basic|strong",
  "lesson_duration_minutes": 12,
  "lesson_count_target": 8,
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

This section owns only the normalized data shape and enum constraints. Course Design Intake resolves the object once and passes it unchanged to Generation and Optimization:

- `mode` is required and must be exactly `enabled`, `disabled`, or `unspecified`.
- `purposes` is required, duplicate-free, and may contain only `learner_context`, `pre_content_thinking`, and `lesson_end_self_check`.
- `enabled` requires a non-empty `purposes` array; `disabled` and `unspecified` require an empty `purposes` array.

The teaching effects, purpose placements, and non-interactive substitutions are defined in [pedagogy.md#interaction-policy-precedence](pedagogy.md#interaction-policy-precedence).

### Validation Rules

- Input files must be readable text or markdown.
- If multiple files are provided, ordering must be explicit.
- `interaction_policy` must satisfy the mode/purpose invariants above before Generation or Optimization applies pedagogical gates.

## Output Contract

### Required Artifacts

1. `lesson_teaching_prompts` — one Teaching Prompt per lesson (written in MarkdownFlow). Each Prompt follows [prompt-contracts.md#prompt-semantics](prompt-contracts.md#prompt-semantics) and the [Lesson Schema](#lesson-schema).
2. `course_index` — `lesson_id`, `lesson_title`, `core_question`, `source_span_map`.
3. `global_variable_table` — see [Variable Table](#variable-table).
4. `course_prompt` — course-level Markdown string; see [course-prompt.md](course-prompt.md) for its artifact contract and authoring rules.
5. `course_description` — learner-facing SEO/listing description written to `course-description.md`.

### `course_index` Schema (array, required)

Each item:

- `lesson_id` (string, required)
- `lesson_title` (string, required) — learner-facing title written in `resolved_target_language`.
- `core_question` (string, required) — human-readable lesson question written in `resolved_target_language`.
- `source_span_map` (array of `{source_id, start, end}`, required)

### `course_prompt` (string, required)

Required for full-course authoring. Its six section headings, fill values, and instruction text use `resolved_target_language`; exact source quotations, code, URLs, and stable MarkdownFlow syntax remain unchanged.

### `course_description` (string, required)

Required for full-course authoring. Write the learner-facing description in `resolved_target_language` to `course-description.md`; its directory contract and build mapping are defined in [course-directory-spec.md](cli/course-directory-spec.md#course-descriptionmd).

## Segment Schema

Each item in the Segmentation output (consumed by Orchestration and Generation):

- `segment_id` (string, required) — stable identifier within the run.
- `segment_type` (string enum, required) — must satisfy [Segment Types](#segment-types).
- `core_point` (string, required) — the single teachable point this segment carries, written in `resolved_target_language`.
- `preserve_block` (boolean, required) — `true` when the source span is selected as immutable by [optimization-workflow.md#preservation-decisions](optimization-workflow.md#preservation-decisions). The field records the decision; downstream MarkdownFlow behavior is defined in [markdownflow.md#preservation](markdownflow.md#preservation).
- `source_span` (object, required) — traceable source location with `source_id`
  (string), `start` (non-negative integer, inclusive character offset), and `end`
  (integer greater than `start`, exclusive character offset). Use the same object
  shape as entries in `course_index.source_span_map`.
- `transfer_signals` (object, required) — must satisfy [Transfer Signals](#transfer-signals).

### Segment Types

`segment_type` must use exactly one of these canonical values:

| Value | Meaning |
|---|---|
| `concept` | Explanatory statements and definitions. |
| `example` | Concrete demonstrations and walkthroughs. |
| `code` | Executable or pseudo-code blocks. |
| `image` | Image files and their source references. |
| `exercise` | Learner action prompts. |
| `transition` | Bridge text that links ideas. |

### Transfer Signals

`transfer_signals` must be non-empty. Include every applicable canonical key, omit inapplicable keys rather than inventing content, and give every included key a non-empty, concise string value in `resolved_target_language`. Preserve an exact source quotation or other immutable source span when the signal intentionally carries it verbatim.

| Key | Meaning |
|---|---|
| `learner_hook` | Teaching entry point. |
| `evidence_type` | Form of source evidence. |
| `visual_cue` | Cue for expressing the segment as a slide. |
| `concept_conflict` | Conceptual conflict or misconception. |
| `boundary_cue` | Applicability boundary. |
| `action_cue` | Executable application. |
| `density_cue` | Information that must not be compressed away. |
| `quote_cue` | Quotation that should be preserved or used. |
| `visual_text_pair_cue` | Division of work between slide and text. |
| `interaction_intent_cue` | Interaction purpose and expected instructional effect. |
| `compare_cue` | Comparison objects or dimensions. |

For segmentation rules and methodology, see [segmentation-orchestration.md#segmentation-methodology](segmentation-orchestration.md#segmentation-methodology).

## Variable Table

`global_variable_table` is an array. Each item:

- `name` (string, required) — the variable name as referenced in `{{var}}` / `?[%{{var}} ...]`; new variable names use `resolved_target_language` and are composed of letters, numbers, and underscores.
- `collected_in` (string, required) — `lesson_id` where the variable is first collected.
- `used_in` (array of strings, required) — every lesson that references the variable through `{{var}}`, plus reserved value `course_prompt` when `course-prompt.md` references it. Include `collected_in` only if that same lesson also references `{{var}}` after collecting it.
- `effect_scope` (string constant: `cross_lesson`, required).

Only named variables belong in `global_variable_table`; no-variable `?[...]` interactions do not create table entries. Every learner-answer variable referenced by a lesson or Course Prompt has one variable-backed collection and one matching table entry. Every table entry has `effect_scope: "cross_lesson"`, names its first collection lesson, and lists every downstream lesson plus `course_prompt` when applicable. A table entry with no cross-lesson or Course Prompt use is invalid. Variable collection, reuse, and pacing decisions are defined in [pedagogy.md#variable-strategy](pedagogy.md#variable-strategy); parser recognition and runtime substitution semantics (`{{var}}` → stored value or `UNKNOWN`) are defined in [markdownflow.md#variables](markdownflow.md#variables).

## Lesson Schema

Each item in `lesson_teaching_prompts` (Generation per-lesson output):

- `lesson_id` (string, required) — stable, deterministic identifier.
- `lesson_title` (string, required) — concise learner-facing title written in `resolved_target_language`. Chapter titles, lesson titles, numbering, hierarchy labels, and ordering markers belong in `course_index` / `structure.json`; do not duplicate them in the Teaching Prompt body.
- `teaching_prompt` (string, required) — the per-lesson Teaching Prompt content, with authored natural-language instructions and learner-facing text written in `resolved_target_language` and MarkdownFlow syntax kept stable; apply [prompt-contracts.md#prompt-semantics](prompt-contracts.md#prompt-semantics).
- `used_variables` (array of strings, required) — every named variable referenced or collected in this lesson; no-variable interactions are excluded. Cross-check with [Variable Table](#variable-table): each item here must have a matching `global_variable_table` entry, and that entry's `used_in` list must include this lesson when the variable is referenced outside the interaction line. If the Course Prompt references the same variable, `used_in` must also include `course_prompt`.
- `depends_on_lessons` (array of lesson ids, required) — explicit list; empty list if none.

## Language Resolution

`resolved_target_language` is a string derived for the current request; it is not an input field or an output artifact field. All downstream references to the selected language use `resolved_target_language`.

### Priority Order

Determine `resolved_target_language` with these two rules:

1. `context_language_directive` — any applicable context explicitly specifies a language, including the current prompt, project or system instructions, earlier conversation turns, and directives from the calling agent. When explicit directives conflict, follow the normal instruction hierarchy; at the same authority level, use the most recent applicable directive.
2. `prompt_language_detection` — otherwise, the language detected from the current user prompt.

## Fallback Output Extensions

When a phase runs under fallback mode (see `authoring-controls.md#execution-modes`), its standard output is augmented with the following fields. Standard-mode output omits these fields entirely; fallback-mode output adds them on top of the standard schema.

### Segmentation fallback fields

Per-segment (extends [Segment Schema](#segment-schema)):

- `uncertainty` (string enum: `low|medium|high`) — confidence on the segment's interpretation.

Top-level addition to the Segmentation output:

- `rerun_hints` (array of strings) — user-facing prompts in `resolved_target_language` describing what authoritative input would resolve the uncertainty.

### Orchestration fallback fields

Per-lesson (extends `course_index` items):

- `uncertainty` (string enum: `low|medium|high`).

Top-level addition:

- `rerun_plan` (object, required when any lesson is uncertain):
  - `lessons_to_rerun` (array of lesson ids).
  - `reason` (string) — why the rerun is needed, written in `resolved_target_language`.

### Generation fallback fields

Per-lesson (extends [Lesson Schema](#lesson-schema)):

- `fallback_mode` (boolean) — `true` when this lesson was generated under fallback.
- `assumptions` (array of strings) — assumptions made due to incomplete input, written in `resolved_target_language`.
- `upgrade_notes` (array of strings) — what additional input would upgrade this lesson, written in `resolved_target_language`.

### Optimization fallback fields

Inside `risk_and_issue_report`:

- `coverage_status` (string enum: `complete|partial|unknown_without_source`).

Top-level addition:

- `follow_up` (array of strings) — required inputs in `resolved_target_language` to complete a full-coverage audit.

For the four end-to-end fallback scenarios, see `examples/fallback-mode.md`.
