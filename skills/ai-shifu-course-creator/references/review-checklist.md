# Review Checklist

Optimization 全面审计清单。Optimization 必须逐项检查可观察结果；规则含义以每项链接的权威文件为准。其他阶段的交付检查见 `segmentation-orchestration.md`、`generation-workflow.md` 和 `deployment-workflow.md` 内的 Validation 段。

## Coverage

- All critical source points are present.
- No unsupported additions alter meaning.
- Source information density preserved (no substance traded for fluency).

## Prompt Semantics

- Teaching Prompt and Course Prompt content passes [prompt-contracts.md#prompt-semantics](prompt-contracts.md#prompt-semantics).

## Language Audit

Resolve `resolved_target_language` from `data-contracts.md#language-resolution`, then inspect every human-readable output produced or changed by the active workflow. Passing one file is not enough; check each applicable item below.

### Phase Output Fields

- **Segmentation:** `segments[].core_point`, every human-readable `segments[].transfer_signals.*` value, `lesson_cut_candidates[].core_question`, and fallback `rerun_hints[]`.
- **Orchestration:** `course_index[].lesson_title`, `course_index[].core_question`, and fallback `rerun_plan.reason`.
- **Generation:** `lesson_teaching_prompts[].lesson_title` and the complete `lesson_teaching_prompts[].teaching_prompt`, including teaching instructions, learner questions and option labels, input hints, feedback or branch descriptions, explanations, summaries, newly authored image alt/content/caption/layout text, and deterministic output text. Also check fallback `assumptions[]` and `upgrade_notes[]`.
- **Optimization:** the complete `course_prompt` (all six headings, fill values, and every section's instruction text), the complete learner-facing `course_description`, human-readable findings in `risk_and_issue_report`, every `change_list[].change`, and fallback `follow_up[]`.
- **Variables:** each newly authored `global_variable_table[].name`; preserve an existing or source-provided variable name when changing it would break the contract.

### Course Directory and Effective Build Values

- **Course title:** check the value that will actually win: `--title`, otherwise the first heading in `README.md`, otherwise the directory name.
- **Course description:** check `--description` when present; otherwise check the complete `course-description.md`; an empty fallback has no language to audit.
- **Chapter titles:** check `structure.json.chapters[].title`; without `structure.json`, check `--chapter-name` or the resolved course-title fallback.
- **Lesson titles:** check `structure.json.chapters[].lessons[].title`; without an explicit title, check the filename-derived title that `build` will emit.
- **Course Prompt and lessons:** check the complete `course-prompt.md` and every lesson file referenced by `structure.json`; without `structure.json`, check every auto-discovered `lessons/lesson-*.md` file.
- **Images:** check newly authored `assets/image-manifest.json.images[].alt` values that are embedded in lessons, plus the resulting lesson alt/content/caption/layout text.
- **Direct management commands:** before mutation, check human-readable values passed through `create --name/--description`, `add-chapter --name`, `add-lesson --name/--teaching-prompt-file`, `update-meta --name/--description/--course-prompt-file`, `update-lesson --teaching-prompt-file`, and `rename-lesson --name`.
- **Built deployment payload:** after `build`, inspect `shifu-import.json` fields `shifu.title`, `shifu.description`, and `shifu.course_prompt`; every `outline_items[].title`; each lesson item's `outline_items[].content`; and each lesson item's copied `outline_items[].course_prompt`. This confirms the final precedence and fallback values, not just the source files.

### User-Facing Operational Outputs

- Check contact and version notices, authentication guidance, course-target choices, Course Design Intake questions and options, progress updates, errors, review notes, and handoff instructions.
- Check every phase report's headings, field labels, findings, issue explanations, suggestions, validation explanations, next actions, and handoff notes.
- Check analytics answer headings, narrative findings, interpretations, refusals, and drill-down offers.
- For canonical concepts, use the corresponding language column in `session-controls.md#canonical-term-translation-table` when available; otherwise localize naturally in `resolved_target_language`.

### Language Audit Exclusions

- Do not translate JSON keys, ids or BIDs, file names and paths, CLI commands and flags, API/DSL fields, code symbols, contract enum values, MarkdownFlow syntax, URLs, code samples, or fixed numeric values.
- Preserve exact source quotations, regulated wording, source-selected immutable alt/captions, tables, and any other span selected by `optimization-workflow.md#preservation-decisions`; audit only the newly authored surrounding explanation.
- In deployment reports, preserve the script-owned Chinese Verification URL hint verbatim as required by `report-template.md#formatting-rules`; localize the link-purpose label and surrounding explanation.

## Structure Separation

- Chapter titles, lesson titles, numbering, and hierarchy labels satisfy the separation defined in `data-contracts.md#lesson-schema`.
- Each standard non-slide-only lesson file's first non-empty line begins a brief teaching lead-in: scenario, guiding question, prior-experience activation, task setup, or practice start. Pure classroom slides instead begin with slide-facing content under `generation-workflow.md#slide-only-generation-override`.
- In standard non-slide-only teaching, the brief lead-in is followed by the first substantive slide before any extended explanation; the first slide is not a cover, decorative page, or objective-only page.
- High-confidence structure pollution is absent: the first line is not a Markdown heading copied from `structure.json`, not a `第X章` / `Chapter X` directory label, and not an exact repeat of the chapter or lesson title.
- Medium-confidence cases are flagged for review instead of auto-deleted: headings used to teach Markdown syntax, code comments beginning with `#`, or courses with an explicit `allow_headings` / heading-supported rendering decision.

## Lesson Loop

- Each Teaching Prompt contains the lesson's teaching method and flow.
- The interaction policy used for this audit resolves to `enabled`, `disabled`, or `unspecified` and matches the Course Design Intake answer.
- The observed lesson loop and any non-interactive substitute match `pedagogy.md#interaction-policy-precedence` and `pedagogy.md#lesson-loop` for that resolved policy.
- The final paragraph of each lesson is non-interactive.
- One core question per lesson; resolved by lesson close.
- Action tasks executable now or explicitly linked to a downstream lesson.
- Variable naming consistent and traceable across lessons; new variable names follow `resolved_target_language` and are composed of letters, numbers, and underscores.
- Carryover statements only where cross-lesson dependency is allowed.
- Lesson structure follows the content, not a forced uniform template that erases lesson specificity.

## Interaction Quality

- The observed control composition passes [generation-workflow.md#interaction-encoding](generation-workflow.md#interaction-encoding), while its purpose, selection type, and feedback effect pass `pedagogy.md#interaction-design`.
- Under `disabled`, no `?[]` interaction control, learner-answer request, learner-answer variable, or answer-dependent branch is present.
- Interactions that are present are concrete and answerable.
- Interaction type matches the decision, and multi-select answers drive combined feedback, prioritization, or tailored examples rather than exhaustive branching for every combination.
- Learner-facing questions for question-bearing interactions appear before interaction syntax, not after `%{{var}}` inside `?[%{{var}} ...]`.
- Each `?[]` interaction appears on its own line.
- In standard non-slide-only teaching, each question-bearing `?[]` immediately follows an interaction-slide instruction that contains the complete learner-facing question as the slide's central content.
- An action-only control such as `?[Continue]` follows the content or instruction it advances and is not failed for lacking an invented question slide.
- A standard question-bearing interaction slide contains no option labels, input hint, simulated clickable control, or answer; the complete option set, order, and wording appears only in `?[]`.
- Input interactions put the specific question on the interaction slide and only the shorter `...` placeholder inside the control.
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

- Standard non-slide-only lessons follow the brief-lead-in → substantive-slide → concise-explanation rhythm in `pedagogy.md#visual-text-coordination` without imposing a word, sentence, or slide-count quota.
- The first standard slide is substantive, and no two standard slide directions appear back to back without the required concise explanation, interaction control, or immediate instructional effect between them.
- Presentation-worthy processes, relationships, comparisons, cases, decisions, core conclusions, key rules, important boundaries, interaction questions, and memorable quotations receive slides when they carry a teaching turn; merely mentioned or supporting instances do not trigger filler pages.
- Information identified by `density_cue` appears without compression in the same MarkdownFlow instruction block as its key-information slide direction, and related key information is grouped by theme instead of split into one slide per item or moved into a following standalone block.
- Every quotation explicitly designated as memorable by the source or author, including one identified by `quote_cue`, appears on a focused quote slide without unrelated points; in the authored Teaching Prompt, the complete quotation plus its existing attribution is wrapped inline with `===...===`, its exact wording and punctuation remain unchanged, and no missing attribution is invented.
- When a rendered preview or runtime output is observable, its quote text, punctuation, and existing attribution match the source byte for byte; any mismatch blocks completion. When rendered output is unavailable, the report records residual runtime fidelity risk and does not claim exact rendering was verified.
- A model-distilled takeaway is presented as a key conclusion rather than as a source quotation or fabricated quote.
- Supporting details, transitions, and repeated conclusions do not receive filler slides.
- Raw graphic source code appears only when explicitly requested, as required by [generation-workflow.md#image-authoring](generation-workflow.md#image-authoring).
- Pure classroom slides follow `generation-workflow.md#slide-only-generation-override` and are not failed for omitting AI narration or a full explanation paragraph.
- Every embedded asset uses the uploaded URL and manifest mapping defined by `cli/cli-reference.md#image-upload` and `cli/course-directory-spec.md#assets`.
- Every fixed-display or HTML-view image conforms to [generation-workflow.md#image-authoring](generation-workflow.md#image-authoring); the resulting URL, description, caption, position, and ordering survive generation and pass [Image Output Validation](generation-workflow.md#image-output-validation).
- Alt text and `图片内容` descriptions carry information about what the image conveys (no `image1` / `示意图`).
- In standard non-slide-only lessons, each selected slide is followed before the next slide by a concise but complete explanation that adds context (background / causality / examples), not just a restatement of the image.

## Runtime Stability

- MarkdownFlow syntax produces the observable runtime effects defined in `markdownflow.md`.
- Standalone single-line and complete multi-line deterministic forms are emitted without an LLM call; inline `===...===` preservation remains LLM-mediated as defined in `markdownflow.md#deterministic-blocks`.
- Preservation scope passes `optimization-workflow.md#preservation-decisions`.
- Code, image, and required source spans remain intact after the applicable preprocessing or generation behavior.

## Course Prompt

- A `course_prompt` artifact is produced when input includes course material.
- All six required canonical sections are present in order, with both headings and every section's instruction text rendered in `resolved_target_language`: Role, Task, Teaching Techniques, Writing Style, Format, and Slides.
- No `XXX` placeholder remains; every non-placeholder instruction from `course-prompt.md#fillable-template` is represented.
- The completed artifact passes `course-prompt.md#materialization-checks` and respects `prompt-contracts.md#artifact-responsibilities`.
- The Teaching Techniques and Slides sections preserve the template's deference to the current Teaching Prompt without introducing competing lesson pedagogy.
