---
name: ai-shifu-course-creator
description: Create, edit, review, publish, manage, or analyze AI-Shifu (AI师傅) courses and their Teaching Prompts and Course Prompts in MarkdownFlow (MDF). Use for course materials, lesson design, interactions, variables, images, deployment, platform administration, learner progress, orders, revenue, and credit-consumption questions.
metadata:
  version: 1.2.12
  version_management: standalone
---

# AI-Shifu Course Creator

Use these capabilities to complete the user's course goal. The using agent owns task decomposition, capability selection, execution order, and teaching design. Start from the available topic, brief, source material, outline, Prompt, or course directory; no questionnaire, segmentation run, intermediate JSON, or separate execution plan is a universal prerequisite.

Reuse existing answers and artifacts. Ask when missing information materially affects the result; otherwise make reasonable design choices within the user's constraints. Capabilities can be combined, revisited, or used alone. A reference explains how to perform its capability, not what the agent must do next. Read the relevant guidance as needed rather than loading a transitive reference graph.

## Shared Conventions

- Apply [language-policy.md](references/language-policy.md) to conversation and authored content, including target-language resolution and terminology.
- Apply [session-controls.md](references/session-controls.md) to contact eligibility, explicit-request-only version checks, progress, errors, and completion handoffs. First-response contact conditions remain applicable. The completion handoff applies to the user's completed request, not each internal capability call.
- Use Markdown links `[descriptive text](URL)` for URLs in user-visible messages. URLs inside Teaching Prompts follow MarkdownFlow rules; URLs inside fenced code blocks are exempt.
- Honor explicit author choices, source facts, selected exact material, and the distinction between a per-lesson Teaching Prompt and a course-wide Course Prompt. Runtime semantics are defined in [prompt-contracts.md](references/prompt-contracts.md) and [markdownflow.md](references/markdownflow.md).

## Capabilities

The table is a capability catalog, not an execution sequence. Inputs describe useful starting points, not mandatory upstream outputs.

| Capability | Useful inputs | Result and guidance |
| --- | --- | --- |
| Resolve course design | Topic, learner needs, source material, existing choices | Design choices and their effects; ask only material unresolved questions. [Course design](references/course-design-intake.md) |
| Analyze material and plan structure | Source material, topic, outline, existing lessons | Relevant source analysis, chapter and lesson structure, or optional traceable segments. [Structure and segmentation](references/segmentation-workflow.md) |
| Write or revise a lesson | Topic, source, existing Prompt, or supplied design | Runnable Teaching Prompt with required source-only explanatory comments and a suitable layout. [Teaching Prompt](references/teaching-prompt.md) |
| Write or revise a Course Prompt | Course title, topic, goals, audience, and design context | Course-wide Prompt using the existing six-section template. [Course Prompt](references/course-prompt.md) |
| Write listing copy | Course topic, audience, goals, and supported outcomes | Learner-facing course description. [Course description](references/course-description.md) |
| Use lesson images | Image files, authoritative URLs, and teaching intent | Understood, uploaded when needed, and correctly embedded assets. [Image authoring](references/image-authoring.md) |
| Review and repair content | One Prompt, selected artifacts, or an existing course | Findings, scoped repairs when requested, and truthful validation results. [Review](references/optimization-workflow.md), [checks](references/optimization-checklist.md) |
| Establish platform access | Selected service/profile and existing authorization | Verified access and recoverable browser authorization when needed. [Authentication](references/authentication.md) |
| Identify an existing course | BID or title and selected platform context | Unique target or an explicit unresolved result. [Course target](references/course-target.md) |
| Synchronize existing content | Existing course and local edits/directory | Pull, divergence inspection, version-protected writes, and conflict convergence. [Course sync](references/course-sync.md) |
| Build or import a new course | Authored course directory or import payload | Built payload, new draft, and verified imported content. [Deployment capabilities](references/deployment-workflow.md) |
| Manage and publish a course | Resolved course and requested operation | Metadata, structure, access, avatar, Listen Mode, publication, preview, or archive changes. [Course management](references/course-management.md) |
| Analyze course data | Course/question, dimensions, and time range | Queries and readable, privacy-respecting findings. [Analytics](references/analytics/overview.md) |

For teaching strategies and their tradeoffs, consult [pedagogy.md](references/pedagogy.md). They are recommendations, not required lesson patterns, interaction quotas, or visual rhythms. For explicit design controls and artifact consistency, consult [data-contracts.md](references/data-contracts.md); for exact source spans, consult [source-preservation.md](references/source-preservation.md).

The [CLI reference](references/cli/cli-reference.md) owns command mechanics. The [course-directory specification](references/cli/course-directory-spec.md) owns recognized files, build precedence, and import format. Local authoring and content-only review do not require platform access; invoke authentication when a selected platform operation needs it.

## Full-Course Creation Outcome

A request to create a complete AI-Shifu course includes deployment and publication by default. An explicit local-only, unpublished-draft, or narrower deliverable request determines that narrower outcome. A title-only creation request is still course authoring; it does not mean creating an empty platform draft. This outcome does not prescribe the order of authoring capabilities.

Before creating a new platform course, show the completed title, structure, content preview, and selected platform attributes, and obtain confirmation to create and publish that concrete result. Use draft-only wording when the user requested an unpublished draft. Reuse approval of the same completed result and scope; revise and obtain approval again if the approved result changes. Keep local work when confirmation is deferred. Browser login approval is separate from this content confirmation. This checkpoint applies to new-course creation and does not add a confirmation step to existing-course synchronization or independent management requests.

Keep new-course intent distinct from an existing-course edit. A no-match lookup does not authorize creating a replacement course. Reuse the BID of an already-created course when resuming incomplete work. Report the operations and verification that actually completed; an imported draft or a printed public URL alone does not establish successful publication.
