# Course Design Choices

Help the author express consequential course choices and translate them into usable design constraints. The using agent decides which choices matter, whether a question is needed, and when to ask it.

## Using Available Context

Reuse the author's instructions, supplied materials, and existing course behavior before asking. Missing fields do not require a questionnaire. For an unresolved choice selected by the using agent, frame the question around the consequence for this course. Questions may be combined and have no prescribed order; this reference does not add a checkpoint or determine when work pauses.

When presenting options, explain their concrete learner- or author-visible effects in the target language. Avoid bare labels and unsupported promises. Terminology and first mentions follow [language-policy.md](language-policy.md).

### Asking for Useful Information

Make each request answerable without knowledge of pedagogy or platform terminology. Say what the information will change, offer a reasonable recommendation or fallback when available, and distinguish a provisional assumption from a confirmed fact. Ask about the learning task rather than handing the author a menu of method names. For example: “这节课学完后，学员更需要判断方案是否合适，还是独立做出一个方案？这会影响我安排案例判断还是动手练习。按您现有材料，我建议先练判断。”

For material requests, identify the needed part and its use: “如果要把这一步画成实际操作图，需要当前版本的操作截图；您可以提供截图，也可以使用明确标注的通用示意图。” Do not present a fabricated interface or teacher experience as an authentic supplied asset. Questions about audience, starting knowledge, source coverage, time limits, learning evidence, or projection context are useful when they resolve the actual design issue; they are not required intake fields. Keep established answers and author corrections usable throughout the task.

### Explaining a Recommendation

Make a recommendation concrete enough to revise: name the proposed method or describe the teaching action, explain the specific learning difficulty it addresses, show the expected learner experience, and state the relevant limit. Apply the [method attribution rules](teaching-design.md#method-attribution) for source selection and evidence boundaries. Keep this explanation brief enough to help the author make the actual decision.

For example: “这一段推荐‘示例演练’：先展示方案如何一步步得到，再解释关键判断。依据是 [MIT 教学与学习实验室的说明](https://tll.mit.edu/teaching-resources/how-people-learn/worked-examples/)。您的学员刚接触这个流程，完整示范的目的是让他们看清思路；但看懂示范还不能证明能独立完成。若已选择举例个性化，可以用学员已有记忆中明确提到的相关任务来讲；缺少相关信息时沿用课程的中性案例。” This explains a proposed choice without requiring the author to select it from a catalog, asking for more learner data, or placing the rationale in learner-time Prompts.

Explain a visual choice by its purpose as well: “这一处用流程图把分支条件放在一起比较，判断理由用文字展开。” Keep author confirmation and revision focused on the substantive decision and its effect; invocation timing and continuation remain with the using agent.

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
