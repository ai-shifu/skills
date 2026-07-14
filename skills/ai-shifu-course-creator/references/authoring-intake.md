# Authoring Intake

## Course Design Intake (before Orchestration)

Run this intake after `course-target.md#resolve-the-course-target` and before Orchestration for end-to-end course creation, author-only generation, and existing-course edits that change structure, lesson design, delivery mode, or interaction strategy. Do not run it for deploy-only, analytics, login, publish, management, or statistics requests.

Before asking anything, extract answers already present in the user's instruction, source material, or pulled course directory. Ask only for missing items in the user's language as a step-by-step choice flow: ask the usage-scenario question first, wait for the answer, then ask only the next still-missing applicable question. Do not offer a bypass before the required choice flow is complete, and do not invent defaults from a sparse topic or short brief. The fallback choices below apply only after the user explicitly skips a question or asks you to continue without answering it.

1. What usage scenarios should this course support? Multiple choices are allowed: students follow AI one-on-one for personalized self-study; classroom slides shown by an instructor.
2. What should interactions do? Multiple choices are allowed: understand learner context for adaptive teaching; ask before teaching to trigger thinking or challenge assumptions; self-check learning effect at each lesson end. Choosing none means no interactions.
3. When the selected profile permits Listen Mode under [Delivery Modes](delivery-modes.md), should AI voice teach the course? State that Listen Mode consumes more AI-Shifu credits. If the user skips this question, record disabled.
4. How many chapters and lessons should the course have?

## Normalization

- **Delivery mode**: only classroom slides selected → `pure_slides`; any personalized self-study selection → `standard`; question explicitly skipped → infer from the supplied source structure without inventing a fixed scenario. The resulting cross-artifact behavior comes only from `delivery-modes.md`.
- **Interaction policy**: one or more purposes selected → `enabled` with exactly those purposes; none selected → `disabled` with an empty `purposes` array; question explicitly skipped → `unspecified` with an empty `purposes` array. Validate the object through `data-contracts.md#interaction-policy`; teaching effects come only from `pedagogy.md#interaction-policy-precedence`.
- **Listen Mode**: record the explicit enable/disable answer, or `false` after an explicit skip; the selected [Delivery Mode](delivery-modes.md) owns any profile-level override.
- **Structure targets**: explicit chapter and lesson counts constrain the outline; after an explicit skip, infer them from source volume and lesson granularity.

## Normalized Output

Return the Course Design Intake subset of `data-contracts.md#course-design-controls`: `delivery_mode`, `listen_mode_enabled`, `interaction_policy`, `chapter_count_target`, and `lesson_count_target`. Authoring Controls adds `execution_mode`; pass the resulting `authoring_run_controls` object unchanged to the selected workflow. This object replaces only those six normalized control fields. Keep the remaining authoring context, including source material, author identity, course profile, delivery constraints, and target language, alongside it without copying those values into the controls object.
