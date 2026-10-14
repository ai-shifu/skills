# Course Prompt

Course-level materialization contract for the Course Prompt artifact.

## Purpose

Use this file to materialize one course-wide artifact from the six-section template below. It defines the template, fill-value sources, context used while filling those values, and completion checks; it does not redefine shared Prompt semantics, lesson pedagogy, or MarkdownFlow runtime behavior.

The template's `# Slides` section is the single runtime owner for presentation requirements that apply uniformly to every slide rather than to a particular slide position or teaching purpose. Teaching Prompts decide each lesson's slide count, order, teaching purposes, required content, relationship to explanatory text, and any position- or purpose-specific treatment; the Course Prompt applies the shared presentation rules without changing those decisions.

The course author's intended audience and course constraints remain hard boundaries. The platform may supply learner context at delivery time; the Course Prompt tells the Teaching Agent how to use that context within the authored boundaries without serializing platform-owned learner-profile fields into the course artifact.

- Apply shared Prompt semantics and the Course Prompt versus Teaching Prompt authority boundary from [prompt-semantics.md](prompt-semantics.md).
- Ground instructions that use earlier learner input in the [memory contract](markdownflow-syntax.md#memory).

## Materialization

Use the available course topic, title, objectives, audience, and resolved design choices to fill the complete [Fillable Template](#fillable-template). A segmentation run, course index, internal plan, local directory, or prior questionnaire is not required.

Preserve all six sections in order and every non-placeholder instruction. Render headings and body in the language resolved under [language-policy.md#language-resolution](language-policy.md#language-resolution); the English template defines structure rather than a default language. Replace placeholders with concrete course-specific instructions under [Placeholder Sources and Context](#placeholder-sources-and-context), without copying fill guidance or unselected alternatives. Check the result with [Materialization Checks](#materialization-checks).

[course-design-choices.md](course-design-choices.md) explains design choices when they need clarification. [authoring-contracts.md#input-contract](authoring-contracts.md#input-contract) describes optional structured controls; neither document requires an intermediate artifact.

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
- Use relevant memory when following the lesson's instructions. Base references to earlier learner input on the learner's actual answers.
- XXX
- Do not quote, summarize, or mention the learner profile. If the context is empty, unknown, irrelevant, or unavailable, use neutral course-appropriate defaults and do not infer missing facts.

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
| Role identity (`You are XXX`) | The supplied teacher identity, optionally represented as `course_author_name`. When it is empty, omit the corresponding list item in the Fillable Template instead of filling the placeholder. |
| Specialty (`You specialize in XXX`) | The course's dominant topic from the request, source material, or existing content. |
| Teaching field (`the field of XXX`) | The subject field supported by the available course content and intended objectives. |
| Course name (`The current course is *XXX*`) | The resolved course title from the request or existing course metadata. When a local directory is in scope, keep its build title consistent under [cli/course-directory-spec.md#build-precedence](cli/course-directory-spec.md#build-precedence). |
| Mastery goal (`help the learner master XXX`) | The course-level learning goal supported by the source, author requirements, and lesson objectives. |
| Delivery instructions (standalone `XXX` under Task) | The resolved delivery experience. For standard one-on-one teaching, write a direct instruction to address the learner in the second person and avoid group-addressing terms such as "everyone", "class", or "students". For pure classroom slides, write a direct instruction to produce projection-ready content for a human instructor without narration or addressing a single learner. Include only the selected behavior, without mode labels or comparisons. Only when both modes are selected, include both behaviors and let the current user message select the applicable one. |
| Personalization instructions (standalone `XXX` under Teaching Techniques) | The resolved directions, with effects defined in [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions). Write direct teaching instructions for exactly those directions, using relevant explicitly stated learner background and preferences. For no selected directions, write a direct instruction to teach from the source, author requirements, and intended audience without individual-background adaptation. Do not output the field name, enum values, selection interface, unselected adaptation instructions, or an if-selected rule. |

Use these inputs as context constraints while wording the applicable fill values; they do not add placeholders to the template:

- Calibrate specificity to the available audience and prerequisite information, whether supplied naturally or in `course_profile`.
- Keep fill values within required topics, excluded topics, source support, and explicit author constraints.
- Match the resolved delivery experience.

## Materialization Checks

- The six template sections are present in their original order and localized to `resolved_target_language`.
- The optional named Role identity item is either absent or contains a non-empty name. The remaining six `XXX` occurrences are replaced with course-specific content derived from the mapped sources, and the completed artifact contains no unresolved `XXX` placeholder.
- Delivery instructions state the selected behavior directly. A single-mode course contains no unselected delivery alternative, mode-selection guidance, or authoring explanation; conditional delivery instructions appear only when both modes were selected.
- Every non-placeholder template instruction remains represented with the same behavior.
- The fill values satisfy the available audience, topic-scope, and delivery context constraints above.
- The learner-context instructions enable exactly the resolved directions under `prompt-semantics.md#personalization-directions`; `[]` produces the uniform course baseline. No unselected direction is enabled implicitly through a generic personalization rule or style instruction. Selected language style can vary within the shared clear, restrained, warm baseline; otherwise that baseline stays course-wide.
- The artifact contains no authoring field name or enum array, platform learner-profile tags, internal learner-profile field names, or unresolved personalization placeholder.
- Every presentation requirement that applies uniformly to every slide remains in the `# Slides` section. The section does not special-case a cover or any other slide position or teaching purpose, and it does not change lesson-specific slide structure or pedagogy supplied by the current user message.
- The completed artifact follows [prompt-semantics.md](prompt-semantics.md), and its instructions for using earlier learner input follow [markdownflow-syntax.md#memory](markdownflow-syntax.md#memory), without copying the runtime contract into this file.
