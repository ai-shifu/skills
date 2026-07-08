# Data Contracts

Authoritative source for all schemas crossing the skill boundary: what comes in (input), what goes out (output), how output target language is resolved, and the per-lesson and per-variable shapes.

## Input Contract

### Required

Provide one of:

- A single long transcript or course document.
- A set of topic-aligned documents with intended order.

### Optional

- Learner persona.
- Lesson granularity preference (`short`, `medium`, `long`).
- Tone constraints.
- Non-negotiable source fragments.
- `course_profile` object.
- `delivery_constraints` object.
- `target_language` (BCP-47 recommended, for example `fr-FR`, `ja-JP`, `zh-CN`).

### Recommended Object Shapes

#### `course_profile`

```json
{
  "audience_level": "beginner|intermediate|advanced",
  "prerequisite_level": "none|basic|strong",
  "lesson_duration_minutes": 12,
  "lesson_count_target": 8,
  "assessment_mode": "quiz|project|discussion|mixed"
}
```

#### `delivery_constraints`

```json
{
  "interaction_density": "low|medium|high",
  "platform_limits": ["no_iframe", "markdown_only"],
  "must_cover_topics": ["topic-a", "topic-b"],
  "avoid_topics": ["topic-x"],
  "non_negotiable_fragments": ["required source fragment or code block id"]
}
```

### Minimal Input Payload Example

```json
{
  "course_material": "long transcript or merged markdown",
  "generation_constraints": {
    "persona": "hands-on mentor",
    "lesson_granularity": "short"
  },
  "course_profile": {
    "audience_level": "beginner",
    "lesson_duration_minutes": 10,
    "lesson_count_target": 6,
    "assessment_mode": "project"
  },
  "delivery_constraints": {
    "interaction_density": "medium",
    "must_cover_topics": ["core workflow", "failure handling"]
  }
}
```

### Validation Rules

- Input files must be readable text or markdown.
- If multiple files are provided, ordering must be explicit.
- Source language and expected output language should be specified when multilingual content exists.
- Explicit output language requests must not be overridden by source-language mixes (see [Language Resolution](#language-resolution)).

## Output Contract

### Required Artifacts

1. `lesson_teaching_prompts` — one Teaching Prompt per lesson (written in MarkdownFlow). Instructional/directive language only (model-guiding), not a final learner manuscript. See [Lesson Schema](#lesson-schema).
2. `course_index` — `lesson_id`, `lesson_title`, `core_question`, `source_span_map`.
3. `global_variable_table` — see [Variable Table](#variable-table).
4. `course_prompt` — markdown string (runnable AI-Shifu course-level system prompt) following [course-prompt.md](course-prompt.md). Required canonical sections: Role, Task, Teaching Techniques, Writing Style, Format, and Slides, rendered as Markdown headings in the resolved output language.
5. `course_description` — SEO/listing description written to `course-description.md`; describe the course topic, target learners, and learning outcomes in learner-facing language. Do not include author-side workflow notes.

### `course_index` Schema (array, required)

Each item:

- `lesson_id` (string, required)
- `lesson_title` (string, required)
- `core_question` (string, required)
- `source_span_map` (array of `{source_id, start, end}`, required)

### `course_prompt` (string, required)

- Markdown string starting with the rendered Role section heading in the resolved output language.
- Six required Markdown section blocks in the canonical order from [course-prompt.md](course-prompt.md): Role, Task, Teaching Techniques, Writing Style, Format, and Slides. Render section headings and body text in the resolved output language.
- Single source of truth at the course level; do not embed per-lesson interaction logic.

### `course_description` (string, required)

- One concise learner-facing SEO/listing description.
- Base it on the course topic, target learners, and concrete learning outcomes.
- Write it to `course-description.md`; the CLI maps it to the platform `description` field during build/import.

### Minimal Output Example

```json
{
  "lesson_teaching_prompts": [
    {
      "lesson_id": "L01",
      "lesson_title": "Core Loop Setup",
      "teaching_prompt": "Ask the learner for the one goal that should shape course-wide examples.\n---\n?[%{{learner_goal}} ...One-sentence goal]\n---\nThe learner goal is {{learner_goal}}. When the learner goal is UNKNOWN, continue with the default production example; otherwise use a first example that matches it.",
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
      "used_in": ["L01", "course_prompt"],
      "effect_scope": "cross_lesson"
    }
  ],
  "course_prompt": "# Role\nYou are ...\n\n# Task\n- The learner goal is {{learner_goal}}. When the learner goal is UNKNOWN, use the course default examples; otherwise adapt course-wide examples to it. ...\n\n# Teaching Techniques\n- ...\n\n# Writing Style\n- ...\n\n# Format\n- ...\n\n# Slides\n- ...",
  "course_description": "A practical course that helps beginner operators diagnose metric drift, identify likely causes, and choose one concrete fix."
}
```

### Artifacts

1. `deployed_course_url` — Platform URL of the deployed course.
2. `shifu_bid` — Course BID on the AI-Shifu platform.

#### `deployment_result` (object, optional)

- `shifu_bid` (string, required)
- `deployed_course_url` (string, required)
- `lesson_count` (number, required)
- `status` (string enum: `published|draft`, required)

### Delivery Guarantees

- Stable schema across reruns.
- Deterministic references for lesson ids and source spans.
- Partial rerun support for changed lessons.

## Segment Schema

Each item in the Segmentation output (consumed by Orchestration and Generation):

- `segment_id` (string, required) — stable identifier within the run.
- `segment_type` (string enum, required) — one of `concept`, `example`, `code`, `image`, `exercise`, `transition`; semantics in [pedagogy.md#segment-types](pedagogy.md#segment-types).
- `core_point` (string, required) — the single teachable point this segment carries.
- `preserve_block` (boolean, required) — `true` for code/image/table/required-quote blocks that must reach the lesson verbatim per [markdownflow.md#preservation](markdownflow.md#preservation).
- `source_span` (string, required) — traceable reference back to the source material.
- `transfer_signals` (object, required) — downstream teaching-quality cues; field names and meanings defined in [pedagogy.md#transfer-signals](pedagogy.md#transfer-signals).

For segmentation rules and methodology see [pedagogy.md#segmentation-methodology](pedagogy.md#segmentation-methodology).

## Variable Table

`global_variable_table` is an array. Each item:

- `name` (string, required) — the variable name as referenced in `{{var}}` / `?[%{{var}} ...]`; new variable names should use the resolved output language and be composed of letters, numbers, and underscores.
- `collected_in` (string, required) — `lesson_id` where the variable is first collected.
- `used_in` (array of strings, required) — every lesson that references the variable through `{{var}}`, plus reserved value `course_prompt` when `course-prompt.md` references it. Include `collected_in` only if that same lesson also references `{{var}}` after collecting it.
- `effect_scope` (string enum: `local|cross_lesson`, required).

Only named variables belong in `global_variable_table`. No-variable `?[...]` interactions do not create table entries. Use named variables only when the learner's answer must be used outside the current lesson; lesson-local branching, examples, feedback, summaries, and inputs stay no-variable. A variable referenced from `course-prompt.md` has `effect_scope: "cross_lesson"` because the Course Prompt can influence more than one lesson; still list `course_prompt` in `used_in` whenever `course-prompt.md` references the variable. For variable *syntax and runtime substitution semantics* (`{{var}}` → stored value or `UNKNOWN`) see [markdownflow.md#variables](markdownflow.md#variables); for variable *strategy and pacing* see [pedagogy.md#variable-strategy](pedagogy.md#variable-strategy).

## Lesson Schema

Each item in `lesson_teaching_prompts` (Generation per-lesson output):

- `lesson_id` (string, required) — stable, deterministic identifier.
- `lesson_title` (string, required) — concise learner-facing title.
- `teaching_prompt` (string, required) — the per-lesson Teaching Prompt content (written in MarkdownFlow); instructional/directive language only.
- `used_variables` (array of strings, required) — every named variable referenced or collected in this lesson; no-variable interactions are excluded. Cross-check with [Variable Table](#variable-table): each item here must have a matching `global_variable_table` entry, and that entry's `used_in` list must include this lesson when the variable is referenced outside the interaction line. If the Course Prompt references the same variable, `used_in` must also include `course_prompt`.
- `depends_on_lessons` (array of lesson ids, required) — explicit list; empty list if none.

### Minimal Example

```json
{
  "lesson_id": "L03",
  "lesson_title": "Diagnose the Bottleneck",
  "teaching_prompt": "Ask the learner where the system feels slow before naming any cause: CPU, IO, or locks.\n---\n?[CPU bound | IO bound | Lock contention]\n---\nAfter the learner answers, run the matching test first.",
  "used_variables": [],
  "depends_on_lessons": ["L02"]
}
```

## Language Resolution

### Priority Order

Resolve target language with this strict priority:

1. `explicit_output_language_request` — language explicitly stated in the current user prompt.
2. `target_language_parameter` — `target_language` field supplied in the input payload (BCP-47 recommended).
3. `prior_context_language_directive` — language requirement declared **outside** the current prompt but visible to the skill: project/system instructions (e.g. `CLAUDE.md`), earlier turns of the same conversation, or directives injected by the calling agent. The skill cannot read external platform/account locale settings, so only in-context directives count here.
4. `prompt_language_detection` — language detected from the wording of the current user prompt itself.
5. `source_material_dominant_language` — the dominant language of the supplied course material.
6. `default_fallback_language` — `zh-CN`.

### Control Fields

- `target_language` (BCP-47 recommended, for example `fr-FR`, `ja-JP`, `zh-CN`)

### Rules

- Do not restrict supported languages to a fixed list.
- If output language is explicit, source-language distribution must not override it.
- Learner-facing script text must follow resolved target language.
- Newly authored MarkdownFlow variable names must follow the resolved output language within the valid variable-character set. Preserve existing or source-provided variable names when renaming would break an existing variable contract.
- User-visible agent output must follow the resolved target language: chat replies, phase summaries, reports, headings, artifact labels, review notes, handoff instructions, and error explanations.
- Human-facing labels for skill concepts must follow the canonical terms in [SKILL.md#canonical-term-translation-table](../SKILL.md#canonical-term-translation-table) when the resolved target language is listed there; do not keep English labels merely because the skill docs and examples are written in English.
- Stable machine-facing identifiers and verbatim source material remain unchanged even when the surrounding prose is localized: JSON keys (`course_index`, `global_variable_table`, `lesson_id`, `lesson_title`, `lesson_teaching_prompts`, `teaching_prompt`, `course_prompt`, `course_description`), file names (`course-description.md`, `course-prompt.md`, `structure.json`), CLI commands and flags, API fields, code symbols, MarkdownFlow syntax, URLs, code samples, and quoted source text or direct quotations that must be preserved verbatim.

### Pre-Deploy Language Audit

Before finalizing or deploying a generated course directory, audit all build-consumed user-visible artifacts and effective build metadata, so template headings or directive phrases from a different language do not remain after target-language rendering:

- Resolved course title (`--title`, `README.md` first heading, or directory-name fallback).
- Resolved course description (`--description` or `course-description.md`).
- Resolved chapter titles (`structure.json`, `--chapter-name`, or course-title fallback).
- Learner-facing lesson title fields in `structure.json`.
- `course-prompt.md`.
- Every lesson file referenced by `structure.json` (or every auto-discovered `lessons/lesson-*.md` file when `structure.json` is absent).

## Fallback Output Extensions

When a phase runs under fallback mode (see SKILL.md `## Execution Modes`), its standard output is augmented with the following fields. Standard-mode output omits these fields entirely; fallback-mode output adds them on top of the standard schema.

### Segmentation fallback fields

Per-segment (extends [Segment Schema](#segment-schema)):

- `uncertainty` (string enum: `low|medium|high`) — confidence on the segment's interpretation.

Top-level addition to the Segmentation output:

- `rerun_hints` (array of strings) — user-facing prompts describing what authoritative input would resolve the uncertainty.

### Orchestration fallback fields

Per-lesson (extends `course_index` items):

- `uncertainty` (string enum: `low|medium|high`).

Top-level addition:

- `rerun_plan` (object, required when any lesson is uncertain):
  - `lessons_to_rerun` (array of lesson ids).
  - `reason` (string) — why the rerun is needed.

### Generation fallback fields

Per-lesson (extends [Lesson Schema](#lesson-schema)):

- `fallback_mode` (boolean) — `true` when this lesson was generated under fallback.
- `assumptions` (array of strings) — assumptions made due to incomplete input.
- `upgrade_notes` (array of strings) — what additional input would upgrade this lesson.

### Optimization fallback fields

Inside `risk_and_issue_report`:

- `coverage_status` (string enum: `complete|partial|unknown_without_source`).

Top-level addition:

- `follow_up` (array of strings) — required inputs to complete a full-coverage audit.

For the four end-to-end fallback scenarios, see `examples/fallback-mode.md`.
