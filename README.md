# AI-Shifu Skills

[中文 README](./README.zh-CN.md)

Reusable AI-Shifu skills for course production, from topic selection to deployment.

## Included Skills

- `ai-shifu-course-creator`: convert raw course material into optimized MarkdownFlow teaching scripts and deploy them as live AI-Shifu courses through a five-phase pipeline (segmentation, orchestration, generation, optimization, deployment).
- `course-direction-advisor`: turn source materials into evidence-bound, market-fit course-topic decisions with competitor analysis, pricing guidance, and GO/HOLD/REWORK/NO-GO recommendations.

The course-creator skill includes runnable examples under `skills/ai-shifu-course-creator/examples/`.

## Repository Layout

```text
skills/
  ai-shifu-course-creator/
  course-direction-advisor/
```

## Usage

The skill keeps `SKILL.md` as the behavior source of truth.
Core skill metadata lives in `skills/ai-shifu-course-creator/skill.yaml`.

## Course Authoring & Deployment Paths

Choose one path based on control needs:

### Path A: End-to-End (Recommended)

Use when you want the fastest route from raw material to a live deployed course.

1. Prepare source material (transcript or course documents).
2. Run Phase 1–4 to produce optimized MarkdownFlow lesson scripts.
3. Run Phase 5 to build, import, and publish to the AI-Shifu platform.

Expected artifacts:

- Structured segmentation
- Lesson-by-lesson MarkdownFlow scripts
- Course index and global variable table
- Optimized lesson prompts and risk report
- Live course on the AI-Shifu platform

### Path B: Author Only

Use when you need optimized MarkdownFlow scripts without deploying. Sub-paths:

- **Segment only**: Phase 1 for semantic segments and manual review.
- **Generate only**: Phase 3 on pre-existing segments.
- **Optimize only**: Phase 4 to audit and improve existing scripts.

### Path C: Deploy Only

Use when you have pre-existing MarkdownFlow files ready to deploy:

1. Organize MarkdownFlow files in a course directory.
2. Run `build --course-dir ./course-a/` to generate the import file.
3. Run `import --new --json-file ./course-a/shifu-import.json` to create the course.
4. Run `publish <shifu_bid>` to make it live.

### Path D: Manage Existing

Use management commands (list, show, update, rename, reorder, delete, publish, archive) on courses already on the platform.

## Validate Metadata

```bash
python3 scripts/validate_skill_quality.py
```

## Language Policy

Skills are language-flexible for course generation. From a user perspective:

- If you explicitly request an output language, that language is used.
- If you provide `target_language`, it is used when no stronger explicit instruction exists.
- If neither is provided, the system uses session preference and prompt language signals.
- If language is still ambiguous, it falls back to `en-US`.
- If you need bilingual output, set `bilingual_output: true`.

Recommended controls for predictable language output:

- `target_language` (for example `zh-CN`, `fr-FR`, `ja-JP`)
- `bilingual_output` (`true|false`)
- `term_policy` (`preserve|translate|mixed`)
- `quote_policy` (`translate_only|original_plus_translation`)

## AI-Shifu

This suite is part of AI-Shifu's course authoring workflow: <https://ai-shifu.com>
