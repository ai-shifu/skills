## Unreleased

- Centralize Prompt audience and addressee semantics so Teaching Prompts and Course Prompts are written to the runtime LLM, Course Prompts call the lesson input the current user message, and learner-visible `?[]` or standalone deterministic output is the explicit exception where second-person references may mean the learner.
- Keep lesson pedagogy in Teaching Prompts and limit Course Prompts to following that pedagogy while adjusting course-wide presentation style.
- Refactor `SKILL.md` into a compact router backed by single-purpose references for language, authoring mode and intake, source preservation, segmentation, orchestration, Teaching and Course Prompt materialization, MarkdownFlow authoring, images, course descriptions, optimization, deployment, sync, management, analytics, and reporting; declare required and conditional dependencies explicitly without changing course behavior.
- Fix `list` and `find-title` to include courses beyond the first API page.
- Restore global language and reporting contracts, narrow analytics routing to live-course data, and add routing regression evals.

## 1.0.0 - 2026-07-12

- Add a stable Skill version identity.
- Add fail-open update checks backed by the public AI-Shifu website manifest.
