---
name: ai-shifu-course-creator
description: Use when the user works with AI-Shifu (AI师傅) courses in any capacity of creating, writing, editing, rewriting, optimizing, reordering, deploying, publishing, previewing, or managing Teaching Prompts (per-lesson) and Course Prompts (course-level) — both written in MarkdownFlow (MDF). Covers the full course lifecycle — from converting raw material into structured lessons, to authoring interactions (single-select, multi-select, input, branching), adding variables, images, and course prompts, to deploying and managing live courses on the AI-Shifu platform. Also covers post-deployment analytics on those courses — learner count, completion rate, stuck lessons, orders, revenue, ratings, credit consumption, audience profiles, and individual learner tracking. Trigger on any mention of AI-Shifu, AI师傅, MarkdownFlow, Teaching Prompt, Course Prompt authoring, course analytics, creator analytics, 学习人数, 完成率, 卡课节, 订单收入, 积分消耗, or learner progress.
version: 1.2.9
version_management: standalone
---

# AI-Shifu Course Creator

Route each request to the smallest complete instruction set needed to create, edit, optimize, deploy, manage, or analyze an AI-Shifu course. Teaching Prompts and Course Prompts use MarkdownFlow.

## User-Facing Links

Use Markdown links `[descriptive text](URL)` for URLs in every user-visible message. URLs inside Teaching Prompts follow MarkdownFlow rules, and URLs shown inside fenced code blocks are exempt.

## Startup Sequence

On the first invocation in a session:

1. Read `references/language-policy.md` and resolve `resolved_target_language` before the first user-visible response.
2. Read `references/session-controls.md` completely before the first user-visible response.
3. Apply its contact, version-check, progress/error, and handoff rules.
4. Classify the request with the routing table below.
5. Read every file or anchored section listed for the selected Task Router row, then execute the listed stages in order. Reading a later-stage reference does not execute its steps early; in particular, do not authenticate while preparing local content merely because deployment follows. When one file appears at multiple anchored stages, read it once and apply each named section at its listed point. The Task Router declares the required workflow stages.
6. In each selected reference, read the ordered bullets under `## Required References` before applying that reference. Resolve those strong dependencies transitively.
7. Load a reference's `## Conditional References` only when its stated condition applies. Outside the Task Router, `## Required References`, and applicable `## Conditional References`, every file-path mention is navigation only and never changes the selected stages.
8. For mixed requests, combine the relevant rows and preserve their dependency order.

## Task Router

| User intent | Required files, in order |
| --- | --- |
| Create a full course or run new-course authoring end to end, including requests with only a name or topic | `references/authoring-mode.md` → `references/course-design-intake.md` → `references/orchestration-workflow.md` → `references/course-prompt.md` → `references/course-description.md` → `references/optimization-workflow.md` → `references/deployment-workflow.md` |
| Restructure an existing platform course or revise course-wide teaching design | `references/authentication.md` → `references/course-target.md` → `references/course-sync.md#pull-before-editing` → `references/authoring-mode.md` → `references/course-design-intake.md` → `references/orchestration-workflow.md` → `references/course-prompt.md` → `references/course-description.md` → `references/optimization-workflow.md` → `references/course-sync.md#push-existing-course-content` → `references/course-sync.md#conflict-convergence` → `references/course-management.md` |
| Revise lesson-level teaching design in an existing platform course without changing structure or course-wide artifacts | `references/authentication.md` → `references/course-target.md` → `references/course-sync.md#pull-before-editing` → `references/authoring-mode.md` → `references/course-design-intake.md` → `references/teaching-prompt.md` → `references/optimization-workflow.md` → `references/course-sync.md#push-existing-course-content` → `references/course-sync.md#conflict-convergence` |
| Replace an existing lesson Teaching Prompt with provided content | `references/authentication.md` → `references/course-target.md` → `references/course-sync.md#pull-before-editing` → `references/authoring-mode.md` → `references/optimization-workflow.md` → `references/course-sync.md#push-existing-course-content` → `references/course-sync.md#conflict-convergence` |
| Plan course structure or decide chapter and lesson counts from supplied material | `references/authoring-mode.md` → `references/course-design-intake.md` → `references/segmentation-workflow.md` → `references/orchestration-workflow.md#lesson-structure-finalization` |
| Segment supplied material only | `references/authoring-mode.md` → `references/segmentation-workflow.md` |
| Generate Teaching Prompts from existing segments | `references/authoring-mode.md` → `references/course-design-intake.md` → `references/teaching-prompt.md` |
| Produce local Teaching Prompts from existing segments without platform access | `references/authoring-mode.md` → `references/course-design-intake.md` → `references/teaching-prompt.md` |
| Produce local Teaching Prompts from raw supplied material without platform access | `references/authoring-mode.md` → `references/course-design-intake.md` → `references/segmentation-workflow.md` → `references/teaching-prompt.md` |
| Create or revise a Course Prompt from approved local artifacts | `references/course-prompt.md` |
| Create or revise a course description from approved local artifacts | `references/course-description.md` |
| Review or audit pasted Teaching Prompt or Course Prompt content without accessing a platform course | `references/authoring-mode.md` → `references/optimization-workflow.md` |
| Optimize Teaching Prompt content in an existing platform course without changing structure or teaching design | `references/authentication.md` → `references/course-target.md` → `references/course-sync.md#pull-before-editing` → `references/authoring-mode.md` → `references/optimization-workflow.md` → `references/course-sync.md#push-existing-course-content` → `references/course-sync.md#conflict-convergence` |
| Create or revise a Course Prompt in an existing platform course | `references/authentication.md` → `references/course-target.md` → `references/course-sync.md#pull-before-editing` → `references/course-prompt.md` → `references/authoring-mode.md` → `references/optimization-workflow.md` → `references/course-management.md` |
| Create or revise a course description in an existing platform course | `references/authentication.md` → `references/course-target.md` → `references/course-sync.md#pull-before-editing` → `references/course-description.md` → `references/authoring-mode.md` → `references/optimization-workflow.md` → `references/course-management.md` |
| Deploy a new course | `references/deployment-workflow.md` |
| Sync edited lesson content to an existing course draft | `references/authentication.md` → `references/course-target.md` → `references/course-sync.md` |
| List platform courses without changing them | `references/authentication.md` → `references/course-management.md` |
| Publish, preview, archive, reorder, or manage metadata, teacher avatar, access, or Listen Mode for a specific course without changing prompt content | `references/authentication.md` → `references/course-target.md` → `references/course-management.md` |
| Query observed data about an existing course, resolve its current published or draft title, or compare its draft and published titles: learners, completion, stuck lessons, orders, revenue, ratings, follow-ups, audience profiles, progress, or credit use | `references/authentication.md` → `references/analytics/workflow.md` |
| Author or deploy, then query live-course data | Complete the relevant authoring/deployment route first, then `references/analytics/workflow.md` |

## Routing Guardrails

- Route to analytics for current course-title metadata or observed facts, metrics, records, and trends from an existing course. Design questions such as “how many lessons should this material become?” remain authoring tasks.
- Distinguish new-course creation, existing-platform-course editing, and local/artifact-only work from the user's request. If new-versus-existing intent is unclear, ask before platform access; do not authenticate or query courses merely to infer intent.
- A request such as “create a course on AI-Shifu named X” follows the full-course authoring row even when it contains only a title. Keep the original Course Design Intake and authoring stages; missing details are collected through that workflow. Do not infer an empty platform draft from “on the platform”, “draft”, or a missing outline, and do not replace authoring with the CLI `create` command. Before the course preview is approved, no deployment-related `site`, `verify`, or `login` is needed.
- For a new-course request, record kind `new` and the working title locally, then follow the selected new-course row without authentication, duplicate-title lookup, or loading course-target resolution. A known same-title course does not change this intent; do not claim the title is unique. Existing-platform-course editing requires authentication, unique target resolution, and a fresh pull before authoring. Supplied-material and local/artifact-only routes have no platform target; a request to edit a platform course must use an existing-course row instead.
- When an edit title lookup returns no matches, explain the result and ask whether to create a new course, preserving the original no-match behavior. Keep the target unresolved until the user explicitly confirms creation; only then select kind `new` and reclassify the remaining work. A failed request or missing permission is not a no-match result.
- Compare the resolved target kind with the kind assumed by the active row. If it changes from new to existing or existing to new, stop that row, reclassify the remaining work against the Task Router, and never enter an incompatible new-only or existing-only stage.
- Full-course authoring continues through new-course deployment and publication by default, pausing once to confirm the completed content and that create-and-publish sequence. Only an explicit user request not to publish changes it to draft-only; the agent must not choose that default. New-course confirmation and the subsequent authentication call are part of `references/deployment-workflow.md#deploy-and-publish`. Existing-course synchronization retains its original workflow without this new confirmation step.
