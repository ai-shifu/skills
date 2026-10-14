---
name: ai-shifu-course-creator
description: Create, edit, review, publish, manage, or analyze AI-Shifu (AI师傅) courses and their Teaching Prompts and Course Prompts in MarkdownFlow (MDF). Use for course materials, lesson design, interactions, variables, images, deployment, platform administration, learner progress, orders, revenue, and credit-consumption questions.
metadata:
  version: 2.0.0
  version_management: standalone
---

# AI-Shifu Course Creator

Use these capabilities to complete the user's course goal. The using agent owns task decomposition, capability selection, execution order, and teaching design. Start from the available topic, brief, source material, outline, Prompt, or course directory; no questionnaire, segmentation run, intermediate JSON, or separate execution plan is a universal prerequisite.

Reuse existing answers and artifacts. Ask when missing information materially affects the result; otherwise make reasonable design choices within the user's constraints. Capabilities can be combined, revisited, or used alone. A reference explains how to perform its capability, not what the agent must do next. Read the relevant guidance as needed rather than loading a transitive reference graph.

## Shared Conventions

- Apply [language-policy.md](references/language-policy.md) to conversation and authored content, including target-language resolution and terminology.
- Apply [session-controls.md](references/session-controls.md) to contact eligibility, explicit-request-only version checks, progress, errors, and completion handoffs. First-response contact conditions remain applicable. The completion handoff applies to the user's completed request, not each internal capability call.
- Use Markdown links `[descriptive text](URL)` for URLs in user-visible messages. URLs inside Teaching Prompts follow MarkdownFlow rules; URLs inside fenced code blocks are exempt.
- Honor explicit author choices, source facts, selected exact material, and the distinction between a per-lesson Teaching Prompt and a course-wide Course Prompt. Runtime semantics are defined in [prompt-semantics.md](references/prompt-semantics.md) and [markdownflow-syntax.md](references/markdownflow-syntax.md).
- For an existing platform course's lesson, Course Prompt, or description edit, apply the [versioned editing baseline](references/course-sync.md#pull-before-editing) before preparing revised content. Course-wide artifact writes use [course management](references/course-management.md#operations) with that baseline. Local-only authoring and read-only review remain independent of platform access.

## Capabilities

Capabilities fall into three categories: **teaching design**, **expressing that design in MarkdownFlow**, and **operating the CLI**. These categories describe responsibilities, not execution phases. Use one alone, combine them, or revisit them in any useful order. Inputs describe useful starting points, not mandatory upstream outputs.

### Teaching Design

Decide what learners should understand or do and how teaching can help them get there. Use existing choices directly; resolve missing choices within the task without requiring a separate design artifact.

| Capability | Useful inputs | Result and guidance |
| --- | --- | --- |
| Resolve course design | Topic, learner needs, source material, existing choices | Design choices and their effects; ask only material unresolved questions. [Course design](references/course-design-choices.md) |
| Analyze material and plan structure | Source material, topic, outline, existing lessons | Relevant source analysis, chapter and lesson structure, or optional traceable segments. [Structure and segmentation](references/course-structure.md) |
| Design lesson teaching | Goals, audience, source, existing teaching choices | Suitable explanations, examples, practice, interactions, visual purposes, and feedback. [Teaching options](references/teaching-design.md) |
| Write listing copy | Course topic, audience, goals, and supported outcomes | Learner-facing course description; this prose does not require MarkdownFlow. [Course description](references/course-description.md) |
| Review teaching quality | Available material, design, or course content | Scoped findings and requested repairs for factual support, source coverage, and learning effectiveness. [Review](references/course-review.md), [checks](references/review-checklist.md) |

Teaching patterns, interaction counts, and visual rhythms in [teaching-design.md](references/teaching-design.md) are recommendations. The agent chooses teaching strategy within the user's explicit constraints.

### Express in MarkdownFlow

Make the intended teaching behavior executable in Teaching Prompts and Course Prompts. Preserve supplied design choices; use the teaching-design capabilities for choices that remain open rather than letting syntax or a layout template determine pedagogy.

| Capability | Useful inputs | Result and guidance |
| --- | --- | --- |
| Write or revise a lesson | Topic, source, existing Prompt, or supplied design | Runnable Teaching Prompt with required source-only explanatory comments and a suitable layout. A separate design run is not required. [Teaching Prompt](references/teaching-prompt.md) |
| Write or revise a Course Prompt | Course title, topic, goals, audience, and design context | Course-wide Prompt using the existing six-section template. [Course Prompt](references/course-prompt.md) |
| Encode interactions, variables, and exact content | Intended response behavior, variable uses, selected exact material | Explicit controls or natural-language interactions with context-generated options, valid references, branches, and deterministic output. [MarkdownFlow](references/markdownflow-syntax.md), [Prompt semantics](references/prompt-semantics.md) |
| Express lesson images | Teaching intent, authoritative asset URLs and metadata | Correct image embedding or HTML-view instructions. [Image authoring](references/image-authoring.md) |
| Review Prompt expression | One Prompt or selected artifacts | Scoped findings and repairs for runtime syntax, variables, comments, layout, and artifact contracts. [Review](references/course-review.md), [checks](references/review-checklist.md) |

### Operate the CLI

Use deterministic commands for local course files, platform access and changes, and observed course data. Existing Prompts and directories can be used directly without redoing teaching design or Prompt authoring. The [CLI reference](references/cli/cli-reference.md) owns command mechanics; the [course-directory specification](references/cli/course-directory-spec.md) owns recognized files, build precedence, and import format.

| Capability | Useful inputs | Result and guidance |
| --- | --- | --- |
| Establish platform access | Selected service/profile and existing authorization | Verified access and recoverable browser authorization when needed. [Authentication](references/authentication.md) |
| Identify an existing course | BID or title and selected platform context | Unique target or an explicit unresolved result. [Course target](references/course-lookup.md) |
| Upload lesson images | Image assets, informative alt text, and selected platform context | Real resource URLs and provenance records for later embedding. [Image upload](references/cli/cli-reference.md#image-upload), [asset handling](references/image-authoring.md) |
| Synchronize existing content | Existing course and local edits/directory | Pull, divergence inspection, version-protected writes, and conflict convergence. [Course sync](references/course-sync.md) |
| Build or import a new course | Authored course directory or import payload | Built payload, new draft, and verified imported content. [Build and import](references/build-and-import.md) |
| Manage and publish a course | Resolved course and requested operation | Metadata, structure, access, avatar, Listen Mode, publication, preview, or archive changes. [Course management](references/course-management.md) |
| Analyze course data | Course/question, dimensions, and time range | Queries and readable, privacy-respecting findings. [Analytics](references/analytics/guide.md) |

Shared references support the relevant category: [authoring-contracts.md](references/authoring-contracts.md) defines optional author controls and artifact consistency; [source-preservation.md](references/source-preservation.md) defines exact-source decisions. An image's teaching purpose, MarkdownFlow representation, and CLI upload are separate actions even when they share a reference. Review likewise applies the criteria for the requested design, expression, or platform result.

Local teaching design, Prompt expression, content-only review, and builds do not require platform access; invoke authentication when a selected platform operation needs it. Analytics may inform a later teaching decision when relevant, but querying data does not itself request a course rewrite.

## Full-Course Creation Outcome

A request to create a complete AI-Shifu course includes deployment and publication by default. An explicit local-only, unpublished-draft, or narrower deliverable request determines that narrower outcome. A title-only creation request is still course authoring; it does not mean creating an empty platform draft. This outcome does not prescribe the order of authoring capabilities.

Before creating a new platform course, show the completed title, structure, content preview, and selected platform attributes, and obtain confirmation to create and publish that concrete result. Use draft-only wording when the user requested an unpublished draft. Reuse approval of the same completed result and scope; revise and obtain approval again if the approved result changes. Keep local work when confirmation is deferred. Browser login approval is separate from this content confirmation. This checkpoint applies to new-course creation and does not add a confirmation step to existing-course synchronization or independent management requests.

Keep new-course intent distinct from an existing-course edit. A no-match lookup does not authorize creating a replacement course. Reuse the BID of an already-created course when resuming incomplete work. Report the operations and verification that actually completed; an imported draft or a printed public URL alone does not establish successful publication.
