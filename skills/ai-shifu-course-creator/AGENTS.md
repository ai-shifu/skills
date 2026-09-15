# AI-Shifu Course Creator Maintenance Guide

## Ownership Rules

- Give each behavior, schema, workflow step, and validation criterion one canonical owner in the map below. Other files route to or cite that owner and add only their own local application.
- Keep `SKILL.md` focused on discovery, startup, and task routing. Put conditional detail in the routed reference that owns the topic.
- Separate decisions from representations: `pedagogy.md` owns teaching decisions, `markdownflow.md` owns runtime syntax and effects, `markdownflow-authoring.md` owns encoding decisions into that syntax, and artifact references own final materialization.
- Separate contracts from execution: `data-contracts.md` owns data shapes, workflow files own phase execution, checklists and evals verify the owned behavior, and scripts implement deterministic operations.
- When a change crosses an ownership boundary, update the canonical owner first. Update consumers only for routing, integration, or validation consequences, and link back to the owner instead of restating its rules.
- When adding, removing, renaming, or materially changing a file's responsibility, update this map in the same change. Give every new file one primary responsibility that is not already owned elsewhere.

## Entrypoint and Package Files

| File | Canonical responsibility |
| --- | --- |
| `AGENTS.md` | Define this skill's maintenance-time ownership map and cross-file editing rules. It guides contributors and does not define learner-time or authoring behavior. |
| `SKILL.md` | Define skill discovery metadata, the package-wide user-facing Markdown link contract, startup requirements, the task router, and routing guardrails. It selects the smallest complete reference set and leaves domain behavior to those references. |
| `.env.example` | Document supported service-selection and token environment variables with safe empty defaults and credential-storage guidance. |
| `CHANGELOG.md` | Record user-visible and maintainer-relevant changes in chronological release history. Current behavior remains defined by `SKILL.md`, references, and scripts. |
| `evals/evals.json` | Hold end-to-end behavioral scenarios, optional input fixtures, and expected outcomes for routing, authoring, platform, analytics, and boundary regressions. Canonical guidance remains the source of behavior. |
| `evals/trigger_eval.json` | Test whether representative requests should or should not discover this skill. Keep capability and trigger wording canonical in `SKILL.md` frontmatter. |

## Core Reference Responsibilities

| File | Canonical responsibility |
| --- | --- |
| `references/language-policy.md` | Own target-language resolution, canonical human-facing terminology, localization boundaries, first-mention wording, and the final language audit across artifacts and messages. |
| `references/session-controls.md` | Own session lifecycle behavior: official contact timing, skill-version update checks, usage reporting, progress and error communication, handoffs, and first-session operational controls. |
| `references/authentication.md` | Own platform site selection, credential verification, browser authorization, login continuation, and authentication failure handling. It establishes access and does not select a course. |
| `references/open-in-app-browser.md` | Own the host-application mechanics for opening a supplied URL in a visible built-in browser and reporting the opening result. The calling workflow owns URL selection and next steps. |
| `references/course-target.md` | Own new-versus-existing resolution, title and BID matching, ambiguity handling, and the resolved target record for authoring and platform-management routes. For analytics, `analytics/tables.md` owns current-title semantics and `analytics/recipes.md` applies them through lookup templates. |
| `references/authoring-mode.md` | Own selection between standard and fallback execution modes for authoring phases. Phase-specific fallback fields remain in `data-contracts.md`. |
| `references/course-design-intake.md` | Own collection and normalization of unresolved author choices, the effect preview shown before each question, and the resulting design-control handoff. Downstream owners define the controls' actual teaching and artifact effects. |
| `references/data-contracts.md` | Own schemas, required and optional fields, enum values, output envelopes, variable-table structure, and cross-field invariants exchanged between authoring phases. |
| `references/source-preservation.md` | Own selection of immutable source spans and exactness verification after transformations. Encoding those decisions belongs to `markdownflow-authoring.md`. |
| `references/prompt-contracts.md` | Own semantics shared by Course Prompts and Teaching Prompts and the responsibility boundary between the two artifact types. It is the integration owner, not the owner of syntax, pedagogy, schemas, or materialization. |
| `references/pedagogy.md` | Own teaching-effect decisions: lesson loops and patterns, interaction purposes and effects, variable-persistence strategy, cognitive techniques, and visual-text coordination by delivery mode. |
| `references/markdownflow.md` | Own the runtime-recognized MarkdownFlow syntax and its observable preprocessing, variable, interaction, branching, deterministic-block, image, and preservation behavior. |
| `references/markdownflow-authoring.md` | Own how already-resolved teaching, interaction, variable, and preservation decisions are encoded and validated in MarkdownFlow. Runtime semantics remain in `markdownflow.md`. |
| `references/image-authoring.md` | Own intake, understanding, upload, composition, embedding, and output validation for lesson image assets. Teacher avatars remain platform metadata under `course-management.md`. |

## Authoring and Artifact Reference Responsibilities

| File | Canonical responsibility |
| --- | --- |
| `references/segmentation-workflow.md` | Own transformation of source material into traceable semantic segments and lesson-boundary candidates, including segmentation validation and fallback output. |
| `references/orchestration-workflow.md` | Own phase coordination from segmentation through lesson-structure finalization and Teaching Prompt generation, then build the course index and global variable table and enforce cross-phase gates. It calls phase owners without redefining their rules. |
| `references/teaching-prompt.md` | Own materialization of one runnable per-lesson Teaching Prompt from approved segments and controls, including personalization levels, output shape, and artifact-specific validation. It routes interaction, variable, branch, and preservation encoding to `markdownflow-authoring.md`. |
| `references/course-prompt.md` | Own materialization of the six-section course-wide Course Prompt, including fill sources and uniform presentation requirements. Lesson pedagogy, sequence, interactions, and position-specific slide decisions remain Teaching Prompt concerns. |
| `references/course-description.md` | Own the learner-facing course listing and SEO description artifact, its supported source claims, output form, and validation. |
| `references/optimization-workflow.md` | Own entry conditions and execution for auditing substantially complete artifacts, applying minimal repairs, classifying findings, and producing the Optimization report. It consumes acceptance criteria from the checklist. |
| `references/optimization-checklist.md` | Own observable pass, fail, and not-assessed acceptance criteria for existing Teaching Prompts, Course Prompts, descriptions, language, fidelity, runtime safety, and repair scope. Linked owners define the underlying behavior. |

## Platform Workflow Reference Responsibilities

| File | Canonical responsibility |
| --- | --- |
| `references/course-sync.md` | Own existing-course cloud-to-local pulls, divergence status, content pushes, version checks, and conflict convergence. It does not author content or manage publication metadata. |
| `references/deployment-workflow.md` | Own new-course deployment from an already-authored course directory through import, publication, readback verification, and completion reporting. |
| `references/course-management.md` | Own non-authoring platform operations: list, preview, publish, archive or restore, reorder, course metadata, teacher avatar, access, visibility, and Listen Mode. It invokes the Course Admin Handoff owned by `session-controls.md`. |
| `references/cli/cli-reference.md` | Own the public `shifu-cli.py` command surface: invocation, flags, command groups, authentication inputs, output conventions, state behavior, and exit codes. Workflow references decide when commands run. |
| `references/cli/course-directory-spec.md` | Own the local course-directory layout, artifact meanings, build precedence, sync and image manifests, generated import shape, and which files each CLI operation reads or writes. |

## Analytics Reference Responsibilities

| File | Canonical responsibility |
| --- | --- |
| `references/analytics/workflow.md` | Own the router-facing end-to-end analytics execution path: required authentication and references, CLI-only execution, query handoff, and completion behavior. |
| `references/analytics/overview.md` | Own analytics intent orientation: supported question families, question-to-query planning, choosing the correct table or recipe, common query-selection pitfalls, and navigation to deeper references. |
| `references/analytics/dsl.md` | Own the analytics query language: JSON body shape, operators, aggregates, limits, auto-filters, and server-enforced query-shape constraints. Field-access policy, refusals, masking, and user-facing handling remain with `privacy-and-presentation.md`. |
| `references/analytics/tables.md` | Own queryable table and field semantics, enum and code translations, identifier relationships, known data traps, and distinctions among independently measured amounts. |
| `references/analytics/recipes.md` | Own ready-to-run query and `credit-detail` templates for supported analytics scenarios. Grammar and field meaning remain in `dsl.md` and `tables.md`. |
| `references/analytics/privacy-and-presentation.md` | Own analytics access restrictions, refusal boundaries, masking and aggregation requirements, UTC-to-local presentation, the translation gate, and user-facing answer structure. |

## Script Responsibilities

| File | Canonical responsibility |
| --- | --- |
| `scripts/shifu-cli.py` | Implement the unified deterministic interface for site configuration, authentication, course queries and writes, sync, import and build, image upload, analytics, state, and structured command results. Reference files own workflow policy. |
| `scripts/image_utils.py` | Implement local image decoding, orientation correction, resizing, recompression, output-format selection, and content-hash naming for upload preparation. |
| `scripts/skill_update.py` | Implement fail-open version discovery, update availability checks, manifest validation, and local update state used by session controls and the CLI. |
| `scripts/usage_tracker.py` | Implement fail-open, privacy-bounded skill-usage telemetry and its opt-out behavior. |
| `scripts/requirements.txt` | Declare Python runtime dependencies used by the course-creator scripts. |

## Change Placement Guide

- Put a new author-facing choice and its effect preview in `course-design-intake.md`; put the normalized field shape in `data-contracts.md`; put its actual teaching effect in `pedagogy.md` or the relevant artifact owner.
- Put shared Course Prompt and Teaching Prompt meaning or ownership boundaries in `prompt-contracts.md`; put artifact-specific construction in `course-prompt.md` or `teaching-prompt.md`.
- Put MarkdownFlow parser facts in `markdownflow.md`, authoring-time encoding instructions in `markdownflow-authoring.md`, and learning-effect requirements in `pedagogy.md`.
- Put executable command behavior in `shifu-cli.py`, its stable public interface in `cli/cli-reference.md`, and the workflow decision to invoke it in the relevant platform or analytics workflow.
- Put validation criteria in the owning artifact reference or `optimization-checklist.md`, then add regression evidence in evals or repository tests. Tests and evals enforce contracts; they do not become the only statement of a requirement.
