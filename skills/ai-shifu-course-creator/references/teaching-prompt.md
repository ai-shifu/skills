# Teaching Prompt

Generate one runnable per-lesson Teaching Prompt from approved segments and design controls. This file materializes teaching decisions and owns their source encoding; it does not define pedagogy, MarkdownFlow runtime behavior, or image handling.

## Required References

- `language-policy.md`
- `prompt-contracts.md`
- `data-contracts.md#teaching-prompt-personalization-level`
- `data-contracts.md#lesson-schema`
- `data-contracts.md#generation-fallback-fields`
- `data-contracts.md#variable-table`
- `pedagogy.md`
- `markdownflow.md`

## Conditional References

- When an image asset must be understood, uploaded, embedded, or validated: `image-authoring.md`
- When immutable source spans were selected for encoding: `source-preservation.md`

## Generation

1. Select the teaching pattern that best fits the lesson's core question and source evidence. Preserve the pattern order defined in `pedagogy.md#teaching-patterns`; do not force every lesson into Evidence Chain.
2. Apply the normalized interaction policy without adding unselected purposes or blanket interactions.
3. Resolve the teaching objective, must-cover evidence and boundaries, required path, interaction purpose and visible effect, and required close from the approved lesson design.
4. Build one internal lesson execution plan from the approved design, selected pedagogy, delivery mode, and interaction policy without using the personalization level to decide its structure. Determine whether the current lesson is the first lesson of the first chapter from the approved course order, not from its lesson id, and apply `pedagogy.md#course-entry` only when it is. Resolve the ordered teaching actions, every required content position and effect, interaction and feedback adjacency, close, and, when slides are used, exact slide count and order. For standard one-on-one teaching and the standard teaching branch of combined delivery, except under an explicit text-only constraint, resolve the complete lead-in and visual-and-explanation cadence from `pedagogy.md#visual-text-coordination` at this step.
5. Apply the normalized `teaching_prompt_personalization_level` only to how much ordinary wording and example detail generation includes at each position in that plan through [Personalization Levels](#personalization-levels).
6. Materialize the plan as direct local instructions to the Teaching Agent in learner-time execution order. Source-only navigation comments may precede the runtime body and are removed before execution. Begin with the first teaching action for the selected delivery mode. At each position, combine the action with the content, relationship, boundary, or intended effect needed there; the resulting sequence and adjacency carry the lesson structure. When the level leaves ordinary expression open, write only those required runtime elements and end the instruction there.
7. Insert every selected interaction, deterministic block, required code or source span, and image instruction directly at its resolved learner-time position using its owning syntax. Express variable lifecycle through the MarkdownFlow control and schema fields; write only the feedback, branch, or carryover behavior the Teaching Agent performs into the Prompt body.
8. Resolve whether [Author-Editable Layout](#author-editable-layout) applies and map the already-resolved teaching actions into its semantic editing units. This step changes only source formatting.
9. Serialize the complete Prompt through [Source Encoding](#source-encoding) after those teaching and layout decisions are complete.
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

This section owns when the source layout applies and how its editing units map to the already-resolved teaching structure. Apply it to every newly generated Teaching Prompt and whenever the user explicitly asks to rewrite a Teaching Prompt. Do not normalize an existing Prompt during an audit-only request, and do not backfill existing courses solely to adopt this layout.

Organize each Prompt with one source-only navigation comment for every smallest useful teaching block. Each comment summarizes only the immediate learner outcome of the block that follows. Use concise, freely worded text that lets an author understand the lesson's learning progression by scanning the comments alone, without requiring a label, prefix, punctuation pattern, numbering scheme, or sentence form. Make the outcome specific enough to distinguish the block from adjacent blocks. Generic text such as "Continue", "Teaching block", or "Explain content" is not useful navigation, and a description of what the Teaching Agent will do is not a learner outcome.

Group the blocks without changing the selected teaching sequence:

- In standard visual-text teaching, make the lead-in one block, each visual-and-explanation pair one block, and each question instruction, interaction control, and immediate feedback sequence one block.
- In pure classroom slides, make each slide one block.
- Under an explicit text-only constraint, make each primary teaching action together with its supporting details and subordinate actions one block.

Write every ordinary Teaching Agent instruction as an unordered-list item in learner-time execution order. Prefer a meaningful hierarchy whenever a teaching block has a primary action with one or more separable details or subordinate actions: state the primary action in a concise parent item, then place its required content, ordered substeps, parallel cases, comparisons, visual elements, constraints, or feedback variants in nested items. If a nested item owns distinct subparts, use another nested level. Within each parent, sibling order remains execution order. Start a new top-level item only for an independent action or when a syntax-owned or exact structure separates it from the prior parent, and keep an instruction flat only when it has no meaningful children or exact preservation prevents splitting. The hierarchy changes only source presentation; it never permits dropping, merging, rewriting, or reordering teaching content. Preserve any required number, step label, or page number as content.

Apply [Author-Editable Layout Encoding](#author-editable-layout-encoding) to serialize this resolved structure. That section owns the HTML comment wrapper, one-comment-per-block placement, list-marker syntax, syntax-owned structures that remain outside list items, interaction adjacency, and format-equivalence validation.

## Lesson Materialization

Each Teaching Prompt must:

- Place the teaching-start instruction's unordered-list item immediately after any leading navigation comments. No syntax-owned or exact structure occupies an earlier learner-time position. Its item text produces the teaching-start behavior defined in `pedagogy.md#lesson-loop`.
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

## Source Encoding

Encode the already-resolved lesson teaching, interaction, variable, preservation, and source-layout decisions into MarkdownFlow without changing their content or order. Parser recognition and runtime effects remain defined only in `markdownflow.md`.

### Author-Editable Layout Encoding

This section owns the exact source serialization of an already-resolved author-editable layout. Encode its teaching blocks and ordinary instructions without changing their content or order:

- Put exactly one standalone HTML comment immediately before each resolved teaching block using `<!-- ... -->`, with the already-resolved free-form learner outcome as its body. The wrapper is the only fixed form. Do not add a separate teaching-phase comment or require a label, prefix, punctuation pattern, numbering scheme, or sentence form. Do not reuse one comment for adjacent blocks or add more than one comment to a block.
- Do not place the literal delimiter sequences `<!--` or `-->` inside a comment body. Rephrase the learner outcome if either sequence would otherwise appear.
- Keep each comment concise and limited to its resolved learner outcome because `markdownflow.md#preprocessing` removes it before runtime.
- Encode each primary ordinary teaching action as a top-level unordered-list item beginning with `-` followed by one space. When it has separable supporting details, place them directly beneath it as nested unordered items, indenting each level by two additional spaces and using `-` followed by one space at every level.
- Prefer nested items over a long compound paragraph or a flat run of related items for required content, ordered substeps, parallel cases, comparisons, visual elements, constraints, and feedback variants. Use another level when a nested item itself owns multiple distinct subparts.
- Preserve sibling source order as execution order at every level. Nesting expresses ownership, not reordering. Start a sibling top-level item for an independent action or after a syntax-owned or exact structure that cannot belong inside the list; do not force an unrelated action under the prior parent merely to create nesting. Keep an item flat when it has no meaningful children or when splitting would alter preserved wording or structure.
- For an HTML-view image block, encode its ordinary insertion instruction as the top-level item and its already-required URL, image-content, caption, layout, ordering, and aspect-ratio fields as nested unordered items. Keep each URL on its own labeled nested line. Fixed-display image lines and other exact image structures remain unprefixed under the next rule.
- Treat unordered-list markers and their hierarchy as ordinary Markdown in the content sent to the Teaching Agent; MarkdownFlow preprocessing does not remove them.
- Do not prefix or newly indent standalone `?[]` controls, standalone `===...===` lines, complete `!===...!===` fences, fenced code, Markdown images, tables, or another exact structure merely to fit the list hierarchy.
- When source-required or learner-visible Markdown list markers are exact content, preserve their markers and indentation unchanged and do not treat them as author-editable layout markers.
- Put a block comment before an interaction's question instruction, then keep the question list item, unchanged standalone control, and feedback list item together with no intervening comment.
- A comment may repeat concepts already present in its block to make the outcome recognizable, but keep every fact, teaching requirement, variable, option, URL, command, exact span, feedback rule, and branch rule outside the comments. For a validation-only content-equivalence comparison, removing comments plus only the unordered-list markers and indentation introduced by Author-Editable Layout must preserve the non-formatting text and its order; source-required list markers remain content. This comparison is not runtime preprocessing.

### Interaction Encoding

- Encode the complete learner-facing question in the block immediately before every question-bearing interaction control, and put the unchanged `?[]` control on its own line.
- In standard one-on-one teaching and the standard teaching branch of combined delivery, except under an explicit text-only constraint, make that preceding block a question-only visual instruction and place the control immediately after it. Make the complete question the visual's central content, without option labels, input hints, simulated controls, or answers. Pure classroom slides retain their projection behavior, and explicit text-only delivery uses ordinary question text as the preceding block, as defined in `pedagogy.md#visual-text-coordination`.
- Keep only option labels, the optional `%{{name}}` assignment prefix, and any free-text marker plus short hint inside `?[]`.
- For an action-only control such as `?[Continue]`, do not invent a learner question or question slide; put the control on its own line after the content or instruction it advances.
- Use `|` for single-select, `||` for multi-select, and `...` immediately before the input hint or custom-answer label.
- Use `%{{name}}` only when the answer must leave the current lesson. Lesson-local answers use the no-variable form; a blank variable name is invalid.
- For input interactions, use a specific question in the preceding block and a shorter hint after `...` in the control; in standard visual-text delivery, that preceding block is the question-only visual. For select-plus-input, put `...` at the start of the custom-answer option.
- Keep the complete option set, order, and wording only in the interaction control. In the standard visual-text scope, do not duplicate those labels on the question-only visual.
- After the control, encode the feedback or visible instructional effect selected by `pedagogy.md#interaction-design`.

Standard visual-text example:

The two comments below deliberately use different sentence forms; neither is a template. The list hierarchy separates requirements that were previously combined without adding a teaching action or changing its effect.

```markdown
<!-- The learner can choose a path that fits the current case -->

- Create a question-only slide.
  - Make "Which path best matches the current case?" its complete central question.
  - Do not show option labels, simulated controls, or the answer.

?[Path A | Path B]

- After the learner answers:
  - Explain the selected path.
  - Contrast it with the other path.

<!-- A course-wide goal is ready to guide later examples and emphasis -->

- Create a question-only slide.
  - Make "What course-wide goal should later lessons use?" its complete central question.
  - Do not show an input hint or simulated input field.

?[%{{learning_goal}} ...One-sentence goal]

- After the learner responds:
  - Acknowledge the goal.
  - Explain that later lessons will use it to adapt examples and emphasis.
```

### Variable and Branch Encoding

- Write branch behavior as natural-language instructions; MarkdownFlow has no programmatic conditional syntax.
- Refer to lesson-local answers naturally rather than inventing a variable.
- For a named value, first bind the substituted value in a natural sentence such as `The learner goal is {{learning_goal}}.`, then describe branches against that value.
- When a named value can be read before collection, branch on the literal substituted value `UNKNOWN`; do not test readiness or marker existence.
- Every named learner-answer reference must have a matching variable-backed collection and pass `data-contracts.md#variable-table`.
- Compose newly authored variable names under `language-policy.md` using only letters, numbers, and underscores. Preserve existing names when changing them would break the contract.

### Preservation Encoding

When immutable source spans were selected, load `source-preservation.md` and encode only those spans:

- Put a complete standalone single-line span that must bypass the Teaching Agent inside `===...===`.
- Put a complete multi-line span that must bypass the Teaching Agent inside `!===...!===`; include the full code fence and language tag when exact fenced output is required.
- In otherwise generated content, wrap only the position- and formatting-sensitive span inline with `===...===`. Inline preservation remains mediated by the Teaching Agent and may be translated.
- Encode each selected span independently and leave adaptive content outside deterministic markers.

Image composition is owned by `image-authoring.md` and is loaded conditionally by the selected workflow.

## Outputs

Produce one `lesson_teaching_prompts` item per lesson using `data-contracts.md#lesson-schema`. Apply `language-policy.md` to authored strings and preserve machine-facing values and immutable source spans.

Under fallback mode, add only the Generation extensions defined in `data-contracts.md#generation-fallback-fields`.

In the Generation report, identify the lesson and summarize generation status, execution mode, constraints, interaction count, and variables used. Report the results of [Validation](#validation). If issues remain, include blockers, suggestions, whether a rerun is needed, and upstream dependencies.

## Validation

- Every `teaching_prompt` is valid runnable MarkdownFlow.
- Every item passes `data-contracts.md#lesson-schema`.
- Every newly generated or explicitly rewritten Teaching Prompt follows [Author-Editable Layout](#author-editable-layout). Audit-only review of an existing Prompt does not add or normalize this layout.
- When [Author-Editable Layout](#author-editable-layout) applies, every smallest useful teaching block has exactly one navigation comment whose freely worded text states only its immediate, specific learner outcome. Scanning the comments in source order reveals the lesson's learning progression, with no separate teaching-stage comments. The blocks retain their resolved grouping and execution order. Each block's primary teaching action is a top-level unordered-list item; separable supporting details and subordinate actions use nested unordered items wherever content and preservation allow; independent actions and actions separated by syntax-owned or exact structures remain top-level siblings.
- The normalized personalization level is an integer from `1` through `5`, and the Teaching Prompt's content-expression specificity matches that level.
- The internal lesson execution plan is resolved before the level is applied. Recover the execution signature from the Teaching Prompt's actual ordered instructions and verify that it matches the plan: teaching actions, slide count and order, content grouping and hierarchy, interaction and feedback adjacency, images, and the close all occur at their resolved positions with their resolved effects.
- When multiple level variants are generated from the same approved design and controls, compare their actual ordered runtime instructions. They have identical execution signatures, including the presence, position, and teaching function of every required example; only ordinary content-expression specificity may differ.
- The first learner-time position is the ordinary teaching-start instruction, and no syntax-owned or exact structure occupies an earlier learner-time position. Every following instruction performs a learner-time teaching, presentation, interaction, feedback, or close function.
- When [Author-Editable Layout](#author-editable-layout) applies, the first remaining block after MarkdownFlow strips navigation comments is that instruction's unordered-list item.
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
- When [Author-Editable Layout](#author-editable-layout) applies, its layout encoding passes [Source Encoding Validation](#source-encoding-validation). Interaction, variable, branch, and preservation encoding pass that validation in every Teaching Prompt, including an audit-only existing Prompt whose layout check is `not-assessed`.
- Image-specific validation runs only for lessons that use image assets.
- Authored human-facing content passes `language-policy.md`.

### Source Encoding Validation

- When the Teaching Prompt layout applies, every resolved teaching block has exactly one standalone outcome comment immediately before it. Each block's primary teaching action uses a top-level unordered-list marker; separable supporting details and subordinate actions use nested unordered items with two additional spaces per level whenever a meaningful hierarchy is available; independent actions and actions separated by syntax-owned or exact structures remain top-level siblings; and every syntax-owned or exact structure remains unprefixed, receives no new indentation, and stays unchanged.
- Every navigation comment body contains neither `<!--` nor `-->`, so preprocessing removes the complete comment without leaking source text into runtime content.
- Every interaction control is on its own line and matches the preceding question or options. Standard question-bearing controls immediately follow their question-only visual instructions and precede their feedback or explanatory effects.
- No navigation comment interrupts an interaction's question instruction, control, and feedback sequence.
- In the validation-only content-equivalence comparison, removing navigation comments plus only the unordered-list markers and indentation introduced by Author-Editable Layout preserves all non-formatting text and its order. Source-required list markers and indentation remain unchanged content.
- Every named variable passes collection, reference, and metadata invariants.
- Branch instructions use natural language and literal `UNKNOWN` where required.
- Each immutable span uses the runtime form matching its selected preservation scope.
