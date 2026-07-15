# Prompt Contracts

## Prompt Semantics

Teaching Prompts and Course Prompts are Prompts, not Scripts. The runtime LLM consumes them. Their purpose is to tell the LLM how to teach the learner: what to explain, ask, show, adapt, and how to respond. They are not text for a person to read aloud or finished lesson prose addressed directly to the learner.

Address imperative instructions to the LLM. When an instruction refers to a learner action or experience, name that person explicitly as "the learner" or "the student", for example:

- "Explain ... to the learner."
- "Ask the student to ..."

Within Prompt instructions, every occurrence of `you`, `your`, `yours`, or `yourself`, in any capitalization, refers only to the runtime LLM. Learner-visible text inside a MarkdownFlow `?[]` interaction is the exception: it may use second-person forms to address the learner because the platform displays that interaction content directly. Outside `?[]`, do not use a second-person form to mean the learner.

Do not write a transcript, lesson-plan narration, or polished learner-facing lecture. Keep author-side structure implicit: do not emit labels such as "Knowledge Block 1/2/3", "Lesson Objective", or "Deliverable", and do not expose internal authoring terms in learner-facing output. Authoring rules, pipeline notes, and process instructions stay in skill docs and references, never in Prompt content; internal design notes may appear only in HTML comments when needed.

## Teaching Prompt and Course Prompt Authoring Hard Rules (Must Follow)

These are the eight red-line rules every Teaching Prompt and Course Prompt must satisfy. Supporting syntax, pedagogy, and rationale live in the referenced files; Prompt semantics are defined only here.

1. **Prompt semantics and addressee.** Apply every requirement in [Prompt Semantics](#prompt-semantics). No other file redefines the Prompt audience, instruction voice, or second-person meaning.

2. **Interaction syntax: prompt outside, options inside.** Keep the learner-facing question on the line **before** the interaction; put only option labels, flow buttons, or a short `...` input placeholder inside the `?[]` line, and give each `?[]` its own standalone line. Full syntax inventory, `...` input-marker rules, and Bad/Good examples: `markdownflow.md#interactions` and `markdownflow.md#input-marker-rules`.

3. **Interaction type selection: match the learner decision.** First apply the normalized policy through `pedagogy.md#interaction-policy-precedence`; when it calls for an interaction, use single-select when options are mutually exclusive or one selected path drives a branch. Use multi-select for non-exclusive learner context — goals, interests, modules, blockers, scenarios, experience, practice needs — and do not avoid multi-select merely because combinations are hard to enumerate. See `pedagogy.md#interaction-design`.

4. **Variables only for cross-lesson or course-level learner input.** Create a named variable (`?[%{{var}} ...]`) only when the learner's answer must leave the current lesson (referenced by `course-prompt.md`, reused in another lesson, or used for cross-lesson personalization). Current-lesson branching, examples, feedback, summaries, and free-text inputs use no-variable `?[...]` and never enter `used_variables` / `global_variable_table`. At runtime every `{{var}}` is replaced with the learner's stored value or `UNKNOWN` — write prompt logic against the substituted value, not against variable availability. Substitution semantics, naming rules, and wording examples: `markdownflow.md#variables`; when to create a variable: `pedagogy.md#variable-strategy`.

5. **Visuals: obey the delivery-mode boundary; raw graphic code is opt-in.** Apply the three existing cases in `pedagogy.md#visual-text-coordination`: standard non-slide-only lessons keep visual-text pairing; author-provided assets use the understand, upload, and embed workflow in `generation-workflow.md#working-with-author-provided-images`; pure classroom slides follow `generation-workflow.md#slide-only-generation-override` and do not require AI narration or a full explanation pair. By default, do not inline SVG, HTML drawings, Mermaid, PlantUML, or Graphviz source as a graphic. When the author explicitly requests one of these raw formats, follow that request; the explicit author instruction overrides the default. Approved uploaded-asset embedding, including instruction-style HTML when needed, remains authoritative in `markdownflow.md#images`.

6. **Structural metadata stays out of Teaching Prompt bodies.** Chapter titles, lesson titles, hierarchy labels, and ordering markers belong in `structure.json` / `course_index`, not repeated as Markdown headings or opening title lines inside `lesson-*.md`. The first paragraph of every Teaching Prompt must perform a teaching-start function — establish a scenario, ask a guiding question, activate prior experience, state the task, or start a practice — never display directory structure or copy source headings. Allow visible headings inside a lesson only when the course explicitly needs them and platform rendering support is confirmed.

7. **Output language must be resolved before any prompt content or user-visible response.** Run Language Resolution per `data-contracts.md#language-resolution` first; the user's invocation language counts as `prompt_language_detection` (priority 4). Examples and templates in this skill are written in English for canonical illustration only — they never override the resolved language. All user-visible output (reports, phase summaries, status notes, artifact labels, handoff instructions, error explanations) and all learner-facing course content follow the resolved language; stable machine-facing identifiers (JSON keys, file names, CLI flags, API fields, MarkdownFlow syntax, code, URLs, verbatim quotes) stay unchanged, and human-facing concept labels follow the [Canonical Term Translation Table](session-controls.md#canonical-term-translation-table). Before finalizing or deploying a course directory, run the Pre-Deploy Language Audit in `data-contracts.md#language-resolution`.

8. **Pedagogy source: Teaching Prompts lead; the Course Prompt follows and styles.** Encode each lesson's teaching method, explanation path, content sequence, pacing, examples, practice, interactions, feedback, and close in its Teaching Prompt. The Course Prompt must follow those instructions and may contribute only course-wide persona, tone, wording, format, slide presentation, and intentional cross-lesson personalization. It must not supply, replace, reorder, omit, or supplement lesson pedagogy with a generic framework. See `pedagogy.md#scope-and-authority-boundaries` and `course-prompt.md#purpose`.
