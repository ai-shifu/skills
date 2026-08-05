# Report Structure

Build one validated data artifact and one polished, self-contained presentation artifact. The JSON is authoritative; the HTML must render it without adding new claims.

## Required References

- `analysis-guidelines.md`
- `report-data.schema.json`

## Output Files

Write exactly these default deliverables in the requested output directory:

- `course-learning-report.json` — privacy-safe schema version 1.0 data and analysis;
- `course-learning-report.html` — the printable report rendered from that JSON.

Do not embed the source analytics rows in either file. PDF is obtained through the browser's print-to-PDF flow and is not a separate source artifact.

## JSON Contract

Set `schema_version` to `"1.0"` and populate these top-level sections:

| Section | Purpose |
| --- | --- |
| `meta` | `course_title`, `generated_at`, `language`, `timezone`, effective `period`, and optional `brand`. |
| `metric_definitions` | An object mapping stable metric keys to exact definitions used by report metrics and recommendation evidence. |
| `overview` | `executive_summary`, course-level `kpis`, and the `learning_path` view. |
| `lesson_health` | An ordered array of eligible published-visible teaching leaf lessons, keyed with report-safe `lesson_key`, position, display title, lesson metrics, and calibrated findings. A `lesson_key` is a report-local key, never a platform ID. |
| `engagement` | `follow_up_analysis` sampling disclosure and themes, `ratings`, and `learning_modes`. |
| `audience` | Named aggregate `dimensions` and a plain-language `note`, including unavailable mapping states. |
| `recommendations` | Three to five prioritized records containing title, observation, interpretation, confidence, action, validation, and evidence. |
| `data_quality` | `overall_status`, `coverage_notes`, `unavailable_metrics`, and cross-cutting `limitations`. |
| `operations` | Optional appendix with `requested_by_user: true` and business/credit metrics, present only after explicit opt-in. |

Follow `report-data.schema.json` for exact property names, enum values, and required fields. Default human-readable values to `zh-CN`; use `en-US` only when the user explicitly requests English. Keep schema keys and contract enum values unchanged.

For a metric whose `unit` is `%`, store the numeric `value` in percentage points from 0 to 100 (for example, `79`, not `0.79`). The dedicated `share` fields on follow-up themes and audience segments remain fractions from 0 to 1.

## Branding

Use a Swiss International Style visual system by default: a disciplined 12-column grid, asymmetric composition, strong sans-serif typography, generous whitespace, left alignment, flat planes, hard-edged rules, and one restrained accent color. Prioritize information hierarchy and scanability over decoration. Do not use rounded cards, soft shadows, gradients, ornamental illustrations, skeuomorphic controls, or dashboard-style visual clutter.

Apply the style consistently:

- make the cover and every report section align to the same modular grid;
- create hierarchy with scale, weight, position, spacing, and rules rather than ornamental containers;
- keep charts geometric and directly labelled, using rectangular bars and exact values;
- use black, white, and neutral grays as the base palette, with the primary accent reserved for navigation, emphasis, and priority signals;
- use the bundled Helvetica-compatible system font stack so the report stays self-contained; never download a font;
- preserve the same grid logic in responsive and print layouts, collapsing it deliberately on small screens rather than shrinking desktop cards.

The optional `meta.brand` object accepts only these report-level overrides when supplied by the user or a trusted calling context:

- `organization_name` — institution display name;
- `accent_color` — primary accent color;
- `logo_text` — short text mark rendered in the header.

Do not promise or load an external or local logo image. Branding may replace the single accent color and text lockup, but must not introduce a second decorative palette, change metric meaning, hide data-quality warnings, or add external runtime dependencies. Treat invalid values as absent and fall back to the accessible Swiss red accent.

## Visible HTML Order

Render the report in this decision sequence:

1. **Cover and management conclusions** — course title, reporting window, generation time, core conclusions, and critical limitations.
2. **Learning path** — ordered reach/progress view for published, visible teaching lessons and completion-proxy explanation.
3. **Lesson health** — comparisons among eligible published-visible lessons with sample sizes, evidence, and cautious interpretations.
4. **Follow-up themes** — latest-sample disclosure, aggregate themes, generalized intents, and lesson concentration.
5. **Feedback and learning preference** — rating coverage and reading/listening feedback mix using the source's exact population.
6. **Audience** — named aggregate profiles and implications, or a clear mapping/missing-data state.
7. **Recommendations** — 3–5 prioritized cards containing observation, interpretation, confidence, action, validation, and evidence.
8. **Methods and data quality** — metric definitions, time scopes, published-visible lesson scope, proxy notes, sampling rules, missing fields, and source coverage.
9. **Operations appendix** — only when `operations` is present due to explicit user opt-in.

Do not use decorative charts when the sample is absent or the comparison is invalid. A well-labelled empty state is more trustworthy than an empty graph or a zero created from missing data.

## Renderer Workflow

Use the bundled standard-library renderer; do not hand-author a second HTML template:

```bash
python3 <skill-directory>/scripts/render_report.py \
  --input <output-directory>/course-learning-report.json \
  --validate-only
python3 <skill-directory>/scripts/render_report.py \
  --input <output-directory>/course-learning-report.json \
  --output <output-directory>/course-learning-report.html
```

Use its validation mode before final rendering when available in the checked-in CLI. A validation failure blocks delivery: correct the JSON rather than weakening or bypassing the schema. Render from the same JSON that will be delivered, then re-run the final privacy gate on both artifacts.

## Presentation Quality Gate

The generated HTML must:

- use only inline CSS, inline SVG, safe embedded assets, and escaped report data; no CDN, analytics beacon, web font, remote script, or network-dependent image;
- remain readable on desktop and mobile and when JavaScript is unavailable;
- use semantic headings, tables, labels, sufficient contrast, keyboard-safe content, and meaningful accessible text;
- include print styles that preserve section hierarchy, prevent important cards from splitting where practical, remove non-print controls, and produce a clean browser PDF;
- label chart units, legends, sample sizes, time scopes, proxy metrics, and unavailable states directly in the visible report;
- show `null` / unavailable values as localized empty states, never as numeric zero;
- escape all user- or data-supplied text before interpolation.
- visibly follow the Swiss International Style contract: modular grid, asymmetric hierarchy, sans-serif type, flat surfaces, square geometry, and restrained accent use.

## Final Consistency Gate

Before delivery, verify:

1. the JSON and HTML course title, report window, metric values, recommendation count, and quality warnings agree;
2. every visible conclusion and recommendation is represented in JSON and cites existing evidence;
3. operations content is absent unless explicitly requested;
4. the HTML contains no remote dependencies and prints without clipped or unreadable sections;
5. privacy scanning passes for both artifacts, including source text and identifier traps supplied in synthetic input;
6. file names remain exactly `course-learning-report.json` and `course-learning-report.html` unless the user explicitly requests different names.
7. every lesson-scoped section uses only the same current published-visible teaching leaf set, and excluded lessons appear nowhere in the report.
