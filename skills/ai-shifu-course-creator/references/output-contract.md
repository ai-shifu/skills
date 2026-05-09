# Output Contract

## Required Artifacts

1. `lesson_mdf_scripts`
- One MarkdownFlow file per lesson.
- Instructional/directive teaching-script language only (model-guiding), not a final learner manuscript.

2. `course_index`
- `lesson_id`
- `lesson_title`
- `core_question`
- `source_span_map`

3. `global_variable_table`
- Variable name
- Collection point
- Downstream usage
- Cross-lesson dependencies

4. `course_prompt`
- Markdown string (runnable AI-Shifu course-level system prompt).
- Required sections: `# Role`, `# Task`, `# Teaching Techniques`, `# Writing Style`, `# Format`.
- Conditional sections: `# Drawing` (when the course involves visuals), `# Translation Rules` (when multilingual or when brand/domain terms need a fixed translation policy).
- Authoring rules: `course-prompt-rules.md`. Fillable template and Substitution Map: `course-prompt-template.md`.

## Artifact Schemas

### `lesson_mdf_scripts` (array, required)

Each item:

- `lesson_id` (string, required)
- `lesson_title` (string, required)
- `mdf_script` (string, required)
- `used_variables` (array, required)
- `depends_on_lessons` (array, required)

### `course_index` (array, required)

Each item:

- `lesson_id` (string, required)
- `lesson_title` (string, required)
- `core_question` (string, required)
- `source_span_map` (array of `{source_id, start, end}`, required)

### `global_variable_table` (array, required)

Each item:

- `name` (string, required)
- `collected_in` (string, required)
- `used_in` (array of lesson ids, required)
- `effect_scope` (string enum: `local|cross_lesson`, required)

### `course_prompt` (string, required)

- Markdown string starting with `# Role`.
- Five required `# Section` blocks: `# Role`, `# Task`, `# Teaching Techniques`, `# Writing Style`, `# Format`.
- Conditional `# Drawing` and `# Translation Rules` sections per `course-prompt-rules.md` `## Conditional Sections`.
- Single source of truth at the course level; do not embed per-lesson interaction logic.

## Minimal Output Example

```json
{
  "lesson_mdf_scripts": [
    {
      "lesson_id": "L01",
      "lesson_title": "Core Loop Setup",
      "mdf_script": "## Objective\n...\n?[%{{learner_goal}} Option A | Option B]\n...",
      "used_variables": ["learner_goal"],
      "depends_on_lessons": []
    }
  ],
  "course_index": [
    {
      "lesson_id": "L01",
      "lesson_title": "Core Loop Setup",
      "core_question": "What makes this loop stable in production?",
      "source_span_map": [{"source_id": "doc-1", "start": 120, "end": 286}]
    }
  ],
  "global_variable_table": [
    {
      "name": "learner_goal",
      "collected_in": "L01",
      "used_in": ["L01", "L02"],
      "effect_scope": "cross_lesson"
    }
  ],
  "course_prompt": "# Role\nYou are ...\n\n# Task\n- The current course is *...*. ...\n\n# Teaching Techniques\n- ...\n\n# Writing Style\n- ...\n\n# Format\n- ..."
}
```

## Phase 5 Artifacts

4. `deployed_course_url`
- Platform URL of the deployed course.

5. `shifu_bid`
- Course BID on the AI-Shifu platform.

### `deployment_result` (object, optional)

- `shifu_bid` (string, required)
- `deployed_course_url` (string, required)
- `lesson_count` (number, required)
- `status` (string enum: `published|draft`, required)

## Delivery Guarantees

- Stable schema across reruns.
- Deterministic references for lesson ids and source spans.
- Partial rerun support for changed lessons.
