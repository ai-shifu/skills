# Generation Workflow

## Generation

Generate a runnable Teaching Prompt for each lesson.

### Teaching Pattern Baseline

Apply the patterns and constraints in `pedagogy.md#teaching-patterns`, `pedagogy.md#cognitive-techniques`, `pedagogy.md#variable-strategy`, `pedagogy.md#interaction-design`, and `pedagogy.md#visual-text-coordination` unless content requires a justified variation.

Encode the selected teaching method in each Teaching Prompt itself. Every lesson must carry enough pedagogical direction to run with the Course Prompt contributing only course-wide role and presentation style; do not rely on the Course Prompt to supply, repair, or override the lesson's pedagogy.

Consume the normalized Course Design Intake interaction policy only after it passes `data-contracts.md#interaction-policy`. Apply its teaching effect and substitution from `pedagogy.md#interaction-policy-precedence`; Generation does not reinterpret the modes or purposes. Whenever that policy calls for an interaction, choose its type and persistence per `pedagogy.md#interaction-design` and `pedagogy.md#variable-strategy`, then apply [MarkdownFlow Authoring](#markdownflow-authoring).

### MarkdownFlow Authoring

This section owns how Generation encodes already-resolved teaching and persistence decisions into MarkdownFlow. Parser recognition and runtime effects remain defined in `markdownflow.md`.

#### Interaction Encoding

- Put the complete learner-facing question immediately before the interaction control, and put the `?[]` control on its own line.
- Keep only control content inside `?[]`: option labels, the optional `%{{name}}` assignment prefix, and any free-text marker plus short hint.
- Use the form whose selection behavior was chosen in `pedagogy.md#interaction-design`: `|` for single-select, `||` for multi-select, and `...` immediately before the hint or custom-answer label for text entry.
- Apply `pedagogy.md#variable-strategy` after deciding the interaction's downstream effect. Use `%{{name}}` only for a named answer that leaves the current lesson; lesson-local answers use the no-variable form. Never use a blank variable name as no-variable syntax.
- For an input, write a specific question before the control and a shorter hint after `...`. For select-plus-input, put `...` at the start of the custom-answer option rather than at the end of the surrounding prompt.
- When preceding text enumerates or describes choices, keep the control labels identical in set, order, and wording.
- After the control, state the immediate feedback or visible downstream effect required by `pedagogy.md#interaction-design`.

Neutral authoring shapes:

```markdown
Ask the learner which path best matches the current case.

?[Path A | Path B]

After the learner answers, explain the selected path and contrast it with the other path.

Ask the learner for the course-wide goal that later lessons and the Course Prompt should use.

?[%{{learning_goal}} ...One-sentence goal]
```

#### Variable and Branch Encoding

- Write branch behavior as natural-language instructions; MarkdownFlow has no programmatic conditional syntax.
- For a lesson-local answer, refer to the learner's latest answer naturally in subsequent lesson instructions rather than inventing a variable.
- For a named value, first bind the substituted value in a natural sentence, such as `The learner goal is {{learning_goal}}.`, and then describe the branches against that sentence's value.
- When a named value can be read before collection, branch on the literal substituted value `UNKNOWN`; do not test whether the marker exists or whether a variable is ready.
- Every named learner-answer reference must have a matching variable-backed collection and satisfy the lifecycle and metadata invariants in `data-contracts.md#variable-table`.
- Compose each newly authored variable name in `resolved_target_language` using only letters, numbers, and underscores. Preserve an existing or source-provided variable name when changing it would break the variable contract.

#### Preservation Encoding

Encode the spans already selected by `optimization-workflow.md#preservation-decisions` with their corresponding MarkdownFlow preservation forms:

- Put a complete standalone single-line span that must bypass the LLM inside `===...===`.
- Put a complete multi-line span that must bypass the LLM inside `!===...!===`. When exact fenced code output is required, keep the complete code fence, language tag, and body inside this form.
- When surrounding content must remain LLM-generated, wrap only the span that needs position and formatting retention inline with `===...===`. Inline preservation does not bypass the LLM and may be translated when output-language transformation applies.
- Encode each selected span independently; content not selected for preservation remains outside its deterministic markers.
- Encode fixed-display and HTML-view images with the distinct forms in [Image Authoring](#image-authoring); an HTML-view directive remains an LLM instruction and therefore does not contain deterministic markers.

The parser and runtime effects of these forms are defined in `markdownflow.md#deterministic-blocks` and `markdownflow.md#preservation`.

### Single-Lesson Generation Strategy

Required anchors per lesson:

1. Opening paragraph with the teaching-start function defined by `pedagogy.md#lesson-loop` — not a copied chapter / lesson title or directory label.
2. Opening objective plus slide-style visual cover.
3. Evidence-chain explanation.
4. The interaction slot or non-interactive substitute required by `pedagogy.md#interaction-policy-precedence`, with visible instructional value.
5. At least one reusable deliverable.
6. Lesson close with summary or decision checkpoint.

Optional modules: viewpoint calibration, misconception correction, dual deliverables (understanding + action), cross-lesson bridge sentence, additional visual-text reinforcement blocks.

### Slide-Only Generation Override

When Course Design Intake resolves to pure slides / classroom interactive slides, replace the default explanation-heavy lesson pattern with a projection pattern. Pure slides are for classroom projection by a human instructor, not AI narration:

- Treat each lesson as a small slide deck controlled by a human instructor.
- Generate slide-facing blocks only: slide title, 2-4 short bullets, and a visual/layout instruction. When the interaction policy permits an interaction, also include its prompt, options, and concise feedback states.
- Keep policy-permitted interactions runnable with the normal MarkdownFlow syntax, but keep the surrounding content presentation-oriented. When the policy calls for the non-interactive substitute, render only the slide-facing content defined by `pedagogy.md#interaction-policy-precedence`.
- Do not instruct the runtime LLM to narrate or verbally explain the slides. Omit long spoken paragraphs and instructions such as "explain to the learner", "walk through", "向学习者说明", "讲解", "用文字解释", or "讲清".
- Do not require the normal visual-text explanation pair. The visual itself and the short on-slide labels carry the projection content; any explanation belongs to the human instructor, not the Teaching Prompt.
- The Course Prompt must describe the runtime role as producing classroom slides, using "interactive slides" only when the interaction policy permits interactions, not as conducting one-on-one tutoring. Do not include course-level instructions that ask the AI to verbally explain the lesson to a single learner.

### Outputs

Per-lesson schema in `data-contracts.md#lesson-schema`.

Write `lesson_teaching_prompts[].lesson_title` and every authored natural-language part of `lesson_teaching_prompts[].teaching_prompt` in `resolved_target_language`. This includes teaching instructions, learner-facing questions and options, input hints, feedback and branch descriptions, explanations, summaries, and deterministic output text. Keep JSON keys, lesson ids, MarkdownFlow syntax, existing variable names, URLs, code, and required verbatim source text unchanged.

When fallback mode adds `assumptions[]` or `upgrade_notes[]`, write those human-readable entries in `resolved_target_language`.

### Validation

- Each `teaching_prompt` is valid runnable MarkdownFlow.
- The first non-empty line of each Teaching Prompt performs the teaching-start function defined by `pedagogy.md#lesson-loop`, not a duplicated `structure.json` chapter / lesson title or a copied source heading such as `# 第2章 ...`.
- Per-lesson schema populated per `data-contracts.md#lesson-schema`.
- Pedagogical decisions pass per `pedagogy.md`; authoring passes [MarkdownFlow Authoring](#markdownflow-authoring); syntax and runtime behavior pass `markdownflow.md`.
- The Teaching Prompt contains the lesson's teaching method and does not outsource pedagogical decisions to the Course Prompt.
- The lesson title and every authored natural-language Teaching Prompt fragment pass the output-language requirements in [Outputs](#outputs).

### Image Authoring

Generation owns the choice and composition of image forms. The runtime behavior of each resulting form is defined in `markdownflow.md#images` and `markdownflow.md#deterministic-blocks`.

Raw SVG, HTML drawings, Mermaid, PlantUML, and Graphviz source are not image-embedding forms by default. Include one of those raw formats only when the author explicitly requests it.

Every uploaded image URL embedded in a Teaching Prompt uses `https://res.ai-shifu.cn/<uuid32>`. Choose one of these forms after the lesson's visual intent is known:

| Authoring intent | Form |
| --- | --- |
| Display the uploaded image as authored, without layout customization | Wrap standard Markdown image syntax in the single-line deterministic form: `===![informative alt](url)===` |
| Control width, alignment, caption, or multi-image layout | Write a natural-language HTML-view instruction and leave it generative |

For a fixed image, make the alt describe what information the image conveys rather than using a generic label. Write newly authored alt text in `resolved_target_language`; preserve a source-provided alt selected as immutable. The deterministic form makes the image line bypass the LLM.

For an HTML-view image, do not put generated HTML or the instruction inside `===...===` / `!===...!===`. Give the LLM one explicit directive in `resolved_target_language` containing the position, exact URL, image content, caption, and layout. Write newly authored descriptions, captions, and layout wording in `resolved_target_language`; preserve source-provided immutable text. The wording must require the image to appear at that position, preserve the URL exactly, retain the content description for a semantic alt, and preserve the original aspect ratio whenever width is constrained. Use this compact shape:

```markdown
必须在此处以 HTML-view 方式插入一张带图注的图片,不得省略,并使用 HTML <figure>/<figcaption> 结构。

- URL(必须原样保留):https://res.ai-shifu.cn/<uuid32>
- 图片内容(必须用于生成语义化 alt,不得省略):图片传达的具体概念或关系
- 图注文字(必须原样输出,不要改写):图注原文
- 展示方式:居中,宽度不超过容器 70%,保持原始宽高比
```

The preservation phrases in this directive constrain the runtime LLM through wording; they are not parser-level locks. Keep every URL on its own labeled line. For multiple images, give each image a separate URL and content line so their order is explicit. Express layout responsively in natural language rather than fixed pixel values.

Apply the explanatory-text requirement and the slide-only exception from `pedagogy.md#visual-text-coordination`; do not redefine that teaching decision here.

#### Image Output Validation

Before finalizing a generated Teaching Prompt that embeds images:

1. Build an expected-image record for every selected asset. For an uploaded asset, read `remote` and `alt` from `<course-dir>/assets/image-manifest.json` as defined by `cli/course-directory-spec.md#assets`; add the selected image form, caption, position, layout constraints, and ordering from the current authoring decision. In explicitly local artifact-only work where upload is excluded, use the authoritative image URL and metadata supplied by the source record instead; do not invent missing fields. If the authoritative record lacks `remote`, an informative `alt`, or any authoring field required by the selected image form, report the missing fields as a blocking error and stop before generating the affected Teaching Prompt.
2. Compare the generated Teaching Prompt with every expected-image record. The exact URL, description or alt, caption, position, layout constraints, and ordering must all be present where required. A fixed-display record must use the complete deterministic Markdown image form; an HTML-view record must retain every required field in one natural-language directive without deterministic markers.
3. If any field is missing, changed, duplicated, or reordered, regenerate only the affected image instruction or lesson from its expected-image record, then run the same comparison again.
4. If the regenerated result still fails, stop Generation for that lesson and report the mismatched fields as a blocking error. Do not finalize or hand off the Teaching Prompt.

### Working with Author-Provided Images

When the author supplies image assets — local files (any format incl. heic/heif) or remote URLs — three steps apply _within_ Generation (and any later phase that touches the same lessons):

1. **Understand each image before placing it.** You cannot choose the lesson, position, or alt text without knowing what the image shows. Two regimes:
   - **You can see the image** (attached in this conversation and your model is multimodal): describe it to yourself in one sentence — what concept, relation, or example it conveys — then choose the lesson and position per `pedagogy.md#visual-text-coordination`.
   - **You cannot see the image** (only a file path / URL, or your model is text-only): **stop and ask the user**. Do not guess from the filename. Offer two options: (a) the user provides a one-sentence description per image (you will pass it as `--alt`), or (b) the user renames each file to a semantically meaningful name so you can infer the topic. Proceed only after one of these is in place.
2. **Upload via `shifu-cli.py upload-image`** (`--file` for local files — auto-preprocessed, or `--url` for remote; always pass `--course-dir` and `--alt`) and capture the printed `https://res.ai-shifu.cn/<uuid32>` URL. Full flags, preprocessing, and manifest behavior: `cli/cli-reference.md#image-upload`.
3. **Embed per [Image Authoring](#image-authoring).** Apply the selected fixed-display or HTML-view form without reinterpreting the image's pedagogical placement.
