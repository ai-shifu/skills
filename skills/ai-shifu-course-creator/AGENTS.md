# AI-Shifu Course Creator Maintenance Guide

## Ownership Rules

- Give each capability, contract, and validation criterion one canonical owner in the map below. Other files link to or cite that owner and add only their own local application.
- Keep `SKILL.md` focused on discovery, shared conventions, the three-category capability catalog, and the default full-course outcome. Preserve its teaching design, MarkdownFlow expression, and CLI operation boundaries without turning them into phases. The using agent owns task decomposition and invocation order; references own how their capabilities work.
- Separate decisions from representations: `teaching-design.md` owns teaching recommendations and their tradeoffs, `markdownflow-syntax.md` owns runtime syntax and effects, and `teaching-prompt.md` owns translation of resolved lesson decisions into a runnable, author-editable Teaching Prompt.
- Separate optional authoring controls from runtime and platform contracts. `authoring-contracts.md` owns supported controls and semantic consistency; capability references explain operations, checklists and evals verify results, and scripts implement deterministic interfaces. Do not reintroduce mandatory phase envelopes or plans.
- When a change crosses an ownership boundary, update the canonical owner first. Update consumers only for navigation, integration, or validation consequences, and link back to the owner instead of restating its rules.
- When adding, removing, renaming, or materially changing a file's responsibility, update this map in the same change. Give every new file one primary responsibility that is not already owned elsewhere.

## Entrypoint and Package Files

| File | Canonical responsibility |
| --- | --- |
| `AGENTS.md` | Define this skill's maintenance-time ownership map and cross-file editing rules. It guides contributors and does not define learner-time or authoring behavior. |
| `SKILL.md` | Define skill discovery metadata, shared conventions, user-facing Markdown links, the teaching design / MarkdownFlow expression / CLI operation categories, and full-course default publication with the completed-content confirmation boundary. It leaves invocation order to the using agent and capability mechanics to references. |
| `agents/openai.yaml` | Define ChatGPT's display label, short description, and starter prompt for this skill. Discovery behavior remains in `SKILL.md`. |
| `.env.example` | Document supported service-selection, token, and usage-analytics opt-out variables with safe empty defaults, credential-storage guidance, and the user-facing account-linked usage notice. |
| `evals/evals.json` | Hold end-to-end behavioral scenarios, optional input fixtures, and expected outcomes for capability use, authoring, platform, analytics, and boundary regressions. Canonical guidance remains the source of behavior. |
| `evals/trigger_eval.json` | Test whether representative requests should or should not discover this skill. Keep capability and trigger wording canonical in `SKILL.md` frontmatter. |

## Core Reference Responsibilities

| File | Canonical responsibility |
| --- | --- |
| `references/language-policy.md` | Own target-language resolution, canonical human-facing terminology, localization boundaries, first-mention wording, and the final language audit across artifacts and messages. |
| `references/session-controls.md` | Own session lifecycle behavior: official contact timing, explicit skill-version update checks, progress and error communication, handoffs, and first-response contact eligibility. |
| `references/authentication.md` | Own platform profile selection and task-context continuity, initial service selection, credential verification, browser authorization, login continuation, and authentication failure handling. It establishes access and does not select a course. Callers own when authentication runs. |
| `references/open-in-app-browser.md` | Own the host-application mechanics for opening a supplied URL in a visible built-in browser and reporting the opening result. The caller owns URL selection and invocation. |
| `references/course-lookup.md` | Own existing-course title and BID matching, ambiguity handling, and resolved or unresolved lookup results. The using agent owns new-versus-existing intent and the response to a no-match result, within the intent boundary in `SKILL.md`. For analytics, `analytics/tables.md` owns current-title semantics and `analytics/query-recipes.md` applies them through lookup templates. |
| `references/course-design-choices.md` | Explain author-facing design choices, their effects, and interpretation. The using agent decides which unresolved choices need questions; no ordered questionnaire or mandatory handoff is owned here. |
| `references/authoring-contracts.md` | Own optional design-control shapes and semantic artifact consistency. CLI payloads and course-directory formats remain in the CLI specifications; internal planning and bookkeeping have no mandatory schema. |
| `references/source-preservation.md` | Own selection of immutable source spans and exactness verification after transformations. Teaching Prompt encoding of those decisions belongs to `teaching-prompt.md#source-encoding`. |
| `references/prompt-semantics.md` | Own semantics shared by Course Prompts and Teaching Prompts, including personalization-direction effects and the responsibility boundary between the two artifact types. It is the integration owner, not the owner of syntax, pedagogy, schemas, or materialization. |
| `references/teaching-design.md` | Own teaching recommendations, pattern examples, interaction-purpose guidance, memory-use advice, and visual-text tradeoffs. The using agent selects pedagogy within explicit author constraints. |
| `references/markdownflow-syntax.md` | Own the runtime-recognized MarkdownFlow syntax and its observable preprocessing, course memory, interaction, branching, deterministic-block, image, and preservation behavior. |
| `references/image-authoring.md` | Own intake, understanding, upload, composition, embedding, and output validation for lesson image assets. Teaching purpose, MarkdownFlow representation, and CLI upload remain separate actions within the entrypoint's categories. Teacher avatars remain platform metadata under `course-management.md`. |

## Authoring and Artifact Reference Responsibilities

| File | Canonical responsibility |
| --- | --- |
| `references/course-structure.md` | Own source analysis, optional traceable segmentation, chapter grouping, and lesson-structure planning from available inputs. It does not require generation or a fixed segment schema. |
| `references/teaching-prompt.md` | Own writing or revising one runnable Teaching Prompt from available inputs, required source-only block comments, optional layout templates, and interaction, memory, branch, preservation, and image integration. Runtime syntax remains in `markdownflow-syntax.md`; no phase envelope or fixed planning run is required. |
| `references/course-prompt.md` | Own materialization of the six-section course-wide Course Prompt, including fill sources and uniform presentation requirements. Lesson pedagogy, sequence, interactions, and position-specific slide decisions remain Teaching Prompt concerns. |
| `references/course-description.md` | Own the learner-facing course listing and SEO description artifact, its supported source claims, output form, and validation. |
| `references/course-review.md` | Own scoped review and requested minimal repairs of available artifacts, findings, uncertainty, and truthful validation results. It applies teaching-design or MarkdownFlow-expression criteria from the checklist without orchestrating other capabilities; platform readback remains with the relevant CLI capability. |
| `references/review-checklist.md` | Own observable pass, fail, and not-assessed acceptance criteria for existing Teaching Prompts, Course Prompts, descriptions, language, fidelity, runtime safety, and repair scope. Linked owners define the underlying behavior. |

## Platform Capability Reference Responsibilities

| File | Canonical responsibility |
| --- | --- |
| `references/course-sync.md` | Own existing-course cloud-to-local pulls, required baselines for lesson, Course Prompt, and description edits, divergence status, content pushes, version checks, and conflict convergence. It does not author content or manage publication metadata. |
| `references/build-and-import.md` | Own building and inspecting an import payload, importing a new draft, and verifying imported content. `SKILL.md` owns the default outcome and content-confirmation policy; management owns publication and public-access verification. |
| `references/course-management.md` | Own non-authoring platform operations: list, preview, publish, archive or restore, reorder, course metadata, teacher avatar, access, visibility, and Listen Mode. Publication includes published-state and public-access verification. User-request completion handoffs remain owned by `session-controls.md`. |
| `references/cli/cli-reference.md` | Own the public `shifu-cli.py` command surface: invocation, flags, command groups, authentication inputs, output conventions, state behavior, and exit codes. The using agent decides when commands run; capability references explain their use. |
| `references/cli/course-directory-spec.md` | Own the local course-directory layout, artifact meanings, build precedence, sync and image manifests, generated import shape, and which files each CLI operation reads or writes. |

## Analytics Reference Responsibilities

| File | Canonical responsibility |
| --- | --- |
| `references/analytics/guide.md` | Own the analytics capability entrypoint, CLI-only execution, supported question families, question-to-query planning, choosing tables or recipes, response and error interpretation, and navigation to deeper references. CLI output conventions and process exit codes remain with `cli/cli-reference.md`. |
| `references/analytics/query-language.md` | Own the analytics query language: JSON body shape, operators, aggregates, limits, auto-filters, and server-enforced query-shape constraints. Field-access policy, refusals, masking, and user-facing handling remain with `privacy-and-presentation.md`. |
| `references/analytics/tables.md` | Own queryable table and field semantics, enum and code translations, identifier relationships, known data traps, and distinctions among independently measured amounts. |
| `references/analytics/query-recipes.md` | Own ready-to-run query and `credit-detail` templates for supported analytics scenarios. Grammar and field meaning remain in `query-language.md` and `tables.md`. |
| `references/analytics/privacy-and-presentation.md` | Own analytics access restrictions, refusal boundaries, masking and aggregation requirements, UTC-to-local presentation, the translation gate, and user-facing answer structure. |

## Script Responsibilities

| File | Canonical responsibility |
| --- | --- |
| `scripts/shifu-cli.py` | Implement the unified deterministic interface for site configuration, authentication, course queries and writes, sync, import and build, image upload, analytics, state, and structured command results. Attach optional usage metadata to business requests. Reference files own capability guidance and relevant constraints. |
| `scripts/agent_detection.py` | Identify the Agent environment and own its canonical IDs, display names, and evidence. The CLI decides reporting eligibility. |
| `scripts/profile_store.py` | Implement named profile configuration, default selection, execution-context resolution, isolated authorization-file storage, URL validation, and recoverable migration from legacy configuration. The CLI consumes one resolved context; references own access guidance. |
| `scripts/image_preparation.py` | Implement local image decoding, orientation correction, resizing, recompression, output-format selection, and content-hash naming for upload preparation. |
| `scripts/skill_update_check.py` | Implement fail-open GitHub Release discovery, update availability checks, and release and development manifest validation. |
| `scripts/requirements.txt` | Declare Python runtime dependencies used by the course-creator scripts. |

## Change Placement Guide

- Put an author-facing choice and its effects in `course-design-choices.md`, optional control shape in `authoring-contracts.md`, and teaching guidance or artifact effects in the appropriate owner. Do not require every user to answer a fixed questionnaire.
- Put shared Course Prompt and Teaching Prompt meaning or ownership boundaries in `prompt-semantics.md`; put artifact-specific construction in `course-prompt.md` or `teaching-prompt.md`.
- Put MarkdownFlow parser facts in `markdownflow-syntax.md`, Teaching Prompt authoring and source-encoding instructions in `teaching-prompt.md`, and teaching recommendations in `teaching-design.md`. Preserve explicit author requirements in the affected artifact.
- Put executable command behavior in `shifu-cli.py`, its stable public interface in `cli/cli-reference.md`, and operation-specific guidance in the relevant capability reference. Invocation timing belongs to the using agent, except for the explicit product conventions owned by `SKILL.md` and `session-controls.md`.
- Put validation criteria in the owning reference or `review-checklist.md`, then add regression evidence in evals or repository tests. Tests and evals enforce contracts; they do not become the only statement of a requirement.
