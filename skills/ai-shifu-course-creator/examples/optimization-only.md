# Optimization Only Example

> Note: This example is illustrated in English; actual output follows [Output Language](../references/session-controls.md#output-language).

Apply the [Optimization Workflow](../references/optimization-workflow.md); this example illustrates a repair without redefining Optimization rules.

This is an internal phase snapshot. It is terminal only for report-only or explicitly artifact-only work; when the selected route applies this repair to a platform course, the validated change continues to the platform write and publication.

## Minimal Input

```json
{
  "existing_teaching_prompt": "## Objective\nUnderstand retry policy.\n---\n?[%{{answer}} yes | no]\n---\nGreat job.",
  "course_material": "Learner must differentiate transient vs permanent failure and choose a matching retry stop rule.",
  "course_author_name": "Priya Shah",
  "target_language": "en-US",
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
    "max_interactions": 4,
    "require_branching_feedback": true
  },
  "course_profile": {
    "audience_level": "beginner"
  }
}
```

## Output Snapshot

```json
{
  "risk_and_issue_report": {
    "overall_risk": "medium",
    "blocking_issues": ["interaction_no_branching"],
    "suggestions": ["add explicit stop-condition task"]
  },
  "change_list": [
    {
      "issue_class": "interaction_no_branching",
      "change": "remove the throwaway variable, branch feedback by learner option, and add next-step action"
    }
  ]
}
```

```md
Differentiate transient and permanent failures before choosing retry policy.
---
?[transient failure | permanent failure]
---
If the learner chooses transient failure, apply bounded retries with backoff.
If the learner chooses permanent failure, stop retries and open a corrective task.
```

### Course-Level Boundary

This focused lesson repair does not create a new Course Prompt or course description. When Optimization runs as full-course finalization, it consumes the canonical [Course Prompt template](../references/course-prompt.md#fillable-template); [Full Pipeline → Course Prompt Artifact](pipeline-full.md#course-prompt-artifact) illustrates only the example-specific bindings instead of copying that template.

## Degraded Input

See [Optimization Fallback: No Source Material](fallback-mode.md#optimization-fallback-no-source-material).

## Acceptance Notes

- Syntax stays runnable after edits.
- Coverage and meaning are closer to source material.
- Runtime safety fixes are applied first.
- Edits stay minimal and avoid broad rewrites.
- Course-level artifacts remain unchanged because this example is scoped to one Teaching Prompt.
