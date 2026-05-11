# MarkdownFlow Spec

Authoritative source for MarkdownFlow syntax, runtime constraints, and preservation rules. Violating anything here makes the script fail to parse, reference an uncollected variable, or silently lose source content. For pedagogical / quality-of-teaching constraints, see [pedagogy.md](pedagogy.md).

## Variables

- Reference syntax: `{{var_name}}`
- No spaces in variable names
- Undefined variables resolve to `UNKNOWN`
- Variables must be collected (via an interaction line) before being referenced in learner-facing text
- See [pedagogy.md#variable-strategy](pedagogy.md#variable-strategy) for collection pacing, downstream-effect, and semantic-duplication rules
- See [data-contracts.md#variable-table](data-contracts.md#variable-table) for the `global_variable_table` schema

## Interactions

- Single-select: `?[%{{var}} Option A | Option B | Option C]`
- Multi-select: `?[%{{var}} Option A || Option B || Option C]`
- Input: `?[%{{var}} ...Enter your answer]`
- Single-select + input: `?[%{{var}} Option A | Option B | ...Other, please specify]`
- Multi-select + input: `?[%{{var}} Option A || Option B || ...Other, please specify]`

### Prompt Placement Rules

- Put the learner-facing question or prompt in the script text immediately before the interaction line.
- Put each `?[]` interaction on its own line.
- Inside the interaction line, include only interaction content: option labels for select interactions, and input markers/placeholders such as `...Other` or `...Brief situation` where applicable.
- Do not place learner-facing question text after `%{{var}}`; it will become part of the interaction content.
- For input interactions, include both the full question before the interaction line and a shorter placeholder after `...`.

Correct:

```markdown
Ask the learner: Which option best matches your situation?
?[%{{choice}} Option A | Option B | Option C | ...Other]

Ask the learner: What is one specific situation where you want to apply this idea this week?
?[%{{example}} ...Brief situation]
```

Incorrect:

```markdown
?[%{{choice}} Which option best matches your situation? Option A | Option B | Option C | ...Other]
?[%{{example}} What is one situation where you want to apply this idea this week? ...Describe your situation]
Ask the learner: Which option best matches your situation? ?[%{{choice}} Option A | Option B | Option C]
```

### Input Marker Rules

- `...` is an input marker, not punctuation.
- `...` must appear immediately before the short free-text placeholder or free-text option label.
- For pure input, use `?[%{{var}} ...Short placeholder]` after a fuller learner-facing question.
- For select + input, put `...` at the start of the option that opens text entry, such as `...Other, please specify`.
- Do not move `...` to the end of the prompt text.
- Do not write `?[%{{var}} Prompt text...]`.
- Do not write `?[%{{var}} Option A | Option B | Other, please specify...]`.

### Input Marker Examples

- Correct:
  Ask the learner: What is one goal you want this lesson to help you achieve in your current work?
  ?[%{{learner_goal}} ...One-sentence goal]
- Correct: `?[%{{difficulty_type}} Concept unclear | Need practice | ...Other, please specify]`
- Incorrect: `?[%{{learner_goal}} Describe your goal in one sentence...]`
- Incorrect: `?[%{{difficulty_type}} Concept unclear | Need practice | Other, please specify...]`

For interaction-design quality (concrete prompts, branching, deepening interactions), see [pedagogy.md#interaction-design](pedagogy.md#interaction-design).

## Deterministic Blocks

- Single-line fixed text: `===fixed text===`
- Multi-line fixed text:

```markdown
!===
Line 1
Line 2
!===
```

Use deterministic blocks only for truly fixed content (legally or operationally locked statements, fixed images). Do not lock entire lessons in fixed syntax — that defeats the model-guiding purpose of MarkdownFlow.

## Preservation

### Immutable Assets

- Code blocks and fence language.
- Image URLs, alt text, and ordering.
- Regulated wording or fixed numeric thresholds.

### Controlled Rewriting

Allowed:
- Filler removal.
- Sentence smoothing.
- Structural reorganization for lesson clarity.

Not allowed:
- Silent factual changes.
- Unmarked omission of required source evidence.
- Variable references before collection.

### Deterministic Block Policy

Use deterministic blocks only for truly fixed content. Do not lock entire lessons in fixed syntax. For images that must remain unchanged, use single-line deterministic syntax per image.

## Common Mistakes

- `?[%{{var}} Prompt text…]` — `...` placed at end of prompt instead of before placeholder.
- `?[%{{var}} A | B | Other, please specify…]` — same issue inside an option label.
- `?[%{{var}} Question prompt? Option A | Option B]` — question inside the interaction line; move it to the line above.
- `Ask the learner the question. ?[%{{var}} A | B | C]` — interaction not on its own line.
- Wrapping an entire lesson body in `=== … ===` or `!=== … !===`.
- Referencing `{{var}}` in learner-facing text before any `?[%{{var}} …]` collects it.
