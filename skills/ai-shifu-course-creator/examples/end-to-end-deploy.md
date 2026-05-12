# End-to-End Deploy Example (Segmentation → Orchestration → Generation → Optimization → Deployment)

> Note: Outputs in this example are illustrated in English for clarity. Actual output language follows `references/data-contracts.md#language-resolution` (e.g., Chinese invocation → Chinese output).

## Input Payload (example)

```json
{
  "course_material": "Module transcript: observe metric drift, classify causes, apply one fix, review impact.",
  "generation_constraints": {
    "persona": "practical coach",
    "lesson_granularity": "short"
  },
  "course_profile": {
    "audience_level": "beginner",
    "lesson_duration_minutes": 10,
    "lesson_count_target": 3,
    "assessment_mode": "project"
  },
  "platform_region": "cn",
  "target_language": "zh-CN"
}
```

## Segmentation through Optimization (Author)

Produces optimized Teaching Prompts (see `pipeline-full.md` for detailed output).

## Deployment Output

### Step 1: Build Course Directory

```
my-course/
  README.md
  course-prompt.md
  structure.json
  lessons/
    lesson-01.md
    lesson-02.md
    lesson-03.md
```

### Step 2: Build Import File

```bash
python3 {skillDir}/scripts/shifu-cli.py build --course-dir ./my-course/ --title "Metric Drift Diagnosis"
```

Output: `my-course/shifu-import.json`

### Step 3: Import and Publish

```bash
python3 {skillDir}/scripts/shifu-cli.py import --new --json-file ./my-course/shifu-import.json
# Returns: shifu_bid = abc123-def456

python3 {skillDir}/scripts/shifu-cli.py publish abc123-def456
```

### Step 4: Verify

```bash
python3 {skillDir}/scripts/shifu-cli.py show abc123-def456
```

Platform URLs (these are copied verbatim from the `Verification URLs:` block printed by `publish` / `import` / `show` — do not reconstruct them):

- Admin: `https://app.ai-shifu.cn/shifu/abc123-def456`
- Course preview: `https://app.ai-shifu.cn/c/abc123-def456?preview=true`
- Lesson preview: `https://app.ai-shifu.cn/c/abc123-def456?preview=true&lessonid=<outline_bid>`

## Acceptance Notes

- All pipeline stages executed end-to-end.
- Teaching Prompts (MarkdownFlow) written to course directory, built, imported, and published.
- Course is live and accessible via platform URL.
