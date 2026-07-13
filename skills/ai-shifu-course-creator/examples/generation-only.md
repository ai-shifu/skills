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
  "teaching_prompt": "Ask the learner to recall a recent fix and name the first signal they checked afterward.\n\nCreate a comparison slide with three columns: p95 latency trend, error-rate slope, and lock-wait drop. For each column, show the expected movement after a successful fix and one misleading interpretation.\n\nExplain that a useful verification signal must respond to the changed mechanism, move within the observation window, and have a clear failure threshold.\n\nAsk the learner to choose the fastest signal that proves the fix works.\n---\n?[p95 latency trend | error-rate slope | lock-wait drop]\n---\nAfter the learner answers, use the selected signal as the first verification checkpoint and explain why the other two signals are secondary for that case.\n\nHave the learner write a one-sentence verification rule containing the signal, expected movement, observation window, and stop condition. Close by restating that a fix is not complete until its expected effect is observed.",
  "used_variables": [],
  "depends_on_lessons": ["L01"]
}
```

Rendered `teaching_prompt` value:

```md
Ask the learner to recall a recent fix and name the first signal they checked afterward.

Create a comparison slide with three columns: p95 latency trend, error-rate slope, and lock-wait drop. For each column, show the expected movement after a successful fix and one misleading interpretation.

Explain that a useful verification signal must respond to the changed mechanism, move within the observation window, and have a clear failure threshold.

Ask the learner to choose the fastest signal that proves the fix works.
---
?[p95 latency trend | error-rate slope | lock-wait drop]
---
After the learner answers, use the selected signal as the first verification checkpoint and explain why the other two signals are secondary for that case.

Have the learner write a one-sentence verification rule containing the signal, expected movement, observation window, and stop condition. Close by restating that a fix is not complete until its expected effect is observed.
```

## Degraded Input

Degraded-input handling for this phase (fallback lesson JSON with `fallback_mode` / `assumptions` / `upgrade_notes`): see `examples/fallback-mode.md` → Generation Fallback.

## Acceptance Notes

- At least one interaction drives current-lesson text changes.
- Core idea includes visual-plus-text explanation in final script.
- Interaction count stays within declared limits.
