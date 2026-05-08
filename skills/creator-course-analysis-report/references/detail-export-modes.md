# Detail Export Modes

Use this reference when the user wants not only a creator-facing report, but also reusable detail tables.

## Default principle

Do not dump large raw tables into the main report body.

Preferred output layering:
- main report: conclusions and recommendations
- appendix: selected supporting examples
- separate detail files: full or filtered detail tables

## Supported output modes

### 1. `report-only`
Use when the user wants a fast creator-facing readout.

Output:
- one report only

Recommended file:
- `creator-analysis-report.md`

### 2. `report-with-appendix`
Use when the user wants a readable report plus a compact evidence section.

Output:
- main report
- appendix with selected follow-up examples or selected learner progress rows

Recommended file:
- `creator-analysis-report.md`

Appendix rules:
- include only representative or high-value examples
- do not paste hundreds of raw rows
- favor samples that explain the conclusion

### 3. `report-with-exports`
Use when the user wants both the report and reusable structured detail outputs.

Output:
- main report
- optional appendix with selected evidence
- one or more standalone detail files

Recommended files:
- `creator-analysis-report.md`
- `follow-up-details.csv`
- `learner-progress-details.csv`
- optional: `learner-theme-clusters.md`

This is the preferred mode when the user supplies CSV files or explicitly asks for detailed data output.

## What belongs in the main report vs exports

### Keep in the main report
- summary findings
- grouped metrics
- top hotspots
- recurring learner themes
- representative examples
- recommendations

### Move to exports
- full follow-up rows
- full learner progress rows
- large chapter coverage tables
- repeated raw learner variable rows
- anything too long for a report reader to scan comfortably

## Export strategies

### Full export
Use when the user explicitly asks for all detail rows.

### Filtered export
Use when only a subset is needed, for example:
- high-follow-up learners
- hotspot chapters
- low-depth learners
- high-value representative follow-ups

### Enriched export
Use when it is helpful to add derived columns while preserving the original fields.
Examples:
- `theme_cluster`
- `question_type`
- `learner_depth_bucket`
- `risk_flag`
- `is_representative_example`

## Important rule

Preserve the original input fields whenever possible. Add derived columns as extra fields, not replacements, unless the user asks for a transformed-only output.
