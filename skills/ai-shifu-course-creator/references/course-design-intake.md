# Course Design Intake

Collect and normalize the author's design choices before course structure or Teaching Prompt generation begins. This file does not define the course pipeline, artifact schemas, or teaching effects.

## Required References

- `language-policy.md`
- `data-contracts.md#interaction-policy`

## Intake Scope

Collect only the unresolved design choices requested by the selected authoring route. Deployment, authentication, platform management, and analytics questions are outside this file.

Before asking anything, extract answers already present in the user's instruction, source material, or pulled course directory. Ask only for missing items, one choice at a time and in the order below. Do not invent defaults from a sparse topic or brief, and do not proactively offer to bypass a required choice or “decide for the author.” Apply a listed fallback only after the author explicitly skips that question or asks to continue without answering.

1. Ask which usage scenarios the course should support. Allow personalized AI one-on-one self-study, interactive classroom slides, or both.
2. Ask what interactions should do. Allow learner-context collection, pre-content thinking or misconception activation, and lesson-end self-check. Choosing none means no interactions.
3. Unless the course is slide-only, ask whether Listen Mode should be enabled and state that it consumes more AI-Shifu credits. An unanswered question defaults to disabled.
4. Ask for the desired chapter and lesson counts.

## Normalized Design Controls

Produce these controls once and pass them unchanged to downstream workflows:

- **Usage scenario**: normalize personalized AI self-study to standard one-on-one delivery, classroom projection to pure-slide delivery, and an explicit combined choice to both modes. If skipped, infer the delivery mode from source structure. Teaching and presentation effects remain in their owning references.
- **Interaction policy**: one or more purposes produces `enabled` with exactly those purposes; none produces `disabled` with an empty `purposes` array; skipped produces `unspecified` with an empty `purposes` array. Validate only the shape against `data-contracts.md#interaction-policy`; teaching effects belong to `pedagogy.md#interaction-policy-precedence`.
- **Listen Mode**: pure slides always disable it. Otherwise preserve the explicit answer or use disabled after a skipped/unanswered question.
- **Chapter and lesson counts**: preserve the explicit numbers. If skipped, infer them from source volume and lesson granularity rather than using a fixed count.

## Validation

- Every answer available from existing context is reused rather than asked again.
- Every missing applicable question is asked before its fallback is applied.
- The normalized interaction policy passes the data-contract invariants.
- The selected delivery mode, Listen Mode, and structure constraints are internally consistent.
