# MarkdownFlow Quick Spec

## Variables

- Reference syntax: `{{var_name}}`
- No spaces in variable names
- Undefined variables resolve to `UNKNOWN`

## Interactions

- Single-select: `?[%{{var}} Option A | Option B | Option C]`
- Multi-select: `?[%{{var}} Option A || Option B || Option C]`
- Input: `?[%{{var}} ...Enter your answer]`
- Single-select + input: `?[%{{var}} Option A | Option B | ...Other, please specify]`
- Multi-select + input: `?[%{{var}} Option A || Option B || ...Other, please specify]`

### Prompt Placement Rules

- Put the learner-facing question or prompt in the script text immediately before the interaction line.
- Put only option labels inside select interactions.
- Do not place the question after `%{{var}}`; it will become part of the selectable interaction content.

Correct:

```markdown
Ask the learner: Which option best matches your situation?
?[%{{choice}} Option A | Option B | Option C | ...Other]
```

Incorrect:

```markdown
?[%{{choice}} Which option best matches your situation? Option A | Option B | Option C | ...Other]
```

### Input Marker Rules

- `...` is an input marker, not punctuation.
- `...` must appear immediately before the free-text prompt or free-text option label.
- For pure input, use `?[%{{var}} ...Prompt text]`.
- For select + input, put `...` at the start of the option that opens text entry, such as `...Other, please specify`.
- Do not move `...` to the end of the prompt text.
- Do not write `?[%{{var}} Prompt text...]`.
- Do not write `?[%{{var}} Option A | Option B | Other, please specify...]`.

### Input Marker Examples

- Correct: `?[%{{learner_goal}} ...Describe your goal in one sentence]`
- Correct: `?[%{{difficulty_type}} Concept unclear | Need practice | ...Other, please specify]`
- Incorrect: `?[%{{learner_goal}} Describe your goal in one sentence...]`
- Incorrect: `?[%{{difficulty_type}} Concept unclear | Need practice | Other, please specify...]`

## Deterministic Output

- Single-line fixed text: `===fixed text===`
- Multi-line fixed text:

```markdown
!===
Line 1
Line 2
!===
```
