# MarkdownFlow Spec

MarkdownFlow is a prompt-processing format used by Teaching Prompts and Course Prompts. This file describes only the syntax the parser recognizes and the runtime behavior that follows from that syntax.

## Processing Model

MarkdownFlow processes a document as an ordered sequence of blocks:

1. The runtime preprocesses fenced code blocks and HTML comments before looking for MarkdownFlow syntax.
2. A standalone line whose trimmed content is `---` separates adjacent content blocks. An unescaped `?[]` control outside a fenced code block or HTML comment becomes its own interaction block. A block whose non-empty content is entirely wrapped in preservation markers becomes a preserved-content block; every other block is a generative content block.
3. Before a block runs, the runtime assembles its context from the Course Prompt, earlier output and interaction answers in the current document, and any named values supplied by the platform or earlier documents.
4. Variable references are substituted with their concrete values. Missing or empty values become the literal `UNKNOWN`.
5. A generative content block is sent to the LLM with the assembled context. A preserved-content block bypasses the LLM and is emitted after variable substitution. An interaction block is rendered as a control and pauses progression until the learner submits an answer.
6. After an interaction answer is accepted, the answer enters the current document context. When the control has a `%{{name}}` assignment prefix, the answer is also written to that named value for later documents.
7. Processing resumes with the next block until the document is complete.

## Preprocessing

CommonMark fenced code blocks are replaced with internal placeholders before block and syntax parsing. Their complete fences, language tags, and bodies are restored before a content block is sent to the LLM or a preserved-content block is emitted. MarkdownFlow-looking text inside a fenced code block is therefore code content rather than an active variable, interaction, separator, or preservation marker.

HTML comments are removed from generative content before it is sent to the LLM. Variable and interaction markers inside those comments do not participate in runtime parsing or substitution.

## Variables

A variable reference has the form `{{name}}`. The parser captures the non-empty text between the braces exactly, including any whitespace, and uses that exact text as the lookup key. It does not enforce an identifier-character policy.

Before the LLM receives a Course Prompt, content block, or interaction block, each `{{name}}` reference is replaced with the corresponding runtime value. List values are joined into a comma-separated string. A missing value, an empty string, or an empty list is replaced with `UNKNOWN`. Substituted values in generative blocks are quoted for prompt isolation; values in complete preserved-content blocks are inserted directly.

Substitution always produces a value. A variable reference does not create a separate present/absent, ready/not-ready, or boolean state for the branch parser to inspect.

Inside an interaction, `%{{name}}` is an assignment prefix rather than a substitution reference. The interaction result is written to `name`; ordinary `{{name}}` references read the resulting value in later processing.

## Interactions

An unescaped control matching `?[...]` is parsed as an interaction block. The runtime removes it from the surrounding generative text, renders the corresponding control, pauses document progression, and resumes after an answer is submitted.

The interaction body is interpreted as follows:

| Form | Parsed control | Runtime state effect |
|---|---|---|
| `?[Continue]` | Single action button | Action remains in the current document context |
| `?[Option A \| Option B]` | Single-select | Answer remains in the current document context |
| `?[Option A \|\| Option B]` | Multi-select | Answers remain in the current document context |
| `?[...Input hint]` | Text input | Answer remains in the current document context |
| `?[Option A \| ...Other]` | Single-select plus text input | Answer remains in the current document context |
| `?[Option A \|\| ...Other]` | Multi-select plus text input | Answers remain in the current document context |
| `?[%{{name}} Option A \| Option B]` | Named single-select | Answer also writes `name` |
| `?[%{{name}} Option A \|\| Option B]` | Named multi-select | Answers also write `name` |
| `?[%{{name}} ...Input hint]` | Named text input | Answer also writes `name` |
| `?[%{{name}} Option A \| ...Other]` | Named single-select plus text input | Answer also writes `name` |
| `?[%{{name}} Option A \|\| ...Other]` | Named multi-select plus text input | Answers also write `name` |

The first separator determines selection mode: `|` represents one selected value and `||` represents multiple selected values. The token `...` marks a free-text entry field, and the text immediately after it is the rendered input hint.

## Branching on User Input

MarkdownFlow has no parser-level conditionals, loops, boolean expressions, `if` blocks, `switch` blocks, or ternary expressions. Natural-language statements that describe different responses for different answers remain ordinary prompt content. The LLM interprets those statements using the current document context and substituted variable values; the MarkdownFlow parser does not create or evaluate a branch graph.

## Deterministic Blocks

MarkdownFlow recognizes two preservation forms:

- Single-line or inline marker: `===fixed text===`
- Multi-line fence:

```markdown
!===
Line 1
Line 2
!===
```

When every non-empty part of a parsed block is covered by these markers, the block is classified as preserved content. The runtime removes the markers, substitutes variables without adding quoting wrappers, restores preprocessed code, and emits the result without an LLM call.

When a preservation marker appears inside a larger generative content block, the block still goes through the LLM. The marked span is converted to a preservation instruction for that generation. If the runtime also applies an output-language transformation, the marked text may be translated while its position and formatting are retained.

## Images

MarkdownFlow has no image-specific control-flow primitive. Standard Markdown image syntax, raw HTML, and natural-language image instructions are processed according to the block that contains them:

- `![alt](url)` in a generative content block is ordinary prompt content and may be transformed by the LLM.
- `===![alt](url)===` as a complete preserved-content block bypasses the LLM through the deterministic-block mechanism.
- A natural-language request for the LLM to emit an HTML image remains generative content. URL lines, descriptions, captions, layout wording, and wording that requests exact preservation have no dedicated parser semantics.

## Preservation

Runtime preservation is the combined result of preprocessing and deterministic blocks:

- Fenced code blocks are hidden from MarkdownFlow syntax parsing and restored before downstream processing.
- Complete deterministic blocks bypass the LLM after variable substitution.
- Marked spans inside generative blocks are sent to the LLM as preservation instructions.
- Images inherit the generative or preserved behavior of their containing block.
- Content outside these mechanisms remains generative and may be paraphrased, reorganized, or omitted by the LLM.
