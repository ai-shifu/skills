# Teaching Prompt

Write or revise one runnable per-lesson Teaching Prompt from a topic, brief, source material, existing Prompt, or supplied design. Use the available context directly; a segmentation schema, separate planning run, Course Prompt, or fixed intermediate JSON is not a prerequisite. The authoring agent chooses teaching strategies and layout; the learner-time Teaching Agent follows the resulting instructions.

Shared Prompt meaning and artifact boundaries are in [prompt-semantics.md](prompt-semantics.md), runtime syntax in [markdownflow-syntax.md](markdownflow-syntax.md), optional author controls in [authoring-contracts.md](authoring-contracts.md), and teaching suggestions in [teaching-design.md](teaching-design.md). Consult [image-authoring.md](image-authoring.md) for actual image assets and [source-preservation.md](source-preservation.md) for selected exact material.

## Lesson Materialization

- Tell the Teaching Agent what to teach, show, ask, and respond, with enough content, reasoning, boundaries, and intended effects to execute. Prompts are instructions rather than mandatory spoken transcripts or finished learner prose.
- Use the user's objectives, source requirements, intended audience, and explicit design choices. Preserve a supplied approved teaching plan instead of silently replacing it. If it contains a material contradiction, identify the affected decision and ask or complete independent work as appropriate.
- Choose a suitable teaching path from the content and goal. Examples, analogies, practice, interactions, slides, openings, and closes serve that path; no prescribed pattern, step count, interaction quota, core-question count, or visual cadence is a universal requirement.
- Make needed explanations concrete: identify the facts or steps, relationships, relevant limits, and understanding or application to reach. An empty instruction such as "explain the concept" or "add an example" is insufficient when it leaves those matters unresolved.
- When a delivery mode is specified, honor it. Classroom slides need usable projected content and instructor pacing; text-only requests exclude visuals. Choose whether and where visuals help when the user has left that choice open.
- Give each included visual its necessary content and teaching purpose. Position-specific slide treatment belongs in this lesson; presentation rules shared by every slide belong in the Course Prompt. A cover, greeting, summary, or visual-and-explanation rhythm may be useful without being mandatory.
- For an instructional interaction, keep the complete question, runtime control, and intended feedback or visible instructional effect together. Honor author-requested branching and disabled interactions. A question slide is optional unless requested; the real control remains the response surface.
- Keep reusable learner context out of reusable course artifacts except through the authorized runtime mechanisms. A lesson can stand alone without a Course Prompt; include the concise runtime guidance it needs and identify any genuine unresolved cross-artifact conflict.

## Personalization Directions

Apply the shared effects and boundaries in [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions). Explicit selections, including an empty selection, are author constraints. Where the author has left design open, the using agent can choose suitable behavior without a compulsory selection question or plan-then-generation phase.

For an enabled example or analogy direction, give the Teaching Agent enough selection criteria, essential reasoning or correspondence, limits, and intended takeaway to adapt the expression using relevant known learner context. Keep an author-fixed example or analogy and adapt only what that author permits. Use a neutral course-appropriate fallback when relevant context is unavailable.

Express practical value at a useful teaching position and language style at the appropriate artifact scope. Do not add collection questions, named variables, branches, or teaching actions merely because personalization is enabled. Runtime personalization changes permitted expression within the authored design; it does not authorize the Teaching Agent to change required facts, explicit teaching decisions, exact material, or interaction behavior.

Check an available Course Prompt for genuine conflicts with the lesson. Report an unavailable or out-of-scope companion check as not assessed; it does not block writing or reviewing the supplied lesson. Keep selection field names, enum arrays, planning rationale, and comparisons between variants out of runtime Prompt prose.

## Author-Editable Layout

Every newly generated or explicitly rewritten Teaching Prompt must have source-only explanatory comments. Layout otherwise remains the agent's choice. Do not normalize layout, add comments, or backfill existing courses during an audit-only request. A limited repair to an existing Prompt is not an explicit rewrite: preserve its layout unless changing it is necessary for that repair.

### Required Comments

- Put a concise standalone `<!-- ... -->` comment before each meaningful teaching block. Explain the block's teaching purpose or the change in understanding, judgment, capability, or readiness it should produce.
- Choose useful editing units from the actual lesson; a block need not correspond to a slide, a visual-text pair, or a fixed lesson phase.
- Use naturally worded labels that distinguish neighboring blocks. Prefixes, numbering, punctuation, and sentence form are optional.
- Comments are removed before runtime. Keep all facts, teaching instructions, variables, options, URLs, exact spans, feedback, and branch rules outside comments. Essential content must remain after comments are stripped.
- Keep the interaction question, unchanged standalone control, and immediate feedback in one editing unit rather than inserting navigation comments inside that sequence.
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

Ordinary instructions may use lists, paragraphs, or another suitable source layout. Keep syntax-owned and exact structures intact: do not prefix or newly indent standalone `?[]` controls, `===...===` lines, complete `!===...!===` fences, fenced code, Markdown images, tables, or fixed-display image lines merely to fit a layout. Preserve source-required list markers and indentation as content.

### Interaction Encoding

- Put a complete learner-facing question immediately before its standalone `?[]` control. Keep option wording and order in the actual control; avoid competing simulated controls.
- Use `|` for single-select, `||` for multi-select, and `...` immediately before the input hint or custom-answer label, according to the required answer semantics.
- For input, use a specific preceding question and a short hint. For select-plus-input, put `...` at the start of the custom-answer option.
- Use `%{{name}}` when a persisted answer is needed; lesson-local answers use the no-variable form. A blank name is invalid.
- An action-only control such as `?[Continue]` advances the preceding content and does not require an invented question or slide.

### Variable and Branch Encoding

- Use natural-language branch instructions; MarkdownFlow has no programmatic conditional syntax.
- Refer to lesson-local answers naturally without inventing a global variable.
- For a named learner answer, ensure a real collection and each intended consumer are consistent. A variable table is optional bookkeeping, not a required output.
- Bind a substituted value naturally, for example `The learner goal is {{learning_goal}}.`, before explaining behavior that depends on it.
- Where reading before collection is possible, handle literal `UNKNOWN` rather than testing whether a marker exists.
- New variable names follow [language-policy.md](language-policy.md); preserve existing names where renaming would break references.
- Prompt prose carries the teaching response, not an explanation of the machine-facing encoding decision.

### Preservation Encoding

Use [source-preservation.md](source-preservation.md) to identify the selected exact span and authoritative source. No segment record or character-offset JSON is required.

- Use standalone `===...===` for a complete single-line span that must bypass the Teaching Agent.
- Use complete `!===...!===` fences for multi-line deterministic output, including the original code fence and language tag when required.
- Inline `===...===` preserves a position-sensitive span within generated content and remains mediated by the Teaching Agent; it is not equivalent to standalone deterministic output.
- Keep adaptive content outside deterministic markers and preserve each selected span at its intended runtime position.

## Outputs

Return the requested Teaching Prompt or write the appropriate lesson file when a course directory is in scope. The directory format is owned by [cli/course-directory-spec.md](cli/course-directory-spec.md). There is no required lesson-schema envelope, generation report, execution mode, or global variable table.

Briefly identify completed work, material assumptions, unresolved dependencies, and checks that affect usability. Do not represent unverified work as validated or require companion artifacts unrelated to the requested deliverable.

## Validation

Check the observable result within the requested scope:

- The Prompt contains executable learner-time instructions with enough content and explanation to fulfill its goal, within the shared Prompt responsibility boundary.
- Explicit source, audience, delivery, interaction, personalization, and approved design constraints are honored.
- Newly written or explicitly rewritten Prompts have useful explanatory comments before meaningful blocks. Essential teaching content survives comment removal, and the chosen layout preserves runtime controls and exact spans.
- Questions, controls, feedback, named-variable collections and consumers, natural-language branches, and literal `UNKNOWN` handling are coherent and use valid MarkdownFlow.
- Source material selected for exact preservation matches its authoritative source. Do not claim source coverage when the source is unavailable.
- Image-specific checks apply when actual image assets are used.
- Available companion artifacts are consistent; unavailable or out-of-scope checks are not assessed. A recommended pattern, visual cadence, interaction quota, or optional layout is never a pass/fail criterion.
