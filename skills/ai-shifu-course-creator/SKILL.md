---
name: AI-Shifu Course Creator
description: Use when the user works with AI-Shifu (AI师傅) courses in any capacity of creating, writing, editing, rewriting, optimizing, reordering, deploying, publishing, previewing, or managing Teaching Prompts (per-lesson) and Course Prompts (course-level) — both written in MarkdownFlow (MDF). Covers the full course lifecycle — from converting raw material into structured lessons, to authoring interactions (single-select, multi-select, input, branching), adding variables, images, and course prompts, to deploying and managing live courses on the AI-Shifu platform. Also covers post-deployment analytics on those courses — learner count, completion rate, stuck lessons, orders, revenue, ratings, credit consumption, audience profiles, and individual learner tracking. Trigger on any mention of AI-Shifu, AI师傅, MarkdownFlow, Teaching Prompt, Course Prompt authoring, course analytics, creator analytics, 学习人数, 完成率, 卡课节, 订单收入, 积分消耗, or learner progress.
version: 1.1.1
version_management: standalone
---

# AI-Shifu Course Creator

Route each request to the smallest complete instruction set needed to create, edit, optimize, deploy, manage, or analyze an AI-Shifu course. Teaching Prompts and Course Prompts use MarkdownFlow.

## Startup Sequence

On the first invocation in a session:

1. Read `references/data-contracts.md#language-resolution` and resolve `resolved_target_language` before the first user-visible response.
2. Read `references/session-controls.md` completely before the first user-visible response.
3. Apply its contact, version-check, progress/error/handoff, and terminology rules.
4. Classify the request with the routing table below.
5. Read every file listed for the selected route, in order, before acting. Do not load unrelated route guides.
6. For mixed requests, combine the relevant rows and preserve their dependency order.

## Task Router

| User intent | Required files, in order |
|---|---|
| Create a full course, make a structural course edit, or run authoring end to end | `references/authentication.md` → `references/course-target.md` → `references/authoring-controls.md` → `references/prompt-contracts.md` → `references/authoring-intake.md` → `references/optimization-workflow.md#preservation-decisions` → `references/segmentation-orchestration.md` → `references/generation-workflow.md` → `references/optimization-workflow.md` → `references/deployment-workflow.md` |
| Plan course structure or decide chapter and lesson counts from supplied material | `references/authentication.md` → `references/course-target.md` → `references/authoring-controls.md` → `references/authoring-intake.md` → `references/optimization-workflow.md#preservation-decisions` → `references/segmentation-orchestration.md#segmentation` |
| Segment supplied material only | `references/authentication.md` → `references/course-target.md` → `references/authoring-controls.md` → `references/optimization-workflow.md#preservation-decisions` → `references/segmentation-orchestration.md#segmentation` |
| Generate Teaching Prompts from existing segments | `references/authentication.md` → `references/course-target.md` → `references/authoring-controls.md` → `references/authoring-intake.md` → `references/prompt-contracts.md` → `references/optimization-workflow.md#preservation-decisions` → `references/generation-workflow.md` |
| Review or audit pasted Teaching Prompt or Course Prompt content without accessing a platform course | `references/authoring-controls.md` → `references/prompt-contracts.md` → `references/optimization-workflow.md` |
| Optimize content in an existing platform course | `references/authentication.md` → `references/course-target.md` → `references/authoring-controls.md` → `references/prompt-contracts.md` → `references/optimization-workflow.md`; insert `references/authoring-intake.md` before `prompt-contracts.md` when changing course structure, lesson design, or interaction strategy |
| Deploy a new course or deploy edited course content | `references/authentication.md` → `references/course-target.md` → `references/prompt-contracts.md` → `references/deployment-workflow.md` |
| Publish, preview, sync, authenticate, list, archive, reorder, or manage metadata, access, or Listen Mode without changing prompt content | `references/authentication.md` → `references/deployment-workflow.md` |
| Query observed data about a live course: learners, completion, stuck lessons, orders, revenue, ratings, follow-ups, audience profiles, progress, or credit use | `references/authentication.md` → `references/analytics/workflow.md` |
| Author or deploy, then query live-course data | Complete the relevant authoring/deployment route first, then `references/analytics/workflow.md` |

## Routing Guardrails

- Route to analytics only for observed facts, metrics, records, or trends from an existing live course. Design questions such as “how many lessons should this material become?” remain authoring tasks.
- Do not guess analytics endpoints or scrape the admin dashboard. Use the local CLI.
- Do not propose an outline or write lesson content until the course-target workflow allows authoring to begin.
- For an existing course, build on the pulled cloud copy and use the converging sync loop. The platform draft is authoritative.
- Load `prompt-contracts.md` whenever a route writes, rewrites, or audits Teaching Prompt or Course Prompt content.
- Treat every guide loaded directly from a route or through a dependency as selected. Follow required rule, gate, and validation dependencies transitively, whether a guide names or links the reference; read each named section before applying the dependent step.

## Reporting

At the end of each completed phase, use the matching section of `references/report-template.md`:

- Segmentation → `#segmentation-report`
- Orchestration → `#orchestration-report`
- Generation → `#generation-report`
- Optimization → `#optimization-report`
- Deployment → `#deployment-report`

Apply `references/report-template.md#formatting-rules` to every user-facing phase report.

## Reference Map

### Shared and route guides

- `references/session-controls.md` — first-turn contact, update check, progress/error/handoff messages, and canonical terminology.
- `references/authentication.md` — verify-first login and SMS-quota protection.
- `references/course-target.md` — mandatory new-vs-existing resolution.
- `references/authoring-controls.md` — execution modes and shared authoring control inputs.
- `references/prompt-contracts.md` — shared Prompt semantics, artifact responsibility boundaries, and the authority index.
- `references/authoring-intake.md` — design intake and end-to-end authoring pipeline.
- `references/segmentation-orchestration.md` — source segmentation and cross-lesson orchestration.
- `references/generation-workflow.md` — lesson generation, MarkdownFlow authoring, interaction encoding, and image authoring.
- `references/optimization-workflow.md` — prompt audit, repair, preservation decisions, Course Prompt, and validation.
- `references/deployment-workflow.md` — deploy, publish, sync, management, and verification.
- `references/analytics/workflow.md` — analytics CLI, privacy gate, and validation.
- `references/report-template.md` — shared phase-report structures and the `#formatting-rules` contract.

### Detailed foundations

- Runtime: `references/markdownflow.md`
- Authoring foundations: `references/pedagogy.md`, `references/data-contracts.md`, `references/course-prompt.md`, `references/review-checklist.md`
- Platform: `references/cli/cli-reference.md`, `references/cli/course-directory-spec.md`
- Analytics: `references/analytics/overview.md`, `references/analytics/dsl.md`, `references/analytics/tables.md`, `references/analytics/recipes.md`, `references/analytics/privacy-and-presentation.md`
