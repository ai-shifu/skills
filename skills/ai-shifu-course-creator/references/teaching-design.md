# Teaching Design Options

Choose teaching approaches for the audience, source, objectives, and author requirements. Throughout this reference, patterns, sequences, visuals, interaction counts, and deliverables are design options, not universal acceptance gates. Use resolved author choices directly; combine approaches only when they address different learning needs. A design rationale or authored activity is not evidence of learner mastery; apply [evidence boundaries](#match-evidence-to-the-claim) to any result claim.

Use [approach selection](#selecting-an-approach-for-the-learning-task) to locate relevant options, [tradeoffs](#choosing-between-plausible-alternatives) and [practice choices](#choosing-practice-for-the-intended-result) for consequential comparisons, [learning actions](#preserve-each-selected-approachs-learning-actions) for execution details, and [method attribution](#method-attribution) for sources. These are reference entry points, not authoring phases.

Prompt semantics and personalization boundaries belong to [prompt-semantics.md](prompt-semantics.md). [markdownflow-syntax.md](markdownflow-syntax.md) defines actual runtime controls; [authoring-contracts.md](authoring-contracts.md) describes optional author controls and artifact invariants.

## Interaction Policy Precedence

Explicit author choices constrain teaching design. The optional structured policy has these effects:

| Mode | Effect |
| --- | --- |
| `enabled` | Use the selected purposes within the author's requested scope. Do not infer permission for an unselected purpose from the selection alone. |
| `disabled` | Solicit no learner answer and create no branch that requires a newly collected answer. Explanations, demonstrations, worked applications, or consolidation may still adapt to relevant [course memory](markdownflow-syntax.md#memory). |
| `unspecified` | Let the authoring agent decide whether and where interactions improve the requested lesson; there is no default per-lesson interaction requirement. |

The supported purpose names describe learner-context collection for later teaching, pre-content thinking that an explanation can refine, and lesson-end self-check for consolidation. The authoring agent chooses suitable placements and scope unless the author has specified them. Selecting learner-context collection does not require repeating information already available; use [existing-information reuse](teaching-prompt.md#encode-existing-context-reuse) for any consequential gap. Selecting self-check does not imply a check in every lesson unless that scope was requested.

## Lesson Design

Useful design questions include what the learner should understand or do, what evidence and boundaries matter, where reasoning needs development, and what demonstrates the result. A lesson may center on one core question or several connected questions.

Choose explanation depth for the learner's comprehension and task. A short authoring Prompt may direct a detailed explanation; an outline alone is insufficient when it leaves essential reasoning unspecified. Keep factual claims supported and required relationships executable. Actions should be feasible or have a clear downstream purpose; do not promise a later lesson that the course does not provide.

### Connect Goals, Difficulties, Teaching Actions, and Evidence

Reason from what the learner should be able to do, the likely obstacle, the teaching action that addresses it, and what would show progress. Use the available material, intended audience, and author requirements; distinguish an observed difficulty from a design hypothesis. This can stay in a short working note or author-facing explanation, without a required template, report, or separate design run.

For example: "Distinguish correlation from causation → may mistake simultaneous changes for causation → compare two cases with different conditions and explain the difference → identify the missing evidence in a new case." Choose the order and depth that fit the material, rather than inserting the same method throughout a course. The alignment of objectives, assessment, and teaching activities is supported by [Carnegie Mellon's Eberly Center](https://www.cmu.edu/teaching/assessment/basics/alignment.html). It does not prescribe a universal lesson sequence.

Evidence should match the objective: recalling a term does not establish the ability to apply a procedure or justify a decision. When learner responses are allowed, an explanation, attempted solution, classification, or small work product can expose understanding. A useful check also defines what feedback or authored next step follows a relevant error; merely asking "Do you understand?" is weak evidence. [Formative assessment](https://www.cmu.edu/teaching/assessment/basics/formative-summative.html) uses such information to support further learning. With interactions disabled, use explained demonstrations or self-study criteria and state the limit: no learner response has been observed. Never invent mastery from an authored activity.

### Selecting an Approach for the Learning Task

Select for a learning task or meaningful teaching block, not just a subject label or an entire course. Consider the required content and its relationships, the intended learner performance, available evidence of prior knowledge or difficulty, and constraints such as time, delivery mode, source fidelity, and permitted interactions. Use the author's resolved choices directly. When missing information would change the recommendation, ask about the consequence, such as whether learners must explain an existing plan or produce one independently, using [course design choices](course-design-choices.md#asking-for-useful-information).

Use this open index to locate a candidate action. The sections below explain its tradeoffs, execution, and evidence; a row is not a diagnosis or a mandatory method assignment.

| Learning need or obstacle | Candidate teaching action |
| --- | --- |
| Uncertain prerequisites would change teaching | Reuse relevant work or consider a focused prior-knowledge diagnostic. |
| An abstract concept lacks meaning | Use a concrete example, a mapped analogy, or an example/non-example contrast. |
| A novice must perform a procedure | Explain a worked solution and support a first attempt. |
| A mechanism or boundary is hard to distinguish | Compare a consequential condition and explain how it changes the result. |
| A plausible misconception obstructs reasoning | Examine the actual reasoning, address the conflict, and revisit another case. |
| A learner must make a contextual judgment | Use case evidence, constraints, and alternatives to support a decision. |
| Previously taught knowledge needs consolidation | Choose retrieval, timing, or activity organization for the intended result. |
| A learner must produce an integrated result | Select a bounded applied task or a full project according to its scope and resources. |
| A learner gets stuck at a particular step | Give a targeted hint and adjust support after a new attempt. |
| A learner cannot improve an existing answer or artifact | Give criterion-based feedback and inspect the next version. |
| Per-item feedback would interrupt independent work | Collect a whole question round before revealing results. |
| A learner can repeat but not explain a concept | Invite an explanation to a beginner and address the actual gap. |
| A position rests on unclear reasons or assumptions | Ask purposeful questions about the actual claim, evidence, or conditions. |
| A relationship needs exploration through changing conditions | Use an operable model to predict, manipulate, compare, and explain. |
| Knowledge must be used in an evolving exchange | Use role-play whose later turns respond to the learner's expression. |

Prefer a strategy whose essential actions fit the goal and available conditions. Consider a plausible alternative when it would change the experience: a worked example can support first attempts, while a case with less scaffolding may better expose an experienced learner's judgment. This is a reasoned recommendation under the available evidence, not proof of a uniquely optimal method. Direct explanation remains appropriate when it serves the goal; an explicitly non-interactive lesson may use a reasoned demonstration without claiming to have observed learner performance.

Identify material conflicts between a goal, an author-specified approach, and available conditions. For example, a 90-second non-interactive explanation cannot by itself establish independent performance of a complex procedure. Within that scope, offer a focused demonstration, explain which practice and performance evidence would still be needed, and surface the unresolved choice to the caller. Do not silently lower the goal, add interactions or lessons, or replace the author's approach. Whether to revisit those choices follows the entrypoint's collaboration guidance.

Make the chosen strategy concrete through what is presented, what the learner does if responses are allowed, what counts as a satisfactory result, and how relevant errors or incomplete reasoning affect feedback. These decisions can stay in ordinary working notes or the teacher-facing explanation; they require no score, selection form, or intermediate schema. The authoring agent selects the approach; learner-time adaptation follows the authored feedback paths and the [personalization boundaries](#personalized-teaching-within-the-resolved-directions). [Teaching Prompt examples](teaching-prompt.md#teaching-strategy-examples) show how different choices become executable instructions.

### Choosing Between Plausible Alternatives

Compare alternatives when the unresolved choice would materially change the lesson. The distinctions below apply the sources in [method attribution](#method-attribution); they are not head-to-head experimental findings or a ranking of methods. Comparing alternatives does not require a new learner questionnaire.

| Choice | Selection conditions and consequential tradeoff |
| --- | --- |
| Diagnose or use available evidence | Diagnose only if uncertain prerequisites would change content, difficulty, or support; relevant existing work may already suffice. Confidence, seniority, or course attendance alone does not establish proficiency. Without permitted responses, use an explicit provisional baseline. This applies CMU's prior-knowledge guidance. |
| Worked example, self-explanation, or independent application | Show a worked example when the learner lacks a way into the task; ask for self-explanation when the gap is why a step applies; reduce support when relevant work demonstrates competence. These can combine. MIT's guidance concerns task-specific expertise, not seniority. |
| Self-explanation, Socratic inquiry, or direct correction | Examine a solution's reasoning through self-explanation; examine a judgment's definitions, evidence, assumptions, or consequences through Socratic questions. A verified factual error may need direct explanation first. An unclear answer is not proof of error. This applies MIT and UConn guidance. |
| Formative feedback and scaffolding | Use feedback on an available answer or artifact; add contingent support when the learner cannot proceed, then fade it as responsibility returns. Shute's feedback forms include hints and examples; van de Pol and colleagues distinguish scaffolding's mechanisms. The approaches overlap, but a hint alone is not scaffolding. |
| Case analysis, role-play, or simulation | Use a case for evidence-based decisions, role-play for perspectives or expression in an evolving exchange, and an operable model for manipulating conditions. Columbia includes role-play within case activities; PhET studies designed simulations. A static case or AI persona is not a manipulable model. |
| Full project or bounded task/case | Use a full project for integrated learning through sustained inquiry and learner choices when time, feedback, revision, and an authentic public audience are feasible. Use a bounded task for a narrow goal or unavailable project resources. PBLWorks supplies design criteria, not a minimum duration or proof of superiority; a simulated audience is not a public audience. |

### Choosing Practice for the Intended Result

Select what learners do, when they revisit, and how support changes for the intended result. Compatible choices can combine, such as spaced retrieval. Sources and their evidence limits are in [method attribution](#method-attribution).

| Intended result | Practice choice |
| --- | --- |
| Access previously taught knowledge without a displayed answer | Use retrieval with recall or application matching the target. Supply explanation or support if a missing concept or prerequisite is the actual obstacle. |
| Retain knowledge beyond the current session | Space revisits when the actual schedule supports later encounters; retrieval can be part of them. An immediate retry is not a delayed retention check. |
| Move from understanding a solution to solving independently | Alternate worked examples and problem-solving attempts, adjusting support to demonstrated proficiency. This changes activity type. |
| Distinguish taught problem types and select a strategy | Consider interleaving those types when method selection is part of the goal. Address missing methods first; this differs from example/problem alternation. |

### Preserve Each Selected Approach's Learning Actions

Use response-dependent steps within the [interaction policy](#interaction-policy-precedence). End when the intended result is adequately shown or the authored practice boundary is reached; for unresolved gaps, use [non-achievement closure](#when-practice-does-not-reach-the-goal).

- **Reasoning and judgment:** Compare cases through the consequential condition and its effect. For a suspected misconception, distinguish a correct reason, a diagnostic error, and an unclear answer before correcting it. For a case decision, use explicit criteria and accept multiple defensible choices when the evidence allows them; a guess alone is weak evidence.
- **Progressive hints:** Allow an attempt before giving away the solution. At a real obstacle, give one useful cue and wait for another actual attempt before adding help. If a prerequisite is missing, supply appropriate support and return to the original or equivalent task. Fade support according to performance; a new independent attempt can check transfer when selected.
- **Actionable feedback:** Identify what currently works, the consequential gap, and a feasible adjustment using the task's criteria. Prioritize rather than overload. When revision is selected, wait for it and inspect the latest answer or artifact, including newly introduced problems. End when the applicable criteria or authored practice boundary is met.
- **Whole-round question practice:** Keep answers unrevealed during a round. At its end, derive and reconcile item results, total, and the wrong-item set from the same actual responses and answer criteria; natural-language scoring is not guaranteed to be exact. Retain original item identities and standards when retrying only still-incorrect items; do not silently substitute new questions. Stop when no wrong items remain or the selected boundary is reached. Correction of these items alone shows neither transfer nor durable retention.
- **Consolidation and transfer:** Choose recall, application, varied conditions, or a delayed revisit for the intended evidence. Let the learner attempt before showing the answer. A new task can expose dependence on the original example; a later check can address retention. Arrange timing and follow-up only within actual delivery support, without assuming automatic reminders.
- **Explain to a beginner:** Treat a Feynman-style explain-to-a-novice task as one form of [self-explanation](#method-attribution). Specify whom the learner is trying to teach and the concept's accuracy criteria. Ask for the learner's own explanation, locate a concrete conceptual or reasoning gap, offer focused help, and wait for a revised explanation if needed. Stop once the required idea and conditions are explained adequately; do not keep requesting rewording for its own sake. A simulated novice's questions are instructional role-play, not evidence that the learner has taught a real peer.
- **Socratic questioning:** Choose the next question from the actual position and its unresolved definition, reason, evidence, assumption, alternative, or consequence. Accept a justified retained view as well as a revision, and preserve unresolved tradeoffs when appropriate. Stop when the relevant judgment is clear enough for the goal rather than extending questions indefinitely.
- **Interactive inquiry:** Make the model and exploration purpose clear. When useful, elicit a prediction, change a consequential condition, compare observations, and relate the result to the mechanism and its limits. Let the selected inquiry use its actual operation surface; do not add a text submission merely to imitate other methods. Without operation readback, use learner-provided observations and state that limit.

### When Practice Does Not Reach the Goal

For repeatable practice, make a feasible stopping boundary explicit in the authored activity. Reuse the author's limit; if none is set, choose a proportionate boundary from the task and available lesson time, without imposing a universal round count or claiming to measure elapsed time without support. The Teaching Prompt owns the executable response paths.

When attempts show no progress or the learner repeatedly says "I don't know," identify the unresolved step and change the support rather than repeating the same demand. Within the author’s constraints, a smaller step, prerequisite explanation, or worked demonstration may help. If the learner asks to stop or skip, stop soliciting retries and identify the unresolved gap. Respect any required completion criteria: pausing or leaving a practice activity does not count as passing it or authorize bypassing a course gate.

For example, after repeated difficulty separating a proposal from a decision, the learner says "I still can't tell; stop this exercise." Acknowledge the stop, briefly identify the remaining distinction, and offer a concise explanation or a later return only if permitted and wanted. Do not fabricate a corrected answer, insist on another submission, or report independent success because the learner has seen a demonstration. Distinguish exposure, supported completion, and independent performance under the evidence rules below.

### Match Evidence to the Claim

Distinguish exposure, explanation, supported completion, independent performance, transfer, and delayed retention. Also distinguish a simulated exchange, actual execution, and improvement in the real problem. Independence concerns the target judgments under permitted conditions and aids; it need not mean working without software or a job aid. Do not count work done by the AI as learner performance. Use suitable process observation for physical or device skills, with an appropriately qualified instructor or professional where needed; a written account cannot replace action evidence.

File access, screen or audio observation, code execution, operation readback, precise timing, reminders, and later feedback depend on the actual delivery setup. Authoring tools do not establish these learner-time capabilities. If they are unavailable, work from the materials actually supplied and identify what has not been observed or verified. A paper design or platform preview does not establish learner effectiveness.

### Course Entry

An opening can establish the course purpose, topic, or verified background about its teacher. This content is distinct from the Teaching Agent greeting the learner or introducing itself; preserve the [Course Prompt template](course-prompt.md#fillable-template) constraints on those behaviors. Determine entry position from actual course order rather than a lesson-id convention.

### Lesson Loop

Examples of possible lesson shapes:

- Setup → explanation → interaction → close.
- Setup → explanation → worked application or consolidation → close.
- Task → attempt → feedback → explanation.
- Demonstration → comparison → practice.

Adapt the shape to the learning need; its opening, closing, and included elements can differ across lessons.

### Teaching Patterns

| Approach | Possible progression | Useful when |
| --- | --- | --- |
| Evidence Chain | Phenomenon → mechanism → implication → application | The learner needs to connect an observation to an explanation and action. |
| Misconception Repair | Plausible misconception → mechanism and boundary → corrected case | A predictable false model obstructs understanding. |
| Comparison-Driven Learning | Baseline case → changed condition → comparison → updated decision | Contrasting cases makes a distinction or boundary visible. |

Each shape can use interactive or non-interactive actions under the interaction policy.

### Method Attribution

The labels in [Teaching Patterns](#teaching-patterns) describe local lesson shapes, not established research-method names. Do not attribute a whole shape to a study that supports only one component. When selecting or applying a named teaching method, tell the teacher its name, a reliable supporting source link, why it fits this learning need, and the relevant evidence limit. A university teaching guide can explain a method without being its original inventor; name an originator or publication year only when the source supports that attribution. Explain the recommendation using [course-design-choices.md](course-design-choices.md#explaining-a-recommendation), proportionately to the task, without repeating the same citation in every lesson. Possible grounded choices include:

| Strategy and source | Supported principle and evidence boundary |
| --- | --- |
| Worked examples and self-explanation — [MIT Teaching + Learning Lab](https://tll.mit.edu/teaching-resources/how-people-learn/worked-examples/) | Initial skill acquisition, explaining solution reasoning, fading support, and avoiding redundant support for proficient learners. The self-explanation guidance concerns worked examples, not validation of every local explain-to-a-beginner activity. |
| Retrieval practice — [Washington University Center for Teaching and Learning](https://ctl.wustl.edu/resources/using-retrieval-practice-to-increase-student-learning/) | Attempting to recall or apply taught knowledge before seeing the answer, with corrective feedback. Repeating a displayed answer is not retrieval; term recall does not establish complex performance. |
| Prior-knowledge assessment — [Carnegie Mellon's Eberly Center](https://www.cmu.edu/teaching/designteach/teach/priorknowledge.html) | Adjusting content, difficulty, or support using prior knowledge; distinguishing direct from indirect measures. Reusing sufficient existing evidence is a local application of this guidance. |
| Case-based learning — [Columbia Center for Teaching and Learning](https://ctl.columbia.edu/resources-and-technology/resources/case-method/) | Applying concepts to contextual decisions, including role-play as a possible activity. A story followed by its answer is not learner case analysis; classroom guidance does not supply peers or a live instructor in individual delivery. |
| Scaffolding — [van de Pol, Volman, and Beishuizen's review](https://doi.org/10.1007/s10648-010-9127-6) | Contingency, fading, and transfer of responsibility. These mechanisms support a rationale, not a validated AI hint ladder or fixed hint count. |
| Formative feedback — [Shute's review](https://doi.org/10.3102/0034654307313795) | Specific, supportive information, including hints and examples, with an opportunity to use it. Timing and form depend on context; the review does not validate every local revision loop. |
| Socratic questions — [University of Connecticut CETL](https://cetl.uconn.edu/resources/teaching-your-course/leading-effective-discussions/socratic-questions/) | Question types for clarification, assumptions, reasons, perspectives, and consequences. This guide does not establish gains from an unbounded dialogue or predetermined conclusion. |
| Interactive simulations — [PhET research](https://phet.colorado.edu/en/research) | Exploring conditions and connecting observations to explanation in particular simulation designs and uses. It does not validate every interactive page or establish AI access to page actions. |
| Study and practice organization — [Pashler et al., IES practice guide](https://ies.ed.gov/ncee/wwc/PracticeGuide/1) | Spaced revisits (recommendation 1) and alternating worked examples with problem solving (recommendation 2). These do not establish a universal optimal interval or benefits for arbitrary mixtures of question types. |
| Interleaved problem types — [Rohrer and Taylor (2007)](https://doi.org/10.1007/s11251-007-9015-8), [MIT practice guide](https://openlearning.mit.edu/mit-faculty/research-based-learning-findings/spaced-and-interleaved-practice) | Experiment 2 studied mixed mathematics practice after initial instruction with a one-week test; MIT explains the discrimination rationale. This does not establish benefits for every subject or mixtures of untaught material. |
| Role-playing — [Carnegie Mellon's active-learning strategies](https://www.cmu.edu/teaching/resources/instructionalstrategies/activelearningstrategies/index.html) | Taking stakeholder roles to compare perspectives or practice contextual expression. An AI role supplies a simulation, not actual peers or evidence of workplace outcomes. |
| Project-based learning — [PBLWorks design framework](https://www.pblworks.org/gold-standard/pbl-project-design) | Challenging problems, sustained inquiry, authenticity, learner choice, reflection, critique and revision, and a public product. These are design criteria, not evidence that a finished artifact implements the full framework or improves learning. |

These sources guide a reasoned choice; they do not guarantee a particular learner's result or authorize new interactions. An author-specified approach can be used directly. Verify a reliable source before presenting another approach as an established named method; if the attribution cannot be verified, describe the concrete teaching action without the label. Keep method names, research rationale, and authoring decisions in author-facing explanations rather than making the Teaching Agent teach pedagogical theory unrelated to the course.

### Cognitive Techniques

Calibration judgments, boundary checks, counterintuitive contrasts, action translation, and reflection can deepen understanding. Use them for an identified learning need, with or without collecting an answer.

### Combining Approaches for Applied Tasks

Select a main approach and only the supporting actions needed for the current obstacle. The combinations below are local design examples, not tested AI-Shifu course results. Reuse actual drafts and records, shorten support for demonstrated skills, and address missing prerequisites or real resource barriers before adding more teaching.

- **Workplace scenario practice:** Supply the role, goal, constraints, and acceptable behaviors. Let the other role respond to what the learner actually says. If help is needed, clearly pause the role-play, give a targeted cue, then resume. Rehearse a consequential turn or vary a constraint; distinguish simulation from later workplace evidence.
- **Errors and exam preparation:** Use the actual question, answer, and available reasoning or time records to distinguish known errors from hypotheses. Choose per-item coaching or whole-round practice for the intended feedback timing. After repair, use an appropriate new or mixed task, or a delayed check when selected; original-item correction alone is not exam readiness. Do not invent timing or attribute score changes to one strategy without evidence.
- **Project work:** Establish a useful output and criteria, retain necessary prerequisites, and start from an existing draft or a feasible first version. Add knowledge at the current obstacle, then return to the same artifact for feedback and revision. Arrange actual peers, users, or external audiences when the design needs them. Shared work should require meaningful integration; assess individual understanding separately from team quality.
- **Software practice:** Connect the task, input, environment, expected output, and checks. Demonstrate a critical operation when needed. For a failure, compare expected and actual results, test one plausible cause with a small change, inspect the result, and finally rerun the original task. Preserve useful original inputs. Without access or execution evidence, do not claim to have inspected the learner's screen or verified a fix; software feedback does not establish physical action quality.

### Examples and Analogies

Use examples or analogies to address a comprehension need, such as abstraction, an unfamiliar mechanism, a confusing distinction, or transfer to action. Reuse an existing demonstration when it already serves that need.

- Examples need enough situation, conditions, and reasoning or action steps to show how the concept works. Connect the result back to the intended understanding.
- Analogies need a useful correspondence and relevant limits. Return to the target concept and its evidence; an analogy is not proof of the claim.
- When the relevant personalization direction is selected, use meaningful learner tasks, situations, or constraints under [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions). A role label alone does not establish familiarity. Otherwise use the course baseline.

### Personalized Teaching Within the Resolved Directions

Apply the resolved directions and fallback rules from [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions). Use relevant personal background, learning preferences, and course memory under [existing-information reuse](teaching-prompt.md#encode-existing-context-reuse). The purpose is to make a relationship, practical consequence, or permitted form of learning support fit the learner's task. Background-based personalization differs from responding to performance through authored feedback paths; [learner evidence and responsive support](prompt-semantics.md#learner-evidence-and-responsive-support) owns that distinction and evidence precedence.

For example, with Examples selected: "When explaining sampling bias, if relevant learning memory explicitly says the learner reviews only returned questionnaires, use that task to explain why nonrespondents may affect the conclusion. Preserve the example's required conditions, reasoning, and conclusion. Without relevant context, use the course's neutral questionnaire example." The stated task makes the missing responses concrete; a profession label alone would not establish that connection. The fallback must still teach the same concept.

With Learning support selected, a stated preference for trying a task before seeing a worked explanation can inform a locally permitted attempt-first path; a preference for explanation first can inform the supported path. Neither preference proves ability. After an actual attempt, choose help from the demonstrated gap and reduce it when the learner can proceed. For example, someone who treats an authentic citation as sufficient evidence needs help comparing the cited passage with the particular conclusion; someone who already makes that comparison may need practice checking the scope of the inference. Keep the same required evidence standard and do not infer a misconception from an unexplained answer. A lesson may use these choices only where its authored constraints allow them; no universal sequence or diagnostic is implied.

## Interaction Design

For a selected interaction, make the question concrete and answerable and give the answer a visible effect: feedback, a branch, an adjusted example, practice, reflection, or a usable result. Do not collect answers that teaching never uses.

- Single-select suits mutually exclusive choices; multi-select suits non-exclusive interests, goals, blockers, or other "which apply?" questions.
- Free text suits information that predefined categories cannot capture well. A specific question and a concise input hint usually work better than an open-ended invitation with no purpose.
- Context-dependent choices can be generated at learner time when useful alternatives depend on the current case, discussion, or prior answers. Define what the learner should decide and how the answer will be used; preserve any author-fixed choices. This is an alternative to prewriting options, not a requirement for every interaction.
- Multi-select can use combined feedback or prioritization; it does not require an exhaustive branch for every combination.
- If a choice is intended to drive distinct next steps, provide the corresponding response behavior. Honor an explicit answer-specific branching requirement.
- Choose interaction placement and number for their teaching value and the author’s scope.

Questions, controls, feedback, and branches must remain executable together. [teaching-prompt.md](teaching-prompt.md) owns their source encoding; [markdownflow-syntax.md#interactions](markdownflow-syntax.md#interactions) owns control syntax.

## Using Memory

Use relevant earlier learner input to connect explanations, feedback, examples, and reflection to what the learner actually said. The runtime memory contract belongs to [markdownflow-syntax.md#memory](markdownflow-syntax.md#memory); express the teaching use naturally, such as revisiting the learner's stated goal or comparing an earlier attempt with the current answer.

Avoid asking for personal background, learning preferences, or course answers already available in memory unless a deliberate update or staged comparison serves the lesson. Follow [existing-information reuse](teaching-prompt.md#encode-existing-context-reuse), [interaction policy precedence](#interaction-policy-precedence), and the personalization boundaries in [prompt-semantics.md](prompt-semantics.md).

## Visual-Text Coordination

Choose visuals for a teaching purpose: orient the learner, focus attention, organize knowledge, explain relationships, expose reasoning, support a task, or prepare later application. When the author leaves the form open, the authoring agent may select board-style work, illustrations, slides, or a mixture and make those choices concrete in the Teaching Prompt. A text-only lesson may already serve the goal; choose each visual for the additional teaching value it provides.

### Situations Worth Considering

Use these situations to identify what the learner needs to see, understand, or remember. A visual may serve several purposes; a short text heading or inline emphasis may suffice.

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
- **Slide or reference page:** Use a shared view for an overall comparison, a focused conclusion, task instructions, or information to consult. Slides can also animate a dynamic process or provide controls for exploring parameters and comparing experimental effects. Choose motion or interaction when the changing state or causal relationship helps the learner understand the material, and encode it under [slide interaction and animation](teaching-prompt.md#slide-interaction-and-animation). A slide can use text, diagrams, or evidence; it does not require decorative imagery. Prepared visuals and board-style annotations can be combined.

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
