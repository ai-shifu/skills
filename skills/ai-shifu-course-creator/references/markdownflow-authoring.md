# MarkdownFlow Authoring

Encode already-resolved teaching, interaction, variable, and preservation decisions into MarkdownFlow. Parser recognition and runtime effects remain defined only in `markdownflow.md`.

## Required References

- `language-policy.md`
- `data-contracts.md#variable-table`
- `pedagogy.md#interaction-design`
- `pedagogy.md#variable-strategy`
- `markdownflow.md`

## Conditional References

- When immutable source spans were selected for encoding: `source-preservation.md`

## Interaction Encoding

- Put the complete learner-facing question immediately before the interaction control, and put the `?[]` control on its own line.
- Keep only option labels, the optional `%{{name}}` assignment prefix, and any free-text marker plus short hint inside `?[]`.
- Use `|` for single-select, `||` for multi-select, and `...` immediately before the input hint or custom-answer label.
- Use `%{{name}}` only when the answer must leave the current lesson. Lesson-local answers use the no-variable form; a blank variable name is invalid.
- For input, write a specific question before the control and a shorter hint after `...`. For select-plus-input, put `...` at the start of the custom-answer option.
- When preceding text describes choices, keep control labels identical in set, order, and wording.
- After the control, encode the feedback or visible instructional effect selected by `pedagogy.md#interaction-design`.

Neutral shapes:

```markdown
Ask the learner which path best matches the current case.

?[Path A | Path B]

After the learner answers, explain the selected path and contrast it with the other path.

Ask the learner for the course-wide goal that later lessons and the Course Prompt should use.

?[%{{learning_goal}} ...One-sentence goal]
```

## Variable and Branch Encoding

- Write branch behavior as natural-language instructions; MarkdownFlow has no programmatic conditional syntax.
- Refer to lesson-local answers naturally rather than inventing a variable.
- For a named value, first bind the substituted value in a natural sentence such as `The learner goal is {{learning_goal}}.`, then describe branches against that value.
- When a named value can be read before collection, branch on the literal substituted value `UNKNOWN`; do not test readiness or marker existence.
- Every named learner-answer reference must have a matching variable-backed collection and pass `data-contracts.md#variable-table`.
- Compose newly authored variable names under `language-policy.md` using only letters, numbers, and underscores. Preserve existing names when changing them would break the contract.

## Preservation Encoding

When immutable source spans were selected, load `source-preservation.md` and encode only those spans:

- Put a complete standalone single-line span that must bypass the LLM inside `===...===`.
- Put a complete multi-line span that must bypass the LLM inside `!===...!===`; include the full code fence and language tag when exact fenced output is required.
- In otherwise generated content, wrap only the position- and formatting-sensitive span inline with `===...===`. Inline preservation remains LLM-mediated and may be translated.
- Encode each selected span independently and leave adaptive content outside deterministic markers.

Image composition is owned by `image-authoring.md` and is loaded conditionally by the selected workflow.

## Validation

- Every interaction control is on its own line and matches the preceding question or options.
- Every named variable passes collection, reference, and metadata invariants.
- Branch instructions use natural language and literal `UNKNOWN` where required.
- Each immutable span uses the runtime form matching its selected preservation scope.
