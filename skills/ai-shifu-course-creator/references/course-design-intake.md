# Course Design Choices

Help the author express consequential course choices and translate them into usable design constraints. The using agent decides which choices matter, whether a question is needed, and when to ask it.

## Using Available Context

Reuse the author's instructions, supplied materials, and existing course behavior before asking. Missing fields do not require a questionnaire. Make reasonable, reversible choices when the task supports them; ask when an unresolved choice materially changes the result or conflicts with an explicit requirement. Questions may be combined and have no prescribed order.

When presenting options, explain their concrete learner- or author-visible effects in the target language. Avoid bare labels and unsupported promises. Terminology and first mentions follow [language-policy.md](language-policy.md).

## Available Choices

| Choice | Effect and useful context |
| --- | --- |
| Delivery experience | One-on-one self-study lets the Teaching Agent guide a learner directly; classroom slides support projection paced by a human instructor; a combined course supports both. Reuse the intended setting or choose the form suited to the task. |
| Personalization | Examples, Analogies, Language style, and Practical value have the effects defined in [prompt-contracts.md#personalization-directions](prompt-contracts.md#personalization-directions). Any combination, including none, is valid. Selection uses available learner context and does not authorize collecting more context. |
| Interactions | Learner-context collection supports later teaching; pre-content thinking activates a judgment the explanation can refine; self-check supports consolidation. Choose useful interactions from the course goal unless the author has constrained them. An explicit choice of none excludes learner-answer controls and branches. |
| Course structure | Chapter and lesson counts control grouping and granularity. Use explicit counts when supplied; otherwise derive a suitable structure from material, audience, and learning goals. See [segmentation-workflow.md](segmentation-workflow.md) for structure design. |
| Teacher identity | A supplied name becomes the optional teacher identity in the Course Prompt. A blank or absent name requires no named identity. Do not invent credentials or a biography. |
| Teacher avatar | A supplied JPG or PNG can become the platform avatar. Setting it is a platform capability described in [course-management.md](course-management.md); it is not course content. An avatar question is optional and never blocks authoring. |

## Optional Controls

Use the shapes in [data-contracts.md#input-contract](data-contracts.md#input-contract) when structured controls are helpful. Natural-language choices are equally usable; no intermediate JSON or separate design report is required.

- Preserve explicit delivery requirements, counts, teacher identity, interaction restrictions, and personalization selections.
- Resolve personalization from the request or existing course instructions. With no basis for individual-background adaptation, use the source, author requirements, and intended audience baseline. An explicit none is an empty selection, not permission to remove needed examples or explanations.
- For structured interaction policy, selected purposes map to `enabled`, explicit none to `disabled`, and no constraint to `unspecified`. Teaching effects are described in [pedagogy.md#interaction-policy-precedence](pedagogy.md#interaction-policy-precedence).
- Keep `course_author_avatar_source` transient. An absent source leaves the platform avatar unchanged; accepted files follow the platform's upload and compression requirements.

The result is the design information needed for the requested work, in a form the using agent finds useful. Record consequential assumptions or unresolved conflicts without requiring every possible choice to be answered.
