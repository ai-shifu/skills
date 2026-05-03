# End-to-End Deploy Example (Phase 1 → 2 → 3 → 4 → 5)

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

## Phase 1–4 (Author)

Produces optimized MarkdownFlow lesson scripts (see `pipeline-full.md` for detailed output).

## Phase 5 Output (Deployment)

### Step 1: Serialize Phase 4 outputs into a single `course.json`

Use placeholder `outline_item_bid` strings for items not yet on the server. Empty `deployment` object means "this is a brand-new course".

```json
{
  "version": "1.0",
  "course": {
    "title": "Metric Drift Diagnosis",
    "description": "Observe drift, classify causes, apply one fix, review impact.",
    "course_prompt": "你是一位实践型导师...",
    "language": "zh-CN"
  },
  "structure": [
    {
      "outline_item_bid": "new:c01",
      "children": [
        {"outline_item_bid": "new:l01", "children": []},
        {"outline_item_bid": "new:l02", "children": []},
        {"outline_item_bid": "new:l03", "children": []}
      ]
    }
  ],
  "items": {
    "new:c01": {"type": "chapter", "title": "Module 1", "markdownflow_prompt": "## Overview\n..."},
    "new:l01": {"type": "lesson", "title": "Observe", "markdownflow_prompt": "## L01 Objective\n..."},
    "new:l02": {"type": "lesson", "title": "Classify", "markdownflow_prompt": "## L02 Objective\n..."},
    "new:l03": {"type": "lesson", "title": "Verify", "markdownflow_prompt": "## L03 Objective\n..."}
  },
  "global_variables": [],
  "deployment": {}
}
```

### Step 2: Import (creates new course + auto-pulls real bids)

```bash
python3 {skillDir}/scripts/shifu-cli.py import --new --course-dir ./
# Output:
#   Creating new shifu 'Metric Drift Diagnosis' ...
#     shifu_bid = abc123-def456
#     Adding 1 chapter(s)
#     Adding 3 lesson(s)
#     Writing MarkdownFlow for 4 item(s)
#     Reordering outlines to match local structure
#   Auto-pulling to refresh ./course.json with real bids and revisions ...
#   Import complete: abc123-def456
```

After this command, `course.json` contains real UUIDs in place of every `new:*` placeholder, plus a populated `deployment.shifu_bid`.

### Step 3: Publish

```bash
python3 {skillDir}/scripts/shifu-cli.py publish abc123-def456
```

### Step 4: Verify

```bash
python3 {skillDir}/scripts/shifu-cli.py show abc123-def456
```

Platform URLs:

- Admin: `https://app.ai-shifu.cn/shifu/abc123-def456`
- Course preview: `https://app.ai-shifu.cn/c/abc123-def456?preview=true`
- Lesson preview: `https://app.ai-shifu.cn/c/abc123-def456?preview=true&lessonid=<outline_item_bid>`

## Acceptance Notes

- All five phases executed end-to-end.
- `course.json` is the single local artifact; no `lessons/`, no `system-prompt.md`.
- After `import`, the local file is in fully-synchronized state and ready for follow-up `push` cycles.
- Course is live and accessible via platform URL.
