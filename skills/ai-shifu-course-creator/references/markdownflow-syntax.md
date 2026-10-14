# MarkdownFlow Runtime Syntax

MarkdownFlow is a prompt-processing format used by Teaching Prompts and Course Prompts. This file describes only the syntax the runtime recognizes and the observable result of that syntax.

## Preprocessing

CommonMark fenced code is protected before MarkdownFlow syntax is recognized. Its complete fence, language tag, and body are restored before downstream generation or deterministic output. MarkdownFlow-looking text inside the fence remains code content rather than an active variable, interaction, or deterministic marker.

## HTML Comments

The Teaching Agent ignores HTML comments (`<!-- ... -->`) in Prompt content.

## Variables

A variable reference has the form `{{name}}`. The 1.0 parser captures the non-empty text between the braces exactly, including any whitespace, and uses that exact text as the lookup key. It does not enforce an identifier-character policy.

In the parser-based 1.0 runtime, before content is generated or an interaction is rendered, each ordinary `{{name}}` reference is replaced with the corresponding runtime value. List values are joined into a comma-separated string. Values sent to the Teaching Agent are quoted for prompt isolation; values in deterministic output are inserted directly.

In that runtime, substitution always produces a value. A variable reference does not create a separate present/absent, ready/not-ready, or boolean state.

Inside an explicit `?[]` control, `%{{name}}` is an assignment prefix rather than a substitution reference. The interaction result is written to `name`; ordinary `{{name}}` references read the resulting value in later processing.

AI-Shifu's MarkdownFlow 2.0 agent runtime also recognizes `%{{name}}` as a collection marker in ordinary instructions outside `?[]`. It preserves the marker rather than substituting an existing value. When a natural-language interaction needs a persisted answer, include that marker in its instruction, for example `Initiate a single-select interaction and save the learner's choice as %{{selected_action}}`. The Teaching Agent names the requested answer `selected_action`, and the runtime saves the actual submitted answer under that name.

This agent runtime substitutes known existing values when preparing the lesson, but leaves collection markers, references to names this lesson collects, and unknown references for the Teaching Agent to interpret. It excludes older values for collected names from the initial learner context, so later `{{selected_action}}` references use this lesson's actual answer. A remaining reference is not a parser-level boolean or readiness test. The 1.0 substitution rules above do not define this agent behavior. Lesson-local answers need no name.

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

This form requires a Teaching Agent runtime that can initiate interactions from instructions, such as AI-Shifu's MarkdownFlow 2.0 agent engine. The 1.0 parser alone does not provide it. A local Prompt can target this capability without platform access; do not claim it works in an existing course whose runtime support has not been established.

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
