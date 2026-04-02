# Trigger Eval Design Principles

## User Persona

Queries are written from the perspective of a user with the following knowledge profile.

**Knows:**
- I'm building courses on the AI-Shifu (AI师傅) platform
- The platform supports course creation, modification, and publishing
- Courses are authored in MarkdownFlow (MDF) scripting language
- Course structure has chapters and lessons; each lesson contains a MarkdownFlow prompt script
- There is a global system prompt that constrains the overall course output
- MarkdownFlow has its own syntax rules
- I can create a course from raw materials end-to-end, or CRUD existing course content

**Does NOT know:**
- The skill internally has multiple phases (Phase 1–5)
- Internal skill constraints beyond MarkdownFlow syntax (e.g., issue classes, gates, segment schema, transfer signals)

---

## should_trigger Principles

- Queries must be **action-type** tasks that require Claude to *do* something (write a script, deploy a course, fix a lesson, convert materials), not just answer a knowledge question.
- Action tasks are complex enough that Claude would benefit from consulting a specialized skill — e.g., multi-step operations, platform-specific syntax, end-to-end workflows.
- Queries must come from someone who already knows they are on the AI-Shifu platform.
- Queries should reference platform-visible concepts: MarkdownFlow, MDF, AI师傅, AI-Shifu, course structure, publishing, system prompt.
- Do not use internal tool names (e.g., shifu-cli) or internal phase/gate terminology that users would not know.

---

## should_not_trigger Principles

- Queries should be **near-miss traps** that share surface-level keywords (course, Markdown, interactive, quiz, publish, variable) but are clearly not about AI-Shifu.
- Distribute by semantic distance:
  - `very_close` — other course platforms (Coursera, Teachable, 小鹅通, etc.)
  - `close` — Markdown-based interactive tools (Slidev, Jekyll, mdBook, etc.)
  - `medium` — LLM/teaching design not on AI-Shifu (ChatGPT prompts, RAG, LangChain, etc.)
  - `far` — unrelated tasks (CI/CD, npm publish, API coverage, env vars, etc.)

---

## Recommended Distribution

| Category | Count |
|---|---|
| should_trigger | 20 |
| should_not_trigger: very_close | 5 |
| should_not_trigger: close | 5 |
| should_not_trigger: medium | 5 |
| should_not_trigger: far | 5 |

---

## Version Notes

**v2 change (2026-04-02):** `should_trigger` queries redesigned from consultation-type to action-type.

| | v1（咨询型） | v2（操作型） |
|---|---|---|
| 示例 | "MarkdownFlow 里单选题语法怎么写？" | "帮我写一段 MarkdownFlow 脚本，包含单选、多选、输入框三种互动" |
| 问题 | Claude 直接回答，不调用 skill | Claude 需要 skill 来完成复杂操作 |
| 触发率 | 0% | 85%+ |

**Reason:** Claude answers knowledge questions directly from training data without invoking any skill. Action-type tasks require multi-step platform-specific workflows that Claude cannot complete without the skill.
