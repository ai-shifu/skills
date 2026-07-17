# Teaching Prompt

Generate one runnable per-lesson Teaching Prompt from approved segments and design controls. This file materializes teaching decisions; it does not define pedagogy, MarkdownFlow runtime behavior, or image handling.

## Required References

- `language-policy.md`
- `prompt-contracts.md`
- `data-contracts.md#lesson-schema`
- `data-contracts.md#generation-fallback-fields`
- `pedagogy.md`
- `markdownflow-authoring.md`

## Conditional References

- When an image asset must be understood, uploaded, embedded, or validated: `image-authoring.md`

## Generation

1. Select the teaching pattern that best fits the lesson's core question and source evidence. Preserve the pattern order defined in `pedagogy.md#teaching-patterns`; do not force every lesson into Evidence Chain.
2. Apply the normalized interaction policy without adding unselected purposes or blanket interactions.
3. Encode the lesson's selected pattern, teaching loop, interaction choices, variable-persistence decisions, and visual-text behavior in the Teaching Prompt itself.
4. Apply `markdownflow-authoring.md` after those teaching decisions are complete.
5. Load `image-authoring.md` only when the lesson actually uses an image asset.

Every lesson must carry enough direction to run with the Course Prompt contributing only course-wide role and presentation style. Do not rely on the Course Prompt to supply, repair, or override lesson pedagogy.

## Lesson Materialization

Each Teaching Prompt must:

- Start with the teaching-start behavior defined in `pedagogy.md#lesson-loop`, not a copied chapter or lesson title.
- Resolve exactly one core question through the selected teaching pattern.
- Use the interaction or non-interactive loop selected by the normalized policy.
- Preserve required source evidence and any downstream deliverable defined by the lesson design.
- Close with the summary, decision checkpoint, or action required by the selected pattern.

For pure classroom slides, materialize the selected behavior directly from `pedagogy.md#visual-text-coordination` without reinterpreting it. Course Prompt delivery-mode behavior remains owned by `course-prompt.md`.

## Outputs

Produce one `lesson_teaching_prompts` item per lesson using `data-contracts.md#lesson-schema`. Apply `language-policy.md` to authored strings and preserve machine-facing values and immutable source spans.

Under fallback mode, add only the Generation extensions defined in `data-contracts.md#generation-fallback-fields`.

## Validation

- Every `teaching_prompt` is valid runnable MarkdownFlow.
- Every item passes `data-contracts.md#lesson-schema`.
- The first non-empty line performs a teaching-start function and does not duplicate structure metadata.
- The Teaching Prompt contains the selected teaching method and does not outsource pedagogy to the Course Prompt.
- Interaction, variable, branch, and preservation encoding pass `markdownflow-authoring.md`.
- Image-specific validation runs only for lessons that use image assets.
- Authored human-facing content passes `language-policy.md`.
