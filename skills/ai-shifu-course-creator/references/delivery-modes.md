# Delivery Modes

Authoritative source for authoring behavior selected by `data-contracts.md#course-design-controls`. This file owns only the differences that a delivery mode applies to Teaching Prompts, the Course Prompt, and the desired Listen Mode state handed off by authoring; general teaching design remains in `pedagogy.md`, the base Course Prompt remains in `course-prompt.md`, MarkdownFlow syntax remains in `markdownflow.md`, and independent platform operations remain outside this contract.

## Resolution and Handoff

- Course Design Intake resolves `delivery_mode` and `listen_mode_enabled`, then returns both through `authoring_run_controls`; downstream authoring phases consume the latest structured handoff without reinterpreting or asking for those fields again, and a full authoring pipeline returns them through `data-contracts.md#final-authoring-output`.
- When the selected route continues from authoring into a platform mutation, pass the normalized `listen_mode_enabled` value to Deployment as the desired platform state. Explicitly artifact-only authoring returns the value only as data and does not authorize a platform change.
- A focused audit or narrow existing-course prompt edit without a same-request intake preserves the supplied artifact's existing mode-dependent structure and does not resolve, infer, or ask for `delivery_mode`. If the requested change would alter that structure or profile, run Course Design Intake before continuing.
- Independent deployment and standalone platform management are outside this authoring contract; the selected platform workflow owns their attribute behavior.
- Apply the selected authoring section below once. Standard preserves the resolved Listen Mode decision; Pure Slides requires `false` within the authoring handoff.
- If one authoring request explicitly combines Pure Slides with Listen Mode enabled, do not silently override either instruction; ask the user to choose between Pure Slides with Listen Mode disabled and Standard with the requested Listen Mode setting.

## Standard

- **Teaching Prompts**: apply the mode-independent lesson and visual-text rules in `pedagogy.md`.
- **Course Prompt**: fill the standard `course-prompt.md#fillable-template` without a delivery-mode replacement.
- **Listen Mode**: carry the schema-valid resolved `listen_mode_enabled` decision through the authoring handoff unchanged.

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

- Normalize `listen_mode_enabled` to `false` within Pure Slides authoring because this profile omits AI narration.
- Carry `false` through the authoring handoff; an independent platform-management request remains governed by its explicit user instruction rather than by inferred course content.
