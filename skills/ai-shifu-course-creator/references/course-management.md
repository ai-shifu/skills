# Course Management

## Related Guidance

- `authentication.md`
- `language-policy.md#language-audit`
- `cli/cli-reference.md#query-commands`
- `cli/cli-reference.md#update-commands`
- `cli/cli-reference.md#state-management`

- When a version-aware management write exits `2`: `course-sync.md#conflict-convergence`
- When a command reads or refreshes a local course directory: `cli/course-directory-spec.md`

## Boundary

Use these capabilities for platform operations that do not author lesson content: publish, preview, list, archive or restore, reorder, course metadata, teacher avatar, lesson access and visibility, and course Listen Mode. The agent selects the requested operations. This reference does not resolve the course target, synchronize lesson content, or decide what authoring text should say.

Platform operations need access to the intended context under `authentication.md`; reuse already verified access. Before mutating learner-facing metadata, apply `language-policy.md#language-audit`.

## Operations

| Intent | Command | Required result check |
| --- | --- | --- |
| List courses | `list` | Confirm the intended title and Shifu BID from current results. |
| Preview course | Reuse the resolved course BID | Apply the Course Admin Handoff below. |
| Preview one lesson | Reuse the known lesson BID; use `show <shifu_bid>` only if it still needs to be identified | Apply the Course Admin Handoff below for that lesson. |
| Publish current draft | `publish <shifu_bid>` | Apply [Publication Verification](#publication-verification). |
| Archive or restore | `archive <shifu_bid>` / `unarchive <shifu_bid>` | Re-run `list` or `show` as appropriate to confirm state. |
| Reorder sibling chapters or lessons | First run `show <shifu_bid>` to inspect sibling groups, then select the group as specified in [the reorder command](cli/cli-reference.md#reorder) and run `reorder <shifu_bid> --order bid1,bid2,...`. | Run `show <shifu_bid>` again and confirm the requested sibling group's order. |
| Update name, description, or Course Prompt | `update-meta <shifu_bid> ... [--course-dir <dir>]` | Use `show` for name/description and `export` for the Course Prompt; confirm only requested fields changed. |
| Set lesson access or visibility | `set-access <shifu_bid> <outline_bid> ...` | Confirm success output; with `--course-dir`, also inspect the updated `structure.json`. |
| Configure Listen Mode | `set-tts <shifu_bid> ...` | Confirm success output; with `--course-dir`, also inspect the refreshed `course-config.json`. |
| Set teacher avatar | `set-avatar <shifu_bid> --file <image> [--course-dir <dir>]` | Confirm the command's readback succeeds and reports the resource URL; with `--course-dir`, inspect the refreshed `course-config.json`. |

When the task has established a local sync baseline through a pull or new import, pass that same directory through `--course-dir` on every version-aware course-level management write, including `update-meta`, `set-tts`, and `set-avatar`, so the recorded revision protects the write and local state is refreshed after success. Existing-platform Course Prompt and description edits require the baseline under [pull-before-editing](course-sync.md#pull-before-editing); send those artifact changes with `update-meta --course-dir <the-pulled-dir>`. Omit `--course-dir` only for a standalone management request that does not author or revise course content, such as an explicit rename, and did not establish a local sync baseline.

For a newly imported course, apply only explicitly selected and approved platform attributes before first publication, or before completing a requested draft-only result. This includes `set-tts <shifu_bid> --enabled true --course-dir <dir>` when Listen Mode was requested and `set-avatar <shifu_bid> --file <image> --course-dir <dir>` when an avatar source was accepted. Leave unspecified attributes unchanged. An approved avatar must be bound and verified before first publication. New-course content approval and the full-course completion default are owned by `../SKILL.md`; do not add that confirmation requirement to existing-course synchronization or standalone management requests.

For a teacher avatar, accept JPG or PNG. Recommend 1:1 because the avatar is shown in square frames on course cards and learning pages, but do not reject other aspect ratios; warn that they may be cropped. Let `set-avatar` compress files over 2 MB automatically and request a replacement only when preprocessing cannot reach the limit. Use this command directly; browser or Chrome control is not required.

When `update-meta --course-dir`, `set-tts --course-dir`, or `set-avatar --course-dir` exits `2`, apply `course-sync.md#conflict-convergence` to the intended management change and retry on the freshly pulled baseline.

## Course Admin Handoff

Apply `session-controls.md#course-admin-handoff` after the requested task and its verification complete, or for a direct preview/debug request. Internal operation calls do not each trigger a handoff.

## Publication Verification

Run `publish <shifu_bid>` for the selected publication operation and require success before describing the course as published. Confirm that the public learner URL returned by `publish` is reachable. A public URL printed by `show` alone is not evidence of publication, and opening the editor is not proof of learner access.

Report publication and public-access verification separately. If publication succeeds but the learner page cannot be verified, retain the Shifu BID and report that specific incomplete check instead of recreating the course. Apply the Course Admin Handoff when the requested work is complete; published tasks include the CLI-returned public learner link.
