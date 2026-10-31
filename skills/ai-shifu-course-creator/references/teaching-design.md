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

### Connect Goals, Difficulties, Teaching Actions, and Evidence

Reason from what the learner should be able to do, the likely obstacle, the teaching action that addresses it, and what would show progress. Use the available material, intended audience, and author requirements; distinguish an observed difficulty from a design hypothesis. This can stay in a short working note or author-facing explanation, without a required template, report, or separate design run.

For example: "Distinguish correlation from causation → may mistake simultaneous changes for causation → compare two cases with different conditions and explain the difference → identify the missing evidence in a new case." Choose the order and depth that fit the material, rather than inserting the same method throughout a course. The alignment of objectives, assessment, and teaching activities is supported by [Carnegie Mellon's Eberly Center](https://www.cmu.edu/teaching/assessment/basics/alignment.html). It does not prescribe a universal lesson sequence.

Evidence should match the objective: recalling a term does not establish the ability to apply a procedure or justify a decision. When learner responses are allowed, an explanation, attempted solution, classification, or small work product can expose understanding. A useful check also defines what feedback or authored next step follows a relevant error; merely asking "Do you understand?" is weak evidence. [Formative assessment](https://www.cmu.edu/teaching/assessment/basics/formative-summative.html) uses such information to support further learning. With interactions disabled, use explained demonstrations or self-study criteria and state the limit: no learner response has been observed. Never invent mastery from an authored activity.

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

### Method Attribution

The pattern labels above describe local lesson shapes, not established research-method names. Do not attribute a whole shape to a study that supports only one component. When selecting or applying a named teaching method, tell the teacher its name, a reliable supporting source link, why it fits this learning need, and the relevant evidence limit. A university teaching guide can explain a method without being its original inventor; name an originator or publication year only when the source supports that attribution. Explain the recommendation using [course-design-choices.md](course-design-choices.md#explaining-a-recommendation), proportionately to the task, without repeating the same citation in every lesson. Possible grounded choices include:

| Strategy and source | Fit and possible teaching action | Boundary |
| --- | --- | --- |
| Worked examples — [MIT Teaching + Learning Lab](https://tll.mit.edu/teaching-resources/how-people-learn/worked-examples/) | A learner new to a procedure needs to see the reasoning behind a solution. Explain the steps and why they work; supported practice can follow when appropriate. | Copying a model is not independent performance. The amount of support should fit prior knowledge; a complete demonstration may be redundant for an experienced audience. |
| Retrieval practice — [Washington University Center for Teaching and Learning](https://ctl.wustl.edu/resources/using-retrieval-practice-to-increase-student-learning/) | Previously taught knowledge needs to be recalled or used. Invite recall or application and provide corrective feedback within permitted interactions. | Repeating a displayed answer is not retrieval. Do not use recall alone as proof of complex performance or insert tests when answers are disallowed. |
| Prior-knowledge assessment — [Carnegie Mellon's Eberly Center](https://www.cmu.edu/teaching/designteach/teach/priorknowledge.html) | Existing attempts may reveal missing prerequisites or a misconception. Use relevant available evidence to identify what an explanation needs to address. | Self-reported confidence is indirect evidence. Do not infer a misconception from a profession or collect a new answer without the relevant interaction permission. |

These sources guide a reasoned choice; they do not guarantee a particular learner's result or authorize new interactions. An author-specified approach can be used directly. Verify a reliable source before presenting another approach as an established named method; if the attribution cannot be verified, describe the concrete teaching action without the label. Keep method names, research rationale, and authoring decisions in author-facing explanations rather than making the Teaching Agent teach pedagogical theory unrelated to the course.

### Cognitive Techniques

Calibration judgments, boundary checks, counterintuitive contrasts, action translation, and reflection can deepen understanding. Use them where they serve an identified learning need; there is no minimum count or requirement that they collect an answer.

### Examples and Analogies

Use examples or analogies to address a comprehension need, such as abstraction, an unfamiliar mechanism, a confusing distinction, or transfer to action. An existing demonstration may suffice; neither aid is required in every lesson.

- Examples need enough situation, conditions, and reasoning or action steps to show how the concept works. Connect the result back to the intended understanding.
- Analogies need a useful correspondence and relevant limits. Return to the target concept and its evidence; an analogy is not proof of the claim.
- When the relevant personalization direction is selected, use meaningful learner tasks, situations, or constraints under [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions). A role label alone does not establish familiarity. Otherwise use the course baseline.

### Personalized Teaching Within the Resolved Directions

AI-Shifu can connect permitted explanations to a learner's actual tasks and earlier input instead of relying only on a single generic example. This is useful when it makes a relationship, analogy, or practical consequence easier to examine. Choose the teaching strategy for the authored objective and difficulty; apply personalization only to expression allowed by [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions). A direction's selection is not permission to change the lesson's sequence, visual structure, interactions, branches, or feedback effects, or to collect more background.

For example, with Examples selected, a reusable instruction can say: "When explaining sampling bias, if relevant learning memory explicitly says the learner reviews only returned questionnaires, use that task to explain why nonrespondents may affect the conclusion. Preserve the original example's required conditions, reasoning, and conclusion. Without relevant context, use the course's neutral questionnaire example." This uses a stated task rather than assuming that everyone in the learner's profession has the same experience. It does not enable Analogies, Language style, or Practical value implicitly. The missing-context fallback must still teach the required content. Keep an individual's background out of reusable artifacts and do not expose the supplied learner profile.

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
- Choose a visual where seeing elements together clarifies a structural or spatial relationship, a process, a comparison, or a change in evidence. Text can carry precise definitions, reasoning, contextual details, and response feedback; a complex topic does not automatically require slides. Explain what comprehension need the proposed visual addresses rather than setting a slide ratio or converting paragraphs into images.
- A visual followed by explanation is one useful pattern: let the explanation develop relationships, reasoning, context, or application rather than merely repeat labels. Other coherent arrangements are valid.
- Keep labels near their referents, signal the relevant relationship, and reveal complex information in manageable parts when useful. These recommendations follow [UCSB's guidance on explaining content and slide design](https://citral.ucsb.edu/faculty/resources/engaging-students/explaining-content). Apply them to the actual delivery medium: findings about narrated graphics do not mean that accompanying explanatory text is forbidden in a text-based lesson. Accessibility and explicit author requirements still matter.
- Keep question controls as the actual response surface. If a visual introduces the question, avoid simulated controls or duplicated option sets that confuse the learner about where to answer.
- Standard one-on-one delivery can speak directly to the learner; pure classroom slides support a human instructor and do not add Teaching Agent narration or address a single learner unless the author changes that setting.
- An explicit text-only requirement excludes slides, images, diagrams, and visual layout instructions. Honor other explicit visual or slide constraints.

Course-wide slide presentation requirements remain in the [Course Prompt](course-prompt.md); the Teaching Prompt describes whichever lesson-specific visual behavior the authoring agent chooses. Selected personalization changes only its permitted expression during delivery.
