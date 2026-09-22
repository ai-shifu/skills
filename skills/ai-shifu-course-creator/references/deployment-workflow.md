# New Course Deployment

## Required References

- `language-policy.md#language-audit`
- `cli/cli-reference.md#query-commands`
- `cli/cli-reference.md#bulk-import`
- `cli/cli-reference.md#state-management`
- `cli/course-directory-spec.md`

## Conditional References

- After the completed deployment preview is approved, before the first platform operation: `authentication.md`
- When a standalone course directory lacks a Course Prompt: `course-prompt.md`
- When a non-empty course description is required but absent: `course-description.md`
- When an explicitly selected platform attribute must be set before first publication: `course-management.md#operations`
- When `course_author_avatar_source` is non-empty: `course-management.md#operations`

## Boundary

The calling route supplies a **new course** intent and an already-authored course directory. This workflow turns that directory into a new live platform course:

`write directory → build and inspect → preview and confirm → authenticate → import --new → publish → verify`

Creation and publication remain one default deployment sequence. The confirmation step approves that sequence; it does not make publication an optional follow-up. Only an explicit user request to keep the course unpublished changes the result to a draft. Do not propose a draft-only default, ask the user to choose between draft and publication routinely, or infer "do not publish" from an initial request that only says "create a course".

When an explicitly selected attribute must be set on the new course, insert that management operation after import and before the first publish.

Existing-course edits and standalone platform-management operations are outside this workflow.

## Preconditions

- Complete `authentication.md`.
- Browser authorization carries a generated Skill handoff identifier and the
  allowlisted host platform configured by the distribution package. The
  platform records it as registration attribution only when authorization
  results in a newly registered account; signing an existing account into the
  CLI does not change that account's registration source.
- Confirm the resolved target is `new`.
- Provide a course directory that conforms to `cli/course-directory-spec.md`, including lesson files. Require a completed `course-prompt.md` for a content-complete deployment; when it is missing, complete the applicable conditional authoring reference before building. A missing course description keeps the CLI's existing empty-description fallback unless the author requests non-empty listing copy. This workflow consumes final artifacts; it does not define their content.
- Complete the source-file checks in `language-policy.md#language-audit` before the first platform mutation.

## Deploy and Publish

1. Write the final authoring artifacts into the course directory without changing their defined filenames.
2. Run `build --course-dir <dir>` to generate `<dir>/shifu-import.json` locally.
3. Complete the payload checks in `language-policy.md#language-audit` against the generated import file. Stop before import if the payload fails.
4. Show the completed course's title, structure, content preview, and selected platform attributes, and ask for confirmation to **create and publish** this result. For example, in Chinese: “是否按此稿创建并发布课程？” Use draft-only wording only when the user explicitly requested no publication. Obtain this confirmation before authenticating for deployment or creating the course; login authorization is not this confirmation. Reuse approval of the same completed result and scope, and do not ask again before publication. If changes are requested, revise and show the updated result for confirmation; if deferred or unanswered, keep the local artifacts and pause deployment.
5. Complete `authentication.md`, reusing valid access if image upload already required it. If authentication is incomplete, retain the local artifacts and pause platform deployment. Do not check for same-title courses. Authentication does not replace or expand the approved scope.
6. Run `import --new --json-file <dir>/shifu-import.json` and capture the returned Shifu BID, then run `pull <shifu_bid> --course-dir <dir>` to establish the synchronized course revision before any management write. `import --new --course-dir <dir>` remains an equivalent one-step build-and-import form that seeds the same synchronization state automatically, but a separate build is required when the payload must be inspected before mutation. If a later step fails, retain this BID and resume the outstanding steps rather than creating another course.
7. Before first publication, or before completing a draft-only deployment, apply only explicitly selected and approved platform-attribute operations through the conditional management reference, always passing the synchronized `--course-dir <dir>`. This includes enabling Listen Mode by running `set-tts <shifu_bid> --enabled true --course-dir <dir>` when the author explicitly requested it and running `set-avatar <shifu_bid> --file <course_author_avatar_source> --course-dir <dir>` when an avatar source was accepted; leave every unspecified attribute unchanged.
8. Run `publish <shifu_bid>` to make the current draft available at the public learner URL. Skip this step only when the user explicitly requested an unpublished draft; otherwise stopping after import is an incomplete deployment, not a successful handoff.

`import --new` creates the platform course but does not publish it. The CLI also
attaches an immutable, generated handoff identifier and the stable
`ai_assistant` / `lobster` source classification to that new course. This
creation-only attribution is not written into local course content or reused
when an existing course is synchronized. The public URL is expected to work
only after `publish` succeeds.

If a create response is lost, the CLI keeps that handoff bound to the exact
command and payload fingerprint. Repeating the same operation safely asks the
platform for the same idempotent course result; a different course operation
receives a new handoff and cannot accidentally claim the earlier course.

## Verify

1. Run `show <shifu_bid>` and compare the platform title, description, chapter structure, lesson count, and lesson titles with the local course directory. Run `export <shifu_bid>` and compare the exported Course Prompt with `course-prompt.md`.
2. For each lesson, use its returned `outline_bid` with `show <shifu_bid> <outline_bid>` and confirm that the deployed Teaching Prompt, variables, and interaction syntax match the local file.
3. Confirm the public learner URL returned by `publish` is reachable. Only for an explicitly requested draft-only deployment, report draft status without claiming public learner access.
4. Apply the Course Admin Handoff from the startup-loaded `session-controls.md#course-admin-handoff`.

## Completion Criteria

- The completed preview and write scope received explicit user confirmation before course creation.
- `build`, `import --new`, synchronization pull, approved attribute writes, and `publish` complete without errors. Publication is omitted only for an explicitly requested unpublished draft.
- The platform structure and content match the source directory.
- Every approved teacher avatar is bound and verified before any publication; a skipped avatar leaves the platform default unchanged.
- Public learner URL verification succeeds unless the user explicitly requested an unpublished draft.
- The final report names the course directory and exact Shifu BID, summarizes results for the build, import, and publication steps actually executed, gives the imported lesson count, and reports the results of [Verify](#verify), including the browser handoff status and the three course links required by `session-controls.md#course-admin-handoff`.
