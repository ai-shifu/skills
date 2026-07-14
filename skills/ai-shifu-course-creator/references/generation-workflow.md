# Generation Workflow

## Generation

Generate a runnable Teaching Prompt for each lesson.

### Teaching Pattern Baseline

Apply the mode-independent patterns and constraints in `pedagogy.md#teaching-patterns`, `pedagogy.md#cognitive-techniques`, `pedagogy.md#variable-strategy`, `pedagogy.md#interaction-design`, and `pedagogy.md#visual-text-coordination`, then apply the selected cross-artifact profile from `delivery-modes.md`.

Consume the normalized Course Design Intake interaction policy only after it passes `data-contracts.md#interaction-policy`. Apply its teaching effect and substitution from `pedagogy.md#interaction-policy-precedence`; Generation does not reinterpret the modes or purposes. Whenever that policy calls for an interaction, apply `pedagogy.md#interaction-design` before writing the standalone interaction line required by [Prompt Contracts](prompt-contracts.md).

### Single-Lesson Generation Strategy

Required anchors per lesson:

1. Opening paragraph with the teaching-start function required by the structural-metadata rule in [Prompt Contracts](prompt-contracts.md) — not a copied chapter / lesson title or directory label.
2. Opening objective plus slide-style visual cover.
3. Evidence-chain explanation.
4. The interaction slot or non-interactive substitute required by `pedagogy.md#interaction-policy-precedence`, with visible instructional value.
5. At least one reusable deliverable.
6. Lesson close with summary or decision checkpoint.

Optional modules: viewpoint calibration, misconception correction, dual deliverables (understanding + action), cross-lesson bridge sentence, additional visual-text reinforcement blocks.

### Slide-Only Generation Override

When `delivery_mode` is `pure_slides`, Generation applies `delivery-modes.md#pure-slides`; that owner defines every replacement to the standard teaching baseline.

### Outputs

Return `data-contracts.md#generation-output`; each item follows `data-contracts.md#lesson-schema`.

### Validation

Run `review-checklist.md#generation-validation` before returning any lesson.

### Working with Author-Provided Images

When the author supplies image assets — local files (any format incl. heic/heif) or remote URLs — three steps apply *within* Generation (and any later phase that touches the same lessons):

1. **Understand each image before placing it.** You cannot choose the lesson, position, or alt text without knowing what the image shows. Two regimes:
   - **You can see the image** (attached in this conversation and your model is multimodal): describe it to yourself in one sentence — what concept, relation, or example it conveys — then choose the lesson and position per `pedagogy.md#visual-text-coordination`.
   - **You cannot see the image** (only a file path / URL, or your model is text-only): **stop and ask the user**. Do not guess from the filename. Offer two options: (a) the user provides a one-sentence description per image (you will pass it as `--alt`), or (b) the user renames each file to a semantically meaningful name so you can infer the topic. Proceed only after one of these is in place.
2. **Upload via `shifu-cli.py upload-image`** (`--file` for local files — auto-preprocessed, or `--url` for remote; always pass `--course-dir` and `--alt`) and capture the printed `https://res.ai-shifu.cn/<uuid32>` URL. Full flags, preprocessing, and manifest behavior: `cli/cli-reference.md#image-upload`.
3. **Embed per `markdownflow.md#images`.** Default to 3.1 (deterministic-wrapped standard markdown); use 3.2 (instruction-style HTML) only when the lesson genuinely needs width control, alignment, a figure caption, or side-by-side layout — express every lock through wording (`必须原样保留` / `必须原样输出` / `不要改写`), never mix deterministic blocks into the instruction. Apply standard placement through `pedagogy.md#visual-text-coordination` and any explanation-pair override through `delivery-modes.md`.
