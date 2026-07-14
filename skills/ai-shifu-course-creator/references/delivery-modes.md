# Delivery Modes

Authoritative source for cross-artifact behavior selected by `data-contracts.md#course-design-controls`. This file owns only the differences that a delivery mode applies to Teaching Prompts, the Course Prompt, and Listen Mode; general teaching design remains in `pedagogy.md`, the base Course Prompt remains in `course-prompt.md`, and MarkdownFlow syntax remains in `markdownflow.md`.

## Resolution and Handoff

- When authoring already produced `authoring_run_controls`, consume `delivery_mode` and `listen_mode_enabled` from the latest structured handoff without reinterpreting or asking for them again; after a full pipeline they come from `data-contracts.md#final-authoring-output`.
- In an independent deployment, management, or existing-course optimization session, read the effective local artifacts, or pull the course before reading its Teaching Prompts and Course Prompt. Preserve the existing delivery mode when those artifacts identify it unambiguously; otherwise ask the user to confirm the mode.
- Return the resolved fields through `authoring_run_controls` when an authoring phase continues. A standalone platform operation carries the same two values as operational context without inventing the other authoring controls.
- Apply the selected section below once. Standard preserves the resolved Listen Mode decision; Pure Slides overrides it to `false`.

## Standard

- **Teaching Prompts**: apply the mode-independent lesson and visual-text rules in `pedagogy.md`.
- **Course Prompt**: fill the standard `course-prompt.md#fillable-template` without a delivery-mode replacement.
- **Listen Mode**: carry the schema-valid resolved `listen_mode_enabled` decision into Deployment unchanged.

## Pure Slides

Use this mode only when Course Design Intake resolves the course to classroom slides without a personalized self-study scenario.

### Teaching Prompt Override

- Treat each lesson as a small projection deck controlled by a human instructor.
- Generate slide-facing blocks only: a slide title, two to four short bullets, and a visual or layout instruction. When the interaction policy permits an interaction, also include its prompt, options, and concise feedback states.
- Keep policy-permitted interactions runnable with normal MarkdownFlow syntax. When the policy calls for a non-interactive substitute, render only the corresponding slide-facing content.
- Do not include AI narration directives or learner-facing lecture prose such as "explain to the learner", "walk through", "向学习者说明", "讲解", "用文字解释", "讲清", or long paragraphs intended for the AI to speak.
- Do not require the standard visual-text explanation pair. The visual and short on-slide labels carry the projection content; any explanation belongs to the human instructor.

### Course Prompt Override

- Replace the standard one-on-one teaching role with a classroom-slide production role.
- Use "interactive slides" only when the resolved interaction policy permits interactions.
- Remove instructions that ask the AI to verbally explain the lesson to one learner; preserve every base-template instruction not explicitly replaced here.

### Listen Mode Override

- Listen Mode is unavailable for this profile.
- Normalize `listen_mode_enabled` to `false` and carry that value into deployment.
