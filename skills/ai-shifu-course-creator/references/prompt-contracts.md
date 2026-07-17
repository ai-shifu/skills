# Prompt Contracts

Define the semantics shared by Teaching Prompts and Course Prompts, plus the responsibility boundary between those two artifacts. This file does not route workflows or own syntax, pedagogy, schemas, or materialization.

## Required References

- `markdownflow.md#interactions`
- `markdownflow.md#deterministic-blocks`

## Prompt Semantics

Teaching Prompts and Course Prompts are Prompts, not Scripts. The runtime LLM consumes them. Their purpose is to tell the LLM how to teach the learner: what to explain, ask, show, adapt, and how to respond. They are not text for a person to read aloud or finished lesson prose addressed directly to the learner.

Prefer intent-level direction with explicit requirements over prewritten delivery. State the behavior and outcome the runtime LLM must produce, the information and boundaries it must not omit, and any ordering or adaptation that materially affects the result. Leave ordinary phrasing, transitions, and non-critical example elaboration to the runtime LLM within the Course Prompt's course-wide presentation constraints and the Teaching Prompt's lesson-specific delivery constraints.

For a Teaching Prompt, make the core question, teaching objective, must-cover evidence and boundaries, required teaching path, interaction purpose and visible effect, and required close concrete enough to execute. Directions such as "explain the concept", "add an example", or "ask a question" are incomplete when they do not identify the content, purpose, or expected effect.

Increase precision only when exactness protects correctness, teaching effect, runtime behavior, source fidelity, or an explicit author requirement. Constrain the smallest affected wording or presentation choice and keep the surrounding teaching adaptive; the owning pedagogy, MarkdownFlow authoring, image, and source-preservation references decide the applicable form.

Address imperative instructions to the LLM. When an instruction refers to a learner action or experience, name that person explicitly as "the learner" or "the student", for example:

- "Explain ... to the learner."
- "Ask the student to ..."

Within Prompt instructions, every second-person form in any language refers only to the runtime LLM. This includes `you`, `your`, `yours`, and `yourself` in English and `你`, `您`, and their possessive forms in Chinese. Learner-visible text inside a MarkdownFlow `?[]` interaction or [standalone deterministic output](markdownflow.md#deterministic-blocks) is the exception: it may use second-person forms to address the learner because the platform displays that content directly or verbatim. Outside `?[]` and standalone deterministic output, do not use a second-person form to mean the learner.

Do not write a transcript, lesson-plan narration, or polished learner-facing lecture. Keep author-side structure implicit: do not emit labels such as "Knowledge Block 1/2/3", "Lesson Objective", or "Deliverable", and do not expose internal authoring terms in learner-facing output. Authoring rules, pipeline notes, and process instructions stay in skill docs and references, never in Prompt content; internal design notes may appear only in HTML comments when needed. Do not prescribe routine lecture sentences, slide titles, point counts, or layout details merely to make a Prompt look complete.

## Artifact Responsibilities

This file owns the semantics shared by Teaching Prompts and Course Prompts and the top-level responsibility boundary between the two artifacts. Detailed syntax, teaching decisions, schemas, and materialization rules live in the sources indexed below.

- A **Teaching Prompt** is the per-lesson runtime instruction artifact. It owns the lesson's teaching intent and execution, learner interactions, and variable collection.
- A **Course Prompt** is the course-level runtime instruction artifact. It owns shared role, presentation, and intentional cross-lesson personalization, but it follows each Teaching Prompt and does not own lesson pedagogy. It may reference persisted learner variables; it contains no MarkdownFlow `?[]` interaction controls, does not collect learner input, and does not define lesson-local branches.
