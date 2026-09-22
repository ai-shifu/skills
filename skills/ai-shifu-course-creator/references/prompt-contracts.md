# Prompt Contracts

Define the semantics shared by Teaching Prompts and Course Prompts, plus the responsibility boundary between those two artifacts. This file does not route workflows or own syntax, pedagogy, schemas, or materialization.

## Required References

- `markdownflow.md#interactions`
- `markdownflow.md#deterministic-blocks`
- `data-contracts.md#personalization-directions`

## Prompt Semantics

The **Teaching Agent** is AI-Shifu's learner-time AI role that executes Course Prompts and Teaching Prompts during course delivery, gives interaction feedback, and answers learner follow-up questions. A deployment may route those responsibilities to different underlying models, but this skill always refers to the product role as the Teaching Agent.

Teaching Prompts and Course Prompts are Prompts, not Scripts. The Teaching Agent consumes them. Their purpose is to tell the Teaching Agent how to teach the learner: what to explain, ask, show, adapt, and how to respond. They are not text for a person to read aloud or finished lesson prose addressed directly to the learner.

State the behavior and outcome the Teaching Agent must produce, the information and boundaries it must not omit, and any ordering or adaptation that materially affects the result. Write enough content to make each action executable; use near-final wording when the source or author requires it.

The course author's intended audience and course constraints are hard boundaries. Platform-supplied learner context is additive within those boundaries: use only explicitly stated relevant background and preferences, and only for the selected [Personalization Directions](#personalization-directions) where the current Teaching Prompt leaves those details open. Never use learner context to change or retarget the intended audience, or to change lesson objectives, source facts and boundaries, pedagogy, sequence, pacing, interactions, exact material, slide structure, or the close. Use neutral course-appropriate defaults when context is empty, `UNKNOWN`, irrelevant, or unavailable; do not infer missing facts or quote, summarize, or reveal the learner profile.

The selected directions are a transient authoring control, not runtime Prompt content. Orchestration resolves the lesson and slide structure first; both Prompt artifacts then materialize the selected teaching behavior. The selection does not set how much wording must be prewritten or how much content the learner receives.

For a Teaching Prompt, turn the resolved lesson design into the actual sequence of learner-time teaching actions. Make the core question, teaching objective, must-cover evidence and boundaries, ordered teaching path, slide or image actions, interaction behavior and visible effect, and required close concrete enough to execute. Include the message, evidence, boundaries, selection constraints, and effect needed at each point without unnecessary delivery wording. Directions such as "explain the concept", "add an example", or "ask a question" are incomplete when they do not identify the content, purpose, or expected effect.

Local directions to use the learner's background for an enabled direction, or to explain supplied content in detail, are executable teaching requirements. They belong at the relevant teaching action under [teaching-prompt.md#lesson-materialization](teaching-prompt.md#lesson-materialization), even when ordinary wording is not prewritten; they are not authoring commentary about the selection.

Precision chosen for ordinary content expression is separate from exact output. Use MarkdownFlow deterministic forms only when exactness protects correctness, teaching effect, runtime behavior, source fidelity, or an explicit author requirement; leaving a direction unselected does not make its ordinary content immutable. The owning pedagogy, MarkdownFlow authoring, image, and source-preservation references decide the applicable form.

Materialize interaction and variable lifecycle choices through the resolved MarkdownFlow control, `used_variables`, and `global_variable_table`. Teaching Prompt prose carries the feedback, branch, or cross-lesson use that the Teaching Agent must perform; the machine-facing encoding choice remains in its syntax and schema fields.

Address imperative instructions to the Teaching Agent. When an instruction refers to a learner action or experience, name that person explicitly as "the learner" or "the student", for example:

- "Explain ... to the learner."
- "Ask the student to ..."

Within Prompt instructions, every second-person form in any language refers only to the Teaching Agent. This includes `you`, `your`, `yours`, and `yourself` in English and `你`, `您`, and their possessive forms in Chinese. Learner-visible text inside a MarkdownFlow `?[]` interaction or [standalone deterministic output](markdownflow.md#deterministic-blocks) is the exception: it may use second-person forms to address the learner because the platform displays that content directly or verbatim. Outside `?[]` and standalone deterministic output, do not use a second-person form to mean the learner.

A Prompt remains an instruction consumed by the Teaching Agent rather than a mandatory spoken transcript. Every part of its body serves learner-time delivery by specifying a teaching action, required content, presentation or interaction behavior, feedback or branch behavior, or learner-visible exact material. Represent the lesson structure through the order and grouping of those runtime instructions. Authoring state such as the fixed-skeleton model, personalization rationale, pipeline notes, and preservation classifications remains in the in-memory handoff and owning references. Runtime-facing labels appear only when they perform a real teaching or delivery function.

## Personalization Directions

The author selects any combination of these independent directions. The field shape and allowed values belong to `data-contracts.md#personalization-directions`; intake owns how to obtain the selection. This table owns the shared teaching meaning used by both Prompt artifacts.

| Direction | Author-facing name | Effect when selected |
| --- | --- | --- |
| `examples` | Examples / 举例 | Use relevant learner tasks, goals, or constraints to choose or explain an already-required example. Preserve its essential conditions, reasoning, and takeaway; a job-title substitution alone is insufficient. |
| `analogies` | Analogies / 类比 | Use a situation supported by the learner's stated experience to explain an already-required analogy. Preserve its correspondences and limits; an occupation alone does not establish familiarity. |
| `language_style` | Language style / 语言风格 | Adapt tone, phrasing, terminology explanations, and sentence style to stated preferences and experience while preserving meaning, required explanation depth, and the resolved output language. |
| `value_relevance` | Practical value / 价值阐述 | Connect the lesson's practical value to stated goals, tasks, or constraints at its existing framing, application, or close positions. Do not invent benefits or promise outcomes. |

- Apply only selected directions. A selection is not a strength ranking and does not grant freedom in another direction. For example, language style alone does not authorize replacing an example or analogy with one from the learner's occupation.
- For an unselected direction, use the source, author requirements, and course-wide audience defaults consistently. Do not delete a needed example, analogy, or value explanation, and do not turn ordinary prose into exact output. An empty selection keeps this baseline for all four directions.
- Required content, detailed explanations, teaching sequence, slide structure, and interaction and feedback effects remain complete for every selection. Background-based personalization does not independently enable prerequisite scaffolding, change explanation depth, or create extra questions, variables, branches, teaching aids, or feedback actions. Existing responses to learner answers still follow the lesson's interaction contract.
- Learner context can become available during delivery even when it was absent during authoring. Selected directions remain executable with that context; use the shared neutral fallback when no relevant context is available. Do not serialize a specific learner's profile into reusable course artifacts.
- The same direction effects apply in every delivery mode, within its existing presentation behavior. Artifact owners translate these shared effects into course-wide instructions and local teaching actions without copying the selection interface or internal enum values into runtime prose.

## Artifact Responsibilities

This file owns the semantics shared by Teaching Prompts and Course Prompts and the top-level responsibility boundary between the two artifacts. Detailed syntax, teaching decisions, schemas, and materialization rules live in the sources indexed below.

- A **Teaching Prompt** is the per-lesson runtime instruction artifact. It owns the lesson's teaching intent and execution, including whether and where that lesson uses slides, each slide's teaching purpose and required content, and any treatment tied to a particular slide's position or teaching purpose. It also owns learner interactions and variable collection.
- A **Course Prompt** is the course-level runtime instruction artifact. It owns shared role, general presentation requirements applied uniformly to every slide, and intentional cross-lesson personalization, but it follows each Teaching Prompt and does not own lesson pedagogy, lesson-specific slide structure, or special handling for an individual slide position or purpose. The platform supplies runtime learner context separately from the artifact, so course authors do not serialize platform learner-profile tags or internal learner-profile variable names into it. It may reference persisted learner variables collected by the course; it contains no MarkdownFlow `?[]` interaction controls, does not collect learner input, and does not define lesson-local branches.
