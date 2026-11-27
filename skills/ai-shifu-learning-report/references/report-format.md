# Report Format and Rendering

Build one validated data artifact and one polished, self-contained presentation artifact. The JSON is authoritative; the HTML must render it without adding new claims.

## Required References

- `analysis-guidelines.md`
- `report-data.schema.json`
- `../assets/example-report.json` — a complete, valid default report to use as a shape reference. Copy its structure, never its numbers or wording.

## Output Files

Write exactly these default deliverables in the requested output directory:

- `course-learning-report.json` — privacy-safe schema version 1.1 data and analysis;
- `course-learning-report.html` — the printable report rendered from that JSON.

Do not embed the source analytics rows in either file. PDF is obtained through the browser's print-to-PDF flow and is not a separate source artifact.

## JSON Contract

Set `schema_version` to `"1.1"` and populate these top-level sections:

| Section | Purpose |
| --- | --- |
| `meta` | `course_title`, `generated_at`, `language`, `timezone`, effective `period`, and optional `brand`. |
| `metric_definitions` | An object mapping stable metric keys to exact definitions used by report metrics and recommendation evidence. |
| `overview` | `executive_summary`, course-level `kpis`, and the `learning_path` view. |
| `lesson_health` | An ordered array of eligible published-visible teaching leaf lessons, keyed with report-safe `lesson_key`, position, display title, lesson metrics, and calibrated findings. A `lesson_key` is a report-local key, never a platform ID. |
| `engagement` | `follow_up_analysis` sampling disclosure and themes, `ratings`, `learning_modes`, and `activity`. |
| `audience` | Named aggregate `dimensions` and a plain-language `note`, including unavailable mapping states. |
| `recommendations` | Prioritized records containing title, observation, interpretation, confidence, action, validation, and evidence. |
| `data_quality` | `overall_status`, `coverage_notes`, `unavailable_metrics`, cross-cutting `limitations`, `privacy_notes`, and optional `teacher_adjustments`. |
| `operations` | Optional appendix with `requested_by_user: true` and business/credit metrics, present only after explicit opt-in. |
| `presentation` | Optional. The teacher's layout and style choices. Omit it for the default report. |
| `custom_sections` | Optional. Analyses the teacher asked for beyond the default sections. |

`presentation`, `custom_sections`, `teacher_adjustments`, a metric's `comparison`, and a definition's `origin` exist to carry a teacher's requests; `customization.md` owns how to use them. A default report contains none of them.

Follow `report-data.schema.json` for exact property names, enum values, and required fields. Default human-readable values to `zh-CN`; use `en-US` only when the user explicitly requests English. Keep schema keys and contract enum values unchanged.

For a metric whose `unit` is `%`, store the numeric `value` in percentage points from 0 to 100 (for example, `79`, not `0.79`). The dedicated `share` fields on follow-up themes and audience segments remain fractions from 0 to 1.

Give each lesson the same set of metric labels, in the same order, wherever the data allows. The renderer builds the lesson comparison table from labels that lessons share, so `触达人数` on every lesson becomes one column.

## What the Reader Sees

The renderer turns the JSON into these sections, in this default order. Each heading is phrased as the question a teacher would ask.

| Section id | Heading | Drawn from |
| --- | --- | --- |
| `summary` | 这门课现在怎么样 | `overview.executive_summary`: the overall assessment, up to three conclusions, and limitations to keep in mind. |
| `kpis` | 几个关键数字 | `overview.kpis` as tiles; each expands to its definition and source. |
| `learning_path` | 学员学到了哪里 | `overview.learning_path` as ordered bars, each compared with the step before it. |
| `lessons` | 每节课的表现如何 | `lesson_health`: a side-by-side comparison table, then one card per lesson with its finding and evidence. |
| `followups` | 学员在问什么 | `engagement.follow_up_analysis`: sample disclosure and themes with shares. |
| `engagement` | 学员怎么评价、怎么学 | `engagement.ratings`, `learning_modes`, and `activity`, kept as separate groups. |
| `audience` | 学员是谁 | `audience.dimensions` with a teaching implication each, or a clear missing-mapping state. |
| `custom:<id>` | The teacher's title | Each `custom_sections` entry. |
| `recommendations` | 下一步可以试什么 | `recommendations`: the action first, then observation, interpretation, validation, confidence, and evidence. |
| `methods` | 这些数字是怎么来的 | `data_quality` and every metric definition. Always shown. |
| `operations` | 经营与积分 | `operations`, only when present. |

The renderer computes simple reading aids from the JSON values — a step's share of the previous step, bar lengths, and a lesson's name on evidence cited outside its own card. It adds no judgement of its own.

Do not use decorative charts when the sample is absent or the comparison is invalid. A well-labelled empty state is more trustworthy than an empty graph or a zero created from missing data.

For Chinese reports, display the standard completion metric as `课程完成率` everywhere readers encounter it. Do not render `代理`, `近似`, or an approximation badge beside its label or value. Display the exact same-cohort completed-learner numerator and started-learner denominator. Keep cohort dates, report cutoff, required-path definition, eligible scope, and the absence of a fixed maturation window in the expandable metric definition and methods section.

## Visual System

The bundled template gives every report the same considered look: a warm page, generous white space, soft cards, one accent color, question-style headings, a side contents list on wide screens, and thin, directly labelled marks. Status always pairs a color with a word. Its design choices serve reading: the conclusion comes first, numbers that are compared share a row or a column, and definitions sit one click from the number they explain.

The default theme is `paper`. The template also carries `forest`, `swiss`, and `night` themes and a compact density; `customization.md` owns when and how to switch them and how to go further. Do not change the look of a report unless the teacher asked.

The optional `meta.brand` object accepts `organization_name`, `logo_text`, and `accent_color`. Do not promise or load a logo image. An accent without enough contrast on the theme surface falls back to the theme's accent.

## Renderer Workflow

Use the bundled standard-library renderer:

```bash
python3 <skill-directory>/scripts/render_report.py \
  --input <output-directory>/course-learning-report.json \
  --validate-only
python3 <skill-directory>/scripts/render_report.py \
  --input <output-directory>/course-learning-report.json \
  --output <output-directory>/course-learning-report.html
```

A validation failure blocks delivery: correct the JSON rather than weakening or bypassing the schema. The validator checks the schema, metric-to-definition agreement, rate arithmetic, evidence references, section and style settings, and privacy patterns. Render from the same JSON that will be delivered, then re-run the final privacy gate on both artifacts.

`--template <path>` renders with a teacher-specific copy of the template; use it only as `customization.md` directs.

## Presentation Quality Gate

The generated HTML must:

- use only inline CSS, inline SVG, safe embedded assets, and escaped report data; no CDN, analytics beacon, web font, remote script, or network-dependent image;
- remain readable on desktop and mobile and when JavaScript is unavailable;
- use semantic headings, tables, labels, sufficient contrast, keyboard-safe content, and meaningful accessible text;
- include print styles that preserve section hierarchy, prevent important cards from splitting where practical, remove non-print controls, and produce a clean browser PDF;
- label chart units, sample sizes, time scopes, teacher-defined metrics, and unavailable states directly in the visible report;
- show `null` / unavailable values as localized empty states, never as numeric zero;
- escape all user- or data-supplied text before interpolation.

After any style customization, open the rendered file and look at it: check for clipped or overlapping text, unreadable contrast, and a broken phone-width layout before delivering.

## Final Consistency Gate

Before delivery, verify:

1. the JSON and HTML course title, report window, metric values, recommendation count, and quality warnings agree;
2. every visible conclusion and recommendation is represented in JSON and cites existing evidence;
3. operations content is absent unless explicitly requested;
4. the HTML contains no remote dependencies and prints without clipped or unreadable sections;
5. privacy scanning passes for both artifacts, including source text and identifier traps supplied in synthetic input;
6. file names remain exactly `course-learning-report.json` and `course-learning-report.html` unless the user explicitly requests different names;
7. every lesson-scoped section uses only the same current published-visible teaching leaf set, and excluded lessons appear nowhere in the report.
