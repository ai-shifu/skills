# Prompt Contracts

## Prompt Semantics

Teaching Prompts and Course Prompts are Prompts, not Scripts. The runtime LLM consumes them. Their purpose is to tell the LLM how to teach the learner: what to explain, ask, show, adapt, and how to respond. They are not text for a person to read aloud or finished lesson prose addressed directly to the learner.

Address imperative instructions to the LLM. When an instruction refers to a learner action or experience, name that person explicitly as "the learner" or "the student", for example:

- "Explain ... to the learner."
- "Ask the student to ..."

Within Prompt instructions, every occurrence of `you`, `your`, `yours`, or `yourself`, in any capitalization, refers only to the runtime LLM. Learner-visible text inside a MarkdownFlow `?[]` interaction or [deterministic block](markdownflow.md#deterministic-blocks) is the exception: it may use second-person forms to address the learner because the platform displays that content directly or verbatim. Outside `?[]` and deterministic blocks, do not use a second-person form to mean the learner.

Do not write a transcript, lesson-plan narration, or polished learner-facing lecture. Keep author-side structure implicit: do not emit labels such as "Knowledge Block 1/2/3", "Lesson Objective", or "Deliverable", and do not expose internal authoring terms in learner-facing output. Authoring rules, pipeline notes, and process instructions stay in skill docs and references, never in Prompt content; internal design notes may appear only in HTML comments when needed.

## Artifact Responsibilities

This file owns the semantics shared by Teaching Prompts and Course Prompts and the top-level responsibility boundary between the two artifacts. Detailed syntax, teaching decisions, schemas, and materialization rules live in the sources indexed below.

- A **Teaching Prompt** is the per-lesson runtime instruction artifact. It owns the lesson's teaching intent and execution, learner interactions, and variable collection.
- A **Course Prompt** is the course-level runtime instruction artifact. It owns shared role, presentation, and intentional cross-lesson personalization, but it follows each Teaching Prompt and does not own lesson pedagogy. It may reference persisted learner variables; it contains no MarkdownFlow `?[]` interaction controls, does not collect learner input, and does not define lesson-local branches.

Apply lesson-level teaching decisions through [Pedagogy](pedagogy.md) and materialize the Course Prompt through [Course Prompt: Fillable Template](course-prompt.md#fillable-template).

## Authority Index

Use each linked source directly. Workflow files apply these authorities through phase-specific actions and checks; they do not redefine them.

| Concern | Authoritative source |
|---|---|
| Prompt audience, instruction voice, addressee, and second-person meaning | [Prompt Semantics](#prompt-semantics) |
| Lesson loop, teaching patterns, interaction decisions, variable-persistence decisions, and teaching-side visual coordination | [Pedagogy](pedagogy.md) |
| MarkdownFlow processing, preprocessing, syntax recognition, variable substitution, interaction execution, branch limitations, deterministic output, and image runtime behavior | [MarkdownFlow Spec](markdownflow.md) |
| Course Prompt structure, placeholder sources, and materialization | [Course Prompt](course-prompt.md) |
| Artifact schemas, metadata fields, variable tables, and output-language resolution | [Data Contracts](data-contracts.md) |
| Source segmentation and cross-lesson orchestration | [Segmentation and Orchestration](segmentation-orchestration.md) |
| Lesson generation and slide-only delivery | [Generation Workflow](generation-workflow.md#generation) |
| MarkdownFlow interaction, variable, branch, and preservation encoding | [MarkdownFlow Authoring](generation-workflow.md#markdownflow-authoring) |
| Image form selection and composition | [Image Authoring](generation-workflow.md#image-authoring) |
| Prompt audit, repair, and optimization execution | [Optimization Workflow](optimization-workflow.md#optimization) |
| Immutable-span and preservation-scope decisions | [Preservation Decisions](optimization-workflow.md#preservation-decisions) |
