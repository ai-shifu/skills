# Teaching Prompt

Write or revise one runnable per-lesson Teaching Prompt from a topic, brief, source material, existing Prompt, or supplied design. Use the available context directly; a segmentation schema, separate planning run, Course Prompt, or fixed intermediate JSON is not a prerequisite. The authoring agent chooses teaching strategies and layout; the learner-time Teaching Agent follows the resulting instructions.

Shared Prompt meaning and artifact boundaries are in [prompt-semantics.md](prompt-semantics.md), runtime syntax in [markdownflow-syntax.md](markdownflow-syntax.md), optional author controls in [authoring-contracts.md](authoring-contracts.md), and teaching suggestions in [teaching-design.md](teaching-design.md). Consult [image-authoring.md](image-authoring.md) for actual image assets and [source-preservation.md](source-preservation.md) for selected exact material.

## Lesson Materialization

- Tell the Teaching Agent what to teach, show, ask, and respond, with enough content, reasoning, boundaries, and intended effects to execute. Prompts are instructions rather than mandatory spoken transcripts or finished learner prose.
- Use the user's objectives, source requirements, intended audience, and explicit design choices. Carry confirmed learning goals, representative-sample decisions, and later teacher corrections into every affected lesson rather than reverting to an earlier draft or copying the sample's surface layout everywhere. Preserve a supplied approved teaching plan instead of silently replacing it. If it contains a material contradiction, identify the affected decision and ask or complete independent work as appropriate.
- Choose a suitable teaching path from the content and goal. Examples, analogies, practice, interactions, slides, openings, and closes serve that path; no prescribed pattern, step count, interaction quota, core-question count, or visual cadence is a universal requirement.
- Make needed explanations concrete: identify the facts or steps, relationships, relevant limits, and understanding or application to reach. An empty instruction such as "explain the concept" or "add an example" is insufficient when it leaves those matters unresolved.
- When a delivery mode is specified, honor it. Classroom slides need usable projected content and instructor pacing; text-only requests exclude visuals. Choose whether and where visuals help when the user has left that choice open.
- Give each included visual its necessary content and teaching purpose. Position-specific slide treatment belongs in this lesson; presentation rules shared by every slide belong in the Course Prompt. A cover, greeting, summary, or visual-and-explanation rhythm may be useful without being mandatory.
- For an instructional interaction, keep its question or generation instructions, response requirements, and intended feedback or visible instructional effect together. Honor author-requested branching and disabled interactions. A question slide is optional unless requested; the real interaction remains the response surface.
- When the selected design uses a learning task to demonstrate the goal, specify what the learner does, what counts as a satisfactory result, and how feedback addresses the actual response, including a useful next attempt when selected. A recall question alone cannot demonstrate an application goal. Follow [teaching-design.md](teaching-design.md) for goal, task, and evidence alignment; this does not require a test in every lesson or override disabled interactions.
- Keep reusable learner context out of reusable course artifacts except through the authorized runtime mechanisms. A lesson can stand alone without a Course Prompt; include the concise runtime guidance it needs and identify any genuine unresolved cross-artifact conflict.
- Keep requests for teacher materials, sample-approval instructions, production notes, and teaching-method rationale or provenance in teacher-facing communication rather than runtime Prompt prose. Source content needed by the learner remains part of the lesson; a method citation becomes lesson content only when the author actually requests teaching it.

## Personalization Directions

Apply the shared effects and boundaries in [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions). Explicit selections, including an empty selection, are author constraints. Where the author has left design open, the using agent can choose suitable behavior without a compulsory selection question or plan-then-generation phase.

For an enabled example or analogy direction, give the Teaching Agent enough selection criteria, essential reasoning or correspondence, limits, and intended takeaway to adapt the expression using relevant known learner context. Keep an author-fixed example or analogy and adapt only what that author permits. Use a neutral course-appropriate fallback when relevant context is unavailable.

Make each selected direction executable at the position where it matters: state which relevant, already available learner input may affect which permitted teaching expression, and what to do when that input is missing or irrelevant. A generic instruction to "personalize the lesson," or replacing a name or occupation while leaving the example unrelated to the learner's task, is insufficient. For example, an adapted cost example can use a learner's stated sales task and constraints to explain the same cost relationship. Clearly labeled hypothetical teaching figures are allowed; do not present them as the learner's actual data, replace author-fixed figures, or change the required reasoning. Language and practical-value adaptations need the same concrete connection to stated preferences or goals under the shared direction semantics.

Express practical value at a useful teaching position and language style at the appropriate artifact scope. Do not add collection questions, branches, or teaching actions merely because personalization is enabled. Runtime personalization changes permitted expression within the authored design; it does not authorize the Teaching Agent to change required facts, explicit teaching decisions, exact material, or interaction behavior.

Check an available Course Prompt for genuine conflicts with the lesson. Report an unavailable or out-of-scope companion check as not assessed; it does not block writing or reviewing the supplied lesson. Keep selection field names, enum arrays, planning rationale, and comparisons between variants out of runtime Prompt prose.

## Author-Editable Layout

Every newly generated or explicitly rewritten Teaching Prompt must have source-only explanatory comments. Layout otherwise remains the agent's choice. Do not normalize layout, add comments, or backfill existing courses during an audit-only request. A limited repair to an existing Prompt is not an explicit rewrite: preserve its layout unless changing it is necessary for that repair.

### Required Comments

- Put a concise standalone `<!-- ... -->` comment before each meaningful teaching block. Explain the block's teaching purpose or the change in understanding, judgment, capability, or readiness it should produce.
- Choose useful editing units from the actual lesson; a block need not correspond to a slide, a visual-text pair, or a fixed lesson phase.
- Use naturally worded labels that distinguish neighboring blocks. Prefixes, numbering, punctuation, and sentence form are optional.
- Keep all facts, teaching instructions, memory-use instructions, options, URLs, exact spans, feedback, and branch rules outside comments, consistent with the [runtime comment semantics](markdownflow-syntax.md#html-comments). Essential content must remain complete when comments are ignored.
- Keep the interaction question and unchanged standalone control, or its natural-language generation instructions, together with immediate feedback in one editing unit rather than inserting navigation comments inside that sequence.
- Do not put the literal delimiters `<!--` or `-->` inside a comment body.

### Optional Layout Templates

These are alternatives, not a required sequence or an exhaustive list. The agent may combine them or design another layout while preserving the comments and runtime syntax.

#### Hierarchical Action List

Useful when one teaching action has several constraints or feedback cases. Nesting expresses ownership; it does not impose a teaching pattern.

```markdown
<!-- The learner can distinguish fixed and variable costs -->

- Explain fixed and variable costs to the learner.
  - Use rent as the fixed-cost example and raw materials as the variable-cost example.
  - Explain that the distinction concerns how total cost changes with activity over the stated period.
  - Ask the learner to consider which assumptions make those examples valid.
```

#### Short Paragraph Blocks

Useful for compact lessons or tightly connected reasoning. Each paragraph remains a direct instruction to the Teaching Agent.

```markdown
<!-- A break-even calculation becomes usable -->

Explain to the learner that break-even units equal fixed costs divided by contribution per unit. Use fixed costs of 1000 and contribution of 20 per unit to demonstrate the result of 50 units. Explain that the calculation assumes the stated price and variable cost remain constant within the relevant range.

<!-- The calculation is checked against its assumptions -->

Ask the learner which assumption would fail if a volume discount changed the selling price.

?[Selling price | Office address]

Explain the selected answer and correct any confusion using the quantities in the calculation. Connect the price change to contribution per unit and explain why the original result must be recalculated.
```

#### Per-Slide Instruction Blocks

Useful for a requested slide deck. Slide count, purpose, order, and the choice to include narration come from the user's needs and lesson design.

```markdown
<!-- Two cost behaviors are visible side by side -->

Create a classroom slide comparing fixed and variable costs. Show total cost against activity for each behavior and label the assumptions. Keep the two diagrams aligned for comparison.

<!-- The comparison can be applied to a concrete case -->

Create a slide with the rent and raw-materials cases. Show the relevant time period and activity measure so the instructor can explain why each classification applies. Do not add Teaching Agent narration to this classroom-only deck.
```

## Source Encoding

Encode the chosen teaching design without changing author requirements or exact material. Parser recognition and runtime effects belong to [markdownflow-syntax.md](markdownflow-syntax.md).

### Layout Encoding

Ordinary instructions may use lists, paragraphs, or another suitable source layout. Keep syntax-owned and exact structures intact: do not prefix or newly indent standalone `?[]` controls, `===...===` lines, multi-line fences with standalone `!===` delimiters, fenced code, Markdown images, tables, or fixed-display image lines merely to fit a layout. Preserve source-required list markers and indentation as content.

### Interaction Encoding

- Choose an [explicit control or natural-language interaction](markdownflow-syntax.md#interactions) according to the intended behavior. Preserve author-fixed questions and choices; when dynamic generation is requested, keep that generation instruction executable at learner time rather than replacing it with an author-time option list.
- Use target capabilities already established by the user or available course context. Natural-language interactions need the [response-surface and waiting capabilities](markdownflow-syntax.md#natural-language-interactions). An explicit-control fallback is suitable only when it preserves the author's requirements. If dynamic choices remain required and support is unavailable or unknown, retain that requirement and identify the runtime dependency. Local authoring can still produce the Prompt with that dependency stated; it does not require platform access.
- Keep explicit `?[]` controls standalone, with option wording and order in the actual control; avoid competing simulated controls. A complete learner-facing question or response task in the [question prefix](markdownflow-syntax.md#question-prefix) is sufficient: repeating it before the control is optional unless the author explicitly requires separate text.
- When generating a new explicit control for a question or response task, fill the question prefix with that complete learner-facing question or response task. Preserve its wording and punctuation rather than using a programmatic key, topic label, answer, or unfilled placeholder. This keeps the response associated with what the learner was asked. For example, write `?[ {{Which action will you take first?}} Verify the source | Check the calculation]`. Preserve an author-supplied exact control unless the requested change includes revising it.
- In explicit controls, use `|` for single-select, `||` for multi-select, and `...` immediately before the input hint or custom-answer label, according to the required answer semantics. For input, put the complete learner-facing question or response task in the prefix and use a short hint. For select-plus-input, put `...` at the start of the custom-answer option.
- For a natural-language interaction, describe the intended learner decision or task, the context used to generate the question or options, and any required answer mode or option constraints. Keep these instructions outside `?[]`, comments, and deterministic blocks. Specify how the actual answer affects the next teaching action; do not invent the learner's answer or continue before it arrives.
- When teaching uses an earlier answer, describe the relevant input and its instructional effect naturally under [Memory and Branch Encoding](#memory-and-branch-encoding).
- An action-only control such as `?[Continue]` advances the preceding content and does not require an invented question or slide.
- The prompt immediately after an interaction can describe how to respond to different answers and, when needed, ask the learner to interact again, using the [runtime follow-up behavior](markdownflow-syntax.md#branching-on-user-input).

For example:

```markdown
<!-- This activity checks whether an action plan specifies the action, owner, and deadline. -->

?[ {{Rewrite "Organize customer feedback" as a plan with a specific action, an owner, and a deadline.}} ...State who will do what and by when]

Respond based on the learner's answer:

- If all three details are present, explain why the plan is clear, then continue with the subsequent content.
- If a detail is missing, identify it and give a hint. Initiate another interaction and ask the learner to complete the plan. Wait for the learner's actual response, then respond to the new answer using the same criteria.
```

### Memory and Branch Encoding

- Use natural-language branch instructions; MarkdownFlow has no programmatic conditional syntax.
- Refer to the learner's actual answers naturally, using relevant memory under [markdownflow-syntax.md#memory](markdownflow-syntax.md#memory).
- Describe how the earlier input affects teaching, for example, "Use the learner's stated goal from memory to explain why this exercise matters."
- If the needed information is unavailable or irrelevant, use the course-appropriate fallback rather than inventing an answer.
- Prompt prose carries the teaching response, not an explanation of the machine-facing encoding decision.

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
Use an explicitly labeled hypothetical teaching order to explain: total cost = fixed cost + per-unit variable cost × quantity.
The fixed cost is 100 yuan and the per-unit variable cost is 5 yuan; 20 units cost 200 yuan in total.
State the assumptions: both cost terms remain unchanged over the quantity range being discussed, and there are no other charges.
Compare 20 units with 30 units: total cost increases from 200 yuan to 250 yuan because of the variable cost of 10 additional units;
the fixed cost is still counted only once. Explain how each term in the formula corresponds to the order.

<!-- Check whether the learner can explain why the cost changes -->
?[ {{With the assumptions above unchanged, why does adding 10 units increase total cost by only 50 yuan, without adding the fixed cost again?}} ...Explain which costs change and which remain unchanged]

Wait for the current actual answer, then give feedback:
- If the learner explains that the fixed cost stays unchanged and each additional unit adds 5 yuan, identify the reasoning they got right.
- If they count the fixed cost again, explain that it is counted only once in this order model, and explain the additional costs item by item.
- If they only repeat "an increase of 50 yuan" or their reasoning is unclear, explain that the correct number alone does not demonstrate understanding of the cause, and explain the cost relationship.
Do not ask another question. Close with one sentence returning to the formula and its assumptions; do not claim that the learner can now produce a quote independently.
```

### Same Beginners, Goal of Producing a Quote

When the goal changes to calculating a quote and stating its assumptions, a worked example makes the procedure visible before an independent attempt. Unlike the explanation variant, do not disclose the target calculation before the response. The teacher permits one supported revision after feedback.

```markdown
<!-- Show a complete calculation and the reasoning behind each step -->
Use a hypothetical teaching order to demonstrate: total cost = fixed cost + per-unit variable cost × quantity.
The fixed cost is 100 yuan and the per-unit variable cost is 5 yuan; for 20 units, the variable cost is 5 × 20 = 100 yuan.
Add the fixed cost of 100 yuan, counted only once, to obtain a total cost of 200 yuan.
Explain which cost each step represents, and state that the model requires unchanged cost terms over the quantity range being discussed and no other charges.

<!-- Independently quote another quantity and state the assumptions -->
?[ {{Using the model with a fixed cost of 100 yuan and a per-unit variable cost of 5 yuan, produce a quote for an order of 30 units. Show your calculation and state the assumptions under which the quote holds.}} ...Write the calculation, total cost, and assumptions]

Wait for the current actual answer. Use the following criteria only for feedback after receiving it; do not show them beforehand:
The complete result is 100 + 5 × 30 = 250 yuan; the assumptions include unchanged cost terms and no other charges.
- If the calculation, amount, and assumptions are all correct, identify what is correct and end the exercise.
- If the calculation is set up correctly but contains an arithmetic error, identify where it occurs; if the fixed cost is counted again or a cost is omitted, explain the relevant cost.
- If the learner gives only 250 yuan or omits assumptions, acknowledge the correct parts they supplied and identify the missing calculation basis or assumptions, without inferring a misconception.
For either of the latter two cases, give a hint targeted to the gap and initiate one text-input interaction asking the learner to revise or complete the quote.
Wait for the actual revision, give feedback using the same criteria, and end. If gaps remain, provide a complete demonstration and identify what remains unresolved.
Do not continue looping or treat seeing the demonstration as independent performance.
```

### Same Quote Goal, Learners Already Able to Use the Formula

For learners with supplied evidence that they already use this formula, keep the quote goal and success criteria but remove the initial step-by-step demonstration. A direct application can reveal whether help is needed. Here the teacher permits one follow-up; an authored feedback path supplies targeted help rather than letting the Teaching Agent freely redesign the lesson.

```markdown
<!-- Use existing skills to produce a quote and reveal where help is needed -->
Briefly state the hypothetical teaching order model: total cost = fixed cost + per-unit variable cost × quantity.
The fixed cost is 100 yuan and the per-unit variable cost is 5 yuan; the given total cost for 20 units is 200 yuan.
The model assumes unchanged cost terms over the quantity range being discussed and no other charges.
Do not demonstrate the calculation steps first or disclose the result of the task below in advance.

?[ {{Using the model with a fixed cost of 100 yuan and a per-unit variable cost of 5 yuan, produce a quote for an order of 30 units. Show your calculation and state the assumptions under which the quote holds.}} ...Write the calculation, total cost, and assumptions]

Wait for the current actual answer, then give feedback using these criteria:
The complete result is 100 + 5 × 30 = 250 yuan, with unchanged cost terms and no other charges stated as assumptions.
- If the result, reasoning, and assumptions are complete, briefly confirm the reasoning and end; do not add a full introductory explanation.
- If there is an arithmetic or cost-classification error, explain the relevant steps for that actual error, then ask the learner to revise the quote.
- If the learner gives only an amount or unclear reasoning, identify the missing basis and ask them to supply it; do not conclude that they cannot calculate merely because the answer is incomplete.
When revision or additional information is needed, initiate one real text-input interaction and wait for the answer. Give feedback on that new answer and end.
If the criteria are still unmet, provide the relevant explanation or complete calculation and identify the remaining gaps; do not retry indefinitely or claim mastery has been demonstrated.
```

The first pair changes the target performance for the same audience; the second pair keeps the quote task and criteria while changing the assumed starting knowledge and support. The differences should be visible in instruction and feedback, not only method labels. These are authored examples, not recorded learner results. The follow-ups in the latter fragments depend on the target's [natural-language interaction capabilities](markdownflow-syntax.md#natural-language-interactions); actual waiting, generated controls, and response-dependent delivery require a learner-time run to verify.

## Outputs

Return the requested Teaching Prompt or write the appropriate lesson file when a course directory is in scope. The directory format is owned by [cli/course-directory-spec.md](cli/course-directory-spec.md). There is no required lesson-schema envelope, generation report, or execution mode.

Briefly identify completed work, material assumptions, unresolved dependencies, and checks that affect usability. Do not represent unverified work as validated or require companion artifacts unrelated to the requested deliverable.

## Validation

Check the observable result within the requested scope:

- The Prompt contains executable learner-time instructions with enough content and explanation to fulfill its goal, within the shared Prompt responsibility boundary.
- Explicit source, audience, delivery, interaction, personalization, and approved design constraints are honored.
- Confirmed goals, sample decisions, and teacher corrections remain consistent across affected content; any included learning task, success criteria, and feedback address the intended capability.
- Selected personalization has concrete permitted effects using relevant available context and a neutral fallback, while preserving required facts, sequence, visual structure, and interaction behavior. Teacher-facing production and method-selection notes remain outside runtime prose.
- Newly written or explicitly rewritten Prompts have useful explanatory comments before meaningful blocks. Essential teaching content remains complete outside comments, and the chosen layout preserves runtime controls and exact spans.
- Questions, controls, feedback, use of relevant memory, natural-language branches, and handling of unavailable information are coherent and use valid MarkdownFlow.
- Source material selected for exact preservation matches its authoritative source. Do not claim source coverage when the source is unavailable.
- Image-specific checks apply when actual image assets are used.
- Available companion artifacts are consistent; unavailable or out-of-scope checks are not assessed. A recommended pattern, visual cadence, interaction quota, or optional layout is never a pass/fail criterion.
