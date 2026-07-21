# Course Design Intake

Collect and normalize the author's design choices before course structure or Teaching Prompt generation begins. This file does not define the course pipeline, artifact schemas, or teaching effects.

## Required References

- `language-policy.md`
- `data-contracts.md#interaction-policy`
- `data-contracts.md#teaching-prompt-personalization-level`
- `teaching-prompt.md#personalization-levels`

## Intake Scope

Collect only the unresolved design choices requested by the selected authoring route. Deployment, authentication, platform management, and analytics questions are outside this file.

Before asking anything, extract answers already present in the user's instruction, source material, or pulled course directory. Ask only for missing items, one choice at a time and in the order below. Do not invent defaults from a sparse topic or brief, and do not proactively offer to bypass a required choice or “decide for the author.” Apply a listed fallback only after the author explicitly skips that question or asks to continue without answering.

1. Ask which usage scenarios the course should support. Allow personalized AI one-on-one self-study, interactive classroom slides, or both.
2. Unless the course is slide-only, ask how much personalization freedom the final learner-facing course should allow. Explain that a higher level makes the Teaching Prompt emphasize teaching intent and key points while fixing less exact learner-facing wording, example identity and detail, and feedback wording. State that the complete teaching sequence, exact slide count, each slide's position and teaching purpose, and which content slots appear, where they appear, and what teaching purpose each serves — including whether an example is required — stay fixed at every level; only expression inside those slots varies. Present all five ordered choices from `teaching-prompt.md#personalization-levels`: `1` — High determinism, `2` — Determinism-leaning, `3` — Balanced, `4` — Personalization-leaning, and `5` — High personalization. Render the question, option names, and owner-defined behavior descriptions in `resolved_target_language`. Do not silently skip this question for standard or combined delivery. For slide-only delivery with no already-provided level, do not ask it and use level `1` (High determinism).
3. Ask what interactions should do. Allow learner-context collection, pre-content thinking or misconception activation, and lesson-end self-check. Choosing none means no interactions.
4. Unless the course is slide-only, ask whether Listen Mode should be enabled and state that it consumes more AI-Shifu credits. An unanswered question defaults to disabled.
5. Ask for the desired chapter and lesson counts.

## Normalized Design Controls

Produce these controls once and pass them unchanged to downstream workflows:

- **Usage scenario**: normalize personalized AI self-study to standard one-on-one delivery, classroom projection to pure-slide delivery, and an explicit combined choice to both modes. If skipped, infer the delivery mode from source structure. Teaching and presentation effects remain in their owning references.
- **Teaching Prompt personalization level**: preserve an explicit integer from `1` through `5` as the top-level `teaching_prompt_personalization_level` and pass it unchanged. Reuse a value already present in context instead of asking again, including for pure-slide delivery. When pure-slide delivery has no explicit value, normalize directly to level `1` without asking. For standard or combined delivery, apply fallback level `3` only when the author explicitly skips or asks to continue without answering; absence alone is not a skip, and the level must not be inferred from source style or other controls. Level semantics and materialization remain owned by `teaching-prompt.md#personalization-levels`.
- **Interaction policy**: one or more purposes produces `enabled` with exactly those purposes; none produces `disabled` with an empty `purposes` array; skipped produces `unspecified` with an empty `purposes` array. Validate only the shape against `data-contracts.md#interaction-policy`; teaching effects belong to `pedagogy.md#interaction-policy-precedence`.
- **Listen Mode**: pure slides always disable it. Otherwise preserve the explicit answer or use disabled after a skipped/unanswered question.
- **Chapter and lesson counts**: preserve the explicit numbers. If skipped, infer them from source volume and lesson granularity rather than using a fixed count.

## Validation

- Every answer available from existing context is reused rather than asked again.
- Every missing applicable question is asked before its fallback is applied.
- Pure-slide delivery resolves an otherwise missing `teaching_prompt_personalization_level` to level `1` without asking the personalization question.
- The normalized `teaching_prompt_personalization_level` passes `data-contracts.md#teaching-prompt-personalization-level`; invalid values are rejected rather than converted or treated as a skip.
- The normalized interaction policy passes the data-contract invariants.
- The selected delivery mode, Listen Mode, and structure constraints are internally consistent.
