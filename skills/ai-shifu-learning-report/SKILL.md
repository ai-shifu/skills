---
name: ai-shifu-learning-report
description: Create a polished, printable learning report for one AI-Shifu course from live course analytics or a supplied report dataset. Use this skill whenever a teacher or teaching manager asks for an AI-Shifu learning report, course review, teaching diagnosis, lesson health analysis, learner engagement or audience insights, follow-up question themes, or a management-ready course analytics dashboard—even when they only say “复盘这门课” or “做个教学报告.” Produce privacy-safe `course-learning-report.json` and `course-learning-report.html`; do not use this skill for multi-course comparison or course-authoring changes.
---

# AI-Shifu Learning Report

Turn observed data from one course into a decision-ready report for teaching managers and teachers. Keep collection, interpretation, and presentation separate so every conclusion can be traced to a defined metric without exposing learner data.

## Required References

Read these files completely, in order, for every report:

1. `references/data-collection-and-privacy.md`
2. `references/analysis-guidelines.md`
3. `references/report-structure.md`

Resolve every `## Required References` declaration in those files transitively before acting.

## Scope Router

| Request | Route |
| --- | --- |
| Build a report from a live AI-Shifu course | Use the current `ai-shifu-course-creator` skill and its analytics CLI to collect the permitted data, then normalize, analyze, and render it here. |
| Build a report from supplied or synthetic data | Do not query the platform. Validate the input against this skill's data and privacy rules, then normalize, analyze, and render it. |
| Re-render an existing `schema_version: "1.0"` report JSON | Validate and privacy-scan the JSON, then render it without inventing missing analysis. |
| Compare multiple courses | Explain that v1 supports one-course diagnosis and ask which course should be reported first. Do not silently merge courses. |
| Edit course content after reading the report | Finish the report first, then hand the requested authoring work to `ai-shifu-course-creator` as a separate task. |

## Workflow

1. **Resolve the request.** Identify exactly one course and any requested time range. Default to `zh-CN` and cumulative-to-date data. Use `en-US` only when the user explicitly asks for English; schema keys, enum values, commands, and file names stay unchanged.
2. **Collect or validate.** Follow `data-collection-and-privacy.md`. Live collection delegates authentication, course resolution, outline resolution, analytics syntax, and platform privacy controls to the current `ai-shifu-course-creator`; never recreate those mechanisms here. Resolve the current published outline and remove hidden, unpublished, and container nodes before normalizing any lesson-scoped signal.
3. **Normalize.** Create a `schema_version: "1.0"` report object. Keep unavailable data as `null` with an explicit quality explanation instead of guessing or converting it to zero.
4. **Analyze.** Follow `analysis-guidelines.md`. Separate observations from interpretations, preserve conflicting signals, and write 3–5 evidence-linked recommendations.
5. **Write the data artifact.** Save the privacy-safe object as `course-learning-report.json`. This file is the single source for the rendered report.
6. **Validate and render.** Follow `report-structure.md`, validate the JSON, then run the bundled renderer to create `course-learning-report.html` from that exact JSON.
7. **Run the release gate.** Confirm that both files describe one course, use the requested language, contain no raw learner text or identifiers, label metric definitions and time scopes, show missing-data states honestly, and contain no external runtime assets.
8. **Deliver both files.** Summarize the reporting window, major data limitations, and whether follow-up text was sampled. Do not paste private source rows into the handoff.

## Non-Negotiable Boundaries

- Use the course creator skill's current CLI for live data. Never read a token, inspect its environment file, compose authentication headers, or call platform HTTP endpoints directly.
- Do not copy or freeze the analytics query language in this skill. The course creator skill owns query syntax, table semantics, codes, and recipes.
- Never place raw follow-up text, answers, phone numbers, emails, names, nicknames, learner labels, or any raw `*_bid` value in either final artifact.
- Build every lesson-scoped analysis from the current published outline. Include only published, visible teaching leaf lessons, and use that same eligible set for the course entrant denominator, completion proxy, learning path, lesson health, follow-up attribution, and recommendations. If publication or visibility cannot be resolved reliably, mark the affected metrics unavailable instead of falling back to a draft outline.
- Calculate completion only when the course has a reliable final required lesson. In reader-facing Chinese content, name the metric exactly `课程完成率`; do not append `代理` or `近似` to its label or refer to it as a proxy in conclusions and recommendations. Put the exact numerator, denominator, eligible-lesson scope, and calculation boundary in the metric definition and source notes. Treat `进行中` / `In progress` as a recorded state, never proof that learners are stuck.
- Keep orders, revenue, payment channels, and AI-Shifu credit consumption out of the teaching report unless the user explicitly requests an operations appendix.
- The JSON is the factual contract and the HTML is its presentation. Do not add claims to HTML that are absent from JSON.
- Present the HTML in the Swiss International Style defined by `report-structure.md`; preserve its modular grid, typographic hierarchy, flat square geometry, and restrained color system when applying brand overrides.

## Completion Checklist

- `course-learning-report.json` passes the bundled validator for schema version 1.0.
- `course-learning-report.html` is self-contained, responsive, accessible, printable, generated from the validated JSON, and rendered with the required Swiss International Style system.
- Every metric includes `key`, `label`, `value`, `unit`, `definition`, `time_scope`, `data_quality`, `is_approximate`, and `source_notes`.
- The report contains 3–5 recommendations with cited evidence, confidence, an action, and a validation method.
- Follow-up analysis discloses its recent-sample size and collection status; an opt-out produces an explicit not-collected state, not an empty-data inference.
- Privacy scan finds no raw source text, identity data, internal IDs, or sensitive learner profile values.
