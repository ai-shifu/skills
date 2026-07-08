# Generation Only Example

> Note: Outputs in this example are illustrated in English for clarity. Actual output language follows `references/data-contracts.md#language-resolution` (e.g., Chinese invocation → Chinese output).

## Minimal Input

```json
{
  "course_material": "structured_lesson_segments",
  "teaching_constraints": {
    "max_interactions": 4,
    "require_visual_text_pair": true
  },
  "course_profile": {
    "audience_level": "beginner",
    "lesson_duration_minutes": 10
  },
  "delivery_constraints": {
    "interaction_density": "medium"
  }
}
```

Structured segments provided:

```json
[
  {
    "lesson_id": "L02",
    "core_question": "How do you verify that a fix removed the bottleneck?",
    "segment_ids": ["S21", "S22"]
  }
]
```

## Output Snapshot

```json
{
  "lesson_id": "L02",
  "lesson_title": "Verify the Fix",
  "teaching_prompt": "Choose the fastest signal that proves the fix works.\n---\n?[p95 latency trend | error-rate slope | lock-wait drop]\n---\nAfter the learner answers, use the selected signal as the first verification checkpoint.",
  "used_variables": [],
  "depends_on_lessons": ["L01"]
}
```

Rendered `teaching_prompt` value:

```md
Choose the fastest signal that proves the fix works.
---
?[p95 latency trend | error-rate slope | lock-wait drop]
---
After the learner answers, use the selected signal as the first verification checkpoint.
```

## Degraded Input

Degraded-input handling for this phase (fallback lesson JSON with `fallback_mode` / `assumptions` / `upgrade_notes`): see `examples/fallback-mode.md` → Generation Fallback.

## Acceptance Notes

- At least one interaction drives current-lesson text changes.
- Core idea includes visual-plus-text explanation in final script.
- Interaction count stays within declared limits.
