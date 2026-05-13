# Course Author Report Template

Use the section matching the executed phase. Omit sections for phases not run.

## Formatting Rules

These rules apply to every report produced from this template, and to any other user-visible chat output that includes URLs.

- **Links must be Markdown, never bare URLs.** Whenever you show a URL to the user (admin console, course preview, lesson preview, contact page, etc.), wrap it in Markdown link syntax `[descriptive text](URL)`. Never emit a bare `https://...` on its own line.
- **Why:** the AI-Shifu chat client only treats Markdown links as clickable / copy-on-tap. A bare URL renders as plain text — the user cannot click it and cannot copy it cleanly on mobile.
- **Where this applies:** phase reports below, the opening introduction, the contact line, and any ad-hoc message that surfaces a URL to the user.
- **Where this does NOT apply:** URLs inside Teaching Prompts (those follow MarkdownFlow image / link rules) and URLs shown inside fenced code blocks for reference.

## Segmentation Report

- Source files:
- Processing mode: `standard|fallback`
- Total segments:
- Lesson candidates:
- Immutable blocks preserved:

Validation:
- Source span traceability: `pass|fail`
- Immutable block preservation: `pass|fail`
- One-core-question lesson check: `pass|fail`

Issues:
- Blocking issues:
- Non-blocking suggestions:

Next actions:
- Targeted reruns:
- Downstream handoff notes:

## Orchestration Report

- Input set:
- Execution mode: `standard|fallback`
- Constraints:
- Lesson files generated:
- Course index status:
- Variable table status:

Gate results:
- Preservation gate: `pass|fail`
- One-core-question gate: `pass|fail`
- Interaction safety gate: `pass|fail`
- Variable safety gate: `pass|fail`

Issues:
- Blocking issues:
- Suggestions:

Rerun plan:
- Lessons to rerun:
- Dependency-linked lessons:

## Generation Report

- Lesson id:
- Execution mode: `standard|fallback`
- Constraints:
- Script generated: `yes|no`
- Interaction count:
- Variables used:

Validation:
- Syntax validity: `pass|fail`
- Variable safety: `pass|fail`
- Visual-text coordination: `pass|fail`
- Teaching loop completeness: `pass|fail`

Issues:
- Blocking issues:
- Suggestions:

Follow-up:
- Rerun needed: `yes|no`
- Upstream dependency notes:

## Optimization Report

- Target script(s):
- Source material set:
- Execution mode: `standard|fallback`
- Overall risk: `low|medium|high`

Issue breakdown:
- Coverage gaps:
- Meaning shifts:
- Interaction issues:
- Visual issues:
- Variable/syntax issues:

Changes applied:
- File references:
- Minimal-edit rationale:

Validation:
- Syntax check: `pass|fail`
- Variable safety check: `pass|fail`
- Interaction branching check: `pass|fail`
- Density preservation check: `pass|fail`

## Deployment Report

- Course directory:
- Build result: `success|fail`
- Import result: `success|fail`
- Shifu BID:
- Lesson count imported:
- Publish result: `success|fail`

Validation:
- Import without errors: `pass|fail`
- Course accessible via URL: `pass|fail`
- Lesson count matches source: `pass|fail`
- Preview mode reachable: `pass|fail`

Verification URLs:

The deployment script (`shifu-cli.py publish` / `import` / `create` / `show`) prints a `Verification URLs:` block that lists the admin console, the course preview, and one preview URL per lesson. Copy those URLs **verbatim** from the script output and wrap each one in a Markdown link — never reconstruct them from a template, and never hand-edit query parameters. Use these descriptive labels:
- Admin console → `[<course name> - 后台管理](<URL from script>)`
- Course preview → `[<course name> - 课程预览](<URL from script>)`
- Lesson preview → `[<lesson name>](<URL from script>)`
