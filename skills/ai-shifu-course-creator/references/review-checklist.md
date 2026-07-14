# Review Checklist

Authoritative observable validation for Segmentation, Orchestration, Generation, Optimization, course-level finalization, pre-deploy language review, and Deployment. Start with the cross-artifact [Prompt Contracts](prompt-contracts.md); other normative behavior remains in the linked owners below, while this file records what must be true before a phase passes.

## Segmentation Validation

- Segment output covers all valid source spans in traceable order.
- The complete handoff satisfies `data-contracts.md#segmentation-output`; every segment satisfies `data-contracts.md#segment-schema`, including a non-empty `transfer_signals` object with every applicable canonical key and no invented signal.
- Source order, semantic boundaries, one-core-question candidates, and immutable-block marking satisfy `pedagogy.md#segmentation-methodology` and `markdownflow.md#preservation`.

## Orchestration Validation

- All artifacts satisfy `data-contracts.md#orchestration-output`; fallback output also satisfies `data-contracts.md#fallback-output-extensions`.
- Every lesson passes the applicable sections below for structure, lesson loop, interaction quality, variable safety, visual-text coordination, and runtime stability.
- Cross-lesson dependencies, `course_index`, and `global_variable_table` agree; no unresolved placeholder or unbound learner-answer variable remains.
- Failed lessons are recomputed before Orchestration reports completion; partial passage is invalid.

## Generation Validation

- The handoff satisfies `data-contracts.md#generation-output`; every `teaching_prompt` is runnable MarkdownFlow and satisfies `data-contracts.md#lesson-schema`.
- The first non-empty line performs a teaching-start function instead of repeating a chapter, lesson, directory, or source heading.
- The normalized interaction policy and delivery mode are applied without reinterpretation.
- Every generated lesson passes the applicable detailed checks below.

## Optimization Validation

- Present the conclusion and overall risk first using `report-template.md`, then run every detailed section below against the selected lesson or full-course scope.
- The result satisfies `data-contracts.md#optimization-output`; full-course finalization also satisfies `data-contracts.md#final-authoring-output`.
- Apply the smallest runtime-safe correction first; list any remaining non-blocking gap explicitly.
- When full-course finalization is in scope, validate the generated Course Prompt section below in addition to the Teaching Prompt checks.
- For a focused audit, validate a Course Prompt only when the user supplies one; otherwise do not invent or emit a `course_prompt` artifact.

## Coverage

- All critical source points are present.
- No unsupported additions alter meaning.
- Source information density preserved (no substance traded for fluency).

## Script Style

- Directive / model-guiding language; no polished learner-facing manuscript prose.
- No author-side meta labels ("Knowledge Block", "Lesson Objective", "Deliverable").
- No internal authoring terms exposed in learner-facing text.

## User-Visible Language

- User-visible agent output outside generated course content follows `session-controls.md#output-language`.
- Generated course artifacts and learner-facing passages follow the resolved target language.
- Effective build metadata follows the resolved target language after precedence is applied: course title (`--title`, `README.md`, or directory-name fallback), course description (`--description` or `course-description.md`), chapter titles (`structure.json`, `--chapter-name`, or course-title fallback), and lesson titles.
- Human-facing labels for canonical concepts follow `session-controls.md#canonical-term-translation-table` when the resolved target language is listed there.
- Machine-facing identifiers and verbatim source material remain unchanged: JSON keys, file names, CLI flags, API fields, code symbols, MarkdownFlow syntax, URLs, code samples, and required verbatim source quotes.

## Pre-Deploy Language Audit

Before finalizing or deploying a generated course directory, verify that no template heading or directive phrase from another language remains in any build-consumed user-visible artifact or effective metadata field:

- Resolved course title from `--title`, the first `README.md` heading, or the directory-name fallback.
- Resolved course description from `--description` or `course-description.md`.
- Resolved chapter titles from `structure.json`, `--chapter-name`, or the course-title fallback.
- Learner-facing lesson title fields in `structure.json`.
- The complete `course-prompt.md` artifact.
- Every lesson referenced by `structure.json`, or every auto-discovered `lessons/lesson-*.md` file when `structure.json` is absent.

## Structure Separation

- Chapter titles, lesson titles, numbering, and hierarchy labels live in `structure.json` / `course_index`, not in Teaching Prompt body text.
- Each lesson file's first non-empty line performs a teaching-start function: scenario, guiding question, prior-experience activation, task setup, or practice start.
- High-confidence structure pollution is absent: the first line is not a Markdown heading copied from `structure.json`, not a `第X章` / `Chapter X` directory label, and not an exact repeat of the chapter or lesson title.
- Medium-confidence cases are flagged for review instead of auto-deleted: headings used to teach Markdown syntax, code comments beginning with `#`, or courses with an explicit `allow_headings` / heading-supported rendering decision.

## Lesson Loop

- The interaction policy used for this audit resolves to `enabled`, `disabled`, or `unspecified` and matches the Course Design Intake answer.
- The observed lesson loop and any non-interactive substitute match `pedagogy.md#interaction-policy-precedence` and `pedagogy.md#lesson-loop` for that resolved policy.
- The final paragraph of each lesson is non-interactive.
- One core question per lesson; resolved by lesson close.
- Action tasks executable now or explicitly linked to a downstream lesson.
- Variable naming consistent and traceable across lessons; new variable names follow the resolved output language and are composed of letters, numbers, and underscores.
- Carryover statements only where cross-lesson dependency is allowed.
- Lesson structure follows the content, not a forced uniform template that erases lesson specificity.

## Interaction Quality

- Under `disabled`, no `?[]` block, learner-answer request, learner-answer variable, or answer-dependent branch is present.
- Interactions that are present are concrete and answerable.
- Interaction type matches the decision: single-select for mutually exclusive path choices, multi-select for non-exclusive learner context, goals, interests, modules, blockers, scenarios, experience, or practice needs. For multi-select, downstream content is driven through combined feedback, prioritization, or tailored examples rather than exhaustive branching for every combination.
- Learner-facing questions appear before interaction syntax, not after `%{{var}}` inside `?[%{{var}} ...]`.
- Each `?[]` interaction appears on its own line.
- If the pre-interaction text enumerates or describes choices, the `?[]` option labels match those choices exactly — same set, order, and wording.
- Input interactions include a specific pre-interaction question plus a shorter `...` placeholder.
- Interaction presence, placement, and deepening match the resolved policy in `pedagogy.md#interaction-policy-precedence`.
- Branching paths are distinct for viewpoint/path interactions and whenever `require_branching_feedback` is explicit.
- Instructional interaction results affect later content through immediate feedback or a visible downstream effect.
- Repeated interaction semantics avoided across lessons unless comparison intent is explicit.
- Variable-backed interactions are used only when the answer must leave the current lesson.
- Lesson-local branching, examples, feedback, summaries, and inputs use no-variable `?[...]` and do not introduce `{{var}}`.

## Variable Safety

- `disabled` lessons contain no learner-answer variables.
- Every referenced learner-answer variable has a corresponding variable-backed interaction and metadata entry.
- Any learner answer used outside the current lesson, including `course-prompt.md`, later lessons, or cross-lesson personalization, difficulty control, examples, summaries, or deliverables, has a named variable.
- No duplicate semantic collection unless comparison intent is explicit.
- No unresolved placeholders in learner-facing content.
- Variable references in Teaching Prompt and Course Prompt content are written as substituted values; references that may run before the learner assigns a value handle the literal `UNKNOWN` fallback.
- Variable-based branches state the substituted value in a natural sentence first, then use natural-language condition phrasing.
- Every variable has cross-lesson or Course Prompt utility.
- No throwaway named variables for continue buttons, confirmations, choices, or inputs used only inside the current lesson.

## Visual-Text Coordination

- In standard non-slide-only lessons, every core concept that uses a visual has a visual-plus-text explanation.
- Raw graphic source code (SVG, HTML drawings, Mermaid, PlantUML, or Graphviz) appears in a Teaching Prompt only when the author explicitly requests that raw format; approved HTML-view image instructions are checked separately below.
- Pure classroom slides follow `delivery-modes.md#pure-slides` and are not failed for omitting AI narration or a full explanation paragraph.
- Every author-provided image changed or uploaded in this run has passed the shared handoff checks in `image-assets.md#validate`; an unchanged valid platform resource does not fail solely because it has no local manifest entry.
- In standard non-slide-only lessons, text adds context (background / causality / examples), not just a restatement of the image.

## Runtime Stability

- MarkdownFlow syntax is valid.
- Deterministic blocks used only where necessary; not wrapping full lessons.
- Interaction count per lesson does not exceed the normalized `authoring_constraints.max_interactions` value; when that field is omitted, the limit is five (recommended three to four).
- Code, image, and required source spans preserved per `markdownflow.md#preservation`.

## Course Prompt

- Full-course finalization includes one `course_prompt`; a focused audit checks this artifact only when it is part of the supplied scope.
- The applicable sections from `course-prompt.md#fillable-template` are present in order, with headings rendered in the resolved output language.
- No `XXX` placeholder remains; every non-placeholder base-template instruction is represented unless `delivery-modes.md` explicitly replaces it.
- Teaching Prompt, Course Prompt, and Listen Mode behavior agree with the same normalized `delivery_mode`.

## Course Description

- Full-course finalization includes one non-empty `course_description` in the resolved output language.
- The description names the topic, target learners, and concrete outcomes without exposing author-side workflow notes.

## Deployment Validation

- Build and import complete without errors.
- The deployed course is accessible through the verification URL returned by the CLI.
- Lesson count and structure match the source directory.
- After publication, the public learner URL returned by the CLI is reachable.
