# Data Collection and Privacy

Collect only what is needed to diagnose teaching quality for one course, and keep raw platform data outside the final report contract.

## Required References

For live AI-Shifu data, read these current files completely and follow their own required references:

1. `../../ai-shifu-course-creator/SKILL.md`
2. `../../ai-shifu-course-creator/references/authentication.md`
3. `../../ai-shifu-course-creator/references/analytics/workflow.md`

For supplied or synthetic input, no external reference is required; the privacy and normalization rules in this file still apply.

## Ownership Boundary

`ai-shifu-course-creator` owns all platform behavior:

- authentication and token storage;
- current course-title and course-ID resolution;
- outline and lesson-ID translation;
- analytics CLI commands, query syntax, recipes, table and field semantics, enum translation, error handling, and server-enforced privacy controls.

This skill owns only:

- selecting the teaching signals needed for a one-course report;
- normalizing translated, privacy-safe results into schema version 1.0;
- deriving calibrated teaching interpretations and recommendations;
- rendering the final JSON into HTML.

For live data, run the course creator skill's current `scripts/shifu-cli.py` commands exactly as its analytics route specifies. Never write raw HTTP, inspect `.env`, read a token, create auth headers, or reproduce analytics query recipes in this skill. If the dependency changes, follow the dependency rather than these descriptive signal names.

## Reporting Window

- Default to cumulative-to-date because most available course signals describe the current accumulated learning history.
- When the user supplies a date range, apply it only to fields whose current analytics source supports that filter. Label every metric independently as `period`, `cumulative`, or `current_snapshot`; never imply that a cumulative or snapshot value belongs only to the requested period.
- Record the effective window in `meta.period`, including the report timezone in `meta.timezone`. If it differs from the requested range, explain the difference in `data_quality.coverage_notes` and the affected metrics' `source_notes`.

## Minimum Teaching Dataset

Collect the smallest set that supports the report. Preserve counts and display labels, not row-level records.

| Signal | Safe report use | Important boundary |
| --- | --- | --- |
| Current course metadata and published outline | Course title, visible lesson order, required final lesson assessment | Resolve the current published learner-facing outline through the course creator's workflow; never show course or lesson IDs. |
| Distinct learners who entered an eligible lesson | Overview denominator and lesson reach comparison | Count distinct learners with progress in at least one published, visible teaching leaf lesson, using the course creator's canonical learner definition. |
| Per-lesson distinct learner progress states | Learning-path reach and recorded in-progress distribution | Deduplicate learners as the analytics guidance requires. A recorded in-progress state is not proof of a blockage. |
| Final required lesson completions | Approximate course completion | Calculate only when a reliable final required lesson exists; otherwise use `null`. |
| Lesson feedback | Rating averages, sample sizes, and reading/listening mix | Always pair an average with its response count. Do not treat mode feedback as total mode usage unless the source actually measures usage. |
| Archive state and recent activity | Current bookshelf status and latest observed activity | “Active” from archive state means non-archived, not recently active; use the source's exact definition. |
| Learner variables | Aggregate audience distributions | Include only when a trusted variable-name mapping exists. Never show raw variable IDs or ungrouped values. |
| Follow-up counts and themes | Question volume, lesson concentration, recent intent themes | Counts and raw-text sampling follow separate rules below. |

Learning duration, grades, retention, attendance, or other familiar education metrics may be unavailable in current sources. Represent an unavailable metric with `value: null`, `data_quality: "unavailable"`, and a plain reason. Never infer one metric from an unrelated field.

## Published Visible Lesson Gate

Apply this gate before querying or aggregating any lesson-scoped signal:

1. Confirm the course and outline source represent the current published, learner-facing version through the course creator's current workflow. A draft outline or a source with ambiguous publication state is not an acceptable fallback.
2. Define the eligible lesson set as teaching leaf lessons that belong to that published outline and are visible to learners. Exclude hidden lessons, draft-only or otherwise unpublished lessons, and chapter/container nodes.
3. Apply the same eligible set to lesson reach and progress, ratings, learning-mode feedback, follow-up counts and theme attribution, lesson health, recommendations, and the completion proxy. Do not render excluded lessons as zero-value or insufficient-data cards, and do not cite their historical records as evidence.
4. Define course entrants as distinct learners with progress in at least one eligible lesson. Learners observed only on excluded lessons must not inflate the denominator.
5. State in `data_quality.coverage_notes` that lesson analysis uses the current published-visible scope. Do not expose excluded lesson titles, IDs, records, or counts in the report.

If the published outline or lesson visibility cannot be resolved reliably, set affected lesson-scoped metrics to `null` / unavailable and explain the scope gap. Do not silently use the authoring draft or mix historical lessons into the current report.

## Completion Proxy Gate

Use a course completion percentage only when all of these are true:

1. the eligible published-visible lesson set identifies a final lesson that every learner is expected to complete;
2. branching, optional endings, or locked alternatives do not make that lesson an unreliable common endpoint;
3. the source can count distinct learners who completed that lesson;
4. the denominator is distinct learners who entered at least one eligible published-visible lesson.

Then compute `distinct learners completing the final required eligible lesson / distinct learners who entered at least one eligible lesson`, mark the metric as approximate, and put the numerator, denominator, published-visible scope, proxy rationale, and any deduplication caveat in the metric definition or source notes. Ignoring hidden lessons does not make the last visible lesson automatically required: visible branches, optional endings, or locked alternatives can still invalidate the proxy. If any condition fails, leave the value `null` and explain why. Do not replace it with a count of completed lesson rows or with an order conversion rate.

## Follow-Up Theme Sampling

Theme analysis uses raw text only as a transient input to aggregate reporting:

1. Before fetching text, tell the user that the report normally reads the latest audited follow-up questions for theme analysis, capped at 100, and that they can opt out. This is a default collection step, so continue unless the user opts out; honor an opt-out received before the query runs.
2. Use the course creator analytics route for the audited `generated_content` access. Fetch learner follow-up questions only, using the current canonical follow-up type and server-enforced active-row behavior. Do not fetch learner identity or answers when aggregate question themes are sufficient.
3. Select the newest `N` questions where `N <= 100`. Record the cap, actual sample size, and audited-access status in `engagement.follow_up_analysis`; keep the newest-first sampling rule and effective time span, if known, in an affected metric's `source_notes` or `data_quality.limitations`.
4. Classify questions into a small, useful theme set. Store only theme labels, counts, lesson display labels, and short generalized intent paraphrases. A paraphrase must describe the shared learning need without reproducing a distinctive sentence.
5. Do not persist raw text in the report directory, JSON, HTML, logs intended for delivery, or recommendation evidence. Do not retain source row IDs.

If the user opts out, set audited access to false, omit text-derived themes, and record an explicit “not collected by user choice” limitation; aggregate follow-up counts and per-lesson volume may still be used. If no recent questions exist, use a zero sample only when the query actually ran successfully. If access fails, use an unavailable quality state and preserve the error category without exposing credentials or query payloads.

Recent questions are a convenience sample, not the voice of all learners. Every text-derived interpretation must state the sample size and avoid population-wide claims.

## Audience Privacy

- Aggregate variable values before they enter the report pipeline. Never copy a raw free-text value list.
- Show an audience distribution only when a trusted course artifact or user-supplied mapping resolves the variable to a human-readable name. The analytics source alone may not provide that mapping.
- If the mapping is missing, do not show the raw variable ID or guess a label. Record a data-quality gap such as “Learner variable exists, but its meaning could not be resolved.”
- Suppress or combine tiny free-text categories when their wording could identify a learner. Prefer broad instructional groups over personally revealing labels.

## Operations Appendix Opt-In

Do not collect orders, revenue, payment channels, refunds, or AI-Shifu credit consumption for the default teaching report. Collect them only after the user explicitly asks for business or operating context. Use the course creator skill's current analytics route, keep the results in the optional `operations` appendix, and never use revenue or credit spend as evidence that teaching is effective.

## Supplied Data

Supplied or synthetic data does not bypass privacy rules:

- Treat fields named like identifiers, phones, emails, names, nicknames, raw answers, or raw follow-up content as source-only.
- Aggregate permitted content in memory, then discard those fields from the normalized object.
- Reject or sanitize any prebuilt report JSON that places source text or identity fields in final sections.
- Preserve synthetic missing values as missing. Do not turn `null` into `0` to make the report look complete.
- Record whether input was live, supplied, or synthetic in `data_quality.coverage_notes` so readers understand the evidence source without adding fields outside the schema.

## Final Privacy Gate

Inspect both `course-learning-report.json` and `course-learning-report.html` before delivery. They must contain none of the following:

- raw learner questions, answers, or widget input;
- phone numbers, email addresses, real names, nicknames, masked identity strings, or learner-level labels;
- raw course, lesson, learner, variable, progress, order, feedback, or generated-block IDs;
- internal query payloads, tokens, authentication headers, stack traces, or CLI responses;
- free-text audience values that could identify one person.

Metric source notes may name the translated source concept, table, command family, and sampling rule, but never source row values. If sanitization would change the meaning of a report claim, remove the claim and expose the resulting data limitation instead.
