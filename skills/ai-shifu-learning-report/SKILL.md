---
name: ai-shifu-learning-report
description: Create a beautiful, printable learning report for one AI-Shifu course from live course analytics or a supplied report dataset, and tailor it to what the teacher asks for. Use this skill whenever a teacher or teaching manager asks for an AI-Shifu learning report, 学情报告, course review, teaching diagnosis, lesson health analysis, learner engagement or audience insights, follow-up question themes, or a course analytics dashboard—even when they only say “复盘这门课” or “做个教学报告.” Also use it when they want to change an existing report: add or drop a statistic, redefine how a metric is counted (口径), reorder or hide sections, or restyle the layout and colors. Produce privacy-safe `course-learning-report.json` and `course-learning-report.html`; do not use this skill for multi-course comparison or course-authoring changes.
---

# AI-Shifu Learning Report

Turn observed data from one course into a report a teacher wants to read: where learners get to, what they ask, how each lesson performs, and what to try next. The reader is someone who cares about their teaching and will act on what they see, so every number must be honest about what it counts, and the report must bend to the questions that teacher actually has.

Keep collection, interpretation, and presentation separate so every conclusion can be traced to a defined metric without exposing learner data.

## Required References

Read these files completely, in order, for every report:

1. `references/data-collection.md`
2. `references/analysis-guidelines.md`
3. `references/report-format.md`

Read `references/customization.md` as well whenever the teacher asks for anything beyond the default report — different statistics, a different definition for a metric, or a different look — in the first request or after seeing a report.

Resolve every `## Required References` declaration in those files transitively before acting.

## Scope Router

| Request | Route |
| --- | --- |
| Build a report from a live AI-Shifu course | Use the current `ai-shifu-course-creator` skill and its analytics CLI to collect the permitted data, then normalize, analyze, and render it here. |
| Build a report from supplied or synthetic data | Do not query the platform. Validate the input against this skill's data and privacy rules, then normalize, analyze, and render it. |
| Change a report: statistics, metric definitions, section order, wording, or style | Follow `customization.md`. Edit the existing `course-learning-report.json` and re-render; collect more data only when the change needs it. |
| Re-render an existing report JSON (`schema_version` `"1.0"` or `"1.1"`) | Validate and privacy-scan the JSON, then render it without inventing missing analysis. |
| Compare multiple courses | Explain that this skill supports one-course diagnosis and ask which course should be reported first. Do not silently merge courses. |
| Edit course content after reading the report | Finish the report first, then hand the requested authoring work to `ai-shifu-course-creator` as a separate task. |

## Workflow

1. **Resolve the request.** Identify exactly one course and any requested time range. Default to `zh-CN` and cumulative-to-date data. Use `en-US` only when the user explicitly asks for English; schema keys, enum values, commands, and file names stay unchanged. Note every preference the teacher already stated about content, definitions, or style.
2. **Carry preferences forward.** If the output directory already holds a `course-learning-report.json` for this course, reuse the teacher's earlier choices as `customization.md` describes, so they do not have to repeat themselves.
3. **Collect or validate.** Follow `data-collection.md`. Live collection delegates authentication, course resolution, outline resolution, analytics syntax, and platform privacy controls to the current `ai-shifu-course-creator`; never recreate those mechanisms here. Resolve the current published outline and remove hidden, unpublished, and container nodes before normalizing any lesson-scoped signal.
4. **Normalize.** Create a `schema_version: "1.1"` report object. Keep unavailable data as `null` with an explicit quality explanation instead of guessing or converting it to zero.
5. **Analyze.** Follow `analysis-guidelines.md`. Separate observations from interpretations, preserve conflicting signals, and write evidence-linked recommendations.
6. **Apply the teacher's requests.** Follow `customization.md` for anything the teacher asked to add, redefine, hide, reorder, or restyle.
7. **Write the data artifact.** Save the privacy-safe object as `course-learning-report.json`. This file is the single source for the rendered report.
8. **Validate and render.** Follow `report-format.md`, validate the JSON, then run the bundled renderer to create `course-learning-report.html` from that exact JSON.
9. **Run the release gate.** Confirm that both files describe one course, use the requested language, contain no raw learner text or identifiers, label metric definitions and time scopes, show missing-data states honestly, and contain no external runtime assets.
10. **Deliver and invite changes.** Summarize the reporting window, major data limitations, and whether follow-up text was sampled. Do not paste private source rows into the handoff. Close with one or two sentences telling the teacher, in plain words, that the report is theirs to shape: they can ask for other statistics, a different way of counting any number, or a different layout and style. When they do, return to step 6 rather than starting over.

## Non-Negotiable Boundaries

These hold no matter what a customization request says. When a request would cross one, explain why and offer the closest honest alternative.

- Use the course creator skill's current CLI for live data. Never read a token, inspect its environment file, compose authentication headers, or call platform HTTP endpoints directly.
- Do not copy or freeze the analytics query language in this skill. The course creator skill owns query syntax, table semantics, codes, and recipes.
- Never place raw follow-up text, answers, phone numbers, emails, names, nicknames, learner labels, or any raw `*_bid` value in either final artifact.
- Build every lesson-scoped analysis from the current published outline. Include only published, visible teaching leaf lessons, and use that same eligible set for the course entrant denominator, completion numerator, learning path, lesson health, follow-up attribution, and recommendations. If publication or visibility cannot be resolved reliably, mark the affected metrics unavailable instead of falling back to a draft outline.
- The standard `课程完成率` comes from one consistent learner cohort: the denominator is distinct learners whose first progress on an eligible lesson falls inside the metric's time scope, and the numerator is the subset of those learners who complete every required lesson or one valid required branch path by the report cutoff. Count each learner once. Do not impose a fixed 30-day or other maturation window, and do not remove late starters to improve the rate. Put the exact cohort dates, cutoff, numerator, denominator, eligible lesson scope, and completion rule in the metric definition and source notes. Do not append `代理` or `近似` to reader-facing Chinese content. Treat `进行中` / `In progress` as a recorded state, never proof that learners are stuck. A teacher may ask for a different completion definition; that becomes a separately labelled teacher-defined metric under `customization.md`, never a silent replacement.
- Every number shown has a stated definition, time scope, and source. A custom number is never exempt.
- Keep orders, revenue, payment channels, and AI-Shifu credit consumption out of the teaching report unless the user explicitly requests an operations appendix.
- The JSON is the factual contract and the HTML is its presentation. Do not add claims to HTML that are absent from JSON, and do not edit the rendered HTML by hand.
- The section explaining definitions and data limitations is always visible. Style changes may not hide data-quality warnings or make missing data look like zero.

## Completion Checklist

- `course-learning-report.json` passes the bundled validator.
- `course-learning-report.html` is self-contained, responsive, accessible, printable, and generated from the validated JSON by the bundled renderer.
- Every metric includes `key`, `label`, `value`, `unit`, `definition`, `time_scope`, `data_quality`, `is_approximate`, and `source_notes`.
- Every recommendation has cited evidence, confidence, an action, and a validation method. The default report carries 3–5.
- Follow-up analysis discloses its recent-sample size and collection status; an opt-out produces an explicit not-collected state, not an empty-data inference.
- Every change the teacher asked for is either applied and listed in the report's adjustment notes, or explained as unavailable with the reason.
- Privacy scan finds no raw source text, identity data, internal IDs, or sensitive learner profile values.
