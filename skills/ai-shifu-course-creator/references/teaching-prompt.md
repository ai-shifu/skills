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
3. Resolve the teaching objective, must-cover evidence and boundaries, required path, interaction purpose and visible effect, and required close from the approved lesson design.
4. Express those decisions as executable instructions under `prompt-contracts.md#prompt-semantics`. Preserve non-critical freedom over wording, transitions, incidental examples, and visual realization instead of supplying a finished lecture or slide deck.
5. Apply `markdownflow-authoring.md` after those teaching decisions are complete.
6. Load `image-authoring.md` only when the lesson actually uses an image asset.

Every lesson must carry enough direction to run with the Course Prompt contributing only course-wide role and presentation style. Do not rely on the Course Prompt to supply, repair, or override lesson pedagogy.

Enough direction means that the runtime LLM can identify what must be taught, why it matters, any required order, the intended learner effect, and the completion condition. It does not mean prewriting ordinary lecture prose, slide copy, or layout decisions that do not affect the required result.

### Intent-First Materialization

A complete Teaching Prompt contains executable teaching intent, not a lecture transcript or finished slide deck. State the lesson's core question and intended understanding, must-cover facts and boundaries, any order that materially affects learning, the teaching moves to use, each interaction's purpose and visible effect, and the required closing result. Leave routine wording, transitions, non-critical example elaboration, slide titles, and visual composition to the runtime LLM.

Reject both under-specified outlines that omit the content or effect needed to teach and over-specified Prompts that unnecessarily prewrite learner-facing prose, fixed slide counts, font or color choices, pixel coordinates, animations, or uniform point quotas.

Once selected by their owning contracts, keep these constraint islands exact without expanding their scope:

- the complete learner-facing interaction question, the `?[]` form, option wording and order, variable assignment and references, literal `UNKNOWN` behavior, and the selected feedback or branch effect;
- deterministic output and required code or fence structure;
- regulated wording, fixed numeric thresholds, and source spans already selected as immutable;
- wording or layout the author explicitly requires; and
- selected image URLs, alt or caption text, ordering, and form.

Apply each island through its owning MarkdownFlow authoring, source-preservation, or image-authoring reference, and leave the surrounding explanation adaptive.

## Lesson Materialization

Each Teaching Prompt must:

- Start with the teaching-start behavior defined in `pedagogy.md#lesson-loop`, not a copied chapter or lesson title.
- Resolve exactly one core question through the selected teaching pattern.
- Make the teaching objective, must-cover facts and boundaries, and required explanatory relationships unambiguous without prewriting ordinary lecture wording.
- Use the interaction or non-interactive loop selected by the normalized policy.
- Preserve required source evidence and any downstream deliverable defined by the lesson design.
- Close with the summary, decision checkpoint, or action required by the selected pattern.

For pure classroom slides, materialize the required visible content and teaching effects from `pedagogy.md#visual-text-coordination`, while leaving non-essential slide count, wording, grouping, and composition to the runtime LLM. Course Prompt delivery-mode behavior remains owned by `course-prompt.md`.

## Outputs

Produce one `lesson_teaching_prompts` item per lesson using `data-contracts.md#lesson-schema`. Apply `language-policy.md` to authored strings and preserve machine-facing values and immutable source spans.

Under fallback mode, add only the Generation extensions defined in `data-contracts.md#generation-fallback-fields`.

## Validation

- Every `teaching_prompt` is valid runnable MarkdownFlow.
- Every item passes `data-contracts.md#lesson-schema`.
- The first non-empty line performs a teaching-start function and does not duplicate structure metadata.
- The Teaching Prompt contains the selected teaching method and does not outsource pedagogy to the Course Prompt.
- The objective, must-cover facts and boundaries, required sequence, interaction effect, and close are specific enough to execute without guessing.
- Ordinary explanation and slide instructions remain at the intent-and-constraint level instead of becoming an unrequired finished lecture, fixed slide count, typography or color specification, element coordinates, or repeated bullet quota.
- Exact wording or layout is limited to content whose precision affects correctness, teaching effect, runtime behavior, source fidelity, or an explicit author requirement.
- The Teaching Prompt is neither an under-specified outline nor an unnecessarily scripted lecture or fixed slide specification.
- Every resolved constraint island remains exact while surrounding teaching content remains open to runtime generation.
- Interaction, variable, branch, and preservation encoding pass `markdownflow-authoring.md`.
- Image-specific validation runs only for lessons that use image assets.
- Authored human-facing content passes `language-policy.md`.
