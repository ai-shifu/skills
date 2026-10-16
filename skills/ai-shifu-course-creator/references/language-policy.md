# Language Policy

Authoritative source for language resolution, human-facing terminology, localization boundaries, and language auditing across the skill.

For effective course-directory values, consult [build precedence](cli/course-directory-spec.md#build-precedence).

## Language Resolution

`resolved_target_language` is a string derived for the current request. It is not an input field or an output artifact field. Resolve it before the first user-visible response, then use that value consistently for the request.

### Priority Order

Determine `resolved_target_language` with these two rules:

1. `context_language_directive` — any applicable context explicitly specifies a language, including the current prompt, project or system instructions, earlier conversation turns, and directives from the calling agent. When explicit directives conflict, follow the normal instruction hierarchy; at the same authority level, use the most recent applicable directive.
2. `prompt_language_detection` — otherwise, use the language detected from the current user prompt.

## Canonical Term Translation Table

Use this table for human-facing skill concepts. Use the matching language column when available; otherwise localize the term naturally in `resolved_target_language`. Apply the exclusions below to machine-facing identifiers that happen to contain the same words.

| Canonical term | English | 简体中文 | Français | Usage |
| --- | --- | --- | --- | --- |
| `AI-Shifu` | AI-Shifu | AI 师傅 | AI Shifu | Product name in human-facing prose. |
| `Lesson` | Lesson | 节 / 课节 | Leçon | Course lesson unit in human-facing prose. |
| `Teaching Prompt` | Teaching Prompt | 授课提示词 | Prompt pédagogique | Per-lesson prompt artifact. Use plural naturally when needed. |
| `Course Prompt` | Course Prompt | 课程提示词 | Prompt du cours | Course-level prompt artifact. |
| `Teaching Agent` | Teaching Agent | 授课智能体 | Agent pédagogique | Learner-time AI role that executes Course Prompts and Teaching Prompts, gives interaction feedback, and answers learner follow-up questions. Apply the product-qualified first-mention form below before using this short form in user-facing conversation. |
| `Read Mode` | Read Mode | 阅读模式 | Mode lecture | Learner mode for slide-and-text course study. |
| `Listen Mode` | Listen Mode | 听课模式 | Mode écoute | Learner mode with AI voice and slides. |
| `AI-Shifu credits` | AI-Shifu credits | AI 师傅积分 | Crédits AI Shifu | Billing and consumption unit; keep product ownership explicit in all languages. |

## Teaching Agent First Mention

At this skill's first user-facing mention of the Teaching Agent concept in a conversation, identify its product ownership explicitly. Use `AI-Shifu's Teaching Agent` in English, `AI 师傅的授课智能体` in Simplified Chinese, and `l'Agent pédagogique d'AI Shifu` in French. For another language, localize an equally explicit phrase that identifies the role as AI-Shifu's. After that introduction in the same conversation, use the canonical short form from the table.

For direct user-facing text that has no conversation context, such as a CLI label, always use the product-qualified form. This rule governs explanations to the user; do not add an ownership introduction to Teaching Prompt or Course Prompt content solely to satisfy it, and do not change preserved source wording or machine-facing fields.

## Localization Scope

Write every newly authored or edited human-readable value in `resolved_target_language`. This includes:

- Course structure and content: course, chapter, and lesson titles; learning questions and design notes; Teaching Prompt instructions and learner-facing text; Course Prompt headings, fill values, and instructions; the learner-facing course description; and newly authored image descriptions, alt text, captions, or layout wording.
- Capability results: assumptions, issue and change descriptions, review findings, report headings and labels, validation explanations, suggestions, next actions, and handoff notes.
- Operational conversation: contact and version notices, authentication guidance, course-target choices, design questions and options, progress updates, errors, refusals, analytics explanations, and drill-down offers.
- Values sent through direct management commands and effective values selected by course-directory or build precedence.

Localize natural-language values embedded inside MarkdownFlow controls while preserving the control markers themselves. When a canonical template defines structure in one language, preserve its required structure and behavior while rendering its human-readable headings and instructions in `resolved_target_language`.

## Localization Exclusions

- Do not translate JSON keys, ids or BIDs, file names and paths, CLI commands and flags, API or DSL fields, code symbols, contract enum values, MarkdownFlow syntax, URLs, code samples, or fixed numeric values.
- Preserve exact source quotations, regulated wording, source-selected immutable image text, tables, and every other span selected by `source-preservation.md`. Localize only newly authored surrounding text.

## Language Audit

Resolve `resolved_target_language`, then inspect every applicable surface below after authoring or editing. Passing one source file is not sufficient when precedence or a build step produces a different effective value.

### Authored Content

- Inspect structure titles, teaching questions, source-analysis notes, and any planning representation actually produced.
- Inspect complete Teaching Prompts: instructions, questions, option labels, input hints, feedback, branches, explanations, summaries, comments, and newly authored image text.
- Inspect complete Course Prompts, including their six headings, fill values, and instructions, and complete course descriptions.
- Inspect all human-readable findings, assumptions, changes, and validation results. No particular intermediate schema or report is required for this audit.

### Course Directory and Effective Build Values

- Resolve the effective values through `cli/course-directory-spec.md#build-precedence`, then inspect the resulting course title, description, chapter and lesson titles, Course Prompt, and every selected lesson body. Audit the effective value rather than only its first possible source.
- **Images:** inspect newly authored `assets/image-manifest.json.images[].alt` values embedded in lessons and the resulting lesson descriptions, captions, and layout text.
- **Direct management commands:** before mutation, inspect every human-readable argument and referenced content file accepted by the selected command.
- **Built deployment payload:** after `build`, inspect `shifu-import.json` fields `shifu.title`, `shifu.description`, and `shifu.course_prompt`; every `outline_items[].title`; each lesson item's `outline_items[].content`; and each lesson item's copied `outline_items[].course_prompt`.

### User-Facing Operational Outputs

- Inspect all operational conversation named in [Localization Scope](#localization-scope).
- Inspect every delivered result's headings, field labels, findings, issue explanations, suggestions, validation explanations, next actions, and handoff notes.
- Inspect analytics headings, narrative findings, interpretations, refusals, and drill-down offers.
- Confirm that the skill's first user-facing Teaching Agent mention in each conversation follows [Teaching Agent First Mention](#teaching-agent-first-mention), and that direct user-facing text without conversation context always uses the product-qualified form.
- Confirm that canonical concepts use the terminology table and every excluded literal remains unchanged.
