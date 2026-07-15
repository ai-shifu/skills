## Unreleased

- Centralize Prompt audience and addressee semantics so Teaching Prompts and Course Prompts are written to the runtime LLM, Course Prompts call the lesson input the current user message, and learner-visible `?[]` content is the explicit exception where second-person references may mean the learner.
- Keep lesson pedagogy in Teaching Prompts and limit Course Prompts to following that pedagogy while adjusting course-wide presentation style.
- Disambiguate pedagogy contracts by centralizing teaching effects, transfer-signal meanings, variable strategy, and visual delivery boundaries while preserving existing behavior.
- Fix `list` and `find-title` to include courses beyond the first API page.
- Turn `SKILL.md` into a task router with explicit shared dependencies.
- Split authoring, deployment, authentication, and analytics instructions into route-specific reference files.
- Restore global language and reporting contracts, narrow analytics routing to live-course data, and add routing regression evals.

## 1.0.0 - 2026-07-12

- Add a stable Skill version identity.
- Add fail-open update checks backed by the public AI-Shifu website manifest.
