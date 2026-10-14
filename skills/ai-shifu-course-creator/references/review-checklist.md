# Course Review Checks

Observable criteria for the artifacts and scope actually available. Use `pass`, `fail`, or `not-assessed` when useful; a complete checklist report is not required. These checks do not prescribe the authoring process or make optional teaching choices mandatory.

## Coverage and Fidelity

- With authoritative source material, required points remain represented and generated additions do not change their meaning. Without it, do not claim external-source coverage or fidelity.
- A focused repair retains the supplied content's intended meaning and information density. A requested rewrite respects its explicit content constraints.
- Required exact content passes [source-preservation.md#verification](source-preservation.md#verification). Missing evidence is reported rather than invented.

## Prompt Boundaries

- Each artifact serves its responsibility under [prompt-semantics.md#artifact-responsibilities](prompt-semantics.md#artifact-responsibilities).
- Teaching Prompts provide executable local teaching directions, required content and relationships, and any chosen feedback or branch behavior. A Course Prompt is not relied on to invent missing lesson pedagogy.
- After MarkdownFlow removes source-only comments, every remaining part of a Teaching Prompt serves runtime delivery. No executable requirement, variable, option, URL, command, or exact span exists only in a comment.
- Authoring controls, selection interfaces, pipeline notes, and learner-profile data do not leak into runtime instructions. Second-person forms obey [prompt-semantics.md#prompt-semantics](prompt-semantics.md#prompt-semantics).

## Teaching Design and Layout

- The lesson's chosen approach makes its intended learning result achievable with supported facts, sufficient reasoning, and useful evidence. Do not fail an artifact for omitting a recommended pattern, fixed loop, single-question structure, visual, cover, cadence, deliverable, or interaction count.
- Examples and analogies, when used, have meaningful conditions or correspondences, explanatory value, and necessary limits under [teaching-design.md#examples-and-analogies](teaching-design.md#examples-and-analogies). Avoid misleading comparisons and unsupported assumptions of familiarity.
- Explicit author decisions about order, delivery experience, interaction restrictions, and other constraints are respected. The agent may choose or revise unspecified design elements within the task.
- New or explicitly rewritten Teaching Prompts have concise source-only navigation comments for useful teaching blocks under [teaching-prompt.md](teaching-prompt.md). Optional layouts and agent-created layouts are valid when readable and runtime-safe.
- In audit-only existing content, comment and layout normalization is `not-assessed`; do not reformat or add comments. Continue checking observable syntax and runtime behavior.
- Syntax-owned structures and immutable source content retain their required form and scope in any layout. Removing source-only comments does not remove runtime content.
- Pure classroom slides retain their intended instructor-paced behavior; explicit text-only constraints contain no visual instructions. Visuals serve a defined purpose rather than padding length. General slide presentation requirements belong in the Course Prompt.

## Personalization

- Resolved directions implement exactly the effects in [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions), including a neutral fallback for missing relevant context. Do not enable an unselected direction through a generic instruction.
- Unselected directions and an explicit empty selection retain the source-, author-, and audience-based baseline without deleting needed examples, analogies, practical value, or explanation.
- Selected adaptations are executable where needed. A generic course-wide claim does not replace a required local example or analogy instruction.
- Runtime personalization preserves the authored objectives, required facts and boundaries, needed explanation depth, sequence, visual structure, and selected interaction or feedback effects. It does not authorize new context collection or branches.
- With no supplied selection, assess observable behavior without inferring an enum array from the Prompt. Selection alignment or absent companion alignment may be `not-assessed`; no missing intermediate plan or schema is manufactured.
- Reusable artifacts contain no specific learner profile, platform learner-profile tags, internal profile variable names, or authoring selection interface.

## Interaction and Runtime Safety

- Questions and options are clear and answerable, and selected instructional interactions have a meaningful feedback or teaching effect under [teaching-design.md#interaction-design](teaching-design.md#interaction-design).
- Every control, assignment, reference, and branch follows [markdownflow-syntax.md](markdownflow-syntax.md) and [teaching-prompt.md#source-encoding](teaching-prompt.md#source-encoding). Controls stay recognizable and distinct from simulated visual controls.
- Named answers have valid collection and meaningful cross-lesson or Course Prompt consumers; local answers remain unnamed. Check actual artifacts under [authoring-contracts.md#variable-table](authoring-contracts.md#variable-table); no variable-table JSON is required.
- Branches use natural language and account for unavailable named values where applicable. No learner-visible authoring placeholders remain.
- Deterministic blocks, code fences, required source spans, and image records survive preprocessing as required. Images use [image-authoring.md#image-output-validation](image-authoring.md#image-output-validation) when present; absent images do not require image work.

## Course Prompt and Description

- The Course Prompt keeps its six sections in order and all non-placeholder template behavior under [course-prompt.md#materialization-checks](course-prompt.md#materialization-checks), with no unresolved `XXX`.
- Its fill values match the available topic, goals, audience, delivery experience, and resolved personalization. Its shared slide rules do not redefine lesson-specific structure or pedagogy.
- The description clearly states audience fit, topic, and supported outcomes under [course-description.md#validation](course-description.md#validation). It contains no unsupported guarantee, authoring notes, Prompt dump, or deployment state.

## Language and Repair Scope

- Human-readable content passes [language-policy.md#language-audit](language-policy.md#language-audit), including effective build values when they are in scope.
- Repairs respect the requested scope and retain executable requirements in their owning artifact. Consequential changes have a clear reason.
- Unresolved correctness, source, or runtime risks and unavailable checks are visible rather than hidden by cosmetic rewriting or a claimed full pass.
