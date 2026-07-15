## Unreleased

- Make platform-bound course creation and content edits continue through deployment and publication by default, while keeping planning and artifact-only work non-mutating.
- Give authoring, platform, and analytics concepts a single file owner, route consumers through one-way authority layers, and guard against cycles, missing authority links, and duplicated contracts.
- Make `version-metadata.json` the leaf authority for update checks so runtime code no longer reads the task router and closes the metadata dependency cycle.
- Preserve legacy authoring inputs through a single normalization boundary, restore shared image handling and platform route semantics, and retain canonical phase outputs.
- Keep focused Optimization audits scoped to supplied artifacts and align rating, follow-up, credit, order, identity, and DSL guidance with backend contracts.
- Disambiguate pedagogy contracts by centralizing teaching effects, transfer-signal meanings, variable strategy, and visual delivery boundaries.
- Fix `list` and `find-title` to include courses beyond the first API page.
- Turn `SKILL.md` into a task router with explicit shared dependencies.
- Split authoring, deployment, authentication, and analytics instructions into route-specific reference files.
- Restore global language and reporting contracts, narrow analytics routing to live-course data, and add routing regression evals.

## 1.0.0 - 2026-07-12

- Add a stable Skill version identity.
- Add fail-open update checks backed by the public AI-Shifu website manifest.
