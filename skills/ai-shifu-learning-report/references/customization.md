# Tailoring a Report to the Teacher

Apply a teacher's requests about what the report measures, how a number is counted, and how the report looks. The default report is a starting point; a teacher who reads it closely will have their own questions, and the report should change to answer them.

## Required References

- `report-format.md`
- `report-data.schema.json`
- `analysis-guidelines.md`
- `data-collection.md` — only when a request needs data the current report does not hold.

## How to Work a Request

1. **Restate the request as a concrete change.** “Which lesson gets the most questions?” becomes “add a per-lesson follow-up count, shown as a bar chart.” When a request has two reasonable readings that would give different numbers, ask one short question; otherwise choose the natural reading and say which one you chose.
2. **Classify it** as content (which statistics), definition (how a number is counted), or presentation (order, wording, style). One sentence from a teacher often contains more than one kind.
3. **Change the JSON, not the HTML.** Every request below is expressed in `course-learning-report.json`. Re-run validation and the renderer after each round of changes. Never patch the rendered HTML: the next render would lose the edit and the two artifacts would disagree.
4. **Do the smallest change that satisfies it.** Leave everything the teacher did not mention as it was. A request to recolor the report must not reword conclusions.
5. **Record it.** Add one plain sentence per change to `data_quality.teacher_adjustments`, naming any statistic that was removed. The report shows these notes, so a colleague reading it later knows it differs from the default, and the next report can repeat the same choices.
6. **Report back briefly:** what changed, anything that could not be done and why, and — when a definition changed — the old and new values side by side.

Apply a batch of requests in one pass and render once.

## Content: Which Statistics Appear

| The teacher wants | Change |
| --- | --- |
| A new headline number | Add a metric to `overview.kpis`. |
| A new per-lesson number | Add a metric with the same `label` to each lesson's `metrics`. Lessons are compared in one table whose columns are those shared labels. |
| Fewer numbers | Remove the metric from where it is displayed. Remove its `metric_definitions` entry only when nothing else cites it. |
| A specific set of columns in the lesson table | List the metric labels in `presentation.lesson_table_columns`, in display order. |
| A new analysis of their own | Add a `custom_sections` entry (see below). |
| A whole section gone | Leave the data in place and omit the section id from `presentation.sections`. |
| A before/after comparison | Add `comparison: {label, value}` to the metric, using a value computed with the same definition for the earlier period or report. It is shown wherever that metric appears. |
| Fewer or more recommendations | Keep 1–5, each still carrying full evidence. |

Every added metric follows the Metric Contract in `analysis-guidelines.md` and needs a `metric_definitions` entry. Give it `"origin": "teacher"` in that entry so the report marks it as the teacher's own.

When the current report data cannot produce the number, collect it under `data-collection.md`. When the platform does not record it at all — learning duration is a common example — say so plainly and offer the nearest available signal. Do not estimate a number to fill the request; if the teacher still wants the slot visible, add the metric with `value: null` and an `unavailable` quality state.

### Custom Sections

A custom section holds an analysis the default report does not have. It has an `id` (lowercase letters, digits, hyphens), a `title` best phrased as the teacher's question, an optional `description`, and an ordered list of `blocks`:

| Block `type` | Fields | Use for |
| --- | --- | --- |
| `metrics` | `metrics` | A few headline numbers shown as tiles. |
| `bars` | `metrics`, optional `title` | Comparing several non-negative values that share one unit, such as a count per lesson. Show signed changes in a `table`. |
| `table` | `columns`, `rows`, `source_note`, optional `title` | Cross-tabulated aggregates that do not fit one metric per value. State the counting rule and time scope in `source_note`. |
| `text` | `body` | An interpretation paragraph; apply the evidence ladder in `analysis-guidelines.md`. |
| `callout` | `body` | A caveat the reader must not miss, such as a small sample. |

Metrics inside custom sections are full metrics: they can be cited as recommendation evidence. Table cells are aggregates only — never one row per learner. Place the section by listing `custom:<id>` in `presentation.sections`; without that list it appears just before the recommendations.

## Definition: How a Number Is Counted

A teacher may know something about their course that makes a different counting rule more meaningful: only learners who started after a revision, completion that ignores an optional final lesson, “active” meaning the last 14 days instead of 7.

1. **Write the new rule precisely** in the metric's `definition`: what is counted, the numerator and denominator for a rate, the time scope, and any exclusion. Name excluded groups in `source_notes`.
2. **Recompute from data**, collecting again if needed. Never rescale the old value to approximate the new rule.
3. **Mark it.** Set `"origin": "teacher"` on its `metric_definitions` entry. Choose a `label`, in the report language, that tells the truth about the rule — for example the completion rate “excluding the optional lesson”.
4. **Keep the standard value comparable** when the standard metric is one of the defaults. Either show both metrics, or keep one and put the other in `comparison` with a label meaning “standard definition”. This protects the teacher too: next term's report can be compared with this one.
5. **Give a redefined metric a new key.** For completion in particular, the standard cohort calculation keeps the reserved `course_completion_proxy` key; a teacher-defined variant uses a different key, for example `completion_core_lessons`.
6. **Update whatever cited the old number.** Conclusions, lesson findings, and recommendations that quote the changed value must quote the new one or be rewritten.

Some requests cannot be honoured as stated, because the result would misdescribe the data. Explain the problem and offer the honest version:

- Dropping learners from a denominator *because* they lower the rate. Offer a clearly labelled subgroup instead, such as “learners who finished lesson 1”, with the subgroup size shown.
- Showing a rate without its numerator and denominator, or a sample-based finding without its sample size.
- Calling a recorded in-progress state “stuck”, or treating reach on the final lesson as completion without labelling it that way.
- Including data from hidden, unpublished, or draft lessons, or any identifying learner detail. The boundaries in `SKILL.md` and the privacy gates in `data-collection.md` are not adjustable.

## Presentation: Order, Wording, and Style

All presentation choices live in the optional top-level `presentation` object. Use the mildest tool that satisfies the request, in this order.

### 1. Built-in options

| Field | Values | Effect |
| --- | --- | --- |
| `theme` | `shifu` (default), `paper`, `forest`, `swiss`, `night` | `shifu`: the AI-Shifu brand look — brand-blue cover, white cards, light-blue panels. `paper`: warm off-white page with a deep-blue accent. `forest`: calm greens. `swiss`: black-and-white, square corners, strong rules, red accent — formal and print-like. `night`: dark background for screens; prints in light colors. |
| `density` | `comfortable` (default), `compact` | `compact` fits more on a screen or page. |
| `subtitle` | text | Replaces the line under the course title. |
| `sections` | ordered list of section ids | Sets both order and visibility. Ids: `summary`, `kpis`, `learning_path`, `lessons`, `followups`, `engagement`, `audience`, `recommendations`, `methods`, `operations`, and `custom:<id>`. |
| `section_titles` | `{id: {title, description}}` | Rewords a section heading in the teacher's own terms. |
| `lesson_table_columns` | list of metric labels | Chooses and orders the lesson comparison columns. |

`meta.brand` sets `organization_name`, shown beside the AI-Shifu logo, and `accent_color` (a `#RRGGBB` value) for a school or institution color. An accent that would be hard to read on the theme's background is ignored in favour of the theme's own accent; tell the teacher when that happens and suggest a darker or lighter shade. The AI-Shifu logo stays on every report in every theme.

`methods` must stay in `sections`. `operations` appears only when the report contains an operations appendix.

Map plain requests to these options: more formal, or printed for leadership → `swiss`; warmer, paper-like → `paper`; softer, fresher → `forest`; dark → `night`; tighter, more per page → `compact`; recommendations first → move `recommendations` up in `sections`; no audience profile → drop `audience` from `sections`.

### 2. Custom CSS

For requests the options cannot express — larger body text, a different card radius, hiding the side contents list, a specific heading color — write a short stylesheet in `presentation.custom_css`. It is appended after the template's own styles.

- Prefer overriding the template's CSS variables on `:root`: `--accent`, `--canvas`, `--surface`, `--surface-2`, `--ink`, `--ink-soft`, `--muted`, `--line`, `--radius`, `--radius-sm`, `--font`. One variable restyles the whole report consistently.
- Target sections by `[data-section="<id>"]` and components by the class names in `assets/report-template.html`.
- Keep text contrast readable and leave the print rules working; check the result in the browser after rendering.
- The validator rejects markup, backslash escapes, `@import`, and `url()`. Reports stay self-contained: no web fonts and no remote images.

### 3. A teacher-specific template

Only when a request changes the page skeleton itself — a different cover structure, for instance — copy `assets/report-template.html` next to the report as `course-learning-report.template.html`, edit the copy, and pass it to the renderer with `--template`. Keep every `{{PLACEHOLDER}}` from the bundled template; the renderer refuses a copy that drops one, repeats the body, or loads a remote asset. Beyond that, and never edit the bundled template for one teacher's preference.

### Wording

The teacher may reword any generated text: conclusions, findings, recommendation text, section titles. Rewording may change tone and vocabulary; it may not change a number, drop a stated limitation, or raise a confidence level.

## Carrying Preferences Forward

When a new report is requested for a course whose output directory already contains a `course-learning-report.json`:

- reuse its `presentation` object and `meta.brand`;
- if `course-learning-report.template.html` sits beside it, render with `--template` again, since the JSON does not record which template was used;
- rebuild each `origin: "teacher"` metric and each custom section with fresh data under the same definitions;
- keep `data_quality.teacher_adjustments`, removing notes for choices that no longer apply;
- reapply every content choice those notes record, including statistics the teacher asked to remove: a fresh report starts from the default metric set, so a removed statistic returns unless it is removed again;
- mention in the handoff that earlier preferences were kept, so the teacher can drop any of them.

If a carried-over definition can no longer be computed, keep the metric with `value: null` and say why, rather than dropping it without notice.
