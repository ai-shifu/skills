# MarkdownFlow Runtime Syntax

MarkdownFlow is a prompt-processing format used by Teaching Prompts and Course Prompts. This file describes only the syntax the runtime recognizes and the observable result of that syntax.

## Preprocessing

CommonMark fenced code is protected before MarkdownFlow syntax is recognized. Its complete fence, language tag, and body are restored before downstream generation or deterministic output. MarkdownFlow-looking text inside the fence remains code content rather than an active variable, interaction, or deterministic marker.

HTML comments are removed before content is sent to the Teaching Agent. Variable and interaction markers inside those comments do not participate in runtime recognition or substitution.

## Variables

A variable reference has the form `{{name}}`. The parser captures the non-empty text between the braces exactly, including any whitespace, and uses that exact text as the lookup key. It does not enforce an identifier-character policy.

Before content is generated or an interaction is rendered, each `{{name}}` reference is replaced with the corresponding runtime value. List values are joined into a comma-separated string. A missing value, an empty string, or an empty list is replaced with `UNKNOWN`. Values sent to the Teaching Agent are quoted for prompt isolation; values in deterministic output are inserted directly.

Substitution always produces a value. A variable reference does not create a separate present/absent, ready/not-ready, or boolean state.

Inside an interaction, `%{{name}}` is an assignment prefix rather than a substitution reference. The interaction result is written to `name`; ordinary `{{name}}` references read the resulting value in later processing.

## Interactions

An unescaped control matching `?[...]` is rendered as an interaction. The runtime pauses document progression and resumes after an answer is submitted. The answer then enters the current document context.

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

## Branching on User Input

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

Execution depends on the lesson's actual runtime:

- **MarkdownFlow 1.0:** A standalone `===...===` line and a complete `!===...!===` fence produce deterministic output without additional boundary syntax. The runtime removes the markers, substitutes variables without quoting wrappers, restores protected code, and emits the result without invoking the Teaching Agent. An inline `===...===` span becomes a preservation instruction within generated content; an output-language transformation may translate that span while retaining its position and formatting.
- **MarkdownFlow 2.0:** The Teaching Agent receives the whole script, including standalone, multi-line, and inline preservation forms. All marked content is instructed to appear verbatim, character for character, without rewording or translation. These forms do not bypass the Teaching Agent. The host removes preservation markers outside code fences from delivered text; it does not compare the content with its source or restore text changed by the Teaching Agent. Marker presence therefore does not prove exact output.

Runtime variable substitution still applies where supported; the expected content is the selected source with the intended values substituted. Use [source-preservation.md#verification](source-preservation.md#verification) to distinguish source checks from observed runtime fidelity.

## Images

MarkdownFlow has no image-specific control-flow primitive. Standard Markdown image syntax, deterministic image syntax, and natural-language image instructions have these results:

- `![alt](url)` is ordinary prompt content and may be transformed by the Teaching Agent.
- `===![alt](url)===` on its own line applies standalone preservation to the image. Its execution follows the runtime-specific behavior in [Deterministic Blocks](#deterministic-blocks).
- A natural-language request for the Teaching Agent to emit an HTML image remains ordinary prompt content. URL lines, descriptions, captions, layout wording, and wording that requests exact preservation have no dedicated parser semantics.

## Preservation

Preservation combines preprocessing with the selected form and runtime:

- Fenced code blocks are hidden from MarkdownFlow syntax parsing and restored before downstream processing.
- Standalone, multi-line, and inline forms follow [Deterministic Blocks](#deterministic-blocks); their execution guarantees differ between MarkdownFlow 1.0 and 2.0.
- A Markdown image wrapped in the single-line preservation form follows the same runtime contract as other standalone content.
- An HTML-view image instruction remains ordinary Teaching Agent input.
- Content outside these mechanisms may be paraphrased, reorganized, or omitted by the Teaching Agent.
