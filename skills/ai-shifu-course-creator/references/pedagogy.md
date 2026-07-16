# Pedagogy

Authoritative source for **Teaching Prompt** pedagogy: interaction-policy effects, lesson loops and patterns, cognitive techniques, interaction and feedback choices, variable-persistence decisions, and pedagogical coordination between slides and text. Prompt audience, instruction voice, and second-person meaning are defined only in [prompt-contracts.md#prompt-semantics](prompt-contracts.md#prompt-semantics). MarkdownFlow syntax and runtime behavior are defined in [markdownflow.md](markdownflow.md), while structured fields and allowed values are defined in [data-contracts.md](data-contracts.md).

## Interaction Policy Precedence

Course Design Intake resolves the author's selection into one of the three modes below. This matrix is the authoritative definition of each mode's instructional effect and replacement behavior.

| Mode | Selection state | Instructional effect | Non-interactive alternative |
| --- | --- | --- | --- |
| `enabled` | One or more purposes selected | Execute interactions only at the selected-purpose placements. Selecting one purpose does not make other purposes or a blanket per-lesson interaction mandatory. | At unselected-purpose slots, use the relevant worked application, model-led demonstration, or consolidation. |
| `disabled` | The author explicitly selected no interactions | Use no learner interaction controls, solicit no learner answer, collect no learner-answer variables, and create no answer-dependent branch. | Use worked examples, model-led application, or consolidation wherever an interaction slot would otherwise appear. |
| `unspecified` | No explicit interaction choice | Add no interaction-policy requirement or override; apply the default teaching rules in this file as-is. | Use an alternative only when the applicable default teaching rule already calls for it. |

When the mode is `enabled`, selected purposes map to exactly these placements:

| Purpose | Placement | Instructional role |
| --- | --- | --- |
| `learner_context` | An early course or module point | Collect context that improves later teaching. |
| `pre_content_thinking` | Before the relevant explanation | Elicit an initial judgment that the explanation can refine. |
| `lesson_end_self_check` | At each lesson end | Let the learner check or consolidate the lesson's core understanding. |

A `disabled` lesson is not incomplete merely because it has no interaction. All non-interaction pedagogy rules remain active.

## Lesson Design

### Lesson Loop

Every lesson must satisfy one of these behavior-equivalent loops, as selected by the [Interaction Policy Precedence](#interaction-policy-precedence) matrix:

- **Default interactive loop**: setup → explanation → interaction → close.
- **Non-interactive loop**: setup → explanation → worked application or consolidation → close.

The default loop applies when `unspecified` leaves the baseline active or when an `enabled` purpose applies to the current lesson. The non-interactive loop applies under `disabled` and to an `enabled` lesson with no selected-purpose placement.

A lesson missing a phase required by its selected loop is incomplete. The following constraints apply to both loops:

- **One core question per lesson**: each lesson resolves exactly one teachable question.
- **Direct teaching start**: the first paragraph must establish a scenario, ask a guiding question, activate prior experience, state the task, or start a practice. Do not use a structural title, hierarchy label, ordering marker, or copied source heading as the opening.
- **Action tasks** must be immediately executable by the learner or explicitly linked to a downstream lesson; do not create orphan actions.
- **Carryover statements** are allowed only when cross-lesson dependency is explicitly permitted; otherwise remove them together with any unbound carryover variables.

### Teaching Patterns

Keep the three patterns and their step order. The interaction-policy matrix decides whether each pattern's interaction slot remains interactive or uses the corresponding non-interactive replacement:

| Pattern | Interaction slot | Non-interactive replacement |
|---|---|---|
| Pattern A: Evidence Chain | Step 4 learner interaction | Worked application |
| Pattern B: Misconception Repair | Step 4 interaction check | Worked boundary check |
| Pattern C: Comparison-Driven Learning | Step 1 baseline response capture | Worked baseline |

#### Pattern A: Evidence Chain

1. Observable phenomenon
2. Mechanism explanation
3. Practical implication
4. Learner interaction slot
5. Summary and action

#### Pattern B: Misconception Repair

1. Surface common misconception
2. Explain why it sounds plausible
3. Correct with mechanism and boundary
4. Interaction check slot
5. Apply corrected model to a real case

#### Pattern C: Comparison-Driven Learning

1. Baseline response-capture slot
2. Alternate scenario or constraint
3. Side-by-side interpretation
4. Updated decision path

### Cognitive Techniques

Increase learner understanding through targeted cognitive moves rather than information dumping. By default, each lesson should include at least one of these moves as a deepening interaction. The interaction-policy matrix determines its form: when the selected loop is non-interactive, express the move as a model-led demonstration, contrast, worked decision, or action synthesis without soliciting learner input.

When `pre_content_thinking` or `lesson_end_self_check` is selected and applies, use a calibration prompt, boundary check, or misconception correction as that interaction. A `learner_context` interaction is not forced into a different purpose merely to satisfy this rule.

1. **Calibration prompt** — Ask learners to make a concrete judgment before explanation.
2. **Boundary framing** — Clarify where the concept works and where it breaks.
3. **Counterintuitive contrast** — Introduce a surprising but valid case to deepen mental models.
4. **Action translation** — Turn conceptual understanding into an immediately executable step.
5. **Reflection loop** — Ask learners to compare current understanding with prior assumptions.

### Interaction Design

These are the teaching rules for permitted interactions. For interaction syntax, see [markdownflow.md#interactions](markdownflow.md#interactions); for branching runtime behavior, see [markdownflow.md#branching-on-user-input](markdownflow.md#branching-on-user-input).

- Include every selected-purpose placement at its defined scope.
- Interaction prompts must be concrete and directly answerable.
- Place interactions at decision points, not only at lesson start.
- Choose the interaction type by the learner decision:
  - Use single-select for mutually exclusive categories, path choices, viewpoint checks, or any interaction where one selected answer should drive a distinct branch.
  - Use multi-select for non-exclusive learner context, goals, interests, modules, blockers, scenarios, experience, or practice needs.
  - When the prompt means "which of these apply?", prefer multi-select unless the source or author explicitly limits the learner to one answer.
  - For multi-select, use combined feedback, prioritization, tailored examples, or coverage of selected items; do not require an exhaustive branch for every option combination.
- Before writing an interaction, decide whether its answer leaves the current lesson and apply [Variable Strategy](#variable-strategy).
- Every instructional interaction must trigger immediate feedback or a visible current-lesson effect, such as a branching explanation, tailored example, practice difficulty, feedback, summary, deliverable, or reflection.
- A viewpoint or path-choice interaction whose answer is meant to drive distinct next steps must branch by option. Use no more than one `viewpoint_check` per lesson unless justified.
- Avoid repetitive interaction semantics across lessons unless comparison intent is explicit.
- Use no more than five interactions per lesson.

### Variable Strategy

These are the teaching decisions for whether to collect an answer, how often to collect it, and how to ensure it matters. Variable syntax, substitution, and `UNKNOWN` runtime behavior are authoritative in [markdownflow.md#variables](markdownflow.md#variables); variable fields and naming constraints are authoritative in [data-contracts.md#variable-table](data-contracts.md#variable-table).

- Collection eligibility follows the interaction policy; `disabled` collects no learner-answer variables.
- Create a named variable only when the learner's answer must leave the current lesson: it is referenced by the [Course Prompt](course-prompt.md), reused in another lesson, or used for cross-lesson personalization, depth control, examples, summaries, or deliverable variation. Every named variable must have that course-level or cross-lesson utility; do not create throwaway variables for continue buttons, confirmations, or lesson-local choices.
- Use a no-variable interaction for lesson-local answers, including current-lesson branching, examples, feedback, summaries, deliverables, reflection, and free-text input.
- Reuse a global variable when possible. Do not recollect the same variable unless it is explicitly marked as a staged comparison, and prevent semantic duplicates even when names differ.

### Visual-Text Coordination

This section defines how slides and explanatory text divide teaching responsibility. Apply image embedding and runtime rules from [markdownflow.md#images](markdownflow.md#images), and use [generation-workflow.md#working-with-author-provided-images](generation-workflow.md#working-with-author-provided-images) for author-provided asset handling.

| Scenario | Authority and requirements |
|---|---|
| Standard non-slide-only teaching | Keep every core concept paired with a slide and textual explanation. The slide carries structural prompting; the text carries the complete explanation and remains understandable when the learner has not seen the slide. Pair each slide direction with a brief explanation of what it should convey. |
| Author-provided image file | Use the asset as part of the teaching explanation rather than as decoration. In standard teaching, follow it with the complete explanatory paragraph. If the course is slide-only, the next row overrides that paragraph requirement. |
| Pure slides | Follow the [Slide-Only Generation Override](generation-workflow.md#slide-only-generation-override). Produce concise, projection-ready slide content; do not require AI narration or a full standalone explanatory paragraph paired with every slide. |
