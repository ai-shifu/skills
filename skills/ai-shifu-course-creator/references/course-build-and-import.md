# Course Build and Import

Build a local import payload, create a new platform draft from it, or verify an imported draft. The agent chooses the capabilities needed for the user's request. These operations consume course artifacts; they do not prescribe how to author them.

## Related Guidance

- `../SKILL.md` owns the full-course completion default and completed-content confirmation. Apply that policy to a new-course task without turning these capabilities into mandatory authoring phases.
- `cli/course-directory-spec.md` defines directory layout, build precedence, and synchronized local state; `cli/cli-reference.md#bulk-import` defines build and import commands.
- `language-policy.md#language-audit` defines source and payload language checks.
- Use `authentication.md` when a platform operation needs access. Local builds need no authentication.
- `course-management.md#operations` covers approved attributes and publication; `course-management.md#publication-verification` covers publication proof.

## Build Import Payload

**Input:** a course directory conforming to `cli/course-directory-spec.md`, with the lesson files and course artifacts needed for the requested result. A complete authored course includes a completed `course-prompt.md` and learner-facing description under [author-controls-and-artifact-invariants.md#artifact-invariants](author-controls-and-artifact-invariants.md#artifact-invariants). For a standalone or narrower build/import request, a missing description retains the CLI's empty-description fallback unless the author requested non-empty listing copy.

Run `build --course-dir <dir>` to generate `<dir>/shifu-import.json`. Inspect the effective title, description, Course Prompt, structure, lesson bodies, variables, and interaction syntax in that payload against the source artifacts. Apply `language-policy.md#language-audit` to both the source files and generated payload. A failing payload must be repaired before import.

Keep the inspected payload as the input to import. The completed-content approval in `../SKILL.md` must cover its effective content and selected attributes. If source edits, configuration, build overrides, or another build change that content, inspect the resulting payload and obtain renewed approval under that policy before creating the course.

**Output:** the generated payload path and the checks actually performed. Building or previewing a file does not create a platform course.

## Import a New Course

**Input:** explicit new-course intent, a valid import payload, the completed-content approval required by `../SKILL.md`, and access to the intended platform context. A same-title course does not change new-course intent; do not run duplicate-title lookup merely to import a new course.

- Run `import --new --json-file <dir>/shifu-import.json` on the inspected, approved payload file and capture the returned Shifu BID. Do not rebuild or replace that file between inspection, approval, and import. Run `pull <shifu_bid> --course-dir <dir>` to establish the synchronized revision before a later management write using that directory.
- The CLI also supports `import --new --course-dir <dir>`, which rebuilds the payload and immediately writes it to the platform before seeding synchronization state. It provides no pre-import inspection checkpoint. Use the separate build and `--json-file` form for this new-course capability so the actual imported payload is the one inspected and approved.
- `import --new` creates a draft and does not publish it. If a later operation fails, keep the returned BID and resume the outstanding work instead of creating another course.
- Preserve local artifacts when authentication or import cannot complete, and report the actual partial result.

**Output:** the new Shifu BID, imported lesson count, CLI-returned preview/editor links, and synchronization status. The agent remains responsible for the user-requested endpoint under `../SKILL.md`; import success alone does not establish that endpoint.

## Verify Imported Draft

**Input:** the imported Shifu BID and the source course directory.

- Run `show <shifu_bid>` and compare the platform title, description, chapter structure, lesson count, and lesson titles with the local artifacts.
- Run `export <shifu_bid>` and compare the exported Course Prompt with `course-prompt.md`.
- For each lesson, use its returned `outline_bid` with `show <shifu_bid> <outline_bid>` to compare the deployed Teaching Prompt, variables, and interaction syntax with the local file.

**Output:** verified matches, discrepancies, and any checks that could not run. These checks verify the platform draft; use the publication capability for public learner access.

## Result and Handoff

Report the course directory, exact Shifu BID when created, imported lesson count, operations actually executed, and verification results. Apply `session-controls.md#course-admin-handoff` when the requested task and its verification complete. Internal capability calls do not each trigger a separate browser handoff.
