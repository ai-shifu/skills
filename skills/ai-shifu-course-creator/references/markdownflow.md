# MarkdownFlow Spec

MarkdownFlow is the **format** (a small DSL) used to author both **Teaching Prompts** (per-lesson, runtime teaching instructions) and **Course Prompts** (course-level AI persona / style / drawing rules). This file is the authoritative source for the format itself — syntax, runtime constraints, and preservation rules. Violating anything here makes the prompt fail to parse, reference an uncollected variable, or silently lose source content.

For pedagogical / quality-of-teaching constraints (which apply to Teaching Prompts), see [pedagogy.md](pedagogy.md). For Course Prompt structure and authoring rules, see [course-prompt.md](course-prompt.md).

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
- If the pre-interaction text enumerates or describes the choices, the option labels in the `?[]` line must match those choices exactly — same set, same order, same wording. The narrative options and the interaction options must not drift apart.

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

## Branching on User Input

MarkdownFlow has no programming-style conditionals, loops, or boolean logic. There is no parser that evaluates `{{var}} == "A"`; there are no `if` blocks, `switch` blocks, or ternary expressions to wire up control flow.

Branching is enacted by writing **natural-language instructions** that describe what the AI should generate under each possible learner input. Phrasings such as "If the learner's input is X, then …" are **generation strategies the AI follows**, not `if`-`else` code.

Example:

```markdown
Ask the learner for their stance on the claim above.
?[%{{attitude}} Agree | Partially agree | Disagree]

The learner's stance is {{attitude}}.

- If the learner's stance is Agree, acknowledge the agreement appreciatively.
- If the learner's stance is Partially agree, ask which parts they agree with and which parts they do not.
- If the learner's stance is Disagree, ask why they disagree.
```

The bullet phrasing reads like `if`, but it is not `if` — it is an instruction the AI engine interprets while generating. Nothing in MarkdownFlow evaluates the condition. The branching is enacted by the AI following the instruction.

### No program syntax around `{{var}}`

A Teaching Prompt looks like code (variables, interaction markers, branched outcomes), but it is read by a language model, not executed by an interpreter. Wrapping `{{var}}` in `if`-`else` blocks, ternary expressions, `switch` / `case`, or fenced pseudo-code blocks makes the script look like a program and pushes the AI toward executing-not-interpreting behavior, which degrades teaching quality.

Express every branch as a plain instruction sentence:

- Bad: `if {{level}} == "beginner": use simple analogies`
- Good: `For {{level}} = beginner, use simple analogies; for intermediate, introduce technical terms; for expert, go deep into edge cases.`

> The point of MarkdownFlow is not to write the lesson content directly, but to use natural language to precisely instruct the AI on how to generate content under each possible learner input.

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
- Pre-interaction text enumerates choices A / B / C but `?[%{{var}} X | Y | Z]` exposes a different set — the narrative description and the interaction options must stay aligned (same set, order, and wording).
- `if {{var}} == "A": …` / `{{#if var}}…{{/if}}` / `switch ({{var}}) { … }` — program-style branching syntax around `{{var}}`. MarkdownFlow has no conditional parser; express branches as plain instruction sentences (see [Branching on User Input](#branching-on-user-input)).
- Wrapping an entire lesson body in `=== … ===` or `!=== … !===`.
- Referencing `{{var}}` in learner-facing text before any `?[%{{var}} …]` collects it.
