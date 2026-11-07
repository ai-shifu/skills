# Teaching Prompt

Write or revise one runnable per-lesson Teaching Prompt from a topic, brief, source material, existing Prompt, or supplied design. Use the available context directly; a segmentation schema, separate planning run, Course Prompt, or fixed intermediate JSON is not a prerequisite. The authoring agent chooses teaching strategies and expresses them using the [author-editable layout](#author-editable-layout); the learner-time Teaching Agent follows the resulting instructions.

Shared Prompt meaning and artifact boundaries are in [prompt-semantics.md](prompt-semantics.md), runtime syntax in [markdownflow-syntax.md](markdownflow-syntax.md), optional author controls in [authoring-contracts.md](authoring-contracts.md), and teaching suggestions in [teaching-design.md](teaching-design.md). Consult [image-authoring.md](image-authoring.md) for actual image assets and [source-preservation.md](source-preservation.md) for selected exact material.

## Lesson Materialization

- Tell the Teaching Agent what to teach, show, ask, and respond, with enough content, reasoning, boundaries, and intended effects to execute. Prompts are instructions rather than mandatory spoken transcripts or finished learner prose.
- Use the user's objectives, source requirements, intended audience, and explicit design choices. Carry confirmed learning goals, representative-sample decisions, and later teacher corrections into every affected lesson rather than reverting to an earlier draft or copying the sample's surface layout everywhere. Preserve a supplied approved teaching plan instead of silently replacing it. If it contains a material contradiction, identify the affected decision and ask or complete independent work as appropriate.
- Choose a suitable teaching path from the content and goal. Examples, analogies, practice, interactions, slides, openings, and closes serve that path; no prescribed pattern, step count, interaction quota, core-question count, or visual cadence is a universal requirement.
- Make needed explanations concrete: identify the facts or steps, relationships, relevant limits, and understanding or application to reach. An empty instruction such as "explain the concept" or "add an example" is insufficient when it leaves those matters unresolved.
- When a delivery mode is specified, honor it. Classroom slides need usable projected content and instructor pacing; text-only requests exclude visuals. Select useful visual purposes, media, and unfolding under [visual-text coordination](teaching-design.md#visual-text-coordination) when the user has left those choices open.
- Give each included visual executable instructions for its necessary content, teaching purpose, focal information, and any selected construction or reveal order. Position-specific slide treatment belongs in this lesson; presentation rules shared by every slide belong in the Course Prompt. A cover, greeting, summary, or visual-and-explanation rhythm may be useful without being mandatory.
- For an instructional interaction, keep its question or generation instructions, response requirements, and intended feedback or visible instructional effect together. Honor author-requested branching and disabled interactions. A question slide is optional unless requested; the real interaction remains the response surface.
- When the selected design uses a learning task to demonstrate the goal, specify what the learner does, what counts as a satisfactory result, and how feedback addresses the actual response, including a useful next attempt when selected. A recall question alone cannot demonstrate an application goal. Follow [teaching-design.md](teaching-design.md) for goal, task, and evidence alignment; this does not require a test in every lesson or override disabled interactions.
- Keep reusable learner context out of reusable course artifacts except through the authorized runtime mechanisms. A lesson can stand alone without a Course Prompt; include the concise runtime guidance it needs and identify any genuine unresolved cross-artifact conflict.
- Keep requests for teacher materials, sample-approval instructions, production notes, and teaching-method rationale or provenance in teacher-facing communication rather than runtime Prompt prose. Source content needed by the learner remains part of the lesson; a method citation becomes lesson content only when the author actually requests teaching it.

## Personalization Directions

Apply the shared effects and boundaries in [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions). Explicit selections, including an empty selection, are author constraints. Where the author has left design open, the using agent can choose suitable behavior without a compulsory selection question or plan-then-generation phase.

For an enabled example or analogy direction, give the Teaching Agent enough selection criteria, essential reasoning or correspondence, limits, and intended takeaway to adapt the expression using relevant known learner context. Keep an author-fixed example or analogy and adapt only what that author permits. Use a neutral course-appropriate fallback when relevant context is unavailable.

Make each selected direction executable at the position where it matters: state which relevant, already available learner input may affect which permitted teaching expression or support, and what to do when that input is missing or irrelevant. Keep this selection executable when personal background and learning preferences arrive only at learner time through [memory](markdownflow-syntax.md#memory). A generic instruction to "personalize the lesson," or replacing a name or occupation while leaving the example unrelated to the learner's task, is insufficient. For example, an adapted cost example can use a learner's stated sales task and constraints to explain the same cost relationship. Clearly labeled hypothetical teaching figures are allowed; do not present them as the learner's actual data, replace author-fixed figures, or change the required reasoning. Language and practical-value adaptations need the same concrete connection to stated preferences or goals under the shared direction semantics.

Express practical value at a useful teaching position and language style at the appropriate artifact scope. For Learning support, identify a useful local choice of explanation entry point, terminology support, hint presentation, or practice conditions and the relevant background or preference that can inform it. Do not treat concise language as permission to omit reasoning or an occupation as demonstrated proficiency. Do not add collection questions or an interaction quota merely because personalization is enabled. Keep adaptations within the shared boundaries rather than granting unrestricted learner-time redesign.

Check an available Course Prompt for genuine conflicts with the lesson. Report an unavailable or out-of-scope companion check as not assessed; it does not block writing or reviewing the supplied lesson. Keep selection field names, enum arrays, planning rationale, and comparisons between variants out of runtime Prompt prose.

### Encode Existing-Context Reuse

At the relevant teaching position, tell the Teaching Agent to use personal background, learning preferences, and current-course answers already available in memory before asking. If the lesson needs a current task, for example, use an already stated task directly; only when it is unavailable and the author permits input, ask which task the learner wants to work on and then use that answer. Do not prewrite an unconditional role, style, or goal question just because future learners' background and preferences are unavailable during authoring.

Keep the conditional question, its permitted scope, the use of an actual answer, and the fallback together. With partial memory, ask for the consequential gap alone; with no relevant memory, teach neutrally unless that gap is required for the selected activity. A standalone Teaching Prompt needs enough local guidance to do this without relying on an omitted Course Prompt. Do not copy a test learner's background, platform profile tags, or internal field names into reusable runtime instructions. Preserve the separation between reusing a stated goal and checking performance through a new task.

Before a necessary context question, instruct the Teaching Agent to tell the learner briefly how the missing detail will be used in the current activity. A purpose written only in source comments, execution notes, an unspoken lesson title, or a later explanation does not explain the request to the learner. This is a local reason for the question, not a required course opening or a new background questionnaire.

### Make Response-Dependent Support Runnable

Apply [learner evidence and responsive support](prompt-semantics.md#learner-evidence-and-responsive-support) to the actual learning task, including when background personalization is explicitly disabled. When the selected task calls for practice, write what counts as an adequate answer, how to distinguish a submitted misconception from an incomplete answer, which support or practice changes are permitted, and when to stop. A generic "give personalized feedback" instruction leaves the teaching decision unresolved.

Use correct answers to acknowledge what was demonstrated and avoid redundant hints. For a real error, target the submitted reasoning before increasing help; for an omission, identify what is missing without assigning a belief the learner did not express. State how another actual answer changes support, whether a source-compatible practice variation is useful, and when sufficient performance or an authored limit ends the activity. Keep author-fixed questions, standards, and hint stages intact. Respect a request to stop without claiming that unfinished work passed, using [non-achievement closure](teaching-design.md#when-practice-does-not-reach-the-goal).

These choices belong at the relevant teaching position, not in a mandatory lesson skeleton. Existing answers can supply evidence without a new diagnostic question. A non-interactive lesson can adapt its explanation to available background but cannot invent observed answers, add prohibited exercises, or claim mastery. Use only current conversation and actually available memory; adapting teaching does not update the learner profile.

## Author-Editable Layout

For every newly written or explicitly rewritten Teaching Prompt, use source-only explanatory comments and write ordinary Teaching Agent instructions as Markdown unordered-list items unless the author explicitly requests a different source layout. In an audit, leave existing formatting intact. In a focused repair, preserve the existing layout and comments except where the requested repair requires a change.

### Required Comments

- Put a concise standalone `<!-- ... -->` comment before each meaningful teaching block. Explain the block's teaching purpose or the change in understanding, judgment, capability, or readiness it should produce.
- Choose useful editing units from the actual lesson; a block need not correspond to a slide, a visual-text pair, or a fixed lesson phase.
- Use naturally worded labels that distinguish neighboring blocks. Prefixes, numbering, punctuation, and sentence form are optional.
- Keep all facts, teaching instructions, memory-use instructions, options, URLs, exact spans, feedback, and branch rules outside comments, consistent with the [runtime comment semantics](markdownflow-syntax.md#html-comments). Essential content must remain complete when comments are ignored.
- Keep the interaction question and unchanged standalone control, or its natural-language generation instructions, together with immediate feedback in one editing unit rather than inserting navigation comments inside that sequence.
- Do not put the literal delimiters `<!--` or `-->` inside a comment body.

### Instruction Lists

- Use one concise top-level item per independent teaching action, in learner-time order. For example, a slide can be a top-level action with its content and presentation constraints beneath it.
- Nest separable details, substeps, constraints, or feedback cases beneath the action they support. Keep a simple action flat. The hierarchy helps the teacher scan and edit one part at a time while preserving the intended teaching sequence and detail.

```markdown
<!-- The learner can distinguish fixed and variable costs -->

- Explain fixed and variable costs to the learner.
  - Use rent as the fixed-cost example and raw materials as the variable-cost example.
  - Explain that the distinction concerns how total cost changes with activity over the stated period.

===In this example, assume rent stays fixed over the period being discussed.===

- Ask the learner to consider which assumptions make those examples valid.
```

## Source Encoding

Encode the chosen teaching design without changing author requirements or exact material. Parser recognition and runtime effects belong to [markdownflow-syntax.md](markdownflow-syntax.md).

### Layout Encoding

Keep syntax-owned and exact structures in their required form and position. Leave standalone `?[]` controls, `===...===` lines, multi-line fences with standalone `!===` delimiters, Markdown images, tables, and fixed-display image lines free of added list markers or indentation. Resume ordinary instructions at the top level after a standalone structure. Preserve any list markers and indentation that belong to exact source content.

Keep ordinary fenced code outside the list by default. When the author explicitly requests a fence inside a list item, use the indentation required for that item only if the target runtime recognizes the complete fence and exact-source requirements permit the indentation. Preserve the fence, language tag, and code content.

For a format-only rewrite, verify that removing only the added comments, list markers, and layout indentation recovers the original content and order. This is an authoring check. The list formatting is ordinary Markdown in the Teaching Prompt.

### Interaction Encoding

- Choose an [explicit control or natural-language interaction](markdownflow-syntax.md#interactions) according to the intended behavior. Preserve author-fixed questions and choices; when dynamic generation is requested, keep that generation instruction executable at learner time rather than replacing it with an author-time option list.
- Use target capabilities already established by the user or available course context. Natural-language interactions need the [response-surface and waiting capabilities](markdownflow-syntax.md#natural-language-interactions). An explicit-control fallback is suitable only when it preserves the author's requirements. If dynamic choices remain required and support is unavailable or unknown, retain that requirement and identify the runtime dependency. Local authoring can still produce the Prompt with that dependency stated; it does not require platform access.
- Keep explicit `?[]` controls standalone, with option wording and order in the actual control; avoid competing simulated controls. A complete learner-facing question or response task in the [question prefix](markdownflow-syntax.md#question-prefix) is sufficient: repeating it before the control is optional unless the author explicitly requires separate text.
- When generating a new explicit control for a question or response task, fill the question prefix with that complete learner-facing question or response task. Preserve its wording and punctuation rather than using a programmatic key, topic label, answer, or unfilled placeholder. This keeps the response associated with what the learner was asked. When a fixed item supplies only a statement to classify, preserve that statement verbatim inside the complete classification question or response task; an item label and statement alone do not replace the task. For example, write `?[ {{Which action will you take first?}} Verify the source | Check the calculation]`. Preserve an author-supplied exact control unless the requested change includes revising it.
- In explicit controls, use `|` for single-select, `||` for multi-select, and `...` immediately before the input hint or custom-answer label, according to the required answer semantics. For input, put the complete learner-facing question or response task in the prefix and use a short hint. For select-plus-input, put `...` at the start of the custom-answer option.
- For a natural-language interaction, describe the intended learner decision or task, the context used to generate the question or options, and any required answer mode or option constraints. Keep these instructions outside `?[]`, comments, and deterministic blocks. Specify how the actual answer affects the next teaching action; do not invent the learner's answer or continue before it arrives.
- When teaching uses an earlier answer, describe the relevant input and its instructional effect naturally under [Memory and Branch Encoding](#memory-and-branch-encoding).
- An action-only control such as `?[Continue]` advances the preceding content and does not require an invented question or slide.
- The prompt immediately after an interaction can describe how to respond to different answers and, when needed, ask the learner to interact again, using the [runtime follow-up behavior](markdownflow-syntax.md#branching-on-user-input).

For example:

```markdown
<!-- This activity checks whether an action plan specifies the action, owner, and deadline. -->

?[ {{Rewrite "Organize customer feedback" as a plan with a specific action, an owner, and a deadline.}} ...State who will do what and by when]

- Respond based on the learner's answer.
  - If all three details are present, explain why the plan is clear, then continue with the subsequent content.
  - If a detail is missing, identify it and give a hint. Initiate another interaction and ask the learner to complete the plan. Wait for the learner's actual response, then respond to the new answer using the same criteria.
```

### Memory and Branch Encoding

- Use natural-language branch instructions; MarkdownFlow has no programmatic conditional syntax.
- Refer to the learner's actual answers naturally, using relevant memory under [markdownflow-syntax.md#memory](markdownflow-syntax.md#memory).
- Describe how the earlier input affects teaching, for example, "Use the learner's stated goal from memory to explain why this exercise matters."
- If the needed information is unavailable or irrelevant, use the course-appropriate fallback rather than inventing an answer.
- Prompt prose carries the teaching response, not an explanation of the machine-facing encoding decision.

### Slide Interaction and Animation

AI-Shifu slide generation supports in-slide interaction and animation as a basic capability. Describe the intended behavior directly in the Teaching Prompt's slide-generation instructions; a separate static image or prebuilt external page is not required. Use the chosen teaching purpose to specify the relevant details:

- **Interaction:** Which elements can be operated, such as buttons, sliders, draggable objects, or selectable cases; what each action changes; and any meaningful input ranges, initial values, or reset behavior.
- **Animation:** What moves or changes, in what order, and what triggers it, such as automatic playback, a click, or a parameter change. Specify timing, stepping, pause, or replay when needed to follow the process.
- **Observable result:** What the learner should compare or notice, with labels and a readable state for inspection. For an experiment or simulation, include the model, assumptions, units, and relationships that determine the displayed effect rather than requesting decorative motion or arbitrary results.

For example:

```markdown
<!-- Comparing rates makes queue growth visible -->

- Generate an interactive experimental slide showing a simplified queue. Use fixed arrival and service rates, an initially empty queue, no random variation, and a continuous quantity model: queue length at time t minutes is max(0, (arrival rate - service rate) * t).
  - Provide arrival-rate and service-rate sliders from 0 to 10 people per minute, initially 5 and 6. Changing either rate resets the model time and queue to zero, pauses playback, preserves earlier traces as comparison history labeled with their arrival and service rates, and starts a new current trace at the origin.
  - Provide Play, Pause, and Reset controls. Animate model time from 0 to 2 minutes, plotting queue length against time with labeled axes and current rate values. Pause preserves the current graph; Reset restores the initial rates and empty queue, sets model time to zero, clears the graph, and pauses playback.
  - Keep the current settings and graph visible so the learner can compare arrival below service with arrival above service, and then compare the effect of increasing service. Keep all exploration within the slide; do not add a course question or submission.
```

Describe the requested behavior without claiming that the slide has already been generated or tested. Course-answer collection and memory integration follow [Simulation Integration](#simulation-integration).

### Simulation Integration

For a selected interactive-page activity, specify the model, assumptions, adjustable quantities, observable changes, and comparisons needed for its teaching purpose. Identify executable HTML or JavaScript, usable controls, and any required page-to-course event bridge as target capabilities to verify; a page-generation instruction alone does not establish them.

Do not treat a slider movement, animation, page-local button, or page-local answer as a recorded course answer without an established integration. When an authored feedback path or later teaching needs the learner's observations, collect them through a real course interaction within the permitted interaction scope, or use a verified integration. State how the actual submission will be used under [Memory and Branch Encoding](#memory-and-branch-encoding). An exploration without a course submission can remain an activity, but do not invent observations or claim that its page events entered course memory.

### Preservation Encoding

Use [source-preservation.md](source-preservation.md) to identify the selected exact span and authoritative source. No segment record or character-offset JSON is required.

- Use standalone `===...===` for deterministic output of a complete single-line span.
- Use paired standalone `!===` delimiter lines for multi-line deterministic output, including the original code fence and language tag when required.
- Inline `===...===` preserves a position-sensitive span within generated content.
- Keep adaptive content outside deterministic markers and preserve each selected span at its intended runtime position.

## Teaching Strategy Examples

Use [approach selection](teaching-design.md#selecting-an-approach-for-the-learning-task) for the teaching decision and [source encoding](#source-encoding) for its representation. The examples below show complete local fragments for the same supplied cost model under different goals or starting knowledge. They are alternatives, not a required sequence, difficulty ladder, or quota of interactions. Explanations of why a strategy was selected stay outside the runtime fragments, under the [method attribution rules](teaching-design.md#method-attribution).

The shared material is a hypothetical order: total cost equals fixed cost plus per-unit variable cost times quantity; fixed cost is 100 yuan, variable cost is 5 yuan per unit, and 20 units cost 200 yuan. The model assumes those cost terms remain unchanged over the stated quantity range and there are no other charges. Each fragment carries the facts it needs. The example-specific follow-up limit prevents an unbounded retry here; it is not a course-wide interaction policy.

### Same Material, Goal of Explaining the Relationship

For beginners whose goal is to explain how quantity affects total cost, use a concrete comparison and ask for the relationship. This checks explanation rather than independent quote production. The teacher has allowed one response and no follow-up question.

```markdown
<!-- Use a concrete order to connect the two cost types to quantity -->
- Use an explicitly labeled hypothetical teaching order to explain: total cost = fixed cost + per-unit variable cost × quantity.
  - The fixed cost is 100 yuan and the per-unit variable cost is 5 yuan; 20 units cost 200 yuan in total.
  - State the assumptions: both cost terms remain unchanged over the quantity range being discussed, and there are no other charges.
- Compare 20 units with 30 units. Total cost increases from 200 yuan to 250 yuan because of the variable cost of 10 additional units.
  - Explain that the fixed cost is still counted only once and show how each term in the formula corresponds to the order.

<!-- Check whether the learner can explain why the cost changes -->
?[ {{With the assumptions above unchanged, why does adding 10 units increase total cost by only 50 yuan, without adding the fixed cost again?}} ...Explain which costs change and which remain unchanged]

- Wait for the current actual answer, then give feedback:
  - If the learner explains that the fixed cost stays unchanged and each additional unit adds 5 yuan, identify the reasoning they got right.
  - If they count the fixed cost again, explain that it is counted only once in this order model, and explain the additional costs item by item.
  - If they give another clearly incorrect explanation, identify the specific error and explain the relevant cost relationship using the quantities in this order.
  - If they only repeat "an increase of 50 yuan" or their reasoning is unclear, explain that the correct number alone does not demonstrate understanding of the cause, and explain the cost relationship.
- Do not ask another question. Close with one sentence returning to the formula and its assumptions; do not claim that the learner can now produce a quote independently.
```

### Same Beginners, Goal of Producing a Quote

When the goal changes to calculating a quote and stating its assumptions, a worked example makes the procedure visible before an independent attempt. Unlike the explanation variant, do not disclose the target calculation before the response. The teacher permits one supported revision after feedback.

```markdown
<!-- Show a complete calculation and the reasoning behind each step -->
- Use a hypothetical teaching order to demonstrate: total cost = fixed cost + per-unit variable cost × quantity.
  - The fixed cost is 100 yuan and the per-unit variable cost is 5 yuan; for 20 units, the variable cost is 5 × 20 = 100 yuan.
  - Add the fixed cost of 100 yuan, counted only once, to obtain a total cost of 200 yuan.
  - Explain which cost each step represents, and state that the model requires unchanged cost terms over the quantity range being discussed and no other charges.

<!-- Independently quote another quantity and state the assumptions -->
?[ {{Using the model with a fixed cost of 100 yuan and a per-unit variable cost of 5 yuan, produce a quote for an order of 30 units. Show your calculation and state the assumptions under which the quote holds.}} ...Write the calculation, total cost, and assumptions]

- Wait for the current actual answer. Use the following criteria only for feedback after receiving it; do not show them beforehand:
  - The complete result is 100 + 5 × 30 = 250 yuan; the assumptions include unchanged cost terms and no other charges.
  - If the calculation, amount, and assumptions are all correct, identify what is correct and end the exercise.
  - If the calculation is set up correctly but contains an arithmetic error, identify where it occurs; if the fixed cost is counted again or a cost is omitted, explain the relevant cost.
  - If the learner gives only 250 yuan or omits assumptions, acknowledge the correct parts they supplied and identify the missing calculation basis or assumptions, without inferring a misconception.
  - If a stated assumption contradicts the model, acknowledge any correct calculation and explain which assumption fails and how it affects the quote.
- If the answer does not meet the criteria, give a hint targeted to the gap and initiate one text-input interaction asking the learner to revise or complete the quote.
- Wait for the actual revision, give feedback using the same criteria, and end. If gaps remain, provide a complete demonstration and identify what remains unresolved.
- Do not continue looping or treat seeing the demonstration as independent performance.
```

### Same Quote Goal, Learners Already Able to Use the Formula

For learners with supplied evidence that they already use this formula, keep the quote goal and success criteria but remove the initial step-by-step demonstration. A direct application can reveal whether help is needed. Here the teacher permits one follow-up; an authored feedback path supplies targeted help rather than letting the Teaching Agent freely redesign the lesson.

```markdown
<!-- Use existing skills to produce a quote and reveal where help is needed -->
- Briefly state the hypothetical teaching order model: total cost = fixed cost + per-unit variable cost × quantity.
  - The fixed cost is 100 yuan and the per-unit variable cost is 5 yuan; the given total cost for 20 units is 200 yuan.
  - The model assumes unchanged cost terms over the quantity range being discussed and no other charges.
- Do not demonstrate the calculation steps first or disclose the result of the task below in advance.

?[ {{Using the model with a fixed cost of 100 yuan and a per-unit variable cost of 5 yuan, produce a quote for an order of 30 units. Show your calculation and state the assumptions under which the quote holds.}} ...Write the calculation, total cost, and assumptions]

- Wait for the current actual answer, then give feedback using these criteria:
  - The complete result is 100 + 5 × 30 = 250 yuan, with unchanged cost terms and no other charges stated as assumptions.
  - If the result, reasoning, and assumptions are correct and complete, briefly confirm the reasoning and end; do not add a full introductory explanation.
  - If there is an arithmetic or cost-classification error, explain the relevant steps for that actual error, then ask the learner to revise the quote.
  - If the learner gives only an amount or unclear reasoning, identify the missing basis and ask them to supply it; do not conclude that they cannot calculate merely because the answer is incomplete.
  - If a stated assumption contradicts the model, acknowledge any correct calculation, explain how the assumption affects the quote, and ask the learner to revise it.
- When revision or additional information is needed, initiate one real text-input interaction and wait for the answer. Give feedback on that new answer and end.
- If the criteria are still unmet, provide the relevant explanation or complete calculation and identify the remaining gaps; do not retry indefinitely or claim mastery has been demonstrated.
```

The first pair changes the target performance for the same audience; the second pair keeps the quote task and criteria while changing the assumed starting knowledge and support. The differences should be visible in instruction and feedback, not only method labels. These are authored examples, not recorded learner results. The follow-ups in the latter fragments depend on the target's [natural-language interaction capabilities](markdownflow-syntax.md#natural-language-interactions); actual waiting, generated controls, and response-dependent delivery require a learner-time run to verify.

### Contingent Hints and Actionable Revision

This notice-revision example applies the [hinting and feedback guidance](teaching-design.md#preserve-each-selected-approachs-learning-actions). The teacher permits responsive revisions until the notice meets the supplied criteria.

```markdown
<!-- Rewrite a vague notice and check whether a reader can act on it -->
- Explain that the task is to rewrite "Please submit a book report soon" using the confirmed requirements.
  - The book report is 300 words, due Friday at 17:00, and submitted through the course platform.
- If the learner asks to stop at any point, end the activity before requesting another draft. If the work is unfinished, name the gap shown by the latest submitted draft, or say what still needs to be demonstrated if there is no assessed draft.

?[ {{Rewrite "Please submit a book report soon" as an actionable notice using the confirmed length, deadline, and submission destination.}} ...Write the revised notice]

- Wait for the actual draft, then check all four criteria: the book-report task, 300 words, Friday at 17:00, and the course-platform destination.
  - When every criterion is accurate and clear, identify what makes the notice actionable, summarize the checking criteria, and end the activity.
  - When a criterion is missing or inaccurate, name a concrete gap in this draft and the edit needed. Do not rewrite the whole notice for the learner.
  - When the learner is stuck making that edit, give one clue tied to the actual obstacle. For a vague deadline, for example, point to the confirmed day and time rather than supplying a complete notice. Do not give hints for requirements already handled correctly.
- When a revision is needed, initiate a real text-input interaction asking for the complete revised notice, with that full response task associated with the control. Wait for the actual new draft before continuing.
- Recheck every criterion in the latest draft, including newly introduced errors; do not check only the gap mentioned last time.
- If the learner still cannot make the edit, add only the support needed for the remaining obstacle, such as modeling that one detail, then ask for another complete revision through a real text-input interaction and wait again.
- Reduce help as the learner can proceed. Repeat the same checking and response process until the notice meets the criteria, then end rather than adding another required revision.
```

### Round-Based Retrieval With Stable Items

This is one implementation of retrieval practice for previously taught distinctions, not a replacement for first explanation or a required quiz pattern. The teacher has selected whole-round feedback and retries of incorrect items until all original items have been answered correctly. Each item's visible label and complete question identify it across rounds; these labels are not MarkdownFlow variables.

```markdown
<!-- Collect a complete round of independent judgments before revealing results -->
- Use this confirmed activity record: 20 people attended, and the activity took place in the library.
  - The learner has already studied that a factual description is checkable, while an opinion expresses an evaluation.
- If the learner asks to stop at any point, end the exercise before requesting another answer. For unfinished practice, identify what still needs practice using the last completed round, or say that no round was completed. Keep correct answers, correctness judgments, explanations, and scores for any incomplete round withheld.
- Ask the following three fixed items in order. Record each actual selection and wait for it before moving to the next item.
  - Until every item in the current round has an actual answer, withhold correct answers, correctness judgments, explanations, and scores.
  - Keep each item's original label, complete question, option wording, option order, and scoring criterion unchanged in every retry.

?[ {{Item A: Is "20 people attended this activity" a factual description or an opinion?}} Factual description | Opinion]

?[ {{Item B: Is "This was the best activity" a factual description or an opinion?}} Factual description | Opinion]

?[ {{Item C: Is "This activity deserves 10 out of 10" a factual description or an opinion?}} Factual description | Opinion]

<!-- Score the actual round and retain only its incorrect original items -->
- Only after receiving actual answers to every item in the current round, use these fixed scoring criteria:
  - Item A is a factual description: the confirmed attendance record supports it.
  - Item B is an opinion: "best" depends on an evaluation standard.
  - Item C is an opinion: a numerical rating still expresses an evaluation.
- Show a result table using the original item labels, the learner's actual selections, correct answers, and correctness.
- Report the number correct out of the number of items included in this round, and briefly explain the incorrect judgments.
- When the round has incorrect items, start a new round containing only those same original items, in their original relative order. Do not add items already answered correctly or renumber the remaining items.
- For each retained item, recreate a real single-select interaction with the same complete question prefix and options, wait for its actual new selection, and record that selection before presenting the next retained item.
- Do not use an earlier answer to complete a pending interaction. Again withhold answers, correctness, explanations, and scores until every retained item has an actual answer in this new round.
- Score that round using the same criteria, match the results by original item label, report its own correct count and denominator, and retain only the items still incorrect for the next round.
- Continue this process until every original item has been answered correctly. Then summarize that factual claims need evidence and numerical statements can still be opinions, and end the exercise.
- Describe this result as completing the current practice; answering the same items after explanations does not establish transfer or long-term retention.
```

### Socratic Questioning for an Open Judgment

Use this fragment when the goal is a defensible judgment with clear reasons and conditions. The criteria evaluate the reasoning, not agreement with one preferred view. It does not require every possible question or counterexample to be asked.

```markdown
<!-- Form an open judgment, then clarify its reasoning and limits -->
- Introduce the question: does fairness require giving every learner exactly the same learning support?
- Explain that different standards may be defensible when their reasons and conditions are clear.

?[ {{Does fairness require exactly the same learning support for every learner? Explain what "fairness" and "the same support" mean in your judgment, and give a reason.}} ...Write your judgment, meanings, and reason]

- Wait for the actual answer. Acknowledge what is already clear, then use the learner's own definitions, reasons, assumptions, and later corrections to decide whether another question is useful.
  - When a key meaning is unclear, ask one concrete clarification, such as whether "the same" refers to time, materials, or access to the task. Do not replace the learner's definition with your preferred standard.
  - When the meanings are clear but the reason or an assumption is missing, ask for the basis of that specific judgment or a condition it needs. Do not repeat questions already answered.
  - When a relevant boundary remains unexamined, choose one comparison that tests the learner's actual reason. For an emphasis on identical materials, ask whether providing larger type to a learner who cannot read ordinary type is fair under that standard. For an emphasis on meeting every need, ask how the standard handles two learners needing extra explanation when only ten minutes remain. For another clear standard, change a condition that matters to that standard.
- For each needed question, initiate one real text-input interaction with the complete question associated with its response surface. Wait for the actual new answer before choosing a further question or giving response-dependent feedback.
- Evaluate whether definitions stay consistent, reasons support the judgment, and relevant conditions are stated. If two statements conflict, point to those actual statements and invite clarification rather than declaring the whole view wrong.
- Allow the learner to retain or revise the judgment with reasons, including acknowledging an unresolved tradeoff. Do not force a change of position or ask all of the comparison questions.
- As soon as the learner can explain a coherent judgment, its reasons, and relevant limits, summarize what their actual answers clarified or changed and what remains uncertain, then end the discussion without another required answer.
```

These additional fragments also require the target's [natural-language interaction capabilities](markdownflow-syntax.md#natural-language-interactions) for generated follow-ups and retries. Static review can assess the authored instructions; actual waiting, stable item identity, whole-round withholding, and response-dependent follow-up need a learner-time run to verify. No learner outcomes are claimed by these examples.

## Outputs

Return the requested Teaching Prompt or write the appropriate lesson file when a course directory is in scope. The directory format is owned by [cli/course-directory-spec.md](cli/course-directory-spec.md). There is no required lesson-schema envelope, generation report, or execution mode.

Briefly identify completed work, material assumptions, unresolved dependencies, and checks that affect usability. Do not represent unverified work as validated or require companion artifacts unrelated to the requested deliverable.

## Validation

Check the observable result within the requested scope:

- The Prompt contains executable learner-time instructions with enough content and explanation to fulfill its goal, within the shared Prompt responsibility boundary.
- Explicit source, audience, delivery, interaction, personalization, and approved design constraints are honored.
- Confirmed goals, sample decisions, and teacher corrections remain consistent across affected content; any included learning task, success criteria, and feedback address the intended capability.
- Selected personalization has concrete permitted effects using relevant available context and a neutral fallback, while preserving required facts, sequence, visual structure, and interaction behavior. Teacher-facing production and method-selection notes remain outside runtime prose.
- Newly written or explicitly rewritten Prompts follow [Author-Editable Layout](#author-editable-layout) and [Layout Encoding](#layout-encoding). Essential teaching content remains complete outside comments.
- Questions, controls, feedback, use of relevant memory, natural-language branches, and handling of unavailable information are coherent and use valid MarkdownFlow.
- Source material selected for exact preservation matches its authoritative source. Do not claim source coverage when the source is unavailable.
- Image-specific checks apply when actual image assets are used.
- Available companion artifacts are consistent; unavailable or out-of-scope checks are not assessed. A recommended pattern, visual cadence, or interaction quota is never a pass/fail criterion.
