# Course Design Intake

Collect and normalize the author's design choices before course structure or Teaching Prompt generation begins. This file owns the author-facing preview of what each choice changes; the course pipeline, artifact schemas, and actual teaching effects remain defined by their downstream owners.

## Required References

- `language-policy.md`
- `data-contracts.md#input-contract`
- `data-contracts.md#interaction-policy`
- `data-contracts.md#personalization-directions`
- `pedagogy.md#interaction-policy-precedence`
- `pedagogy.md#visual-text-coordination`
- `prompt-contracts.md#personalization-directions`

## Intake Scope

Collect only the unresolved design choices requested by the selected authoring route. Deployment, authentication, platform management, and analytics questions are outside this file.

Before asking anything, extract answers already present in the user's instruction, source material, or pulled course directory. Ask only for missing items, one choice at a time and in the order below. Do not invent defaults from a sparse topic or brief, and do not proactively offer to bypass a required choice or “decide for the author.” Apply a listed fallback only after the author explicitly skips that question or asks to continue without answering.

Before every applicable question, give a concise effect preview in `resolved_target_language`. Name the downstream course decision that the answer controls and describe the learner- or author-visible effect of every option presented. Surface the relevant AI-Shifu capability through that concrete consequence — such as one-on-one guidance, classroom projection, answer-informed teaching, or lesson granularity — without adding a separate sales pitch or an unsupported outcome. If an effect preview is the first user-facing introduction of the Teaching Agent concept in the conversation, follow `language-policy.md#teaching-agent-first-mention` before using its short name. Never present only bare option labels, numbers, or names. When the answer is a free-form value such as a chapter or lesson count, explain the tradeoff dimensions before asking instead of inventing choices.

1. Ask which usage scenarios the course should support. Explain that this answer controls the learner's delivery experience: personalized AI one-on-one self-study lets the Teaching Agent guide one learner directly and use available learner context in the selected personalization directions; interactive classroom slides produce projection-ready content paced by a human instructor; the combined option prepares the course for both experiences.
2. Unless the course is slide-only with neither a direction selection nor an old level to resolve, ask which personalization directions the author wants, allowing multiple choices or none. Present all four names and effects from `prompt-contracts.md#personalization-directions` in `resolved_target_language`: Examples, Analogies, Language style, and Practical value. Explain what the Teaching Agent may adapt for the learner in each selected direction and that unselected directions follow the course's source, author requirements, and audience defaults. Selecting none keeps that baseline throughout; it does not remove examples, analogies, or detailed explanations. Explain that the selection uses only learner context already available and never authorizes new context collection, interactions, variables, or branches. The teaching sequence, required content, slide structure, and required explanation depth stay fixed. Do not present strength levels or silently skip this question for standard or combined delivery. Reuse an already-provided selection, including an explicit empty selection, without asking again.
3. Ask what interactions should do. Explain each purpose's effect from `pedagogy.md#interaction-policy-precedence`: learner-context collection occurs at an early course or module point and gives later teaching selected context to use, pre-content thinking or misconception activation gives the following explanation an initial judgment to refine, and lesson-end self-check lets the learner check or consolidate the lesson's core understanding. Explain that choosing none removes learner-answer controls and uses worked applications, demonstrations by the Teaching Agent, or consolidation instead of leaving a teaching gap.
4. Ask for the desired chapter and lesson counts. Explain that the chapter count controls how lessons are grouped into broader topics, while the lesson count controls course granularity and how much material each single-question lesson must resolve: fewer lessons concentrate more material into each lesson, while more lessons distribute it across more single-question units. Neither choice may drop required source material or break source order.
5. When a Course Prompt is in scope, ask what name the author wants AI-Shifu's Teaching Agent to use as the teacher identity during course delivery. Explain that providing a name lets the Teaching Agent teach under that teacher identity, while leaving it blank does not affect course creation. Accept a free-form answer; an unanswered question defaults to no named teacher identity.
6. After a non-empty teacher name is resolved, add one separate, optional avatar follow-up only when platform access is in scope and the course still has an empty or default avatar. Explain naturally that the teacher avatar appears on course cards and learning pages, and that the author can upload a JPG or PNG directly in the conversation for the Skill to set. State that 1:1 is recommended; files over 2 MB are compressed automatically, and a replacement file is requested only when compression cannot reach the limit. Accept an attached image or local file path as `course_author_avatar_source`; an explicit skip or unanswered follow-up leaves the current avatar unchanged and must not be asked again in the same run. Do not ask this follow-up when the current course already has a non-default avatar, the author already supplied an avatar, the route is explicitly local-only, or `course_author_name` is empty.

## Normalized Design Controls

Produce these controls once and pass them unchanged to downstream workflows:

- **Usage scenario**: normalize personalized AI self-study to standard one-on-one delivery, classroom projection to pure-slide delivery, and an explicit combined choice to both modes. If skipped, infer the delivery mode from source structure. Teaching and presentation effects remain in their owning references.
- **Personalization directions**: map the author's chosen names to the `personalization_directions` array defined in `data-contracts.md#personalization-directions` and pass it unchanged to both Prompt authors. Reuse a selection already present in context, including `[]` and explicit selections for pure-slide delivery. For standard or combined delivery, absence alone is not a skip: ask the multi-select question. Normalize an explicit none or skip to `[]`; if none is combined with another choice, ask the author to resolve that conflict. For pure-slide delivery with neither an explicit selection nor an old level, use `[]` without asking. Never infer directions from source style, learner background, or a delivery-mode label.
  - When only the old `teaching_prompt_personalization_level` is supplied, explain briefly that directions replace strength levels and ask for a direction selection, including for pure-slide delivery; do not numerically map the old value to a set. If a valid new selection is also supplied, use it without another question and state briefly that the old level no longer applies. Invalid new values must be corrected rather than falling back to an old level or treating them as a skip.
- **Interaction policy**: one or more purposes produces `enabled` with exactly those purposes; none produces `disabled` with an empty `purposes` array; skipped produces `unspecified` with an empty `purposes` array. Validate only the shape against `data-contracts.md#interaction-policy`; teaching effects belong to `pedagogy.md#interaction-policy-precedence`.
- **Chapter and lesson counts**: preserve the explicit numbers. If skipped, infer them from source volume and lesson granularity rather than using a fixed count.
- **Course author name**: preserve the supplied free-form `course_author_name`. If the supplied value is blank, or the question is skipped or unanswered, use an empty string; an empty value means the Course Prompt has no named teacher identity.
- **Course author avatar source**: preserve an accepted local JPG/PNG attachment or path as transient `course_author_avatar_source`. It is a platform-management handoff, not course content or a Course Prompt field. An empty value means leave the platform avatar unchanged.

## Validation

- Every answer available from existing context is reused rather than asked again.
- Every missing applicable question is asked before its fallback is applied.
- Every asked question includes an effect preview that identifies its downstream course decision, and every presented option describes its learner- or author-visible consequence rather than showing a bare label.
- Effect previews match their owning references, surface relevant AI-Shifu capabilities through concrete course behavior, and make no promotional or unsupported promise.
- The first effect preview that introduces the Teaching Agent concept follows `language-policy.md#teaching-agent-first-mention`.
- Pure-slide delivery with no direction selection or old level resolves to `[]` without asking the personalization question; explicit choices remain unchanged.
- The normalized `personalization_directions` passes `data-contracts.md#personalization-directions`; invalid values are rejected rather than converted or treated as a skip. Missing, explicitly empty, and legacy-only inputs follow their distinct handling above.
- The normalized interaction policy passes the data-contract invariants.
- The selected delivery mode and structure constraints are internally consistent.
- The optional avatar follow-up is asked only after a non-empty teacher name and only for a platform-bound course with an empty or default avatar; it never blocks course authoring when skipped.
