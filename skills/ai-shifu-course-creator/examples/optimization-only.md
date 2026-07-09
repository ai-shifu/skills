# Optimization Only Example

> Note: Outputs in this example are illustrated in English for clarity. Actual output language follows `references/data-contracts.md#language-resolution` (e.g., Chinese invocation → Chinese output).

## Minimal Input

```json
{
  "existing_teaching_prompt": "## Objective\nUnderstand retry policy.\n---\n?[%{{answer}} yes | no]\n---\nGreat job.",
  "course_material": "Learner must differentiate transient vs permanent failure and choose a matching retry stop rule.",
  "optimization_constraints": {
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
  ],
  "course_prompt": "# Role\nYou are a coach helping beginners reason about retry policy.\n\n# Task\nDifferentiate transient vs permanent failure and select a retry stop rule.\n\n# Teaching Techniques\nViewpoint branching on failure type; bounded retries with backoff for transient.\n\n# Writing Style\nDirective, action-oriented.\n\n# Format\nMarkdownFlow; `?[]` interactions on standalone lines.\n\n# Slides\nCreate failure-taxonomy slides in natural language."
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

## Degraded Input

Degraded-input handling for this phase (missing source material, high-risk report, minimal safe edits): see `examples/fallback-mode.md` → Optimization Fallback.

## Acceptance Notes

- Syntax stays runnable after edits.
- Coverage and meaning are closer to source material.
- Runtime safety fixes are applied first.
- Edits stay minimal and avoid broad rewrites.
