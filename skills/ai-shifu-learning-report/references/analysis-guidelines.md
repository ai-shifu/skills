# Analysis Guidelines

Convert course signals into calibrated teaching decisions. The report should help a manager decide where to investigate and help a teacher decide what to try next, without overstating what the data proves.

## Required References

- `data-collection-and-privacy.md`

## Metric Contract

Every reported metric uses the same object shape:

| Field | Rule |
| --- | --- |
| `key` | Stable report-local metric key used by definitions and recommendation evidence; never reuse a platform ID. |
| `label` | Short localized display label. |
| `value` | Number, string, structured value accepted by the schema, or `null`. Never substitute zero for missing data. |
| `unit` | Human-readable unit appropriate to the value, localized with the report. |
| `definition` | State exactly what was counted or calculated, including numerator and denominator for a rate. |
| `time_scope` | An object containing the schema's scope mode and human label, plus start/end dates when applicable. Use cumulative, period, or current-snapshot meaning accurately. |
| `data_quality` | Use the schema's quality state and explain limitations rather than hiding them. |
| `is_approximate` | Mark proxies and estimates true; use false only for directly defined observed values. |
| `source_notes` | Name the source concept, sampling and proxy rules, and important caveats without exposing raw IDs, text, or payloads. |

Give each metric a stable key and define it in `metric_definitions`. Recommendation evidence cites those stable keys or stable lesson-level metric references, not prose claims.

## Evidence Ladder

Use the least confident claim that the evidence can support:

1. **Observation:** report a measured difference, count, distribution, or missing value.
2. **Interpretation:** offer a plausible teaching meaning while naming competing explanations.
3. **Recommendation:** propose a reversible teaching action and a way to test whether it helped.

Do not turn correlation into causation. A reach drop can reflect difficulty, a branch, optional content, access rules, learner intent, or measurement gaps. A high number of questions can signal confusion, engagement, or both. A high rating with a sharp reach drop is a conflict to surface, not a reason to discard one signal.

## Learning Path and Lesson Health

- Use distinct-learner reach and progress states to describe how learners move through the ordered lessons.
- Describe `进行中` / `In progress` as the platform's recorded state. Call a lesson a “bottleneck candidate” only when several independent signals align, such as a sharp reach drop plus weak feedback or concentrated follow-ups.
- Never label a lesson “stuck” from in-progress rows alone. Phrase the finding as an investigation priority and state the evidence.
- Compare lesson metrics only when their definitions and time scopes match. Show sample sizes next to ratings and question themes.
- Treat the final-required-lesson completion rate as a proxy, mark it approximate, and repeat the denominator in the visible explanation. If the proxy gate fails, show an unavailable state rather than an invented percentage.
- When data is sparse, prefer a factual baseline and a plan to gather more evidence over a strong diagnosis.

## Engagement, Feedback, and Follow-Ups

- Keep archive state, latest activity, feedback response, reading/listening feedback mode, and follow-up activity as separate signals. They measure different behaviors.
- Do not rename non-archived learners as “recently active” unless a time-based activity metric supports it.
- Do not claim that reading/listening feedback rows equal all reading/listening sessions. Name the population the source actually covers.
- For latest-question themes, report `sample_size`, the newest-first sampling rule, the effective span if known, and the share or count of sampled questions in each theme.
- Store only generalized intent summaries, for example “Learners want another worked example of the core method.” Do not quote, closely paraphrase, or preserve distinctive wording from a learner.
- A low follow-up count can mean clarity, low reach, or low willingness to ask. Cross-check reach and feedback before interpreting it.

## Audience Interpretation

- Explain each distribution in teaching terms only when its variable meaning is known.
- Avoid demographic or sensitive-trait inference. Use declared learning goals, experience levels, or learning preferences only at an aggregate level.
- If the audience is mixed, recommend adaptations that preserve access for all groups rather than optimizing only for the largest group.
- When a variable-name mapping is unavailable, show the data gap and do not infer a label from the values.

## Recommendation Contract

Produce 3–5 prioritized recommendations. Each recommendation must include a short, decision-oriented `title` plus:

- **Observation:** a concise measured fact.
- **Interpretation:** the likely teaching implication plus uncertainty or an alternative explanation.
- **Confidence:** `high`, `medium`, or `low`, calibrated to signal agreement, sample size, and data quality.
- **Action:** one concrete, feasible change for the teacher or teaching manager.
- **Validation method:** a named metric and comparison window that can show whether the action helped.
- **Evidence:** at least one stable metric reference; use two or more when claiming a bottleneck or explaining conflicting signals.

Recommendations must remain actionable when the reader sees only the report. Prefer “Add a worked example before Lesson 3 and compare its reach and rating after the next 30 learners” over “Improve Lesson 3.” Do not recommend course edits that the observed data does not motivate.

Calibrate confidence as follows:

- `high`: multiple aligned signals, adequate samples, direct definitions, and no major quality warning;
- `medium`: one strong signal or several incomplete/contradictory signals with a plausible action;
- `low`: sparse samples, proxy metrics, unknown coverage, or an interpretation intended mainly to guide further investigation.

## Missing and Conflicting Data

- Use `null` and an explicit quality state for unavailable duration, grades, retention, ratings, audience mappings, or completion proxies.
- Distinguish “zero observed” from “not collected,” “not supported,” and “query failed.” Only a successful query can justify zero.
- Put cross-cutting limitations in `data_quality`; keep metric-specific caveats on the metric itself.
- Surface contradictions in the management summary when they change the decision. Preserve both signals and recommend a test that can separate plausible explanations.
- Do not calculate a rate when its numerator or denominator is missing or zero. Keep the value `null` and explain why.

## Management Summary

Lead with no more than three decision-relevant conclusions:

1. overall course health and whether the completion proxy is usable;
2. the highest-priority lesson or learner need, with evidence and confidence;
3. the most useful next action or the most important data gap.

Write for a mixed audience: a teaching manager should understand the operational priority, and a teacher should understand what to change or investigate. Avoid analytics jargon when a plain teaching term is available.
