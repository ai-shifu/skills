# Course Management

## Required References

- `authentication.md`
- `language-policy.md#language-audit`
- `cli/cli-reference.md#query-commands`
- `cli/cli-reference.md#update-commands`
- `cli/cli-reference.md#state-management`

## Conditional References

- When a version-aware management write exits `2`: `course-sync.md#conflict-convergence`
- When a command reads or refreshes a local course directory: `cli/course-directory-spec.md`

## Boundary

Use this workflow for platform operations that do not author lesson content: publish, preview, list, archive or restore, reorder, course metadata, teacher avatar, lesson access and visibility, and course Listen Mode. It does not resolve the course target, synchronize lesson content, or decide what authoring text should say.

Complete `authentication.md` first. Before mutating learner-facing metadata, complete `language-policy.md#language-audit`.

## Operations

| Intent | Command | Required result check |
| --- | --- | --- |
| List courses | `list` | Confirm the intended title and Shifu BID from current results. |
| Preview course | Reuse the resolved course BID | Apply the Course Admin Handoff below. |
| Preview one lesson | Reuse the known lesson BID; use `show <shifu_bid>` only if it still needs to be identified | Apply the Course Admin Handoff below for that lesson. |
| Publish current draft | `publish <shifu_bid>` | Confirm the CLI-produced public learner URL works. |
| Archive or restore | `archive <shifu_bid>` / `unarchive <shifu_bid>` | Re-run `list` or `show` as appropriate to confirm state. |
| Reorder lessons | `reorder <shifu_bid> --order bid1,bid2,...` | Run `show <shifu_bid>` and confirm the returned order. |
| Update name, description, or Course Prompt | `update-meta <shifu_bid> ... [--course-dir <dir>]` | Use `show` for name/description and `export` for the Course Prompt; confirm only requested fields changed. |
| Set lesson access or visibility | `set-access <shifu_bid> <outline_bid> ...` | Confirm success output; with `--course-dir`, also inspect the updated `structure.json`. |
| Configure Listen Mode | `set-tts <shifu_bid> ...` | Confirm success output; with `--course-dir`, also inspect the refreshed `course-config.json`. |
| Set teacher avatar | `set-avatar <shifu_bid> --file <image> [--course-dir <dir>]` | Confirm the command's readback succeeds and reports the resource URL; with `--course-dir`, inspect the refreshed `course-config.json`. |

When this workflow follows `course-sync.md#pull-before-editing`, pass that same directory through `--course-dir` on every version-aware course-level management write, including `update-meta`, `set-tts`, and `set-avatar`, so the recorded course revision protects the write and the local course state is refreshed after success. This must be the pulled directory that established the sync baseline. Omit `--course-dir` only for a standalone management request that did not pull or otherwise establish a local sync baseline.

For a teacher avatar, accept JPG or PNG. Recommend 1:1 because the avatar is shown in square frames on course cards and learning pages, but do not reject other aspect ratios; warn that they may be cropped. Let `set-avatar` compress files over 2 MB automatically and request a replacement only when preprocessing cannot reach the limit. Use this command directly; browser or Chrome control is not required.

When `update-meta --course-dir`, `set-tts --course-dir`, or `set-avatar --course-dir` exits `2`, apply `course-sync.md#conflict-convergence` to the intended management change and retry on the freshly pulled baseline.

## Course Admin Handoff

Apply the startup-loaded `session-controls.md#course-admin-handoff`.
