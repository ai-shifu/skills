# Detail Output Specs

Use these output specs when the user supplies AI-Shifu creator-analysis CSV inputs or asks for detail tables.

## 1. Follow-up detail output

### Typical source shape
Common source columns include:
- learner phone
- follow-up chapter
- learner question
- AI answer

### Standard output goal
Produce one of:
- a preserved raw copy
- a filtered subset
- an enriched export with derived columns

### Recommended output fields
Preserve original fields first, then optionally add:
- `theme_cluster`
- `question_type`
- `chapter_hotspot_flag`
- `is_representative_example`
- `analysis_note`

### Question type examples
- concept clarification
- application mapping
- terminology clarification
- KPI / metric understanding
- report or communication framing
- action design

## 2. Learner progress detail output

### Typical source shape
Common source columns include:
- learner phone
- nickname
- learner id
- chapter sequence
- chapter title
- chapter id
- chapter type code
- learning status code
- progress position
- chapter first learning time
- chapter latest learning time
- chapter follow-up count
- learner total follow-up count
- learner learned chapter count
- learner first learning time
- learner latest learning time

### Standard output goal
Produce one of:
- a preserved raw copy
- a grouped or filtered subset
- an enriched export with diagnostic columns

### Recommended derived fields
- `learner_depth_bucket`
- `engagement_flag`
- `dropoff_risk_flag`
- `chapter_hotspot_flag`
- `analysis_note`

### Learner depth bucket examples
- started-only
- shallow
- mid-depth
- deep
- near-complete

## 3. Appendix selection rule

When generating appendix examples for the report:
- pick rows that explain the report conclusion
- prefer repeated patterns over one-off oddities
- include enough raw wording to stay credible
- keep the appendix much shorter than the full export

## 4. File naming rule

Use names that are stable and readable.
Examples:
- `creator-analysis-report.md`
- `follow-up-details.csv`
- `follow-up-details-enriched.csv`
- `learner-progress-details.csv`
- `learner-progress-details-enriched.csv`
- `learner-theme-clusters.md`
