# Full Pipeline Example (Segmentation → Orchestration → Generation → Optimization → Deployment)

> Note: This example is illustrated in English; actual output follows [Output Language](../references/session-controls.md#output-language).

Apply [Segmentation and Orchestration](../references/segmentation-orchestration.md), then continue through [Deployment and Course Management](../references/deployment-workflow.md); this example illustrates the handoffs without redefining either owner.

## Input Payload (example)

```json
{
  "course_material": "Module transcript: observe metric drift, classify causes, apply one fix, review impact.",
  "course_author_name": "Maya Chen",
  "authoring_run_controls": {
    "execution_mode": "standard",
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
    "teaching_persona": "practical coach",
    "lesson_granularity": "short"
  },
  "course_profile": {
    "audience_level": "beginner",
    "lesson_duration_minutes": 10,
    "assessment_mode": "project"
  },
  "delivery_constraints": {
    "must_cover_topics": ["diagnosis", "verification"]
  },
  "target_language": "en-US"
}
```

## Segmentation Output

```json
{
  "structured_segments_json": [
    {
      "segment_id": "S01",
      "segment_type": "concept",
      "core_point": "Metric drift signals a systemic shift, not just noise.",
      "preserve_block": false,
      "source_span": {"source_id": "course_material", "start": 0, "end": 39},
      "transfer_signals": {
        "learner_hook": "Start from a metric that changed unexpectedly.",
        "visual_cue": "Show a baseline metric line followed by a sustained shift.",
        "visual_text_pair_cue": "Explain how persistence separates drift from random noise."
      }
    },
    {
      "segment_id": "S02",
      "segment_type": "concept",
      "core_point": "Classify causes before applying fixes.",
      "preserve_block": false,
      "source_span": {"source_id": "course_material", "start": 41, "end": 71},
      "transfer_signals": {
        "concept_conflict": "Jumping to a fix before classifying the cause can hide the real bottleneck.",
        "interaction_intent_cue": "Ask the learner to choose the highest-signal diagnostic check.",
        "action_cue": "Run one focused verification before applying a fix."
      }
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

The unchanged source material, author identity, course profile, delivery constraints, and target language remain in the handoff context; this snapshot shows only the phase-owned result fields rather than copying that context.

```json
{
  "authoring_run_controls": {
    "execution_mode": "standard",
    "delivery_mode": "standard",
    "listen_mode_enabled": false,
    "chapter_count_target": 1,
    "lesson_count_target": 1,
    "interaction_policy": {
      "mode": "enabled",
      "purposes": ["pre_content_thinking"]
    }
  },
  "lesson_teaching_prompts": [
    {
      "lesson_id": "L01",
      "lesson_title": "Observe and Classify",
      "teaching_prompt": "Open with a production metric that changed unexpectedly and ask the learner to identify the highest-signal diagnostic step before explaining how to classify the drift.\n---\n?[check workload shape | check lock wait | check cache hit ratio]\n---\nAfter the learner answers, create a slide that shows a stable baseline followed by a sustained metric shift. Begin with the selected check, explain why it is or is not the highest-signal first step for this case, then compare it with workload shape, lock wait, and cache hit ratio.\n\nExplain that persistence separates drift from noise, while classification prevents a plausible fix from targeting the wrong cause. Walk through one focused verification before suggesting a fix.\n\nPresent a reusable one-sentence verification plan naming the signal, expected movement, and stop condition. Close by summarizing the sequence: observe, classify, verify, then fix.",
      "used_variables": [],
      "depends_on_lessons": []
    }
  ],
  "course_index": [
    {
      "lesson_id": "L01",
      "lesson_title": "Observe and Classify",
      "core_question": "Which signal separates symptom from root cause?",
      "source_span_map": [{"source_id": "course_material", "start": 0, "end": 71}]
    }
  ],
  "global_variable_table": []
}
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
  ]
}
```

### Course Prompt Artifact

Optimization fills the canonical [Course Prompt template](../references/course-prompt.md#fillable-template) from these example-specific bindings. The example does not reproduce the template, so its wording remains owned by one file.

| Placeholder source | Example value |
|---|---|
| Teacher name | Maya Chen |
| Specialty and teaching field | Production observability; metric drift diagnosis |
| Course name | Metric Drift Diagnosis |
| Mastery goal | Apply the observe, classify, verify, and fix workflow to production metric drift |
| Learner profile | Beginner operators |
| Problems in scope | Diagnosis and verification |

The resulting `course_prompt` string uses the standard delivery profile and must pass the canonical [Course Prompt validation](../references/review-checklist.md#course-prompt).

### Course Description Artifact

The final `course_description` is: `A practical course for beginner operators who want to distinguish metric drift from noise, classify likely causes, verify one targeted fix, and confirm its production impact.`

## Deployment Continuation

This example assumes Course Target Resolution selected a new platform target. After the Course Prompt, course description, lesson files, structure, images, and effective language pass their routed checks, continue into Deployment without asking for another upload or publication confirmation. An existing target uses the same validated authoring handoff but follows the non-destructive sync path owned by Deployment.

The terminal result adds the required `deployment_result` with the CLI-returned `shifu_bid`, deployed course URL, lesson count, and `status: published`. Do not invent example URLs or reconstruct them from templates.

## Acceptance Notes

- All four authoring phases and the Deployment continuation executed end-to-end.
- One core question per lesson; this single-lesson example uses a no-variable interaction because the answer does not leave the lesson.
- The Course Prompt bindings fill the single canonical template and pass Course Prompt validation.
- Optimization pass found no blockers, only enhancement suggestions.
- The route ends with a published `deployment_result`, not a local authoring handoff.
