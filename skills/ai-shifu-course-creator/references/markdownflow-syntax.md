# MarkdownFlow Runtime Syntax

MarkdownFlow is a prompt-processing format used by Teaching Prompts and Course Prompts. This file describes only the syntax the runtime recognizes and the observable result of that syntax.

## Preprocessing

CommonMark fenced code is protected before MarkdownFlow syntax is recognized. Its complete fence, language tag, and body are restored before downstream generation or deterministic output. MarkdownFlow-looking text inside the fence remains code content rather than an active interaction or deterministic marker.

## HTML Comments

The Teaching Agent ignores HTML comments (`<!-- ... -->`) in Prompt content.

## Memory

Every learner input within a course is automatically recorded in that learner's course memory, including choices, text answers, follow-up questions, and corrections. The Teaching Agent can use this memory anywhere in the course, across lessons and in the Course Prompt.

Describe memory use in ordinary language, for example `Use the communication difficulty the learner described earlier in the course to tailor the next practice task`. Memory is recorded automatically; authors describe what earlier input is relevant and how it affects teaching.

Use the learner's actual inputs and account for later corrections. If relevant information is unavailable, follow the authored fallback rather than inventing it. When a lesson asks a new question, wait for the actual new answer before giving its feedback; existing memory does not answer a pending interaction on the learner's behalf.

## Interactions

An interaction can be authored as an explicit `?[...]` control or as a natural-language instruction to the Teaching Agent. The runtime pauses document progression and resumes after an answer is submitted.

### Explicit Controls

An unescaped control matching `?[...]` specifies the response surface directly.

The interaction body is interpreted as follows:

- `?[Continue]`: single action button.
- `?[Option A | Option B]`: single-select.
- `?[Option A || Option B]`: multi-select.
- `?[...Input hint]`: text input.
- `?[Option A | ...Other]`: single-select plus text input.
- `?[Option A || ...Other]`: multi-select plus text input.

The first separator determines selection mode: `|` represents one selected value and `||` represents multiple selected values. The token `...` marks a free-text entry field, and the text immediately after it is the rendered input hint.

### Natural-Language Interactions

A Teaching Prompt can directly describe what the Teaching Agent should ask the learner to do, without a `?[]` control or a fixed option list. The Teaching Agent generates the question and response surface at learner time using the lesson context and relevant course memory. Selection mode, option constraints, and whether a custom text answer is allowed can be stated in words.

This is ordinary Prompt content interpreted by the Teaching Agent, not additional parser syntax. Put the instruction outside `?[]`: `?[Generate suitable options]` specifies a button with that text rather than requesting dynamic options. Generated choices still require a real interaction and an actual learner answer before subsequent feedback or teaching proceeds.

For example:

```markdown
Using the communication situation the learner described earlier in the course, initiate a single-select interaction asking the learner which communication action they most want to practice next. Dynamically generate three specific, distinct action options for that situation, and allow the learner to enter another action.

Wait for the learner's actual answer, then provide one actionable practice suggestion for the selected or custom action.
```

Explicit controls and natural-language interactions may coexist in one lesson. An author-fixed question, option list, order, or answer mode remains fixed unless the author permits adaptation. Dynamic generation does not create parser-level branches or guarantee a particular generated wording.

## Branching on User Input

The prompt after an interaction can tell the Teaching Agent to give different responses based on the learner's answer, including asking the learner to interact again. Express these instructions in natural language.

MarkdownFlow has no parser-level conditionals, loops, boolean expressions, `if` blocks, `switch` blocks, or ternary expressions. Natural-language statements that describe different responses for different answers remain ordinary prompt content. The Teaching Agent interprets those statements using the lesson context and course memory; the MarkdownFlow parser does not create or evaluate a branch graph.

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
- Standalone single-line and complete multi-line forms produce deterministic output.
- An inline `===...===` marker preserves its content within generated content.
- An HTML-view image instruction remains ordinary Teaching Agent input.
- Content outside these mechanisms may be paraphrased, reorganized, or omitted by the Teaching Agent.
