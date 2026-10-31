# Course Design Choices

Help the author express consequential course choices and translate them into usable design constraints. The using agent decides which choices matter, whether a question is needed, and when to ask it.

## Using Available Context

Reuse the author's instructions, supplied materials, and existing course behavior before asking. Missing fields do not require a questionnaire. For an unresolved choice selected by the using agent, frame the question around the consequence for this course. Questions may be combined and have no prescribed order; this reference does not add a checkpoint or determine when work pauses.

When presenting options, explain their concrete learner- or author-visible effects in the target language. Avoid bare labels and unsupported promises. Terminology and first mentions follow [language-policy.md](language-policy.md).

### Asking for Useful Information

Make each request answerable without knowledge of pedagogy or platform terminology. Say what the information will change, offer a reasonable recommendation or fallback when available, and distinguish a provisional assumption from a confirmed fact. Ask about the learning task rather than handing the author a menu of method names. For example: "After this lesson, do learners need to judge whether a plan is suitable, or produce a plan independently? This determines whether I suggest case analysis or hands-on practice. Based on your material, I recommend starting with judgment."

For material requests, identify the needed part and its use: "To illustrate this step using the actual interface, I need a screenshot of the current version. You can supply one, or we can use a clearly labeled generic diagram." Do not present a fabricated interface or teacher experience as an authentic supplied asset. Questions about audience, starting knowledge, source coverage, time limits, learning evidence, or projection context are useful when they resolve the actual design issue; they are not required intake fields. Keep established answers and author corrections usable throughout the task.

### Explaining a Recommendation

Make a recommendation concrete enough to revise: name the proposed method or describe the teaching action, explain the specific learning difficulty it addresses, show the expected learner experience, and state the relevant limit. Apply the [method attribution rules](teaching-design.md#method-attribution) for source selection and evidence boundaries. Keep this explanation brief enough to help the author make the actual decision.

For example: "I recommend a worked example here: show how the solution develops step by step and explain the key judgments. This follows [MIT Teaching + Learning Lab's guidance](https://tll.mit.edu/teaching-resources/how-people-learn/worked-examples/). Your learners are new to this process, so a complete demonstration can make the reasoning visible; understanding it does not yet demonstrate independent performance. If example personalization is selected, we can use a relevant task explicitly mentioned in the learner's existing memory. Without relevant context, use the course's neutral example." This explains a proposed choice without requiring the author to select it from a catalog, asking for more learner data, or placing the rationale in learner-time Prompts.

Explain a visual choice by its purpose as well: "A flowchart lets learners compare the branch conditions together, while the text develops the reasoning behind each judgment." Keep author confirmation and revision focused on the substantive decision and its effect; invocation timing and continuation remain with the using agent.

## Available Choices

| Choice | Effect and useful context |
| --- | --- |
| Delivery experience | One-on-one self-study lets the Teaching Agent guide a learner directly; classroom slides support projection paced by a human instructor; a combined course supports both. Reuse the intended setting or choose the form suited to the task. |
| Personalization | Examples, Analogies, Language style, and Practical value have the effects defined in [prompt-semantics.md#personalization-directions](prompt-semantics.md#personalization-directions). Any combination, including none, is valid. Selection uses available learner context and does not authorize collecting more context. |
| Interactions | Learner-context collection supports later teaching; pre-content thinking activates a judgment the explanation can refine; self-check supports consolidation. Choose useful interactions from the course goal unless the author has constrained them. Apply an explicit choice of none under [interaction policy precedence](teaching-design.md#interaction-policy-precedence). |
| Course structure | Chapter and lesson counts control grouping and granularity. Use explicit counts when supplied; otherwise derive a suitable structure from material, audience, and learning goals. See [course-structure.md](course-structure.md) for structure design. |
| Teacher identity | A supplied name becomes the optional teacher identity in the Course Prompt. A blank or absent name requires no named identity. Do not invent credentials or a biography. |
| Teacher avatar | A supplied JPG or PNG can become the platform avatar. Setting it is a platform capability described in [course-management.md](course-management.md); it is not course content. An avatar question is optional and never blocks authoring. |

## Optional Controls

Use the shapes in [authoring-contracts.md#input-contract](authoring-contracts.md#input-contract) when structured controls are helpful. Natural-language choices are equally usable; no intermediate JSON or separate design report is required.

- Preserve explicit delivery requirements, counts, teacher identity, interaction restrictions, and personalization selections.
- Resolve personalization from the request or existing course instructions. With no basis for individual-background adaptation, use the source, author requirements, and intended audience baseline. An explicit none is an empty selection, not permission to remove needed examples or explanations.
- For structured interaction policy, selected purposes map to `enabled`, explicit none to `disabled`, and no constraint to `unspecified`. Teaching effects are described in [teaching-design.md#interaction-policy-precedence](teaching-design.md#interaction-policy-precedence).
- Keep `course_author_avatar_source` transient. An absent source leaves the platform avatar unchanged; accepted files follow the platform's upload and compression requirements.

The result is the design information needed for the requested work, in a form the using agent finds useful. Record consequential assumptions or unresolved conflicts without requiring every possible choice to be answered.
