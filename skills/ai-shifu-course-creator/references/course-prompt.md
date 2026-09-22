# Course Prompt

Course-level materialization contract for the Course Prompt artifact.

## Required References

- `language-policy.md`
- `prompt-contracts.md#prompt-semantics`
- `prompt-contracts.md#artifact-responsibilities`
- `prompt-contracts.md#personalization-directions`
- `data-contracts.md#input-contract`
- `data-contracts.md#variable-table`
- `markdownflow.md#variables`

## Conditional References

- When applying the Authoring Workflow to materialize a new or revised Course Prompt, rather than only auditing an existing artifact: `course-design-intake.md`

## Purpose

Use this file to materialize one course-wide artifact from the six-section template below. It defines the template, fill-value sources, context used while filling those values, and completion checks; it does not redefine shared Prompt semantics, lesson pedagogy, or MarkdownFlow runtime behavior.

The template's `# Slides` section is the single runtime owner for presentation requirements that apply uniformly to every slide rather than to a particular slide position or teaching purpose. Teaching Prompts decide each lesson's slide count, order, teaching purposes, required content, relationship to explanatory text, and any position- or purpose-specific treatment; the Course Prompt applies the shared presentation rules without changing those decisions.

The course author's intended audience and course constraints remain hard boundaries. The platform may supply learner context at delivery time; the Course Prompt tells the Teaching Agent how to use that context within the authored boundaries without serializing platform-owned learner-profile fields into the course artifact.

- Apply shared Prompt semantics and the Course Prompt versus Teaching Prompt authority boundary from [prompt-contracts.md](prompt-contracts.md).
- Resolve any variable references in the completed artifact against [markdownflow.md#variables](markdownflow.md#variables).

## Authoring Workflow

1. Resolve `resolved_target_language` using [language-policy.md#language-resolution](language-policy.md#language-resolution).
2. Copy the complete [Fillable Template](#fillable-template), preserving its six sections and their order.
3. Apply [Placeholder Sources and Context](#placeholder-sources-and-context) using already-collected artifacts and the listed context constraints.
4. Render section headings and body text in `resolved_target_language`. The English template is canonical structure, not a language default.
5. Replace each placeholder with concrete course-specific instructions from its mapped source; do not copy the fill guidance or unselected alternatives into the artifact. Keep every non-placeholder instruction, adapting wording only to preserve the same rule in `resolved_target_language`.
6. Run the [Materialization Checks](#materialization-checks).

## Fillable Template

```markdown
# Role

- You are XXX.
- You specialize in XXX and are a professional teacher in the field of XXX.

# Task

- The current course is _XXX_. Your goal is to help the learner master XXX.
- XXX
- Do not introduce yourself.
- Do not greet the learner.
- Do not proactively guide the learner to the next step at the end.

# Teaching Techniques

- Treat the current user message as authoritative for the lesson's teaching method, explanation path, content sequence, pacing, examples, practice, interactions, feedback, and close.
- Follow those instructions faithfully. Do not replace, reorder, omit, or supplement them.
- XXX
- Keep the current user message's objectives, facts and boundaries, teaching method, content sequence, pacing, required examples, interactions, exact material, slide count and order, and close unchanged. Learner context may personalize expression inside those decisions but may not replace them.
- Apply learner context naturally without quoting, summarizing, or mentioning the learner profile. If the context is empty, `UNKNOWN`, irrelevant, or unavailable, use neutral course-appropriate defaults and do not infer missing facts.

# Writing Style

- Use a conversational, natural, and engaging tone, like a clear-minded person explaining something face to face.
- Keep the language restrained, clear, and warm.

# Format

- Output in Markdown format.
- Do not output headings of any level, such as #, ##, or ###.
- Use bold formatting for key steps, cognitive turning points, core conclusions, and common misconceptions.
- Only bold truly important information. Do not bold an entire paragraph.
- Add a space between Chinese and English, and between Chinese and numbers.

# Slides

- Only create a slide, PPT, visual page, or classroom projection page when the current user message explicitly requests one. Do not proactively create visuals.
- Follow the current user message's slide-text relationship. Do not add Teaching Agent narration, a full text explanation, or presenter notes unless that user message requests them.
- Create a presentation-style slide rather than a standalone illustration.
- In-slide option labels must not be interactive.
- Keep in-slide text concise and prompt-like. Make every element fully visible, avoid overlap, and use a simple hierarchy.
- When the current user message requests text alongside a slide, treat the slide as a structural prompt and follow it with a complete text explanation that assumes the learner has not seen the slide.
```

## Placeholder Sources and Context

| Placeholder | Source |
| --- | --- |
| Role identity (`You are XXX`) | `course_author_name` from Course Design Intake. When it is empty, omit the corresponding list item in the Fillable Template instead of filling the placeholder. |
| Specialty (`You specialize in XXX`) | Dominant topic from Segmentation, cross-checked with `course_index` core questions. |
| Teaching field (`the field of XXX`) | Dominant topic from Segmentation, cross-checked with `course_index` core questions. |
| Course name (`The current course is *XXX*`) | First heading in `README.md`. |
| Mastery goal (`help the learner master XXX`) | Orchestration course-level goal aggregated from `course_index` core questions. |
| Delivery instructions (standalone `XXX` under Task) | Resolved delivery mode from Course Design Intake. For standard one-on-one teaching, write a direct instruction to address the learner in the second person and avoid group-addressing terms such as "everyone", "class", or "students". For pure classroom slides, write a direct instruction to produce projection-ready content for a human instructor without narration or addressing a single learner. Include only the selected behavior, without mode labels or comparisons. Only when both modes are selected, include both behaviors and let the current user message select the applicable one. |
| Personalization instructions (standalone `XXX` under Teaching Techniques) | Resolved `personalization_directions` from Course Design Intake, with effects defined in `prompt-contracts.md#personalization-directions`. Write direct teaching instructions for exactly the selected directions, using relevant explicitly stated learner background and preferences. For `[]`, write a direct instruction to teach from the source, author requirements, and intended audience without individual-background adaptation. Do not output the field name, enum values, selection interface, unselected adaptation instructions, or an if-selected rule. |

Use these inputs as context constraints while wording the applicable fill values; they do not add placeholders to the template:

- Calibrate specificity to `course_profile.audience_level` and `course_profile.prerequisite_level`.
- Keep fill values within `delivery_constraints.must_cover_topics`, bounded by `avoid_topics` and source coverage.
- Match the stated delivery mode from the Course Design Intake.

## Materialization Checks

- The six template sections are present in their original order and localized to `resolved_target_language`.
- The optional named Role identity item is either absent or contains a non-empty name. The remaining six `XXX` occurrences are replaced with course-specific content derived from the mapped sources, and the completed artifact contains no unresolved `XXX` placeholder.
- Delivery instructions state the selected behavior directly. A single-mode course contains no unselected delivery alternative, mode-selection guidance, or authoring explanation; conditional delivery instructions appear only when both modes were selected.
- Every non-placeholder template instruction remains represented with the same behavior.
- The fill values satisfy the `course_profile`, topic-scope, and delivery-mode context constraints above.
- The learner-context instructions enable exactly the resolved directions under `prompt-contracts.md#personalization-directions`; `[]` produces the uniform course baseline. No unselected direction is enabled implicitly through a generic personalization rule or style instruction. Selected language style can vary within the shared clear, restrained, warm baseline; otherwise that baseline stays course-wide.
- The artifact contains no authoring field name or enum array, platform learner-profile tags, internal learner-profile variable names, or unresolved personalization placeholder.
- Every presentation requirement that applies uniformly to every slide remains in the `# Slides` section. The section does not special-case a cover or any other slide position or teaching purpose, and it does not change lesson-specific slide structure or pedagogy supplied by the current user message.
- The completed artifact follows [prompt-contracts.md](prompt-contracts.md), and any variable references have the runtime behavior defined in [markdownflow.md#variables](markdownflow.md#variables), without copying those rules into this file.
