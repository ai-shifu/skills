# Existing Course Sync

## Related Guidance

- `authentication.md`
- `course-lookup.md`
- `language-policy.md#language-audit`
- `cli/cli-reference.md#version-sync-pull--status`
- `cli/cli-reference.md#create-commands`
- `cli/cli-reference.md#update-commands`
- `cli/cli-reference.md#delete-commands`
- `cli/cli-reference.md#bulk-import`
- `cli/course-directory-spec.md#shifu-syncjson`

## Boundary

Use these capabilities for a uniquely identified **existing course** in the intended authenticated context. They provide cloud-to-local pull, divergence status, lesson-content pushes, and conflict recovery. The platform draft is the source of truth.

These capabilities do not resolve the target, author content, publish the course, or manage metadata and attributes. The agent chooses the required operations.

## Pull Before Editing

Run `pull <shifu_bid> --course-dir <dir>` to obtain the current cloud draft and `.shifu-sync.json` baseline before preparing lesson, Course Prompt, or description edits that will be synchronized back to this existing platform course. This baseline is required even when the eventual write is a course-wide `update-meta` operation under [course management](course-management.md#operations). Preserve any already unpushed work before a pull overwrites the directory, then reapply it to the pulled baseline. Inspecting a local artifact alone does not require a pull.

Run `status --course-dir <dir>` when cloud/local divergence needs inspection. Before pushing changed content, apply `language-policy.md#language-audit` to the actual changed artifacts.

Never hand-edit `.shifu-sync.json`. Always pass `--course-dir` to a version-aware push so the CLI can compare the recorded revision. Without the manifest baseline, concurrent-edit protection is degraded. Use the task context established by `authentication.md` for every command. The directory source checks in `cli/course-directory-spec.md#shifu-syncjson` run before network access; a mismatch is a configuration error and does not enter the conflict-convergence loop.

## Push Existing Course Content

Choose the narrowest command that represents the content change:

- `update-lesson <bid> <outline_bid> --teaching-prompt-file <file> --course-dir <dir>` updates one lesson and preserves its BID.
- `add-chapter`, `add-lesson`, `rename-lesson`, and `delete-lesson` apply the corresponding structural content change.
- `import <bid> --course-dir <dir>` pushes the whole directory. This operation deletes and recreates every outline, regenerates lesson BIDs, and gives recreated lessons the platform-default permission. Use it only when that destructive whole-course effect is intended.

The four structural commands do not accept `--course-dir` and do not refresh `.shifu-sync.json`. Immediately after each successful `add-chapter`, `add-lesson`, `rename-lesson`, or `delete-lesson`, run `pull <shifu_bid> --course-dir <dir>` before another local, status, or version-aware operation. Use the fresh pull to capture platform-assigned BIDs, outline mappings, and revisions; never continue from the pre-mutation sync baseline.

Course name, description, Course Prompt, publication, and other platform attribute writes are outside these capabilities.

## Verify Updated Draft

Keep the intended edits available for comparison. After a successful lesson-content write, run `show <shifu_bid> <outline_bid>` and compare the returned Teaching Prompt with the intended content. For structural changes, compare `show <shifu_bid>` with the requested outline changes, using the BIDs from the fresh pull. After a whole-course import, apply [imported-draft verification](build-and-import.md#verify-imported-draft).

Report matches, discrepancies, and checks that could not run. A successful write or refreshed local baseline alone does not establish that the requested content matches the platform draft.

## Conflict Convergence

All version-aware content and management writes use this exit-code loop:

- Exit `0`: the push succeeded; the local sync baseline is refreshed.
- Exit `1`: a hard error occurred; stop and report it.
- Exit `2`: the cloud advanced since the recorded baseline. Treat this as a retry signal, not a terminal failure.

On exit `2`, the CLI backs up the unpushed work, pulls the latest cloud course over the local directory, and prints who changed it and when. Then repeat:

1. Read the freshly pulled files as the new baseline.
2. Reapply the intended change on top of that baseline. The agent performs this merge; the CLI never merges content automatically.
3. Run the same version-aware command again with `--course-dir`.
4. Repeat until exit `0`, stop on exit `1`, or stop after three consecutive exit-`2` responses for the same intended change.

After the third consecutive conflict, stop automatic retries, report the repeated convergence failure and current conflict details, and require explicit user confirmation before attempting the write again.

Do not force the stale local copy over the cloud. Backup locations and exact command side effects are defined in `cli/cli-reference.md`.
