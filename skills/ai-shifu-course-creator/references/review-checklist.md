# Review Checklist

Optimization 全面审计清单。Optimization 必须逐项检查可观察结果；规则含义以每项链接的权威文件为准。其他阶段的交付检查见 `segmentation-orchestration.md`、`generation-workflow.md` 和 `deployment-workflow.md` 内的 Validation 段。

## Coverage

- All critical source points are present.
- No unsupported additions alter meaning.
- Source information density preserved (no substance traded for fluency).

## Prompt Semantics

- Teaching Prompt and Course Prompt content passes [prompt-contracts.md#prompt-semantics](prompt-contracts.md#prompt-semantics).

## User-Visible Language

- User-visible agent output outside generated course content follows the resolved target language from `data-contracts.md#language-resolution`.
- Generated course artifacts and learner-facing passages follow the resolved target language.
- Effective build metadata follows the resolved target language after precedence is applied: course title (`--title`, `README.md`, or directory-name fallback), course description (`--description` or `course-description.md`), chapter titles (`structure.json`, `--chapter-name`, or course-title fallback), and lesson titles.
- Human-facing labels for canonical concepts follow [session-controls.md#canonical-term-translation-table](session-controls.md#canonical-term-translation-table) when the resolved target language is listed there.
- Machine-facing identifiers and verbatim source material remain unchanged: JSON keys, file names, CLI flags, API fields, code symbols, MarkdownFlow syntax, URLs, code samples, and required verbatim source quotes.

## Structure Separation

- Chapter titles, lesson titles, numbering, and hierarchy labels satisfy the separation defined in `data-contracts.md#lesson-schema`.
- Each lesson file's first non-empty line performs a teaching-start function: scenario, guiding question, prior-experience activation, task setup, or practice start.
- High-confidence structure pollution is absent: the first line is not a Markdown heading copied from `structure.json`, not a `第X章` / `Chapter X` directory label, and not an exact repeat of the chapter or lesson title.
- Medium-confidence cases are flagged for review instead of auto-deleted: headings used to teach Markdown syntax, code comments beginning with `#`, or courses with an explicit `allow_headings` / heading-supported rendering decision.

## Lesson Loop

- Each Teaching Prompt contains the lesson's teaching method and flow.
- The interaction policy used for this audit resolves to `enabled`, `disabled`, or `unspecified` and matches the Course Design Intake answer.
- The observed lesson loop and any non-interactive substitute match `pedagogy.md#interaction-policy-precedence` and `pedagogy.md#lesson-loop` for that resolved policy.
- The final paragraph of each lesson is non-interactive.
- One core question per lesson; resolved by lesson close.
- Action tasks executable now or explicitly linked to a downstream lesson.
- Variable naming consistent and traceable across lessons; new variable names follow the resolved output language and are composed of letters, numbers, and underscores.
- Carryover statements only where cross-lesson dependency is allowed.
- Lesson structure follows the content, not a forced uniform template that erases lesson specificity.

## Interaction Quality

- The observed control composition passes [generation-workflow.md#interaction-encoding](generation-workflow.md#interaction-encoding), while its purpose, selection type, and feedback effect pass `pedagogy.md#interaction-design`.
- Under `disabled`, no `?[]` block, learner-answer request, learner-answer variable, or answer-dependent branch is present.
- Interactions that are present are concrete and answerable.
- Interaction type matches the decision, and multi-select answers drive combined feedback, prioritization, or tailored examples rather than exhaustive branching for every combination.
- Learner-facing questions appear before interaction syntax, not after `%{{var}}` inside `?[%{{var}} ...]`.
- Each `?[]` interaction appears on its own line.
- If the pre-interaction text enumerates or describes choices, the `?[]` option labels match those choices exactly — same set, order, and wording.
- Input interactions include a specific pre-interaction question plus a shorter `...` placeholder.
- Interaction presence, placement, and deepening match the resolved policy in `pedagogy.md#interaction-policy-precedence`.
- Branching paths are distinct for viewpoint/path interactions and whenever `require_branching_feedback` is explicit.
- Instructional interaction results affect later content through immediate feedback or a visible downstream effect.
- Repeated interaction semantics avoided across lessons unless comparison intent is explicit.
- Interaction count per lesson is at most five.
- Variable-backed interactions are used only when the answer must leave the current lesson.
- Lesson-local branching, examples, feedback, summaries, and inputs use no-variable `?[...]` and do not introduce `{{var}}`.

## Variable Safety

- `disabled` lessons contain no learner-answer variables.
- Every referenced learner-answer variable has a corresponding variable-backed interaction and metadata entry.
- Any learner answer used outside the current lesson, including `course-prompt.md`, later lessons, or cross-lesson personalization, difficulty control, examples, summaries, or deliverables, has a named variable.
- No duplicate semantic collection unless comparison intent is explicit.
- No unresolved placeholders in learner-facing content.
- Variable references and pre-collection `UNKNOWN` behavior pass [generation-workflow.md#variable-and-branch-encoding](generation-workflow.md#variable-and-branch-encoding).
- Every variable has cross-lesson or Course Prompt utility.
- No throwaway named variables for continue buttons, confirmations, choices, or inputs used only inside the current lesson.

## Visual-Text Coordination

- In standard non-slide-only lessons, every core concept that uses a visual has a visual-plus-text explanation.
- Raw graphic source code appears only when explicitly requested, as required by [generation-workflow.md#image-authoring](generation-workflow.md#image-authoring).
- Pure classroom slides follow `generation-workflow.md#slide-only-generation-override` and are not failed for omitting AI narration or a full explanation paragraph.
- Every embedded asset uses the uploaded URL and manifest mapping defined by `cli/cli-reference.md#image-upload` and `cli/course-directory-spec.md#assets`.
- Every fixed-display or HTML-view image conforms to [generation-workflow.md#image-authoring](generation-workflow.md#image-authoring); the resulting URL, description, caption, position, and ordering survive generation as required by the selected form.
- Alt text and `图片内容` descriptions carry information about what the image conveys (no `image1` / `示意图`).
- In standard non-slide-only lessons, text adds context (background / causality / examples), not just a restatement of the image.

## Runtime Stability

- MarkdownFlow blocks parse and execute with the runtime effects defined in `markdownflow.md`.
- Complete deterministic blocks bypass the LLM; inline preservation remains within a generative block as defined in `markdownflow.md#deterministic-blocks`.
- Preservation scope passes `optimization-workflow.md#preservation-decisions`.
- Code, image, and required source spans remain intact after the applicable preprocessing, deterministic, or generative path.

## Course Prompt

- A `course_prompt` artifact is produced when input includes course material.
- All six required canonical sections are present in order, with headings rendered in the resolved output language: Role, Task, Teaching Techniques, Writing Style, Format, and Slides.
- No `XXX` placeholder remains; every non-placeholder instruction from `course-prompt.md#fillable-template` is represented.
- The completed artifact passes `course-prompt.md#materialization-checks` and respects `prompt-contracts.md#artifact-responsibilities`.
- The Teaching Techniques and Slides sections preserve the template's deference to the current Teaching Prompt without introducing competing lesson pedagogy.
