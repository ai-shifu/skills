---
name: creator-course-analysis-report
description: Build creator-facing course analysis reports from course metrics, learner progress, chapter coverage, follow-up details, satisfaction signals, and revenue or order data. Use when Codex needs to diagnose how a course is performing for a creator, explain learner drop-off or pain points, compare chapters or cohorts, summarize follow-up patterns, or turn analytics exports into a structured report with conclusions and next-step recommendations.
---

# Creator Course Analysis Report

Turn creator-facing course, learner, and business data into a reusable analysis report that explains what is happening, why it is likely happening, and what the creator should do next.

## Core Output

Produce a report, not just a metric dump. The default deliverable should include:
- summary
- core metrics
- learning progress and coverage
- learner personas and common pain points
- follow-up analysis
- rating and satisfaction signals
- stage judgment
- recommended actions
- one-line conclusion
- metric notes / caveats

Use `assets/report-template.md` as the default skeleton.
Use `assets/export-manifest-template.md` when the task includes standalone detail outputs.

## Live Helper

This skill includes a local helper script for live AI-Shifu lookup:

- `scripts/creator-analysis-cli.py`

Use it when the current environment has:

- `SHIFU_BASE_URL`
- `SHIFU_TOKEN`

available either in this skill's `.env`, via CLI args, or via the fallback `.env` from `ai-shifu-course-creator`.

Typical commands:

```bash
python scripts/creator-analysis-cli.py login --region cn --phone <phone>
python scripts/creator-analysis-cli.py login --region cn --phone <phone> --sms-code <code>
python scripts/creator-analysis-cli.py entry
python scripts/creator-analysis-cli.py context <shifu_bid>
python scripts/creator-analysis-cli.py export <shifu_bid> learner_progress
python scripts/creator-analysis-cli.py export <shifu_bid> follow_up_detail
python scripts/creator-analysis-cli.py bundle <shifu_bid>
```

## Output Modes

Choose one of these modes based on the user request.

### `report-only`
- output only the creator-facing report

### `report-with-appendix`
- output the creator-facing report
- add a compact appendix with representative follow-up or learner examples

### `report-with-exports`
- output the creator-facing report
- optionally include a compact appendix
- also output standalone detail tables such as CSV or Markdown tables

When the user provides CSV files or explicitly asks for detailed data output, prefer `report-with-exports`.


## Access Preconditions

Before using live creator-facing course data, apply these checks:
- confirm the user is authenticated
- confirm owner check passes for the requested course in the current version
- confirm uploaded CSV, screenshots, or offline tables belong to the same course

If these checks do not pass, do not continue as if access is valid. See `references/access-and-scope-checks.md`.

## Input Expectations

Accept any mix of:
- dashboard screenshots
- analytics exports
- SQL results
- CSV or spreadsheet summaries
- chapter-level or learner-level tables
- follow-up detail samples
- rating samples or comments
- creator notes about course goal, audience, price, or current concern

If critical data is missing, continue with a partial report and mark the missing fields explicitly. For AI-Shifu-specific work, first check `references/ai-shifu-current-surface.md` so the report does not assume a dashboard capability that the current product does not yet expose.

## Direct Invocation Flow

When the user invokes this skill directly for AI-Shifu creator analysis, prefer the following conversation flow.

### Default guided flow

Unless the user already provided a valid course id and explicitly asked for a narrow export, prefer this default guided workflow:

1. Briefly explain what the skill does.
2. Check whether a valid login is already available.
3. If login is missing or expired, guide the user through phone + SMS-code login.
4. After login succeeds, list the current account's available courses.
5. Ask which course the user wants to analyze.
6. Run the owner check for that selected course.
7. Ask whether to export:
   - report only
   - report + learner data table + follow-up data table
8. Fetch only the data needed for the selected output mode.
9. Generate the report or report-plus-tables in the interaction language.

Keep the interaction concise, direct, and task-oriented. Match the steady product-assistant tone used by other AI-Shifu skills: explain the current step, state the next action, and avoid overly chatty or playful phrasing.

See `references/conversation-flow.md` for the recommended wording pattern and the exact decision points.

### If the user provides only a course id or `shifu_bid`

1. Treat this as a live-course lookup request.
2. Confirm or assume the current environment can provide authenticated user context.
3. Run the current version's owner-only access checks before analysis.
4. If live analysis context is available, default to `report-only`.
5. If live export endpoints are also available and the user asks for detail rows, switch to `report-with-exports`.

Do not ask the user to prepare CSV files first when live lookup is sufficient for the requested report.

### If the user provides a course id plus screenshots

1. Use live lookup for the core report.
2. Use screenshots only as supporting evidence.
3. If screenshots do not clearly match the requested course, stop and ask for clarification instead of blending evidence.

### If the user provides CSV files or exported tables

1. Prefer `report-with-exports`.
2. Preserve source fields whenever possible.
3. Add derived fields only as extra columns, not replacements.

### If live lookup is unavailable

1. Downgrade to offline-only analysis.
2. State clearly that login / owner verification could not be confirmed in this run.
3. Continue only with the evidence the user actually provided.

### If login is missing or the token is expired

Prefer a human-style recovery flow instead of immediately asking the user for a raw token.

Recommended interaction order:

1. say that live lookup needs a fresh login
2. offer to help the user log in now
3. ask for the phone number
4. send the SMS code
5. ask the user to provide the received code
6. verify the code, save the token silently, and continue the live lookup

For China-mainland environments, prefer using:

```bash
python scripts/creator-analysis-cli.py login --region cn --phone <phone>
python scripts/creator-analysis-cli.py login --region cn --phone <phone> --sms-code <code>
```

This should feel like a guided login flow, not a configuration task. Only fall back to manual token input when the environment does not support SMS login, such as the global region.

### First-turn behavior

If the user says something like:

- `Analyze course shifu_bid=...`
- `Use creator-course-analysis-report for this course`
- `Give me a creator report for course ...`

then the skill should:

1. identify the course id
2. choose live-course analysis when possible
3. decide whether the default output should be `report-only` or `report-with-exports`
4. proceed with the smallest number of clarification questions needed to keep the run accurate

If live lookup fails only because auth is stale, the next question should be about login recovery, not about CSV upload.

### Course selection after login

After a successful live login, do not immediately ask the user to type a course id from memory unless there is only one possible course. Prefer this order:

1. call the entry/list surface
2. show the courses owned by the current account
3. let the user choose by course name or `shifu_bid`
4. if there are too many courses, show the top slice and still accept a direct `shifu_bid`

When listing courses, keep the list lightweight. Prefer:

- course name
- `shifu_bid`
- learner count when available
- order count when available

If the entry surface returns no course, say so clearly instead of pretending the account has analysis-ready content.

### Output mode selection

For live guided use, prefer exactly two user-facing choices:

1. report only
2. report + learner data table + follow-up data table

Do not force the user to understand internal mode labels such as `report-only` or `report-with-exports`. Translate those internal modes into plain product language in the interaction.

Map them as follows:

- `report only` -> `report-only`
- `report + learner data table + follow-up data table` -> `report-with-exports`

If the user asks for only one detail table, honor that narrower request instead of forcing the bundled export.

## Analysis Order

Follow this order unless the user asks for a narrower task.

1. Identify the analysis object.
- single course, multiple courses, time window, cohort, or chapter slice
- creator goal: revenue, completion, engagement, satisfaction, or diagnosis

2. Normalize the evidence boundary.
- separate observed facts from interpretation
- do not infer unavailable metrics
- if screenshots are partial, mark the report as partial
- when working on AI-Shifu data, distinguish current live dashboard metrics from extra offline evidence such as follow-up detail exports or learner tables

3. Read the course at three layers.
- business layer: exposure, orders, paid learners, revenue, coupon or campaign effects
- learner layer: started learners, active learners, completion, depth, return behavior
- content layer: chapter reach, chapter completion, follow-up hotspots, low-score hotspots

4. Explain the learning path.
- where learners enter
- where they continue
- where they stall
- where they drop
- which chapters create repeated confusion or repeated value

5. Interpret follow-ups carefully.
- high follow-up volume is not automatically bad
- distinguish “healthy engagement” from “blocked understanding”
- use follow-up detail samples to identify repeated concepts, ambiguous phrasing, missing examples, or pacing issues

6. Read learner variables or qualitative fields when available.
- cluster repeated inputs into themes instead of listing raw text only
- use those themes to explain learner persona, pressure, and pain points
- keep qualitative evidence supportive, not magically definitive

7. Write a stage judgment.
- early validation
- growth with structural bottlenecks
- mature but locally weak
- strong sales but weak learning retention
- strong learning signal but weak conversion

8. End with action recommendations.
- prioritize actions by impact and effort
- prefer content, structure, onboarding, pricing, or promotion recommendations that are directly supported by the evidence

## Required Reporting Discipline

Always separate these four layers in the write-up:
- `Observation`: what the data directly shows
- `Interpretation`: the most likely explanation
- `Confidence`: high / medium / low based on evidence completeness
- `Suggested action`: what the creator should do next

Do not blur assumptions into facts.

## Interpretation Rules

- Compare chapters before judging the whole course.
- Use learner progress plus follow-up detail together; do not rely on only one.
- Treat rating signals as supporting evidence, not the whole conclusion.
- If business data and learning data conflict, call out the conflict explicitly.
- Distinguish count-based metrics from user-based metrics.
- Distinguish total follow-ups from follow-up learners and follow-up rate.
- Prefer ratios and distributions over raw totals when course sizes differ.
- If the course is newly launched or sample size is low, state that conclusions are directional.
- In AI-Shifu, treat `avg_learning_duration_seconds` as an approximate learning span unless the user provides a more precise duration source.

## Report Modes

### Full report

Use the full template when enough data exists across metrics, learner behavior, and chapter or follow-up signals.

### Diagnosis memo

Use a shorter memo when the user asks a narrow question such as:
- why completion is low
- why a chapter has many follow-ups
- whether the course should optimize content or conversion first

### Comparison note

Use a comparison structure when the user asks to compare:
- two courses
- two time periods
- two learner cohorts
- before and after a course change or promotion

## Reusable References

Read only the references needed for the task.

- `references/ai-shifu-current-surface.md`: what the current AI-Shifu creator dashboard actually exposes
- `references/ai-shifu-metric-notes.md`: current project-specific metric meanings and confidence levels
- `references/report-style-patterns.md`: how to write the report in the creator-report style shown by the reference analysis
- `references/variable-theme-analysis.md`: how to turn learner variables or structured text fields into persona and pain-point diagnosis
- `references/conclusion-and-notes.md`: how to write reusable one-line conclusions and explicit metric notes
- `references/detail-export-modes.md`: when to output only the report, add an appendix, or emit standalone exports
- `references/detail-output-specs.md`: standard shapes for follow-up and learner-progress detail outputs
- `references/access-and-scope-checks.md`: login check, owner check, and evidence match rules for the current version
- `references/report-structure.md`: section-by-section writing guide
- `references/metric-dictionary.md`: creator-facing metric definitions and cautions
- `references/learner-analysis.md`: how to read progress, coverage, depth, and rhythm
- `references/follow-up-analysis.md`: how to read follow-up counts, details, and hotspots
- `references/stage-judgement.md`: how to classify the course stage and choose actions

## Output Language

Write the final report in the user's requested language. If the user does not specify a language, match the language of the request.

### Default language rule

- if the conversation is in Chinese, output the report in Chinese
- if the conversation is in English, output the report in English
- do not ask an extra language question unless the user explicitly asks for bilingual output or the target audience is unclear

### Bilingual output rule

If the user explicitly asks for bilingual delivery, output two separate files instead of mixing languages in one file.

Recommended pattern:

- one Chinese report file
- one English report file

Prefer:

- `creator-course-report.zh-CN.md`
- `creator-course-report.en-US.md`

If appendix files are also needed, keep them separate too:

- `creator-course-report-appendix.zh-CN.md`
- `creator-course-report-appendix.en-US.md`

If an export manifest is needed, keep that separate as well:

- `export-manifest.zh-CN.md`
- `export-manifest.en-US.md`

### Export language rule

- report body language follows the interaction language unless the user explicitly requests another language
- detail-table headers and surrounding explanatory text should follow the interaction language as well
- keep raw detail cell values as close to source values as possible
- do not translate source text fields such as learner nicknames, follow-up content, or answer content unless the user explicitly asks for translated raw content
- when bilingual delivery is requested, prefer translating the report files while keeping raw exports source-stable unless the user explicitly asks for translated export headers

## Detail Output Discipline

- Keep the main report readable; do not paste large raw tables into the main body.
- Preserve original CSV fields whenever possible in standalone exports.
- Add derived columns as extra fields rather than replacing source fields.
- If the user asks for “this kind of detail data”, output both the report and the detail file spec when appropriate.
- When selecting appendix examples, prefer representative rows that support the report conclusion.

## Failure and Gap Handling

When data is incomplete:
- say what is missing
- downgrade confidence
- keep the report useful with directional findings
- recommend the next data pull needed to firm up the conclusion

When access checks fail:
- stop live-course analysis
- state whether the failure is login, owner, or evidence-match related
- do not behave as if the current user is authorized for that course

Do not fabricate chapter-level, learner-level, or revenue-level findings that the provided data cannot support.
