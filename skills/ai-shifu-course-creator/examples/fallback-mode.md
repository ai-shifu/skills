# Fallback Mode Example

> Note: This example is illustrated in English; actual output follows [Output Language](../references/session-controls.md#output-language).

Select fallback through [Authoring Controls](../references/authoring-controls.md), apply the extensions owned by [Data Contracts](../references/data-contracts.md#fallback-output-extensions), and validate through the [Review Checklist](../references/review-checklist.md).

Demonstrates degraded-input handling across the four phases. This file is the single home for complete fallback scenarios; phase-only examples point to the matching section instead of restating fallback behavior.

## Segmentation Fallback: Conflicting Sources

```json
{
  "course_material": "doc-a: retries should stop after 3 attempts...\ndoc-b: retries can continue until queue drains...\ndoc-c: [image:failure-matrix.png]",
  "execution_mode": "fallback",
  "lesson_count_target": 1,
  "course_profile": {
    "audience_level": "intermediate",
    "lesson_duration_minutes": 15
  },
  "delivery_constraints": {
    "must_cover_topics": ["stop condition design"],
    "non_negotiable_fragments": ["[image:failure-matrix.png]"]
  }
}
```

Output includes uncertainty markers and rerun hints; preserved blocks survive even under fallback:

```json
{
  "structured_segments_json": [
    {
      "segment_id": "S10",
      "segment_type": "concept",
      "core_point": "Retry stop conditions differ across sources.",
      "preserve_block": false,
      "source_span": {"source_id": "course_material", "start": 0, "end": 96},
      "transfer_signals": {
        "concept_conflict": "The sources disagree on whether retries stop at a fixed count or when the queue drains.",
        "boundary_cue": "Do not choose a stop condition until the authoritative policy is confirmed."
      },
      "uncertainty": "high"
    },
    {
      "segment_id": "S11",
      "segment_type": "image",
      "core_point": "Failure matrix image preserved",
      "preserve_block": true,
      "source_span": {"source_id": "course_material", "start": 104, "end": 130},
      "transfer_signals": {
        "visual_cue": "Preserve the failure matrix as the visual comparison surface.",
        "visual_text_pair_cue": "Explain which cells support each proposed retry boundary."
      },
      "uncertainty": "low"
    }
  ],
  "preserve_block_index": [
    {"block_id": "B10", "segment_id": "S11", "type": "image"}
  ],
  "lesson_cut_candidates": [
    {
      "lesson_id": "L01",
      "segment_ids": ["S10", "S11"],
      "core_question": "Which retry boundary is supported by the authoritative policy?"
    }
  ],
  "rerun_hints": [
    "Provide authoritative policy for max retry attempts.",
    "Confirm whether queue-drain mode is allowed in this course."
  ]
}
```

## Orchestration Fallback: Incomplete Input

```json
{
  "course_material": "doc-1: classify by latency tiers\n\ndoc-2: classify by resource contention\n\ndoc-3: missing section ordering",
  "authoring_run_controls": {
    "execution_mode": "fallback",
    "delivery_mode": "standard",
    "listen_mode_enabled": false,
    "chapter_count_target": 1,
    "lesson_count_target": 1,
    "interaction_policy": {"mode": "unspecified", "purposes": []}
  },
  "authoring_constraints": {
    "lesson_granularity": "medium"
  }
}
```

Pipeline produces partial but runnable output:

```json
{
  "authoring_run_controls": {
    "execution_mode": "fallback",
    "delivery_mode": "standard",
    "listen_mode_enabled": false,
    "chapter_count_target": 1,
    "lesson_count_target": 1,
    "interaction_policy": {"mode": "unspecified", "purposes": []}
  },
  "lesson_teaching_prompts": [
    {
      "lesson_id": "L03",
      "lesson_title": "Choose a Classification Axis",
      "teaching_prompt": "Ask the learner to select a first-pass classification rule before comparing the two taxonomies.\n---\n?[latency first | contention first]\n---\nAfter the learner answers, begin with the selected taxonomy, compare where each taxonomy is reliable, and state that the evidence is partial. Close by asking the author to confirm one canonical taxonomy before the final pass.",
      "used_variables": [],
      "depends_on_lessons": [],
      "fallback_mode": true,
      "assumptions": ["The two supplied taxonomies are both provisional."],
      "upgrade_notes": ["Confirm the canonical taxonomy and source ordering."]
    }
  ],
  "course_index": [
    {
      "lesson_id": "L03",
      "lesson_title": "Choose a Classification Axis",
      "core_question": "When should you prefer latency tiers over contention classes?",
      "source_span_map": [
        {"source_id": "course_material", "start": 0, "end": 32},
        {"source_id": "course_material", "start": 34, "end": 72}
      ],
      "uncertainty": "medium"
    }
  ],
  "global_variable_table": [],
  "rerun_plan": {
    "lessons_to_rerun": ["L03"],
    "reason": "conflicting taxonomy across doc-1 and doc-2"
  }
}
```

## Generation Fallback: Minimal Segments

```json
{
  "course_material": "structured_lesson_segments",
  "authoring_run_controls": {
    "execution_mode": "fallback",
    "delivery_mode": "standard",
    "listen_mode_enabled": false,
    "chapter_count_target": 1,
    "lesson_count_target": 1,
    "interaction_policy": {
      "mode": "enabled",
      "purposes": ["pre_content_thinking"]
    }
  },
  "authoring_constraints": {
    "max_interactions": 2,
    "must_use_viewpoint_check": true,
    "allow_cross_lesson_dependency": false
  },
  "delivery_constraints": {
    "platform_limits": ["markdown_only"]
  }
}
```

```json
{
  "lesson_teaching_prompts": [
    {
      "lesson_id": "L07",
      "lesson_title": "Pick a Rollback Trigger",
      "teaching_prompt": "Pick a rollback trigger that minimizes blast radius.\n---\n?[latency spike threshold | error budget burn threshold]\n---\nAfter the learner answers, define one immediate rollback condition and one follow-up diagnostic for the selected trigger.",
      "used_variables": [],
      "depends_on_lessons": [],
      "fallback_mode": true,
      "assumptions": [
        "No cross-lesson variable carryover is used.",
        "One viewpoint check is enough for this pass."
      ],
      "upgrade_notes": [
        "Add richer evidence chain after full source context is available."
      ]
    }
  ]
}
```

## Optimization Fallback: No Source Material

```json
{
  "existing_teaching_prompt": "## Goal\nPick a fix.\n---\n?[%{{fix_choice}} option A | option B]\n---\n?[%{{choose_fix}} option A | option B]\n---\nUse {{fix_context}} now.",
  "course_material": "",
  "authoring_run_controls": {
    "execution_mode": "fallback",
    "delivery_mode": "standard",
    "listen_mode_enabled": false,
    "chapter_count_target": null,
    "lesson_count_target": 1,
    "interaction_policy": {"mode": "unspecified", "purposes": []}
  },
  "authoring_constraints": {
    "minimize_optimization_scope": true
  },
  "delivery_constraints": {
    "platform_limits": ["markdown_only"]
  }
}
```

```json
{
  "risk_and_issue_report": {
    "overall_risk": "high",
    "blocking_issues": [
      "variable_or_syntax_risk",
      "semantic_duplicate_interactions"
    ],
    "suggestions": [],
    "coverage_status": "unknown_without_source"
  },
  "change_list": [
    {
      "issue_class": "variable_or_syntax_risk",
      "change": "remove the learner-answer reference with no collection contract and keep one canonical no-variable interaction"
    }
  ],
  "lesson_teaching_prompts": [
    {
      "lesson_id": "L01",
      "lesson_title": "Choose a Safe First Fix",
      "teaching_prompt": "Pick one safe first fix.\n---\n?[option A | option B]\n---\nAfter the learner answers, apply one verification step before rollout.",
      "used_variables": [],
      "depends_on_lessons": [],
      "fallback_mode": true,
      "assumptions": ["The source is unavailable, so the correction is limited to runtime safety."],
      "upgrade_notes": ["Provide source material for a coverage and meaning audit."]
    }
  ],
  "follow_up": [
    "Provide source material for full coverage and meaning audit."
  ]
}
```

## Acceptance Notes

- Each phase degrades gracefully instead of failing hard.
- Uncertainty is marked explicitly, never silently merged.
- Rerun hints guide the user toward resolution.
- Output schemas remain compatible across standard and fallback modes.
- The `course_prompt` artifact is omitted when `course_material` is empty, as verified by [Optimization Validation](../references/review-checklist.md#optimization-validation).
