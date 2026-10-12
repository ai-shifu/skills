# Data Contracts

Authoritative source for shared authoring inputs, source-span and variable shapes, enum values, and cross-field invariants. Each workflow owns its phase-specific outputs and fallback extensions; course-directory and import formats belong to `cli/course-directory-spec.md`.

## Required References

None.

## Input Contract

Optional context supplied by the author or normalized by Course Design Intake:

- Learner persona.
- Lesson granularity preference (`short`, `medium`, `long`).
- Tone constraints.
- Non-negotiable source fragments.
- `course_author_name` (string): the optional name the author wants the Teaching Agent to use as the teacher identity during course delivery. A blank or unanswered value normalizes to an empty string, which produces no named teacher identity in the Course Prompt.
- `course_author_avatar_source` (local path or attached-file reference): an optional, transient platform-management handoff. Accept only a JPG or PNG source. Do not serialize it into a Teaching Prompt, Course Prompt, course directory, import payload, or platform metadata; after the course exists, consume it through `set-avatar` and retain only the returned platform avatar URL in platform state and `course-config.json` when synchronized.
- `course_profile` object.
- `delivery_constraints` object.
- `interaction_policy` object.
- `personalization_directions` (array of strings): a course-wide, transient authoring input selecting which aspects of teaching may adapt to learner background and preferences. It does not control teaching or slide structure.

### Personalization Directions

`personalization_directions` is a top-level, duplicate-free array of strings and a transient authoring input. It is not a member of `course_profile`, `delivery_constraints`, or `interaction_policy`. Each entry must be one of the following enum values; author-facing names and behavior belong to `prompt-contracts.md#personalization-directions`.

| Value             |
| ----------------- |
| `examples`        |
| `analogies`       |
| `language_style`  |
| `value_relevance` |

Array order has no behavioral meaning. An empty array explicitly selects no background-based personalization; an absent field is unresolved, not an empty selection. Reject non-array values, non-string entries, unknown values, and duplicates rather than coercing them. Intake owns collection and skip handling. The former `teaching_prompt_personalization_level` is not a valid substitute for this array and has no numeric mapping to directions; intake owns handling an old selection.

This is a content-expression control, not a structure control. It never changes the internal lesson execution plan, including the teaching sequence, required actions and effects, slide count and order, or interaction and feedback placement.

Pass the normalized selection unchanged through the in-memory authoring handoff to Teaching Prompt and Course Prompt generation and, when applicable, optimization review. Materialize its teaching effects as direct runtime instructions. Keep the control's name, enum array, and authoring semantics absent from Prompt bodies, output fields, course-directory files, CLI inputs or configuration, all build or deployment payloads including `shifu-import.json`, and platform metadata. In particular, do not serialize this control as a field in `lesson_teaching_prompts`, `course_index`, `global_variable_table`, `course_prompt`, `course_description`, or fallback output extensions.

### Interaction Policy

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

- `mode` is required and must be exactly `enabled`, `disabled`, or `unspecified`.
- `purposes` is required, duplicate-free, and may contain only `learner_context`, `pre_content_thinking`, and `lesson_end_self_check`.
- `enabled` requires a non-empty `purposes` array. `disabled` and `unspecified` require an empty `purposes` array.

## Source Spans

Source tracking shared by Segmentation, source preservation, and course-index construction uses these fields:

- `preserve_block` (boolean, required) — `true` exactly when the source span is selected as immutable; otherwise `false`.
- `source_span` (object, required):
  - `source_id` (string, required).
  - `start` (non-negative integer, required) — inclusive character offset.
  - `end` (integer greater than `start`, required) — exclusive character offset.

Entries in `course_index.source_span_map` use the same `source_span` object shape.

## Variable Table

`global_variable_table` is an array. Each item contains:

- `name` (string, required) — the name referenced by `{{var}}` or `?[%{{var}} ...]`; letters, numbers, and underscores only.
- `collected_in` (string, required) — `lesson_id` where the variable is first collected.
- `used_in` (array of strings, required) — every lesson that references the variable through `{{var}}`, plus reserved value `course_prompt` when the Course Prompt references it. Include `collected_in` only if that lesson also references `{{var}}` after collection.
- `effect_scope` (string constant `cross_lesson`, required).

Only named variables belong in `global_variable_table`; no-variable `?[...]` interactions do not create entries. Every referenced learner-answer variable has exactly one variable-backed collection and one matching table entry. Every table entry has cross-lesson or Course Prompt use and lists every consumer in `used_in`.
