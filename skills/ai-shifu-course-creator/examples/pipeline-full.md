# Full Pipeline Example (Course Target Resolution → Deployment)

> Note: Outputs in this example are illustrated in English for clarity. Actual output language follows `references/data-contracts.md#language-resolution` (e.g., Chinese invocation → Chinese output).

## Input Payload (example)

```json
{
  "course_material": "Module transcript: observe metric drift, classify causes, apply one fix, review impact.",
  "generation_constraints": {
    "persona": "practical coach",
    "lesson_granularity": "short"
  },
  "course_profile": {
    "audience_level": "beginner",
    "lesson_duration_minutes": 10,
    "lesson_count_target": 3,
    "assessment_mode": "project"
  },
  "delivery_constraints": {
    "interaction_density": "medium",
    "must_cover_topics": ["diagnosis", "verification"]
  },
  "target_language": "en-US"
}
```

## Course Target Resolution Output

```json
{
  "target_mode": "new",
  "auth_verified": true,
  "shifu_bid": null,
  "course_dir": "./metric-drift-course",
  "sync_baseline": "not_applicable"
}
```

The next stage consumes this object directly. It does not repeat login or title
search.

## Course Design Intake Output

```json
{
  "usage_scenarios": ["personalized_self_study"],
  "interaction_purposes": ["adaptive_context", "lesson_end_self_check"],
  "listen_mode": "disabled",
  "chapter_count": 2,
  "lesson_count": 3
}
```

Orchestration consumes this resolved design instead of replaying the intake
conversation.

## Segmentation Output

```json
{
  "structured_segments_json": [
    {
      "segment_id": "S01",
      "segment_type": "concept",
      "core_point": "Metric drift signals a systemic shift, not just noise.",
      "preserve_block": false,
      "source_span": {"start": 0, "end": 42}
    },
    {
      "segment_id": "S02",
      "segment_type": "concept",
      "core_point": "Classify causes before applying fixes.",
      "preserve_block": false,
      "source_span": {"start": 43, "end": 78}
    }
  ],
  "preserve_block_index": [],
  "lesson_cut_candidates": [
    {
      "lesson_id": "L01",
      "segment_ids": ["S01", "S02"],
      "core_question": "Which signal separates symptom from root cause?"
    }
  ]
}
```

## Orchestration + Generation Output

```json
{
  "course_index": [
    {
      "lesson_id": "L01",
      "lesson_title": "Observe and Classify",
      "core_question": "Which signal separates symptom from root cause?",
      "source_span_map": [{"source_id": "course_material", "start": 0, "end": 78}]
    }
  ],
  "global_variable_table": [
    {
      "name": "diagnosis_choice",
      "collected_in": "L01",
      "used_in": ["L01", "L02"],
      "effect_scope": "cross_lesson"
    }
  ]
}
```

```md
Ask the learner to identify the highest-signal diagnostic step for the drifting metric.
---
?[%{{diagnosis_choice}} check workload shape | check lock wait | check cache hit ratio]
---
The learner's diagnosis choice is {{diagnosis_choice}}. Based on it, run one focused verification next.
```

## Optimization Output

```json
{
  "risk_and_issue_report": {
    "overall_risk": "low",
    "blocking_issues": [],
    "suggestions": ["add boundary framing after diagnosis interaction"]
  },
  "change_list": [
    {
      "issue_class": "explanation_clarity",
      "change": "add brief boundary note after diagnosis selection"
    }
  ],
  "course_prompt": "# Role\nYou are a practical coach helping beginners diagnose bottlenecks.\n\n# Task\nGuide the learner through observation → classification → one focused verification.\n\n# Teaching Techniques\nEvidence chain; one core question per lesson; viewpoint branching on diagnosis choice.\n\n# Writing Style\nDirective, concise, action-oriented; English (en-US).\n\n# Format\nMarkdownFlow; `?[]` interactions on standalone lines.\n\n# Slides\nCreate diagnostic-flow slides in natural language; do not inline SVG/Mermaid."
}
```

## Deployment Output

```json
{
  "shifu_bid": "xyz789",
  "deployed_course_url": "https://example.invalid/c/xyz789",
  "lesson_count": 3,
  "status": "published",
  "auth_verified": true
}
```

The URL above is illustrative only. A real run reports the exact URL printed by
the CLI.

## Acceptance Notes

- Every stage consumed declared handoff fields and passed its result forward.
- No completed upstream stage was rerun by a downstream stage.
- One core question per lesson, every learner-answer variable has a corresponding variable-backed interaction and metadata entry.
- Optimization pass found no blockers, only enhancement suggestions.
