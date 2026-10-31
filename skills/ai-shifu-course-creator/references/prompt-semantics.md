# Prompt Semantics

Shared semantics and responsibility boundaries for Teaching Prompts and Course Prompts. Runtime syntax belongs to [markdownflow-syntax.md](markdownflow-syntax.md); optional author controls belong to [authoring-contracts.md](authoring-contracts.md).

## Prompt Semantics

The **Teaching Agent** is AI-Shifu's learner-time AI role that executes Course Prompts and Teaching Prompts, gives interaction feedback, and answers learner follow-up questions. The agent using this skill authors the course; it is distinct from that learner-time role.

Teaching Prompts and Course Prompts are instructions consumed by the Teaching Agent, not a mandatory spoken transcript or finished prose addressed directly to the learner. State what the Teaching Agent should explain, ask, show, adapt, and do in response. Include the required content, relationships, boundaries, and intended effect needed for reliable execution. Near-final wording is appropriate when source fidelity or the author requires it.

The authoring agent chooses teaching approaches, lesson steps, visuals, and layouts suited to the task. No fixed teaching pattern, internal execution plan, or authoring phase is a prerequisite. Once written, a Prompt makes its intended learner-time behavior concrete; optionality during authoring does not make runtime instructions optional.

Address imperative instructions to the Teaching Agent. Name the learner explicitly when referring to learner actions, for example, "Ask the learner to compare the cases." Every second-person form in Prompt instructions, including English `you` and Chinese `你` or `您`, refers to the Teaching Agent. Learner-visible text inside a MarkdownFlow `?[]` interaction or [standalone deterministic output](markdownflow-syntax.md#deterministic-blocks) may address the learner directly.

The intended audience, source facts, and explicit author constraints remain boundaries. Use relevant memory to connect teaching to the learner's actual earlier input under [markdownflow-syntax.md#memory](markdownflow-syntax.md#memory). Platform-supplied learner context is additive within the same boundaries: use only explicitly stated, relevant background and preferences for the resolved personalization directions. Do not retarget the course, infer missing facts, or quote, summarize, or reveal the learner profile. Empty, unknown, irrelevant, or unavailable context uses neutral course-appropriate defaults.

Each Prompt body serves learner-time delivery. Keep authoring decisions, selection interfaces, workflow notes, and rationale outside runtime instructions. Teaching Prompt source-only comments may help an author navigate the content, as defined in [teaching-prompt.md](teaching-prompt.md); all executable content remains outside comments. Express interactions using either form in [markdownflow-syntax.md#interactions](markdownflow-syntax.md#interactions), with direct feedback, branch, or instructions for using relevant memory.

Use deterministic forms only when exactness protects correctness, teaching effect, runtime behavior, source fidelity, or an explicit requirement. Unselected personalization does not make ordinary prose immutable. [source-preservation.md](source-preservation.md) owns exact-source decisions.

## Personalization Directions

These independent directions describe what learner background may change. The optional structured selection is defined in [authoring-contracts.md#personalization-directions](authoring-contracts.md#personalization-directions); natural-language requirements can express the same choices.

| Direction | Author-facing name | Effect when selected |
| --- | --- | --- |
| `examples` | Examples / 举例 | Use relevant learner tasks, goals, or constraints to choose or explain a required example. Preserve essential conditions, reasoning, and takeaway; changing only a job title is insufficient. |
| `analogies` | Analogies / 类比 | Use a situation supported by the learner's stated experience to explain an analogy. Preserve correspondences and limits; an occupation alone does not establish familiarity. |
| `language_style` | Language style / 语言风格 | Adapt tone, phrasing, terminology explanations, and sentence style to stated preferences and experience, preserving meaning, needed explanation depth, and output language. |
| `value_relevance` | Practical value / 价值阐述 | Connect the lesson's practical value to stated goals, tasks, or constraints at a relevant teaching point. Do not invent benefits or promise outcomes. |

- Honor explicit selections, including none. Resolve an absent selection from the task or existing instructions; with no basis for individual-background adaptation, use the course baseline. One direction does not silently authorize another.
- Unselected directions use source material, author requirements, and intended audience defaults. An empty selection does not remove examples, analogies, practical value, or explanations needed for understanding.
- Personalization affects permitted expression within the authored lesson. It does not independently authorize changes to objectives, required content, source boundaries, explanation depth, teaching sequence, slide structure, interactions, branches, or feedback effects.
- Learner context may become available only at delivery. Keep selected adaptations executable with that context and give a neutral fallback. Do not embed a specific learner's profile in reusable course artifacts.
- A fallback still obeys explicit author constraints. If analogies are permitted only from the learner's explicitly known experience, missing relevant experience calls for a literal explanation or source-based example, not a newly invented analogy. Selecting a direction does not require using it when its author-defined conditions are unmet.
- Both Prompt artifacts implement consistent resolved effects within their own responsibilities. Do not serialize the authoring selection's field name, enum array, or interface into runtime prose. Alignment is checked against available artifacts; an isolated lesson does not require generating an absent companion.

## Artifact Responsibilities

A **Teaching Prompt** contains the lesson's runtime teaching instructions: its intent, required content and reasoning, chosen sequence, visuals, learner interactions, feedback, branches, close, and use of relevant memory. It also owns lesson-specific slide purposes, order, content, and treatment tied to an individual slide. It is sufficiently concrete to run without relying on a Course Prompt to invent lesson pedagogy.

A **Course Prompt** contains course-wide role, shared presentation requirements, and bounded course-wide personalization. Its six-section template is defined in [course-prompt.md](course-prompt.md). It follows each Teaching Prompt and does not replace lesson pedagogy or lesson-specific slide structure. It may use relevant memory, but contains no MarkdownFlow `?[]` controls, collects no learner input, and defines no lesson-local branches. The platform supplies learner context separately; do not serialize platform learner-profile tags or internal profile field names into the artifact.
