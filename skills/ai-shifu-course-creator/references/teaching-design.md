# Teaching Design Options

Teaching approaches available to the authoring agent. Choose, adapt, combine, or replace them for the audience, source, objectives, and author requirements. Patterns, lesson steps, visual cadence, interaction counts, and per-lesson deliverables below are options rather than universal acceptance gates.

Prompt semantics and personalization boundaries belong to [prompt-semantics.md](prompt-semantics.md). [markdownflow-syntax.md](markdownflow-syntax.md) defines actual runtime controls; [authoring-contracts.md](authoring-contracts.md) describes optional author controls and artifact invariants.

## Interaction Policy Precedence

Explicit author choices constrain teaching design. The optional structured policy has these effects:

| Mode | Effect |
| --- | --- |
| `enabled` | Use the selected purposes within the author's requested scope. Do not infer permission for an unselected purpose from the selection alone. |
| `disabled` | Solicit no learner answer and create no branch that requires a newly collected answer. Explanations, demonstrations, worked applications, or consolidation may still adapt to relevant [course memory](markdownflow-syntax.md#memory). |
| `unspecified` | Let the authoring agent decide whether and where interactions improve the requested lesson; there is no default per-lesson interaction requirement. |

The supported purpose names describe learner-context collection for later teaching, pre-content thinking that an explanation can refine, and lesson-end self-check for consolidation. The authoring agent chooses suitable placements and scope unless the author has specified them. Selecting self-check does not imply a check in every lesson unless that scope was requested.

## Lesson Design

Useful design questions include what the learner should understand or do, what evidence and boundaries matter, where reasoning needs development, and what demonstrates the result. A coherent lesson may center on one core question, but multiple connected questions or another structure can be appropriate. No question, action, or deliverable quota applies.

Choose explanation depth for the learner's comprehension and task. A short authoring Prompt may direct a detailed explanation; an outline alone is insufficient when it leaves essential reasoning unspecified. Keep factual claims supported and required relationships executable. Actions should be feasible or have a clear downstream purpose; do not promise a later lesson that the course does not provide.

### Course Entry

A welcome, course introduction, or teacher introduction can be useful when consistent with the course's runtime instructions. These are optional design choices, not prerequisites or mandatory opening steps. Determine entry position from actual course order rather than a lesson-id convention. Use only verified teacher information. The existing Course Prompt template's no-greeting and no-self-introduction rules remain unchanged.

### Lesson Loop

Examples of possible lesson shapes:

- Setup → explanation → interaction → close.
- Setup → explanation → worked application or consolidation → close.
- Task → attempt → feedback → explanation.
- Demonstration → comparison → practice.

Choose the useful shape or create another. Lessons need not share a fixed sequence, start with text, end with a particular close, or include all the listed elements.

### Teaching Patterns

| Approach | Possible progression | Useful when |
| --- | --- | --- |
| Evidence Chain | Phenomenon → mechanism → implication → application | The learner needs to connect an observation to an explanation and action. |
| Misconception Repair | Plausible misconception → mechanism and boundary → corrected case | A predictable false model obstructs understanding. |
| Comparison-Driven Learning | Baseline case → changed condition → comparison → updated decision | Contrasting cases makes a distinction or boundary visible. |

These are examples, not an exhaustive list or required step order. Interactive and non-interactive forms are both available; the explicit interaction policy still applies.

### Cognitive Techniques

Calibration judgments, boundary checks, counterintuitive contrasts, action translation, and reflection can deepen understanding. Use them where they serve an identified learning need; there is no minimum count or requirement that they collect an answer.

### Examples and Analogies

Use examples or analogies to address a comprehension need, such as abstraction, an unfamiliar mechanism, a confusing distinction, or transfer to action. An existing demonstration may suffice; neither aid is required in every lesson.

- Examples need enough situation, conditions, and reasoning or action steps to show how the concept works. Connect the result back to the intended understanding.
- Analogies need a useful correspondence and relevant limits. Return to the target concept and its evidence; an analogy is not proof of the claim.
- When the relevant personalization direction is selected, use meaningful learner tasks, situations, or constraints under [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions). A role label alone does not establish familiarity. Otherwise use the course baseline.

## Interaction Design

For a selected interaction, make the question concrete and answerable and give the answer a visible effect: feedback, a branch, an adjusted example, practice, reflection, or a usable result. Do not collect answers that teaching never uses.

- Single-select suits mutually exclusive choices; multi-select suits non-exclusive interests, goals, blockers, or other "which apply?" questions.
- Free text suits information that predefined categories cannot capture well. A specific question and a concise input hint usually work better than an open-ended invitation with no purpose.
- Context-dependent choices can be generated at learner time when useful alternatives depend on the current case, discussion, or prior answers. Define what the learner should decide and how the answer will be used; preserve any author-fixed choices. This is an alternative to prewriting options, not a requirement for every interaction.
- Multi-select can use combined feedback or prioritization; it does not require an exhaustive branch for every combination.
- If a choice is intended to drive distinct next steps, provide the corresponding response behavior. Honor an explicit answer-specific branching requirement.
- Choose the number and placement of interactions for their teaching value. There is no universal count limit or required interaction slide.

Questions, controls, feedback, and branches must remain executable together. [teaching-prompt.md](teaching-prompt.md) owns their source encoding; [markdownflow-syntax.md#interactions](markdownflow-syntax.md#interactions) owns control syntax.

## Using Memory

Use relevant earlier learner input to connect explanations, feedback, examples, and reflection to what the learner actually said. The runtime memory contract belongs to [markdownflow-syntax.md#memory](markdownflow-syntax.md#memory); express the teaching use naturally, such as revisiting the learner's stated goal or comparing an earlier attempt with the current answer.

Avoid asking for information already available in memory unless a deliberate update or staged comparison serves the lesson. Handle missing or irrelevant context without inventing an answer. Apply [interaction policy precedence](#interaction-policy-precedence) and the personalization boundaries in [prompt-semantics.md](prompt-semantics.md) when using memory.

## Visual-Text Coordination

Decide whether visuals serve the teaching purpose; text-only, slide-led, image-led, and mixed lessons are available. There is no mandatory visual unit, opening page, cover, alternating cadence, or closing visual.

- A visual can expose a relationship, comparison, sequence, evidence, or case. Avoid pages added solely to pad length.
- A visual followed by explanation is one useful pattern: let the explanation develop relationships, reasoning, context, or application rather than merely repeat labels. Other coherent arrangements are valid.
- Keep question controls as the actual response surface. If a visual introduces the question, avoid simulated controls or duplicated option sets that confuse the learner about where to answer.
- Standard one-on-one delivery can speak directly to the learner; pure classroom slides support a human instructor and do not add Teaching Agent narration or address a single learner unless the author changes that setting.
- An explicit text-only requirement excludes slides, images, diagrams, and visual layout instructions. Honor other explicit visual or slide constraints.

Course-wide slide presentation requirements remain in the [Course Prompt](course-prompt.md); the Teaching Prompt describes whichever lesson-specific visual behavior the authoring agent chooses. Selected personalization changes only its permitted expression during delivery.
