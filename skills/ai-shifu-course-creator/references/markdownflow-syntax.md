# MarkdownFlow Runtime Syntax

MarkdownFlow is a prompt-processing format used by Teaching Prompts and Course Prompts. This file describes only the syntax the runtime recognizes and the observable result of that syntax.

## Preprocessing

CommonMark fenced code is protected before MarkdownFlow syntax is recognized. Its complete fence, language tag, and body are restored before downstream generation or deterministic output. MarkdownFlow-looking text inside the fence remains code content rather than an active interaction or deterministic marker.

## HTML Comments

The Teaching Agent ignores HTML comments (`<!-- ... -->`) in Prompt content.

## Memory

The platform's account-wide teaching inputs are the learner's preferred form of address, account language, and saved personal introduction. The introduction is optional free text, up to 1000 characters; relevant experience, preferences, goals, and constraints are available only when the learner actually supplied them. These are not separate required registration fields or a verified assessment of ability. Onboarding can be configured, skipped, or unavailable, so a new course must not assume a complete introduction.

The Teaching Agent can also use the current conversation and supplied current-course memory. Account-wide inputs can follow the learner between courses; another course's conversations, wrong answers, scores, or mastery judgments are not automatically imported. A genuinely new course normally has no task-performance evidence yet. A later lesson can receive this course's saved values; resuming or restarting an existing course is not necessarily an empty-memory start.

Ordinary answers, follow-up questions, and corrections can inform the current lesson conversation. Durable reuse across lessons depends on the runtime's named-answer mechanism or the learner's actual explicit request to remember information, and on the value actually being available. An author instruction to remember ordinary input is not itself a learner request or a named binding; do not promise that every ordinary input is automatically saved throughout the course. A current-course memory write does not automatically update the account-wide introduction. Refer naturally to available input, for example `Use the communication difficulty the learner described earlier in this course to tailor the next practice task`, without inventing a storage action or requiring a separate save ritual merely to respond to the current answer.

Use the learner's actual inputs and account for later corrections. If relevant information is unavailable, follow the authored fallback rather than inventing it. When a lesson asks a new question, wait for the actual new answer before giving its feedback; existing memory does not answer a pending interaction on the learner's behalf.

The host refreshes available values during teaching, but model context is bounded: stored information can be omitted, and values being collected again for the current authored task can be withheld from initial memory. Missing context does not prove that the learner never provided it. Use available authorized recall when supported; otherwise follow the lesson's scoped question or fallback. Do not assume that all account, order, progress, or historical records are teaching input.

The implementation basis is the platform's [account-field mapping](https://github.com/ai-shifu/ai-shifu/blob/52841676e8226f9e66138b9e5678cc2ead46309a/src/api/flaskr/service/profile/account_fields.py#L108), [current-course memory scope](https://github.com/ai-shifu/ai-shifu/blob/52841676e8226f9e66138b9e5678cc2ead46309a/src/api/flaskr/service/memory/facade.py#L25), [memory-write policy](https://github.com/ai-shifu/ai-shifu/blob/52841676e8226f9e66138b9e5678cc2ead46309a/src/api/markdownflow/engine/prompts/memory_policy.md), and [bounded first-prompt memory](https://github.com/ai-shifu/ai-shifu/blob/52841676e8226f9e66138b9e5678cc2ead46309a/src/api/markdownflow/engine/script.py#L301). These are runtime input boundaries, not additional authoring fields or instructions to copy platform keys into course artifacts.

## Interactions

An interaction can be authored as an explicit `?[...]` control or as a natural-language instruction to the Teaching Agent. A supported interaction pauses document progression and resumes after the learner submits an answer.

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

### Question Prefix

An explicit control can carry its complete learner-facing question or response task in a prefix immediately after `?[`, before the options or input hint:

- `?[ {{Which action will you take first?}} Verify the source | Check the calculation]`: single-select.
- `?[ {{Which checks will you perform?}} Verify the source || Check the calculation]`: multi-select.
- `?[ {{What is your learning goal?}} ...Describe your goal]`: text input.
- `?[ {{Rewrite the plan with an action, an owner, and a deadline.}} ...Write the revised plan]`: text input for an imperative response task.
- `?[ {{Which action will you practice?}} Verify the source | ...Another action]`: single-select plus text input.
- `?[ {{Which actions will you practice?}} Verify the source || ...Other actions]`: multi-select plus text input.

The prefix associates the answer with that question or response task; the response controls retain their existing selection and input semantics. Conversation use and durable availability follow the [memory contract](#memory); input without this prefix must not be promised automatic reuse in a later lesson. Authoring requirements for filling the question or response task belong to [Interaction Encoding](teaching-prompt.md#interaction-encoding).

### Natural-Language Interactions

These instructions require a Teaching Agent that can create a real response surface and wait for the learner's answer before continuing. Rendering explicit controls alone does not execute natural-language interaction instructions.

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
