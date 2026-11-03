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

### Selecting an Approach for the Learning Task

Select for a learning task or meaningful teaching block, not just a subject label or an entire course. Consider the required content and its relationships, the intended learner performance, available evidence of prior knowledge or difficulty, and constraints such as time, delivery mode, source fidelity, and permitted interactions. Use the author's resolved choices directly. When missing information would change the recommendation, ask about the consequence, such as whether learners must explain an existing plan or produce one independently, using [course design choices](course-design-choices.md#asking-for-useful-information).

The following is an open set of design options, not a classifier or an exhaustive method catalog. The teaching actions describe possible implementations; established method names and source boundaries follow [method attribution](#method-attribution).

| Learning need or obstacle | Candidate teaching action | Evidence and limits to consider |
| --- | --- | --- |
| An abstract concept lacks meaning | Explain a concrete instance, map an analogy where useful, or compare an example and a non-example. | Look for an explanation of the relevant relationship or classification of a new instance. Check the analogy's limits; familiarity cannot be inferred from a job title. |
| A novice must perform a procedure | Show a worked example with reasons for the steps; offer a partially supported attempt before independent application when useful. | An actual attempt can show whether the learner selects and executes the steps. Reduce redundant support for a learner who can already perform them. |
| A mechanism or boundary is hard to distinguish | Compare cases that differ in a consequential condition, asking for a prediction or explanation when allowed. | The explanation should connect the changed condition to its consequence. Merely describing two examples does not establish that connection. |
| A plausible misconception obstructs reasoning | Elicit the reasoning when permitted, address the specific conflict, and revisit the idea in another case. | Distinguish a correct reason, a diagnostic error, and an unclear answer. An unclear answer is not proof of a misconception; a correct answer needs no invented correction. |
| A learner must make a contextual judgment | Use a case with relevant facts, constraints, and viable alternatives; require a decision supported by evidence. | Evaluate the reasoning against explicit criteria. A preference or guess alone is weak evidence; acknowledge multiple defensible choices when the case allows them. |
| Previously taught knowledge needs consolidation | Use retrieval practice with corrective feedback, choosing recall or application to match the goal. | The learner must attempt retrieval before seeing the answer. Do not infer durable retention from one immediate correct response. |
| A learner must produce an integrated result | Set a feasible task with a usable output and success criteria; support difficult components and provide feedback on the actual attempt. | Inspect the work and its reasoning, including revisions when selected. A short exercise does not automatically implement a complete project-based learning method. |
| A learner can start but gets stuck at a particular step | Offer a targeted hint, wait for a new attempt, and adjust support to the actual difficulty. | Keep supported completion distinct from independent performance; check prerequisites rather than repeatedly increasing hints. |
| A learner has an answer or work product but cannot improve it | Give actionable feedback against clear criteria and inspect the learner's next version. | Recheck both the previous gap and new problems in the current version; a suggestion is not evidence of revision. |
| Per-item answers would interrupt independent work on a question set | Collect a whole round before revealing results, then focus subsequent rounds on the still-incorrect original items. | Reconcile item results, total, and remaining items against the actual answers; natural-language scoring is not guaranteed to be exact. |
| A learner can repeat a definition but cannot explain it to a beginner | Invite the learner to organize an explanation, address the actual gap, and have them explain again when needed. | Seeing the teacher's explanation is not learner explanation; this does not establish that a real beginner was taught. |
| A position or decision rests on unclear reasons or assumptions | Use purposeful open questions about the learner's actual claim, evidence, alternatives, or conditions. | A reasoned position may be retained or revised; do not steer every learner to a predetermined opinion. |
| A relationship needs to be explored through changing conditions | Use a suitable interactive model to predict, manipulate conditions, compare observations, and explain the relationship. | State model assumptions; an illustration is not an operable simulation, and page actions may not reach the Teaching Agent. |
| Knowledge or scripts must be used in an evolving exchange | Set a role or communication task with a goal and constraints, and let later turns respond to the learner's actual expression. | Evaluate relevant decisions and behaviors; simulated responses cannot establish real customer, colleague, or workplace outcomes. |

Prefer a strategy whose essential actions fit the goal and available conditions. Consider a plausible alternative when it would change the experience: a worked example can support first attempts, while a case with less scaffolding may better expose an experienced learner's judgment. This is a reasoned recommendation under the available evidence, not proof of a uniquely optimal method. Direct explanation remains appropriate when it serves the goal; an explicitly non-interactive lesson may use a reasoned demonstration without claiming to have observed learner performance.

Combine approaches where they address different obstacles, for example a worked example followed by retrieval of the decision criteria. Do not add methods just for variety or repeat one sequence across every lesson. Preserve an author-specified or custom approach; identify a material conflict with the goal or constraints rather than silently replacing it with a catalog entry.

Make the chosen strategy concrete through what is presented, what the learner does if responses are allowed, what counts as a satisfactory result, and how relevant errors or incomplete reasoning affect feedback. These decisions can stay in ordinary working notes or the teacher-facing explanation; they require no score, selection form, or intermediate schema. The authoring agent selects the approach; learner-time adaptation follows the authored feedback paths and the [personalization boundaries](#personalized-teaching-within-the-resolved-directions). [Teaching Prompt examples](teaching-prompt.md#teaching-strategy-examples) show how different choices become executable instructions.

### Preserve Each Selected Approach's Learning Actions

These are local implementation options, not a common sequence. Use response-dependent steps only within the [interaction policy](#interaction-policy-precedence) and the author's scope. An approach can end when its intended result is adequately shown or its selected practice boundary is reached; identify remaining gaps rather than forcing a universal submission, mastery, or summary routine.

- **Progressive hints:** Allow an attempt before giving away the solution. At a real obstacle, give one useful cue and wait for another actual attempt before adding help. If a prerequisite is missing, supply appropriate support and return to the original or equivalent task. Fade support according to performance; a new independent attempt can check transfer when selected.
- **Actionable feedback:** Identify what currently works, the consequential gap, and a feasible adjustment using the task's criteria. Prioritize rather than overload. When revision is selected, wait for it and inspect the latest answer or artifact, including newly introduced problems. End when the applicable criteria or authored practice boundary is met.
- **Whole-round question practice:** Keep answers unrevealed during a round. At its end, derive item results, total, and the wrong-item set from the same actual responses and answer criteria. Retain original item identities and standards when retrying only still-incorrect items; do not silently substitute new questions. Stop when no wrong items remain or the selected boundary is reached. Correction of these items alone shows neither transfer nor durable retention.
- **Consolidation and transfer:** Choose recall, application, varied conditions, or a delayed revisit for the intended evidence. Let the learner attempt before showing the answer. A new task can expose dependence on the original example; a later check can address retention. Arrange timing and follow-up only within actual delivery support, without assuming automatic reminders.
- **Explain to a beginner:** Treat a Feynman-style explain-to-a-novice task as one form of [self-explanation](#method-attribution). Specify whom the learner is trying to teach and the concept's accuracy criteria. Ask for the learner's own explanation, locate a concrete conceptual or reasoning gap, offer focused help, and wait for a revised explanation if needed. Stop once the required idea and conditions are explained adequately; do not keep requesting rewording for its own sake. A simulated novice's questions are instructional role-play, not evidence that the learner has taught a real peer.
- **Socratic questioning:** Choose the next question from the actual position and its unresolved definition, reason, evidence, assumption, alternative, or consequence. Accept a justified retained view as well as a revision, and preserve unresolved tradeoffs when appropriate. Stop when the relevant judgment is clear enough for the goal rather than extending questions indefinitely.
- **Interactive inquiry:** Make the model and exploration purpose clear. When useful, elicit a prediction, change a consequential condition, compare observations, and relate the result to the mechanism and its limits. Let the selected inquiry use its actual operation surface; do not add a text submission merely to imitate other methods. Without operation readback, use learner-provided observations and state that limit.

### Match Evidence to the Claim

Distinguish exposure, explanation, supported completion, independent performance, transfer, and delayed retention. Also distinguish a simulated exchange, actual execution, and improvement in the real problem. Independence concerns the target judgments under permitted conditions and aids; it need not mean working without software or a job aid. Do not count work done by the AI as learner performance. Use suitable process observation for physical or device skills, with an appropriately qualified instructor or professional where needed; a written account cannot replace action evidence.

File access, screen or audio observation, code execution, operation readback, precise timing, reminders, and later feedback depend on the actual delivery setup. Authoring tools do not establish these learner-time capabilities. If they are unavailable, work from the materials actually supplied and identify what has not been observed or verified. A paper design or platform preview does not establish learner effectiveness.

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

The labels in [Teaching Patterns](#teaching-patterns) describe local lesson shapes, not established research-method names. Do not attribute a whole shape to a study that supports only one component. When selecting or applying a named teaching method, tell the teacher its name, a reliable supporting source link, why it fits this learning need, and the relevant evidence limit. A university teaching guide can explain a method without being its original inventor; name an originator or publication year only when the source supports that attribution. Explain the recommendation using [course-design-choices.md](course-design-choices.md#explaining-a-recommendation), proportionately to the task, without repeating the same citation in every lesson. Possible grounded choices include:

| Strategy and source | Fit and possible teaching action | Boundary |
| --- | --- | --- |
| Worked examples — [MIT Teaching + Learning Lab](https://tll.mit.edu/teaching-resources/how-people-learn/worked-examples/) | A learner new to a procedure needs to see the reasoning behind a solution. Explain the steps and why they work; supported practice can follow when appropriate. | Copying a model is not independent performance. The amount of support should fit prior knowledge; a complete demonstration may be redundant for an experienced audience. |
| Retrieval practice — [Washington University Center for Teaching and Learning](https://ctl.wustl.edu/resources/using-retrieval-practice-to-increase-student-learning/) | Previously taught knowledge needs to be recalled or used. Invite recall or application and provide corrective feedback within permitted interactions. | Repeating a displayed answer is not retrieval. Do not use recall alone as proof of complex performance or insert tests when answers are disallowed. |
| Prior-knowledge assessment — [Carnegie Mellon's Eberly Center](https://www.cmu.edu/teaching/designteach/teach/priorknowledge.html) | Existing attempts may reveal missing prerequisites or a misconception. Use relevant available evidence to identify what an explanation needs to address. | Self-reported confidence is indirect evidence. Do not infer a misconception from a profession or collect a new answer without the relevant interaction permission. |
| Self-explanation — [MIT Teaching + Learning Lab](https://tll.mit.edu/teaching-resources/how-people-learn/worked-examples/) | A learner can follow a solution but may not understand its reasoning. Ask why a step or principle applies, then use the explanation to address a gap. | Paraphrasing the displayed answer is insufficient. This source discusses self-explanation with worked examples; it does not establish every locally designed explanation activity. |
| Case-based learning — [Columbia Center for Teaching and Learning](https://ctl.columbia.edu/resources-and-technology/resources/case-method/) | A learner needs to apply concepts to a contextual problem or decision. Provide case evidence and constraints, elicit a reasoned response, and examine consequences or alternatives. | A story followed by its answer does not by itself provide learner case analysis. Adapt classroom activities to the available individual interaction; do not assume peers or a live instructor are present. |
| Scaffolding — [review of contingency, fading, and transfer of responsibility](https://doi.org/10.1007/s10648-010-9127-6) | Adjust help to the actual difficulty, reduce it as performance permits, and return responsibility to the learner. | These mechanisms support a design rationale, not a validated AI hint ladder or a fixed number of hints. |
| Formative feedback — [Shute's review](https://doi.org/10.3102/0034654307313795) | Give specific, supportive information suited to the task and learner, with an opportunity to use it. | Feedback timing and form depend on context; this source does not validate every locally designed revision loop. |
| Socratic questions — [University of Connecticut CETL](https://cetl.uconn.edu/resources/teaching-your-course/leading-effective-discussions/socratic-questions/) | Examine clarification, assumptions, reasons, perspectives, and consequences through purposeful questions. | A guide to questioning is not evidence that an unbounded dialogue or a predetermined conclusion improves learning. |
| Interactive simulations — [PhET research](https://phet.colorado.edu/en/research) | Use a suitably designed model to explore conditions and connect observations with an explanation. | Evidence concerns particular simulation designs and uses; it does not validate every interactive page or establish AI access to page actions. |
| Study and practice organization — [IES practice guide](https://ies.ed.gov/ncee/wwc/PracticeGuide/1) | For relevant consolidation needs, space revisits, use retrieval and explanatory questions, or alternate worked examples with problem solving. | The guide's recommendation to interleave examples and problems is not direct evidence for every mixture of question types; application and delayed retention need their own evidence. |
| Role-playing — [Carnegie Mellon's active-learning strategies](https://www.cmu.edu/teaching/resources/instructionalstrategies/activelearningstrategies/index.html) | Take a stakeholder's role to compare perspectives or practice contextual expression. | An AI role is a simulation; it does not supply actual peers or establish real interpersonal outcomes. |
| Project-based learning — [PBLWorks design framework](https://www.pblworks.org/gold-standard/pbl-project-design) | A full project design connects a challenging problem, sustained inquiry, authenticity, student choice, reflection, critique and revision, and a public product. | This is a design framework, not evidence that any local AI project has implemented all elements or improved learning. |

These sources guide a reasoned choice; they do not guarantee a particular learner's result or authorize new interactions. An author-specified approach can be used directly. Verify a reliable source before presenting another approach as an established named method; if the attribution cannot be verified, describe the concrete teaching action without the label. Keep method names, research rationale, and authoring decisions in author-facing explanations rather than making the Teaching Agent teach pedagogical theory unrelated to the course.

### Cognitive Techniques

Calibration judgments, boundary checks, counterintuitive contrasts, action translation, and reflection can deepen understanding. Use them where they serve an identified learning need; there is no minimum count or requirement that they collect an answer.

### Combining Approaches for Applied Tasks

Select a main approach and only the supporting actions needed for the current obstacle. These examples are design options, not tested AI-Shifu course combinations or fixed lesson orders. Reuse actual drafts and records, shorten support for demonstrated skills, and address missing prerequisites or real resource barriers before adding more teaching.

- **Workplace scenario practice:** Supply the role, goal, constraints, and acceptable behaviors. Let the other role respond to what the learner actually says. If help is needed, clearly pause the role-play, give a targeted cue, then resume. Rehearse a consequential turn or vary a constraint; distinguish simulation from later workplace evidence.
- **Errors and exam preparation:** Use the actual question, answer, and available reasoning or time records to distinguish known errors from hypotheses. Choose per-item coaching or whole-round practice for the intended feedback timing. After repair, use an appropriate new or mixed task, or a delayed check when selected; original-item correction alone is not exam readiness. Do not invent timing or attribute score changes to one strategy without evidence.
- **Project work:** Establish a useful output and criteria, retain necessary prerequisites, and start from an existing draft or a feasible first version. Add knowledge at the current obstacle, then return to the same artifact for feedback and revision. Arrange actual peers, users, or external audiences when the design needs them. Shared work should require meaningful integration; assess individual understanding separately from team quality.
- **Software practice:** Connect the task, input, environment, expected output, and checks. Demonstrate a critical operation when needed. For a failure, compare expected and actual results, test one plausible cause with a small change, inspect the result, and finally rerun the original task. Preserve useful original inputs. Without access or execution evidence, do not claim to have inspected the learner's screen or verified a fix; software feedback does not establish physical action quality.

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

Choose visuals for a teaching purpose: orient the learner, focus attention, organize knowledge, explain relationships, expose reasoning, support a task, or prepare later application. When the author leaves the form open, the authoring agent may select board-style work, illustrations, slides, or a mixture and make those choices concrete in the Teaching Prompt. Text-only lessons remain valid. There is no mandatory visual unit, opening page, cover, slide ratio, alternating cadence, or closing visual.

### Situations Worth Considering

Use this open set of situations to identify what the learner needs to see, understand, or remember. These are design options, not a page checklist or evidence that each situation needs a separate slide. A visual may serve several purposes; a short text heading or inline emphasis may already suffice.

| Situation | Teaching purpose and possible treatment |
| --- | --- |
| Course or lesson cover | Establish the topic, core question, or intended result. Use a concise title and purposeful visual when useful; a new lesson does not automatically need a separate cover. |
| Learning route or transition | Show the current position and how it connects to earlier and later material with a route, chapter map, or stage marker. |
| Core question or cognitive conflict | Focus attention on a question, unexpected observation, or consequential case that the lesson will explain. |
| Memorable statement or core conclusion | Make a reusable principle or decision criterion a focal point. Preserve its conditions and limits; a memorable phrase must still convey an accurate idea. |
| Key facts, definitions, formulas, or warnings | Make information easy to identify or consult, including thresholds, units, and operating restrictions. A clear text card or board note may be sufficient without an illustration. |
| Overall structure or conceptual relationships | Expose parts, hierarchy, dependencies, or connections through an architecture diagram, concept map, tree, or network. |
| Procedure or decision path | Make order, prerequisites, and branches visible with a flowchart, decision tree, or action checklist. |
| Mechanism, causation, or change | Show how a process develops, which condition changes, and why an outcome follows through a causal chain, state diagram, or progressively built model. |
| Comparison, boundary, or misconception | Place cases, examples and non-examples, or an error and its correction together; identify the consequential difference rather than only contrasting their appearance. |
| Data, evidence, or trends | Show quantities, distributions, changes, or evidential comparisons with an appropriate chart. Keep values, units, axes, assumptions, and sources accurate. |
| Real objects, situations, or spatial details | Use a photograph, interface capture, map, or section diagram when shape, location, or observable detail is itself part of the learning task; mark where to look. |
| Derivation, worked example, or operation | Expose intermediate judgments through board-style construction, staged solutions, execution traces, or annotated demonstrations rather than showing only a finished answer. |
| Shared task or thinking material | Keep case evidence, constraints, instructions, or an incomplete diagram available while the learner works. Visual material does not by itself authorize a new interaction. |
| Feedback or correction | Mark the relevant part of the learner's actual available answer or work, or compare versions and explain why a change is needed. Do not invent a learner submission. |
| Integration, review, or transfer | Reorganize what has been taught into a summary map, checklist, decision card, or action path for later use. Displaying it does not establish retention or mastery. |

### Select the Medium and Unfolding

- **Board-style construction:** Prefer progressive writing, drawing, or annotation when the learner needs to follow the formation of a derivation, model, solution, or judgment. Retain intermediate steps needed for comparison and leave a usable overall reference. A static sequence of stages can serve this purpose when live drawing or animation is unavailable; do not promise unsupported learner-time capabilities.
- **Illustration, photograph, or annotated capture:** Prefer a prepared visual when shape, spatial relations, real detail, or a precise diagram matters. Place labels near what they describe and connect the representation to the concept or task.
- **Slide or reference page:** Prefer a stable shared view when the learner needs an overall comparison, a focused conclusion, task instructions, or information to consult. A slide can use text, diagrams, or evidence; it does not require decorative imagery. Prepared visuals and board-style annotations can be combined.

The medium is a design choice, not a ranking of learning effectiveness. Choose whether an item needs its own page from the need to pause, focus attention, compare, or revisit it. Avoid pages added solely to pad length or reproduce ordinary paragraphs as images. A complex topic does not automatically require slides, and important information does not automatically require a separate page.

### Research Basis and Limits

Use these sources under [method attribution](#method-attribution) when explaining a choice to the teacher. The situations and medium choices above apply the supported principles; they are not a research-validated page taxonomy.

- **Multimedia learning:** [Mayer's review](https://onlinelibrary.wiley.com/doi/10.1111/jcal.12197) supports relevant verbal and graphical representations, pre-training, and segmenting. The [IES practice guide](https://ies.ed.gov/ncee/wwc/PracticeGuide/1) rates combining graphics with verbal descriptions as moderate evidence and also recommends connecting abstract and concrete representations. These support meaningful relationships and processes, not arbitrary illustration of every paragraph or a guarantee for a particular learner.
- **Signaling, coherence, and contiguity:** [Fiorella and Mayer](https://www.cambridge.org/core/books/abs/cambridge-handbook-of-multimedia-learning/principles-for-reducing-extraneous-processing-in-multimedia-learning/F29A19FCD34C542806F736E0661C05F5) explain highlighting essential organization, excluding irrelevant material, and aligning related words and graphics in space and time. These inform a focal conclusion, clear labels, and selective emphasis; they do not establish that every memorable statement deserves a separate page or that decoration improves learning.
- **Organization and signposts:** [Carnegie Mellon's lecture guidance](https://www.cmu.edu/teaching/designteach/teach/instructionalstrategies/lectures.html) recommends an introduction, outline, agenda, or visual organization and markers for key points and transitions. This supports orientation and route design; a particular cover or transition page remains a local choice, not a mandatory research-backed unit.
- **Conclusion with evidence:** [Alley and colleagues' slide research](https://www.writing.engr.psu.edu/research.html) found better understanding and retention for an assertion-evidence structure than common topic-and-bullet slides in the studied technical presentation. This supports a clear claim with relevant visual evidence; it does not establish learning gains from a slogan alone or require the same slide structure everywhere.
- **Progressive construction and attention:** [Durham's digital-handwriting guidance](https://helpguides.webspace.durham.ac.uk/approaches/inclusive/structuring-learning-content/digital-handwriting-in-teaching-a-practical-guide/) describes live derivations, models, and prepared visuals with annotation; it is a practice guide. In [Zhang and colleagues' normal-distribution experiments](https://link.springer.com/article/10.3758/s13421-024-01526-7), the study detected no significant learning difference between a moving cursor over static slides and visible-hand drawing in one comparison; this does not establish equivalence. Attend to unfolding and attention guidance rather than assuming that handwriting or animation is always superior.

### Coordinate With Text and Delivery

- Text can carry precise definitions, reasoning, contextual details, and response feedback. Preserve the explanation needed by the actual learning task and medium.
- A visual followed by explanation is one useful pattern: let the explanation develop relationships, reasoning, context, or application rather than merely repeat labels. Other coherent arrangements are valid.
- Keep labels near their referents, signal the relevant relationship, and reveal complex information in manageable parts when useful. These recommendations follow [UCSB's guidance on explaining content and slide design](https://citral.ucsb.edu/faculty/resources/engaging-students/explaining-content). Apply them to the actual delivery medium: findings about narrated graphics do not mean that accompanying explanatory text is forbidden in a text-based lesson. Accessibility and explicit author requirements still matter.
- Keep question controls as the actual response surface. If a visual introduces the question, avoid simulated controls or duplicated option sets that confuse the learner about where to answer.
- Standard one-on-one delivery can speak directly to the learner; pure classroom slides support a human instructor and do not add Teaching Agent narration or address a single learner unless the author changes that setting.
- An explicit text-only requirement excludes slides, images, diagrams, and visual layout instructions. Honor other explicit visual or slide constraints.

Course-wide slide presentation requirements remain in the [Course Prompt](course-prompt.md); the Teaching Prompt describes whichever lesson-specific visual behavior the authoring agent chooses. Selected personalization changes only its permitted expression during delivery.
