# Teaching Prompt

Generate one runnable per-lesson Teaching Prompt from approved segments and design controls. This file materializes teaching decisions; it does not define pedagogy, MarkdownFlow runtime behavior, or image handling.

## Required References

- `language-policy.md`
- `prompt-contracts.md`
- `data-contracts.md#teaching-prompt-personalization-level`
- `data-contracts.md#lesson-schema`
- `data-contracts.md#generation-fallback-fields`
- `pedagogy.md`
- `markdownflow-authoring.md`

## Conditional References

- When an image asset must be understood, uploaded, embedded, or validated: `image-authoring.md`

## Generation

1. Select the teaching pattern that best fits the lesson's core question and source evidence. Preserve the pattern order defined in `pedagogy.md#teaching-patterns`; do not force every lesson into Evidence Chain.
2. Apply the normalized interaction policy without adding unselected purposes or blanket interactions.
3. Resolve the teaching objective, must-cover evidence and boundaries, required path, interaction purpose and visible effect, and required close from the approved lesson design.
4. Build one internal lesson execution plan from the approved design, selected pedagogy, delivery mode, and interaction policy without using the personalization level to decide its structure. Determine whether the current lesson is the first lesson of the first chapter from the approved course order, not from its lesson id, and apply `pedagogy.md#course-entry` only when it is. Resolve the ordered teaching actions, every required content position and effect, interaction and feedback adjacency, close, and, when slides are used, exact slide count and order. For standard one-on-one teaching and the standard teaching branch of combined delivery, except under an explicit text-only constraint, resolve the complete lead-in and visual-and-explanation cadence from `pedagogy.md#visual-text-coordination` at this step.
5. Apply the normalized `teaching_prompt_personalization_level` only to how much ordinary wording and example detail generation includes at each position in that plan through [Personalization Levels](#personalization-levels).
6. Materialize the plan as direct local instructions to the Teaching Agent in learner-time execution order. Source-only navigation comments may precede the runtime body and are removed before execution. Begin with the first teaching action for the selected delivery mode. At each position, combine the action with the content, relationship, boundary, or intended effect needed there; the resulting sequence and adjacency carry the lesson structure. When the level leaves ordinary expression open, write only those required runtime elements and end the instruction there.
7. Insert every selected interaction, deterministic block, required code or source span, and image instruction directly at its resolved learner-time position using its owning syntax. Express variable lifecycle through the MarkdownFlow control and schema fields; write only the feedback, branch, or carryover behavior the Teaching Agent performs into the Prompt body.
8. Apply [Author-Editable Layout](#author-editable-layout) after all teaching content and runtime syntax are resolved. This step changes only source formatting.
9. Apply `markdownflow-authoring.md` after those teaching decisions are complete.
10. Load `image-authoring.md` only when the lesson actually uses an image asset.

Every lesson must carry enough direction to run with the Course Prompt contributing course-wide role, general presentation requirements shared by every slide, and bounded cross-lesson personalization. Do not duplicate the learner-context strategy in each lesson or rely on the Course Prompt to supply, repair, or override lesson pedagogy, lesson-specific slide structure, or treatment tied to a particular slide position or teaching purpose.

Enough direction means that the ordered runtime instructions tell the Teaching Agent what to teach, show, ask, and respond at each point; why the required relationships and boundaries matter; what effect each interaction must have; and how the lesson completes. The selected personalization level decides how much ordinary learner-visible wording, already-required example identity and detail, transition wording, and feedback wording to include in those local instructions.

## Personalization Levels

Course Design Intake resolves one course-wide integer and passes it unchanged to every Teaching Prompt generated in that authoring run. Before applying it, resolve one internal lesson execution plan from the approved lesson design, selected pedagogy, delivery mode, and interaction policy. The plan includes the teaching sequence and the required presence, position, and teaching effect of titles, ordinary explanations, examples, transitions, interactions, images, feedback states, and the close. When slides are used, it also includes the exact slide count, each slide's ordinal position and teaching function, required content groups, visual hierarchy, and semantic layout.

Apply the level only while writing the local runtime instructions for that plan. A higher value writes less ordinary title, explanation, transition, example-detail, and non-deterministic feedback wording while retaining the concrete message, evidence, boundaries, selection constraints, and effect needed to execute each position. The shorter local instruction itself represents the open expression; no runtime sentence substitutes for the omitted wording or detail. Every level materializes the same teaching actions, slide order and grouping, interactions, images, feedback states, and close. The level adds no learner-context collection, interactions, variables, or branches. The level itself and this authoring rationale remain in the in-memory handoff.

| Level | Author-facing name | Teaching Prompt materialization |
| --- | --- | --- |
| `1` | High determinism | Write exact or near-final title wording, selected example details, ordinary explanations, transitions, and feedback wording into the corresponding runtime instructions. Permit only minor fluency or learner-context substitutions that preserve meaning. |
| `2` | Determinism-leaning | Write the main title wording, example identity and key details, principal explanation language, and required feedback points. Leave ordinary transition wording, secondary elaboration, incidental example details, and non-essential feedback phrasing unwritten. |
| `3` | Balanced | Write each title's communicative meaning, each required example's type and teaching point, all key definitions and conclusions, and each feedback response's required meaning and effect. Include ordinary explanation detail only where it is needed for reliable execution. |
| `4` | Personalization-leaning | Write each title's intent, must-cover points, each required example's selection constraints and intended takeaway, and the required feedback effect. Omit ordinary title, example-detail, explanation, transition, and feedback wording that is not needed to preserve those requirements. |
| `5` | High personalization | Write the concrete message and outcome for every teaching action, critical facts and boundaries, each required example's material requirements and intended takeaway, and feedback completion conditions and effects. Omit all other ordinary wording and example identity or detail. |

Levels `1` and `2` may produce near-final learner-visible delivery, but the artifact remains a Prompt rather than a mandatory spoken transcript. Levels `4` and `5` retain enough content and effect to execute without guessing; an empty outline such as "explain the concept", "add an example", or "ask a question" is incomplete.

### Cross-Level Constraints

The level changes only content-expression specificity. It does not change factual or source fidelity, the selected teaching pattern and loop, interaction policy, variable lifecycle, delivery mode, Course Prompt responsibility, or the internal lesson execution plan.

The actual ordered runtime instructions at every level implement the same structural decisions:

- the complete teaching sequence and the position and effect of every required teaching action;
- the exact slide count, slide order and placement in the teaching loop, each slide's teaching function, content grouping, visual hierarchy, and semantic layout; and
- whether and where titles, ordinary explanations, examples, transitions, interactions, images, feedback states, and the close appear. Every required action remains executable at every level. For a required example, only its permitted identity and details may vary; its required meaning and effect remain fixed.

Insert material selected for exact preservation directly at its resolved runtime position:

- the complete learner-facing interaction question, the `?[]` form, option wording and order, variable assignment and references, literal `UNKNOWN` behavior, and the selected feedback or branch effect;
- deterministic output and required code or fence structure;
- regulated wording, fixed numeric thresholds, and source spans already selected as immutable;
- wording or layout the author explicitly requires; and
- selected image URLs, alt or caption text, ordering, and form.

Apply each item through its owning MarkdownFlow authoring, source-preservation, or image-authoring reference at every level. A level changes ordinary expression only; exact material keeps its selected form and scope.

## Author-Editable Layout

Apply this source layout to every newly generated Teaching Prompt and whenever the user explicitly asks to rewrite a Teaching Prompt. Do not normalize an existing Prompt during an audit-only request, and do not backfill existing courses solely to adopt this layout.

Use two levels of localized, standalone HTML comments for navigation. Render the labels and values in `resolved_target_language`; for Simplified Chinese, use these exact shapes:

- `<!-- 教学阶段：<阶段名称> -->`
- `<!-- 教学块：<简短用途> -->`

Place one teaching-stage comment before the first block of each already-resolved stage, and place one teaching-block comment immediately before each smallest useful editing unit. These comments are source-only navigation removed by `markdownflow.md#preprocessing`; they do not count as runtime instructions. Group units without changing the selected teaching sequence:

- In standard visual-text teaching, make the lead-in one block, each visual-and-explanation pair one block, and each question instruction, interaction control, and immediate feedback sequence one block.
- In pure classroom slides, make each slide one block.
- Under an explicit text-only constraint, make each teaching action one block.

Write every ordinary Teaching Agent instruction as a top-level unordered-list item beginning with `-` followed by one space, with one teaching action per item. The list's source order remains the learner-time execution order. Use a flat list by default; use nested unordered lists only when the already-required content contains parallel subitems. Do not use an ordered list merely as layout. Preserve any required number, step label, or page number as content inside the applicable item or exact structure.

Keep these forms outside unordered-list markers so their syntax and exact content remain intact:

- standalone `?[]` interaction controls;
- standalone `===...===` lines and complete `!===...!===` fences;
- fenced code, Markdown image syntax, tables, and any other author- or source-required exact structure; and
- the teaching-stage and teaching-block HTML comments themselves.

Within an interaction block, keep the question instruction list item, standalone unchanged control, and immediate feedback list item adjacent. Insert no navigation comment between them.

Comments only name the existing stage or block purpose. Never put a fact, teaching requirement, variable or option, URL, command, exact source span, feedback rule, or branch rule only inside a comment. Removing every navigation comment must leave all previously required teaching content and runtime behavior complete and in the same order.

## Lesson Materialization

Each Teaching Prompt must:

- Begin its runtime body, after HTML comment removal, with an unordered-list instruction that produces the teaching-start behavior defined in `pedagogy.md#lesson-loop`.
- When it is the first lesson of the first chapter, materialize the applicable course-entry behavior from `pedagogy.md#course-entry` inside that first direct-teaching lead-in. Every later lesson omits the course greeting, course introduction, and teacher self-introduction.
- For standard one-on-one teaching and the standard teaching branch of combined delivery, except under an explicit text-only constraint, express the lesson as one brief learner-visible text lead-in followed by the ordered local instructions for at least one substantive visual-and-explanation pair. Place every explanation instruction before the next visual instruction and make the final explanation perform the close, exactly as defined in `pedagogy.md#visual-text-coordination`.
- Resolve exactly one core question through the selected teaching pattern.
- Make the teaching objective, must-cover facts and boundaries, and required explanatory relationships unambiguous at the specificity selected by the normalized personalization level.
- Use the interaction or non-interactive loop selected by the normalized policy.
- Preserve required source evidence and any downstream deliverable defined by the lesson design.
- Close with the summary, decision checkpoint, or action required by the selected pattern.
- Place each interaction's complete learner-facing question, unchanged `?[]` control, and immediate feedback instruction next to one another at the point where the interaction affects teaching.

Whenever a Teaching Prompt creates one or more slides, give slide 1 a clear cover-page visual treatment with lesson title and author information. Apply every other slide and explanation rule normally for the selected delivery mode.

For pure classroom slides, write the complete ordered sequence of direct slide-creation instructions needed by `pedagogy.md#visual-text-coordination`. Each instruction supplies that slide's required visible content, teaching function, content grouping, visual hierarchy, and semantic layout at the specificity selected by the personalization level. General slide presentation and delivery-mode behavior remain owned by `course-prompt.md`.

## Outputs

Produce one `lesson_teaching_prompts` item per lesson using `data-contracts.md#lesson-schema`. Apply `language-policy.md` to authored strings and preserve machine-facing values and immutable source spans.

Under fallback mode, add only the Generation extensions defined in `data-contracts.md#generation-fallback-fields`.

In the Generation report, identify the lesson and summarize generation status, execution mode, constraints, interaction count, and variables used. Report the results of [Validation](#validation). If issues remain, include blockers, suggestions, whether a rerun is needed, and upstream dependencies.

## Validation

- Every `teaching_prompt` is valid runnable MarkdownFlow.
- Every item passes `data-contracts.md#lesson-schema`.
- Every newly generated or explicitly rewritten Teaching Prompt follows [Author-Editable Layout](#author-editable-layout). Audit-only review of an existing Prompt does not add or normalize this layout.
- Teaching-stage and teaching-block comments are localized, standalone, placed only at resolved boundaries, and contain navigation text only. Strip them before validating runtime content; they cannot satisfy any teaching, interaction, variable, preservation, or close requirement.
- Every ordinary Teaching Agent instruction is a top-level list item beginning with `-` followed by one space in execution order, with nested unordered items used only for already-required parallel subitems. Interaction controls, deterministic forms, fenced code, images, tables, and other exact structures keep their owning syntax without an added list marker.
- The normalized personalization level is an integer from `1` through `5`, and the Teaching Prompt's content-expression specificity matches that level.
- The internal lesson execution plan is resolved before the level is applied. Recover the execution signature from the Teaching Prompt's actual ordered instructions and verify that it matches the plan: teaching actions, slide count and order, content grouping and hierarchy, interaction and feedback adjacency, images, and the close all occur at their resolved positions with their resolved effects.
- When multiple level variants are generated from the same approved design and controls, compare their actual ordered runtime instructions. They have identical execution signatures, including the presence, position, and teaching function of every required example; only ordinary content-expression specificity may differ.
- After ignoring navigation comments and ordinary-instruction list markers, the Teaching Prompt's non-formatting body begins with the first learner-time teaching instruction for the selected delivery mode, and every following instruction performs a learner-time teaching, presentation, interaction, feedback, or close function.
- Course-entry status is derived from the approved chapter and lesson order rather than a lesson-id pattern. In applicable delivery modes, the first lesson of the first chapter places its brief greeting, learner-centered course introduction, optional verified named-teacher introduction, learner hook, and lesson objective inside one lead-in before moving directly into teaching; later lessons do not repeat those elements. Pure classroom slides add no Teaching Agent greeting or self-introduction.
- In standard one-on-one teaching and the standard teaching branch of combined delivery, except under an explicit text-only constraint, the first instruction makes the first learner-visible block a brief text lead-in; the actual instruction sequence contains at least one substantive visual unit, no consecutive visual units, one concise but complete explanation after every visual and before the next, no unpaired learner-visible text turn after the lead-in, and a final explanation that also performs the close.
- A standard question-bearing interaction uses the question-only visual, unchanged `?[]` control, and immediate feedback or explanation sequence defined by `pedagogy.md#visual-text-coordination`; pure classroom slides and explicit text-only delivery retain their respective overrides.
- When a Teaching Prompt creates one or more slides, slide 1 has a clear cover-page visual treatment with lesson title and author information, and every other slide or explanation behavior follows the selected delivery mode's existing rules.
- In other delivery modes, the first instruction produces the applicable teaching-start behavior.
- The Teaching Prompt contains the selected teaching method and does not outsource pedagogy to the Course Prompt.
- The Teaching Prompt's actual slide instructions implement lesson-specific order, content, teaching function, and position- or purpose-specific treatment without restating the general presentation requirements that the Course Prompt applies to every slide.
- The objective, must-cover facts and boundaries, required sequence, interaction effect, and close are specific enough to execute without guessing.
- Levels `1` and `2` provide the requested near-final specificity without introducing unrequested typography, color, coordinates, animation, or deterministic markers.
- Levels `4` and `5` omit ordinary wording and example or feedback detail that the selected level leaves open while every required teaching action, content relationship, boundary, and effect remains executable in the actual instruction sequence.
- At levels `2` through `5`, open ordinary expression is visible as a shorter local instruction, not as a runtime explanation of who may choose or adapt the omitted wording, example identity or detail, transition, or feedback phrasing.
- Level `3` preserves the balanced division defined in the level table rather than silently behaving like either endpoint.
- Every item selected for exact preservation appears in its required form at its resolved runtime position at every level.
- Interaction and variable lifecycle decisions appear through their resolved MarkdownFlow syntax and schema fields; related Prompt prose performs only the required feedback, branch, or carryover behavior.
- No navigation comment interrupts a question instruction, unchanged `?[]` control, and immediate feedback sequence. Removing comments and ordinary-instruction list markers preserves the non-formatting text, exact structures, and their order.
- Interaction, variable, branch, and preservation encoding pass `markdownflow-authoring.md`.
- Image-specific validation runs only for lessons that use image assets.
- Authored human-facing content passes `language-policy.md`.
