# Author Controls and Artifact Invariants

Optional controls express author intent; artifact invariants protect reusable, runnable courses. These are not a required authoring pipeline or intermediate exchange format. The actual course files and CLI payloads are defined in [cli/course-directory-spec.md](cli/course-directory-spec.md).

## Input Contract

Use whatever the task provides: source material, a course brief, an outline, existing artifacts, or a platform course. No particular document set or structured control object is required to begin useful work.

Optional context includes audience, prerequisites, lesson granularity, tone, desired chapter or lesson counts, delivery experience, required topics, excluded topics, and exact source fragments. Two useful optional objects are:

- `course_profile`: audience level, prerequisite level, lesson duration or count preferences, and assessment intent.
- `delivery_constraints`: platform limits, must-cover topics, avoided topics, and non-negotiable source fragments.

Their absence does not require collection. Preserve explicit author constraints; ask or state a consequential assumption when available context cannot resolve them. [course-design-choices.md](course-design-choices.md) describes the available choices and their effects.

`course_author_name` is an optional teacher identity. A blank or absent value means no named identity in the Course Prompt. `course_author_avatar_source` is an optional transient JPG or PNG attachment/path for platform avatar management. Do not serialize the local avatar source into course content, any course-directory file, an import payload, or platform metadata. Consume it through [avatar management](course-management.md#operations) after the course exists; synchronized state may retain only the returned platform avatar URL.

### Personalization Directions

When a structured `personalization_directions` control is used, it is a duplicate-free array containing only:

| Value             | Meaning                    |
| ----------------- | -------------------------- |
| `examples`        | Examples / 举例            |
| `analogies`       | Analogies / 类比           |
| `language_style`  | Language style / 语言风格  |
| `value_relevance` | Practical value / 价值阐述 |

Order has no meaning. `[]` explicitly selects no individual-background personalization. Reject invalid types, unknown values, and duplicates instead of silently broadening the selection. An absent field leaves the agent to resolve the intended behavior from the request or existing course; it does not mandate a question or enable every direction.

The effects and boundaries belong to [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions). Materialize the resolved effects as runtime instructions. Keep this transient field name, enum array, and selection rationale out of Prompt bodies, course-directory files, CLI configuration, import payloads, and platform metadata.

### Interaction Policy

If a structured `interaction_policy` is useful, use:

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

- `mode` is exactly `enabled`, `disabled`, or `unspecified`.
- `purposes` is duplicate-free and contains only the three values shown.
- `enabled` has at least one purpose; `disabled` and `unspecified` have an empty array.

This optional representation does not make those three purposes exhaustive for unconstrained agent-designed teaching. Explicit author restrictions remain binding; [teaching-design.md#interaction-policy-precedence](teaching-design.md#interaction-policy-precedence) explains their effects.

## Artifact Invariants

- Teaching Prompts contain executable lesson instructions in MarkdownFlow; Course Prompts contain shared course instructions; descriptions contain learner-facing listing prose. [prompt-semantics.md#artifact-responsibilities](prompt-semantics.md#artifact-responsibilities) defines the boundary.
- Produce the artifacts required by the task. A single lesson or a pasted Prompt body does not require a full-course envelope, `course_index`, segment list, variable-table JSON, or uncertainty extensions.
- A complete authored course includes its lesson content, Course Prompt, learner-facing description, and suitable course/chapter structure. Use the recognized directory files when materializing it; do not invent additional manifest files to preserve authoring state.
- Course hierarchy and platform lesson titles belong in structure metadata. Source-only navigation and explanatory comments are defined in [teaching-prompt.md](teaching-prompt.md); runtime content must not exist only in a removed comment.
- Keep authoring assumptions and incomplete work separate from claims that an artifact is ready. Uncertainty may be explained directly without a fixed fallback schema.

## Variable Table

Named learner-answer variables need consistent collection and use, whether checked directly in the artifacts or recorded in optional bookkeeping:

- Names use letters, numbers, and underscores. Preserve existing names when renaming would break consumers.
- A named answer has a valid `%{{name}}` collection and a real use outside its collection lesson, including a Course Prompt reference. Lesson-local answers use unnamed interactions.
- Every `{{name}}` reference has an identified collection and meaningful consumer. Reuse an existing value instead of collecting a semantic duplicate; repeated collection needs an intentional staged-comparison purpose.
- If a table is helpful, record the name, collection lesson, and every consuming lesson or Course Prompt. No `global_variable_table` or `used_variables` envelope is required.
- Handle unavailable values without inventing them or testing whether the template marker exists.

Variable-persistence decisions belong to [teaching-design.md#variable-strategy](teaching-design.md#variable-strategy); MarkdownFlow owns collection and substitution syntax.
