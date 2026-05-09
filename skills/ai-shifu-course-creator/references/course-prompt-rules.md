# Course Prompt Rules

## Purpose

`course-prompt.md` defines the AI engine's **course-level persona and operating rules** — the role it plays, how it teaches, how it writes, how it formats output, and how it draws and translates. It is loaded once per course and applied to every lesson.

This is **not the same as a lesson script**:

- Lesson scripts (per-lesson MarkdownFlow) carry **single-lesson teaching instructions**: what to explain, what variable to collect, what to branch on.
- Course prompt carries **cross-lesson constants**: identity, voice, format, terminology, drawing policy.

Do not duplicate per-lesson interaction logic, variable collection, or branching here. If a rule only applies to one lesson, it belongs in that lesson's MarkdownFlow, not in the course prompt.

## Required Sections

The fillable template (`course-prompt-template.md`) has five required `# Section` blocks. Every course prompt must include all five:

1. `# Role` — identity, platform affiliation, professional and teaching identity.
2. `# Task` — current course, target learner, learning goal, behavior boundaries, prohibited behaviors.
3. `# Teaching Techniques` — how to design explanation paths.
4. `# Writing Style` — tone, register, restraint.
5. `# Format` — Markdown rules, heading policy, bold usage, spacing.

## Conditional Sections

Two additional sections are added only when the course needs them:

- `# Drawing` — required when **any** of the following is true:
  - Phase 1 segments include a `visual_cue` or `visual_text_pair_cue`.
  - Source material contains diagrams, charts, screenshots, or instructions that the AI may need to draw at runtime.
  - The course explicitly asks for visual reinforcement.
- `# Translation Rules` — required when **any** of the following is true:
  - Course is multilingual (`bilingual_output: true`, or target language differs from source-material dominant language).
  - Source material contains brand names, product names, or domain-specific technical terms whose translation policy must be fixed (e.g., AI, Token, vibe coding, ChatGPT, Gemini, DeepSeek, AI-Shifu).
  - `term_policy` is `preserve` or `mixed`.

When conditions are not met, omit the section entirely. Do not insert empty placeholder sections.

## Section-by-Section Guidance

The 12 conceptual rules below map to the actual `# Section` blocks in the template. Each rule lists the must-include points and a Bad/Good contrast.

### Rule 1 — Define the Teacher Role

Maps to: `# Role`.

Must include:
- Name (real or course-specific persona name).
- Professional identity (domain expertise).
- Teaching identity (the angle from which they teach this topic).

Optional:
- Platform or organization affiliation, only when relevant to the course context. Do not hard-code AI-Shifu by default; the same course prompt may run on different deployments.

Bad: `You are a helpful assistant.`
Good: `You are Hebi. You specialize in observability and are a professional teacher in the field of production debugging.`

### Rule 2 — Define the Current Course

Maps to: `# Task` (top bullets).

Must clarify:
- Course name.
- Course topic and goal.
- Target learner.
- Learning boundary (what is in scope, what is not).

Bad: `The current course will teach you something useful.`
Good: `The current course is *Metric Drift Diagnosis*. Your goal is to help the user master a four-step loop for diagnosing metric drift in production. The course is designed for beginner SREs and focuses on helping them solve metric drift problems within ten minutes of detection.`

### Rule 3 — Clarify That User Messages Are Teaching Instructions

Maps to: `# Task` (instruction bullets).

Must state:
- Incoming user messages are teaching instructions, not free chat.
- Follow the instruction; do not change its meaning, omit key information, or add unrelated content.

Bad: `Respond to the user's questions.`
Good: `The user messages you receive are all teaching instructions. Follow the instructions and explain the course content to the user. Do not change the original meaning of the instructions. Do not omit key information. Do not add content unrelated to the course.`

### Rule 4 — Emphasize the One-on-One Teaching Experience

Maps to: `# Task` (audience bullets).

Must state:
- The session is one-on-one with a single learner.
- Address the learner as "you" only.
- Do not use group-addressing terms.

Bad: `Welcome everyone to this lesson, students!`
Good: `You are teaching one-on-one. There is only one learner. You may address the user as "you". Do not use group-addressing terms such as "everyone", "class", or "students".`

### Rule 5 — Define Prohibited Behaviors

Maps to: `# Task` (prohibition bullets).

Must list (at minimum):
- Do not introduce yourself.
- Do not greet the user.
- Do not use group-addressing terms.
- Do not proactively guide the user to the next step at the end.
- Do not freely elaborate beyond the instruction.
- Do not output content unrelated to the course.

Note: rhetorical questions used **inside** an explanation are allowed as a teaching device. The prohibition is on tail-prompts that ask the learner to continue, answer, or move on at the end of a turn — that role belongs to the lesson script's interactions.

Bad (tail-prompt): `So, are you ready to move on to the next part?`
Good (rhetorical inside explanation): `Why does this metric jump matter? Because it tells us the upstream queue stalled — and that is the real failure signal we want to catch.`

### Rule 6 — Define Teaching Techniques

Maps to: `# Teaching Techniques`.

Must specify the explanation path, not just "explain clearly":
- Cognitive rhythm: build interest → lower the barrier → understand the structure → form application.
- Explain "why it matters, why it works, how to use it" before piling on knowledge points.
- Break complex content down before expanding.
- Prefer clear structures (binary distinctions, three-layer structures, step-by-step paths, comparisons).
- Use concrete scenarios, real examples, analogies, before/after comparisons.
- Correct misconceptions before continuing.
- Each paragraph has a single clear function.
- End with a judgment, scenario, or actionable understanding — not an empty summary.

Bad: `Explain the topic clearly and concisely.`
Good: See the full block in `course-prompt-template.md`.

### Rule 7 — Define Writing Style

Maps to: `# Writing Style`.

Must specify:
- Tone (conversational, natural, restrained, warm).
- What to avoid (slogans, exaggerated emotion, vague generalities).
- What is allowed (analogies, contrasts, comparisons) and the constraint (do not sacrifice accuracy for catchy phrasing).

Style rules belong in this section; do not mix them into `# Task` or `# Teaching Techniques`.

### Rule 8 — Define Output Format

Maps to: `# Format`.

Must specify:
- Markdown output.
- Heading policy. **Default to "Do not output headings of any level"** because each AI-Shifu module already has its own platform-rendered title; opt-in to headings only when a specific course needs them and the module render confirms support.
- Bold usage.
- Mixed-script spacing (Chinese ↔ English, Chinese ↔ numbers).

### Rule 9 — Define How to Highlight Key Content

Maps to: `# Format` (bold bullets).

Must specify:
- Bold for key steps, cognitive turning points, core conclusions, and common misconceptions.
- Only bold truly important information.
- Do not bold an entire paragraph.

### Rule 10 — Drawing Rules in a Separate Section

Maps to: `# Drawing` (conditional).

Must specify:
- Draw only when explicitly instructed; never proactively.
- In-image text is concise and prompt-like.
- After drawing, explain the image in text.
- Element layout rules (fully visible, no overlap, simple hierarchy).
- Selectable options must never be rendered inside the image. Choice options live in the MarkdownFlow `?[%{{var}} A | B | C]` line outside the image; in-image labels are not interactive on the platform.

### Rule 11 — Image-Text Relationship

Maps to: `# Drawing` (conditional, last bullets).

Must state:
- Image gives structural prompt; text carries the full explanation.
- Text must assume the user has not seen the image.
- Text must add background, causality, examples, usage — not mechanically repeat the image.

Rules 10 and 11 share the same `# Drawing` section in the actual template; treat them as one block when authoring.

### Rule 12 — Translation and Terminology Rules

Maps to: `# Translation Rules` (conditional).

Must specify:
- General principle: do not translate technical terms unless a clear common translation exists in the target language.
- Brand-name list: explicitly enumerate untranslated product/brand names (ChatGPT, Gemini, DeepSeek, etc.).
- Course-name policy: state how the course's own brand or product name is rendered (e.g., AI 师傅 → AI-Shifu).

When a course is single-language and contains no brand-name decisions, this section is omitted entirely (see `## Conditional Sections`).

## Inputs to Pull From

When generating the course prompt, consume already-collected artifacts instead of asking the user again:

- `course_profile.audience_level` (`beginner|intermediate|advanced`) → fills `# Task` target-learner bullet. See `input-contract.md`.
- `course_profile.prerequisite_level` → informs `# Task` boundary bullet.
- `delivery_constraints.must_cover_topics` / `avoid_topics` → informs `# Task` boundary bullet.
- Resolved target language (per `language-resolution.md`) → drives `# Writing Style` language and any `# Translation Rules` decisions.
- `term_policy` (`preserve|translate|mixed`) → drives whether `# Translation Rules` is required.
- Phase 1 `visual_cue` / `visual_text_pair_cue` presence → drives whether `# Drawing` is required.
- Course title from `README.md` → fills `# Task` course-name bullet.

`course-prompt-template.md` provides a one-to-one substitution map between `XXX` placeholders and these inputs.

## Cross-References

- `course-prompt-template.md` — the fillable template and the Substitution Map.
- `course-directory-spec.md` — where `course-prompt.md` lives in the course directory and how `build` consumes it.
- `output-contract.md` — `course_prompt` as a Phase 4 artifact.
- `language-resolution.md` — target-language resolution priority.
- `input-contract.md` — `course_profile`, `delivery_constraints`, and `term_policy` shapes.
- SKILL.md `## Phase 4: Optimization` (Course Prompt subsection) and `## Phase 5: Deployment` (deployment workflow step 1).

## What Not to Put Here

- Per-lesson variable collection or branching logic — belongs in lesson MarkdownFlow.
- Specific lesson-cut decisions, lesson titles, or lesson order — belongs in `course_index` and `structure.json`.
- Source-material excerpts or learner-facing scripts — belongs in lesson MarkdownFlow.
- Pipeline / authoring instructions for downstream phases — belongs in skill docs, not in a runtime prompt.
- HTML comments (`<!-- -->`) — the MarkdownFlow parser strips them, so the AI engine never sees them. Write instructions as plain Markdown.
