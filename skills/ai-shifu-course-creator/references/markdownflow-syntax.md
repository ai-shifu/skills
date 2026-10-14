# MarkdownFlow Runtime Syntax

MarkdownFlow is a prompt-processing format used by Teaching Prompts and Course Prompts. This file describes only the syntax the runtime recognizes and the observable result of that syntax.

## Preprocessing

CommonMark fenced code is protected before MarkdownFlow syntax is recognized. Its complete fence, language tag, and body are restored before downstream generation or deterministic output. MarkdownFlow-looking text inside the fence remains code content rather than an active variable, interaction, or deterministic marker.

## HTML Comments

The Teaching Agent ignores HTML comments (`<!-- ... -->`) in Prompt content.

## Variables

A variable reference has the form `{{name}}`. It reads the named value from the learner context.

Use `%{{name}}` to name an answer the lesson collects. In an explicit `?[]` control, it is an assignment prefix; in a natural-language interaction, include it in the instruction, for example `Initiate a single-select interaction and save the learner's choice as %{{selected_action}}`. The marker is preserved rather than substituted with an existing value.

When preparing the lesson, the runtime substitutes known existing values into ordinary references. List values are joined into a comma-separated string. Collection markers, references to names this lesson collects, and references with missing, null, or empty-string values remain for the Teaching Agent to interpret.

Older values for names collected by this lesson are excluded from the initial learner context. After the learner actually submits an answer, the runtime saves it under the collection name. The Teaching Agent uses that answer to interpret later references such as `{{selected_action}}`. Lesson-local answers need no name.

A reference does not create a parser-level boolean or readiness test. Give the Teaching Agent instructions for handling unavailable information without inventing a value.

## Interactions

An interaction can be authored as an explicit `?[...]` control or as a natural-language instruction to the Teaching Agent. The runtime pauses document progression and resumes after an answer is submitted. The answer then enters the current document context.

### Explicit Controls

An unescaped control matching `?[...]` specifies the response surface directly.

The interaction body is interpreted as follows:

- `?[Continue]`: single action button; the action remains in the current document context.
- `?[Option A | Option B]`: single-select; the answer remains in the current document context.
- `?[Option A || Option B]`: multi-select; the answers remain in the current document context.
- `?[...Input hint]`: text input; the answer remains in the current document context.
- `?[Option A | ...Other]`: single-select plus text input; the answer remains in the current document context.
- `?[Option A || ...Other]`: multi-select plus text input; the answers remain in the current document context.
- `?[%{{name}} Option A | Option B]`: named single-select; the answer also writes `name`.
- `?[%{{name}} Option A || Option B]`: named multi-select; the answers also write `name`.
- `?[%{{name}} ...Input hint]`: named text input; the answer also writes `name`.
- `?[%{{name}} Option A | ...Other]`: named single-select plus text input; the answer also writes `name`.
- `?[%{{name}} Option A || ...Other]`: named multi-select plus text input; the answers also write `name`.

The first separator determines selection mode: `|` represents one selected value and `||` represents multiple selected values. The token `...` marks a free-text entry field, and the text immediately after it is the rendered input hint.

### Natural-Language Interactions

A Teaching Prompt can directly describe what the Teaching Agent should ask the learner to do, without a `?[]` control or a fixed option list. The Teaching Agent generates the question and response surface at learner time using the current lesson context and the learner's actual prior answers. Selection mode, option constraints, and whether a custom text answer is allowed can be stated in words.

This is ordinary Prompt content interpreted by the Teaching Agent, not additional parser syntax. Put the instruction outside `?[]`: `?[Generate suitable options]` specifies a button with that text rather than requesting dynamic options. Generated choices still require a real interaction and an actual learner answer before subsequent feedback or teaching proceeds.

For example:

```markdown
Using the communication situation just discussed, initiate a single-select interaction asking the learner which communication action they most want to practice next. Dynamically generate three specific, distinct action options from the current conversation, and allow the learner to enter another action.

Wait for the learner's actual answer, then provide one actionable practice suggestion for the selected or custom action.
```

Explicit controls and natural-language interactions may coexist in one lesson. An author-fixed question, option list, order, or answer mode remains fixed unless the author permits adaptation. Dynamic generation does not create parser-level branches or guarantee a particular generated wording.

## Branching on User Input

The prompt after an interaction can tell the Teaching Agent to give different responses based on the learner's answer, including asking the learner to interact again. Express these instructions in natural language.

MarkdownFlow has no parser-level conditionals, loops, boolean expressions, `if` blocks, `switch` blocks, or ternary expressions. Natural-language statements that describe different responses for different answers remain ordinary prompt content. The Teaching Agent interprets those statements using the current document context and substituted variable values; the MarkdownFlow parser does not create or evaluate a branch graph.

## Deterministic Blocks

MarkdownFlow recognizes two preservation forms:

- Single-line or inline marker: `===fixed text===`
- Multi-line fence:

```markdown
!===

Paragraph 1

Paragraph 2

!===
```

A standalone `===...===` line and a complete multi-line fence produce deterministic output without requiring any additional boundary syntax. The markers are omitted from delivered text.

Inline `===...===` preserves the marked content and position within generated content. The surrounding content remains generated by the Teaching Agent. If an output-language transformation applies, marked content in all preservation forms is translated into the target language while its position and formatting are retained. Source wording in the authored Teaching Prompt follows the [localization exclusions](language-policy.md#localization-exclusions); this translation applies to runtime output.

## Images

MarkdownFlow has no image-specific control-flow primitive. Standard Markdown image syntax and natural-language image instructions have these results:

- `![alt](url)` is ordinary prompt content and may be transformed by the Teaching Agent.
- A natural-language request for the Teaching Agent to emit an HTML image remains ordinary prompt content. URL lines, descriptions, captions, layout wording, and wording that requests exact preservation have no dedicated parser semantics.

## Preservation

Runtime preservation is the combined result of preprocessing and deterministic forms:

- Fenced code blocks are hidden from MarkdownFlow syntax parsing and restored before downstream processing.
- Standalone single-line and complete multi-line forms produce deterministic output after variable substitution.
- An inline `===...===` marker preserves its content within generated content.
- An HTML-view image instruction remains ordinary Teaching Agent input.
- Content outside these mechanisms may be paraphrased, reorganized, or omitted by the Teaching Agent.
