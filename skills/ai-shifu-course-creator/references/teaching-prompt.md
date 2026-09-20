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

### Workflow

When a finalized internal lesson execution plan is supplied, retain it unchanged and start at step 3. Its teaching decisions, including whether an example or analogy is needed and whether an existing demonstration already suffices, are inputs to materialization. Do not reselect teaching aids, replace approved demonstrations, or rebuild the plan. If a supplied plan has a gap that requires changing its teaching actions, report that unresolved design dependency through [Outputs](#outputs) instead of silently repairing the plan during generation.

When only approved segments and design controls are supplied, resolve the missing plan locally with steps 1 and 2, then continue at step 3; a separate orchestration run is not required.

1. Resolve the lesson's teaching decisions from the approved design:
   - Select the pattern that best fits the core question and source evidence, preserving the order in `pedagogy.md#teaching-patterns` rather than forcing Evidence Chain.
   - Apply the normalized interaction policy without adding unselected purposes or blanket interactions.
   - Resolve the objective, must-cover evidence and boundaries, required path, interaction purpose and visible effect, and close.
   - Select examples and analogies for the comprehension needs identified under `pedagogy.md#examples-and-analogies`, including any source example or demonstration that already meets the need.
2. Build one internal lesson execution plan before applying the personalization level:
   - Determine course-entry status from the approved chapter and lesson order rather than the lesson id.
   - Resolve every teaching action, content position and effect, interaction and feedback adjacency, close, and any slide count and order.
   - Fix each selected example's or analogy's position, purpose, essential conditions or explanatory relationships, necessary limits, and takeaway before applying the personalization level.
   - For standard visual-text teaching, resolve the complete lead-in and visual-and-explanation cadence from `pedagogy.md#visual-text-coordination`.
3. Materialize that plan through [Lesson Materialization](#lesson-materialization), applying [Personalization Levels](#personalization-levels) only while writing ordinary local instructions.
4. Insert each selected interaction, deterministic block, required code or source span, and image instruction at its resolved learner-time position using its owning syntax:
   - Load `image-authoring.md` before composing an image instruction, and only when the lesson uses an image asset.
   - Represent variable lifecycle through MarkdownFlow controls and schema fields; Prompt prose carries only the required feedback, branch, or carryover behavior.
5. When [Author-Editable Layout](#author-editable-layout) applies, map the resolved actions into its semantic editing units without changing teaching content or order.
6. Serialize the result through [Source Encoding](#source-encoding), then produce [Outputs](#outputs) and run [Validation](#validation).

### Lesson Materialization

- Give every lesson enough direct local instruction to run while the Course Prompt supplies only the course-wide role, presentation requirements shared by every slide, and bounded cross-lesson personalization.
  - Tell the Teaching Agent what to teach, show, ask, and respond at each point; why required relationships and boundaries matter; what effect each interaction has; and how the lesson completes.
  - Do not duplicate the learner-context strategy in each lesson or rely on the Course Prompt to supply, repair, or override lesson pedagogy, lesson-specific slide structure, or treatment tied to a particular slide position or teaching purpose.
- Materialize the complete lesson:
  - Resolve exactly one core question through the selected teaching pattern.
  - Make the objective, must-cover facts and boundaries, and required explanatory relationships unambiguous at the selected personalization level.
  - Use the interaction or non-interactive loop selected by the normalized policy.
  - Preserve required source evidence and any downstream deliverable defined by the lesson design.
  - Close with the summary, decision checkpoint, or action required by the selected pattern.
- Begin at the correct learner-time position:
  - Place the teaching-start instruction's unordered-list item immediately after any leading navigation comments; no syntax-owned or exact structure occupies an earlier learner-time position.
  - Make that item produce the teaching-start behavior in `pedagogy.md#lesson-loop`.
  - In the first lesson of the first chapter, include `pedagogy.md#course-entry` in that first direct-teaching lead-in. Later lessons omit the course greeting, course introduction, and teacher self-introduction.
- Apply the selected delivery mode:
  - In standard one-on-one teaching and the standard teaching branch of combined delivery, except under an explicit text-only constraint, use one brief learner-visible text lead-in followed by at least one substantive visual-and-explanation pair. Put each explanation before the next visual and make the final explanation perform the close, as defined in `pedagogy.md#visual-text-coordination`.
    - A syntax-owned or exact structure at a resolved position does not replace the paired explanation. Keep any such structure before that explanation when it belongs between a visual and its explanation, and leave no learner-visible block after the final closing explanation.
  - Whenever slides are created, give slide 1 a clear cover-page visual treatment with lesson title and author information.
    - Apply that treatment to the already-resolved first slide without adding a teaching action or changing the plan's slide count or order.
    - Apply every other slide and explanation rule normally for the selected delivery mode.
  - For pure classroom slides, write the complete ordered sequence of direct slide-creation instructions required by `pedagogy.md#visual-text-coordination`. Give each slide its required visible content, teaching function, content grouping, visual hierarchy, and semantic layout at the selected personalization level. General slide presentation and delivery-mode behavior remain owned by `course-prompt.md`.
  - In other delivery modes, begin with their applicable teaching-start behavior.
- At each interaction, keep the complete learner-facing question, unchanged `?[]` control, and immediate feedback instruction together where the answer affects teaching.

### Personalization Levels

- Course Design Intake resolves one course-wide `teaching_prompt_personalization_level` integer.
  - Pass it unchanged to every Teaching Prompt in the authoring run.
  - Keep the level and its authoring rationale only in the in-memory handoff.
- Apply the level only while writing ordinary instructions for the already-fixed execution plan.
  - A higher value predetermines less ordinary title, explanation, transition, example-detail, and non-deterministic feedback wording while retaining the message, evidence, boundaries, selection constraints, and effect required at every position.
  - When the level leaves ordinary expression open, write only the required runtime elements and end the instruction there; never add runtime prose announcing that wording, examples, transitions, or feedback were omitted, left open, adaptable, or not prewritten.
- At every level, use relevant explicitly stated learner context already available during authoring to materialize the selected examples and analogies under `pedagogy.md#examples-and-analogies`. Lower levels prewrite a fitting concrete scenario; higher levels carry its relevant selection constraints into the local teaching action so learner-time context can guide the remaining choices. If individual context is unavailable during authoring, use the shared course-appropriate default rather than assuming a future learner identity. The level changes prescription, not whether known relevant context matters.

| Level | Author-facing name | Teaching Prompt materialization |
| --- | --- | --- |
| `1` | High determinism | Write exact or near-final title wording, selected example details, ordinary explanations, transitions, and feedback wording into the corresponding runtime instructions. For selected examples and analogies, prewrite the concrete situation, key conditions, explanatory relationships, and necessary limits using relevant known background. Permit only minor fluency or learner-context substitutions that preserve meaning. |
| `2` | Determinism-leaning | Write the main title wording, example or analogy identity, key conditions and correspondences, necessary limits, intended takeaway, principal explanation language, and required feedback points. Leave ordinary transition wording, secondary elaboration, incidental scenario details, and non-essential feedback phrasing unwritten. |
| `3` | Balanced | Write each title's communicative meaning, each required example's or analogy's scenario type, selection conditions, teaching point, essential relationships and necessary limits, all key definitions and conclusions, and each feedback response's required meaning and effect. Include ordinary explanation detail only where it is needed for reliable execution; leave incidental identities and scenario details unwritten. |
| `4` | Personalization-leaning | Write each title's intent, must-cover points, each required example's or analogy's comprehension need, background-relevant selection constraints, essential relationships, necessary limits and intended takeaway, and the required feedback effect. Omit concrete scenario identity and ordinary title, example-detail, explanation, transition, and feedback wording that is not needed to preserve those requirements. |
| `5` | High personalization | Write the concrete message and outcome for every teaching action, critical facts and boundaries, each required example's material requirements and intended takeaway, the essential conditions or explanatory relationships, necessary limits and completion criteria for every selected example or analogy, and feedback completion conditions and effects. Omit all other ordinary wording and example identity or detail, including the concrete analogy source situation. |

- Levels `1` and `2` may produce near-final learner-visible delivery, but the artifact remains a Prompt rather than a mandatory spoken transcript.
- Levels `4` and `5` must still be executable without guessing; an empty outline such as "explain the concept", "add an example", or "ask a question" is incomplete.

#### Cross-Level Constraints

- Every level preserves factual and source fidelity, the selected teaching pattern and loop, interaction policy, variable lifecycle, delivery mode, Course Prompt responsibility, and internal lesson execution plan.
- Every level has the same execution signature:
  - The complete teaching sequence and each required action's position and effect.
  - The exact slide count, order, placement, teaching function, content grouping, visual hierarchy, and semantic layout.
  - The presence and position of titles, explanations, examples, analogies, transitions, interactions, images, feedback states, and the close. A required example's permitted identity or details may vary, but its required meaning and effect do not. The same applies to an analogy's source situation: its required explanatory relationships and necessary limits remain fixed.
- The level adds no learner-context collection, interactions, variables, or branches.
- Insert exact material at its resolved runtime position at every level:
  - The complete interaction question, `?[]` form, option wording and order, variable assignments and references, literal `UNKNOWN` behavior, and selected feedback or branch effect.
  - Deterministic output and required code or fence structure.
  - Regulated wording, fixed numeric thresholds, and immutable source spans.
  - Wording or layout explicitly required by the author.
  - Selected image URLs, alt or caption text, ordering, and form.
- Apply exact material through its owning MarkdownFlow, source-preservation, or image-authoring reference. Personalization changes ordinary expression only.

### Author-Editable Layout

- Apply this source layout to every newly generated Teaching Prompt and whenever the user explicitly requests a rewrite.
  - Do not normalize an existing Prompt during an audit-only request.
  - Do not backfill existing courses solely to adopt the layout.
- Organize each Prompt with one source-only navigation comment for every smallest useful teaching block.
  - Name the immediate change in understanding, judgment, capability, or next-step readiness established by the following block.
  - Use concise result phrases with natural wording and varied openings across adjacent comments.
  - Give each result enough specificity to distinguish it from neighboring blocks and reveal the learning progression when the comments are scanned together.
  - Choose the label, prefix, punctuation, numbering, and sentence form that makes each result easiest to scan.
- Map one block to each smallest useful editing unit without changing the teaching sequence:
  - Standard visual-text teaching:
    - Keep the lead-in in one block.
    - Keep each visual and its immediately following complete explanation in one block under one comment.
    - Keep each question instruction, interaction control, and immediate feedback sequence in one block under one comment.
  - Pure classroom slides: each slide.
  - Explicit text-only delivery: each primary teaching action together with its supporting details and subordinate actions.
- Write ordinary Teaching Agent instructions as unordered-list items in learner-time execution order.
  - Use a concise parent item for the primary action and nested items for separable teaching purpose, title intent, required content, ordered substeps, parallel cases, comparisons, visual elements, constraints, or feedback variants.
  - Add another nested level when a child owns distinct subparts; sibling order remains execution order at every level.
  - Start a top-level sibling for an independent action or after a syntax-owned or exact structure. Keep an item flat when it has no meaningful children or exact preservation prevents splitting.
  - Preserve required numbers, step labels, and page numbers as content. Hierarchy changes only source presentation and never permits dropping, merging, rewriting, or reordering teaching content.
- Apply [Layout Encoding](#layout-encoding) after these editing units and relationships are resolved.

## Source Encoding

Encode the already-resolved lesson teaching, interaction, variable, preservation, and source-layout decisions into MarkdownFlow without changing their content or order. Parser recognition and runtime effects remain defined only in `markdownflow.md`.

### Layout Encoding

Encode the already-resolved author-editable layout without changing teaching content or order:

- Put exactly one standalone `<!-- ... -->` comment immediately before each resolved teaching block; do not reuse a comment across blocks or add another navigation comment to a block.
  - Put the resolved free-form result text inside the wrapper without rewriting it; the wrapper is the only fixed form.
  - Keep the body concise because `markdownflow.md#preprocessing` removes it before runtime.
  - If the body would contain the literal delimiter `<!--` or `-->`, rephrase the outcome.
- Encode each primary ordinary action as a top-level item beginning with `-` followed by one space.
  - Put supporting details directly beneath it, indenting every nested level by two additional spaces and using `-` followed by one space at every level.
  - Preserve sibling source order as execution order. Nesting expresses ownership, not reordering.
  - Keep independent actions or actions after syntax-owned or exact structures as top-level siblings; do not force an unrelated action beneath the prior parent.
- For an HTML-view image block, use the ordinary insertion instruction as the top-level item and nest its already-required position, URL, image-content, caption, layout, ordering, and aspect-ratio fields beneath it. Keep each URL on its own labeled nested line.
- Keep syntax-owned and exact structures intact:
  - Treat layout list markers and hierarchy as ordinary Markdown sent to the Teaching Agent; MarkdownFlow preprocessing does not remove them.
  - Do not prefix or newly indent standalone `?[]` controls, standalone `===...===` lines, complete `!===...!===` fences, fenced code, Markdown images, tables, fixed-display image lines, or another exact structure merely to fit the hierarchy.
  - Preserve source-required or learner-visible Markdown list markers and indentation unchanged; do not treat them as layout markers.
- Put the block comment before an interaction's question instruction, then keep the question item, unchanged standalone control, and feedback item together with no intervening comment.
- Keep comments navigational rather than authoritative:
  - They may repeat concepts from the block so its outcome is recognizable.
  - Keep every fact, teaching requirement, variable, option, URL, command, exact span, feedback rule, and branch rule outside them.
- For validation only, removing navigation comments plus only the list markers and indentation introduced by Author-Editable Layout must preserve all non-formatting text and its order. Source-required list markers remain content; this comparison is not runtime preprocessing.

### Interaction Encoding

- For every question-bearing interaction:
  - Put the complete learner-facing question in the immediately preceding block and the unchanged `?[]` control on its own line.
  - In standard one-on-one teaching and the standard teaching branch of combined delivery, except under an explicit text-only constraint, make that block a question-only visual whose central content is the complete question. Put no option labels, input hints, simulated controls, or answers on it. Pure classroom slides retain projection behavior; explicit text-only delivery uses ordinary question text, as defined in `pedagogy.md#visual-text-coordination`.
  - Keep the complete option set, order, and wording only in the control; the control may also contain an optional `%{{name}}` assignment and a free-text marker with its short hint.
  - For input, use a specific preceding question and a shorter hint after `...`; for select-plus-input, put `...` at the start of the custom-answer option.
  - Follow the control with the feedback or visible instructional effect selected by `pedagogy.md#interaction-design`.
- For an action-only control such as `?[Continue]`, add no invented learner question or question slide; put it on its own line after the content or instruction it advances.
- Encode control behavior exactly:
  - Use `|` for single-select, `||` for multi-select, and `...` immediately before the input hint or custom-answer label.
  - Use `%{{name}}` only when the answer must leave the current lesson. Lesson-local answers use the no-variable form; a blank name is invalid.

#### Example

The comments demonstrate free-form variation through a noun phrase and a result clause. The hierarchy separates existing requirements without adding or changing a teaching action.

```markdown
<!-- A fitting path for the current case -->

- Create a question-only slide.
  - Make "Which path best matches the current case?" its complete central question.
  - Do not show option labels, simulated controls, or the answer.

?[Path A | Path B]

- After the learner answers:
  - Explain the selected path.
  - Contrast it with the other path.

<!-- One course-wide goal now guides later examples and emphasis -->

- Create a question-only slide.
  - Make "What course-wide goal should later lessons use?" its complete central question.
  - Do not show an input hint or simulated input field.

?[%{{learning_goal}} ...One-sentence goal]

- After the learner responds:
  - Acknowledge the goal.
  - Explain that later lessons will use it to adapt examples and emphasis.
```

### Variable and Branch Encoding

- Write branch behavior as natural-language instructions because MarkdownFlow has no programmatic conditional syntax.
- Keep lesson-local answers unnamed and refer to them naturally.
- Let the interaction control and schema show whether a value is named; do not explain that encoding decision in Prompt prose.
- For a named value:
  - Bind the substituted value first in a natural sentence such as `The learner goal is {{learning_goal}}.`, then describe branches against it.
  - When it can be read before collection, branch on literal `UNKNOWN`; do not test readiness or marker existence.
  - Require a matching variable-backed collection and the metadata in `data-contracts.md#variable-table` for every learner-answer reference.
  - Compose new names under `language-policy.md` with letters, numbers, and underscores only. Preserve existing names when changing them would break references.

### Preservation Encoding

When immutable source spans were selected, load `source-preservation.md` and encode only those spans:

- Put a complete standalone single-line span that must bypass the Teaching Agent inside `===...===`.
- Put a complete multi-line span that must bypass the Teaching Agent inside `!===...!===`; include the full code fence and language tag when exact fenced output is required.
- In otherwise generated content, wrap only the position- and formatting-sensitive span inline with `===...===`. Inline preservation remains mediated by the Teaching Agent and may be translated.
- Encode each selected span independently and leave adaptive content outside deterministic markers.

Image composition is owned by `image-authoring.md` and is loaded conditionally by the selected workflow.

## Outputs and Validation

### Outputs

- Produce one `lesson_teaching_prompts` item per lesson using `data-contracts.md#lesson-schema`.
  - Apply `language-policy.md` to authored strings.
  - Preserve machine-facing values and immutable source spans.
- In fallback mode, add only the Generation extensions in `data-contracts.md#generation-fallback-fields`.
- In the Generation report:
  - Identify the lesson and summarize generation status, execution mode, constraints, interaction count, and variables used.
  - Report [Validation](#validation).
  - If issues remain, include blockers, suggestions, whether a rerun is needed, and upstream dependencies.

### Validation

- Validate the artifact and its ownership boundaries:
  - Every `teaching_prompt` is runnable MarkdownFlow, every item passes `data-contracts.md#lesson-schema`, and authored human-facing content passes `language-policy.md`.
  - The Prompt contains the selected teaching method and locally executable objective, facts and boundaries, sequence, interaction effect, and close rather than outsourcing pedagogy to the Course Prompt.
  - Slide instructions contain lesson-specific order, content, teaching function, and position- or purpose-specific treatment without restating general presentation requirements owned by the Course Prompt.
- Validate the lesson execution:
  - When a finalized plan was supplied, compare the generated artifact with that original plan, not a replacement plan inferred or rebuilt during generation.
  - The internal execution plan is resolved before personalization. Its recovered signature matches the actual instruction order, actions, slide count and order, content grouping and hierarchy, interaction and feedback adjacency, images, and close.
  - The first learner-time position is the ordinary teaching-start instruction; no syntax-owned or exact structure precedes it, and every later instruction performs a teaching, presentation, interaction, feedback, or close function.
  - After MarkdownFlow removes navigation comments from an author-editable layout, the first remaining block is that instruction's unordered-list item.
  - Course-entry status comes from approved course order. The first applicable lesson keeps its greeting, learner-centered course introduction, optional verified named-teacher introduction, learner hook, and objective in one lead-in; later lessons do not repeat them, and pure classroom slides add no Teaching Agent greeting or self-introduction.
  - Standard visual-text delivery begins with a brief text lead-in, contains at least one substantive visual, never places visuals consecutively or delays their explanations, has no unpaired learner-visible text after the lead-in, and makes the final concise but complete explanation perform the close.
    - Exact or syntax-owned structures do not replace a paired explanation or follow the final closing explanation.
  - A standard question-bearing interaction follows the question-only visual, unchanged `?[]` control, and immediate feedback or explanation sequence in `pedagogy.md#visual-text-coordination`; pure slides and explicit text-only delivery retain their overrides.
  - When slides exist, slide 1 has a clear cover-page treatment with lesson title and author information, and every other slide or explanation behavior follows the selected delivery mode's existing rules.
  - Other delivery modes begin with their applicable teaching-start behavior.
- Validate personalization:
  - The normalized level is an integer from `1` through `5`, and ordinary content-expression specificity matches it.
  - Multiple variants of the same approved plan have identical execution signatures, including every required example's presence, position, and teaching function; only permitted ordinary expression differs.
  - Levels `1` and `2` provide near-final specificity without unrequested typography, color, coordinates, animation, or deterministic markers.
  - Levels `4` and `5` omit permitted ordinary wording and detail while every required action, relationship, boundary, and effect remains executable.
  - At levels `2` through `5`, open expression appears as a shorter local instruction rather than runtime prose about wording or detail being chosen, adapted, omitted, left open, or not prewritten. Level `3` retains its balanced division.
  - Every exact item remains in its required form, scope, and runtime position at every level.
- Validate source encoding:
  - New and explicitly rewritten Prompts apply [Author-Editable Layout](#author-editable-layout); audit-only review of an existing Prompt does not add or normalize it.
  - Layout, interaction, variable, branch, and preservation encoding pass [Encoding Checks](#encoding-checks). In an audit-only existing Prompt, layout checks are `not-assessed` while observable runtime encoding is still checked.
  - Interaction and variable lifecycle decisions appear through their resolved MarkdownFlow syntax and schema fields; Prompt prose performs only required feedback, branch, or carryover behavior.
- Run image-specific validation only when the lesson uses image assets.

#### Encoding Checks

- When Author-Editable Layout applies:
  - Every resolved block has exactly one standalone outcome comment immediately before it, so the number and order of navigation comments match the resolved teaching blocks.
  - Comments use concise, naturally varied result phrases that keep adjacent results immediately distinguishable and make the learning progression scannable.
  - Each primary action is a top-level unordered-list item; meaningful supporting details use nested items indented by two additional spaces per level; independent or syntax-separated actions remain top-level siblings.
  - Syntax-owned and exact structures remain unprefixed, receive no new indentation, and stay unchanged.
  - Every comment body excludes `<!--` and `-->`, allowing preprocessing to remove the complete comment without leaking source text.
  - Removing comments plus only layout-introduced list markers and indentation preserves all non-formatting text and its order; source-required list syntax remains unchanged content.
- Every interaction control is on its own line and matches the preceding question or options. A standard question-bearing control immediately follows its question-only visual and precedes its feedback or explanatory effect, with no navigation comment inside that sequence.
- Every named variable passes collection, reference, and metadata invariants.
- Branch instructions use natural language and literal `UNKNOWN` where required.
- Each immutable span uses the runtime form matching its selected preservation scope.
