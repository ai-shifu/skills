# Metric Dictionary

Define terms carefully before comparing courses or periods.

## Business Metrics
- `orders`: total order count; may differ from distinct paying learners
- `paid_learners`: distinct learners who completed payment or valid entitlement activation, depending on the dataset
- `revenue`: actual collected amount when available; do not mix with list price
- `conversion_rate`: always state the denominator, such as visitor-to-paid or started-to-paid

## Learner Metrics
- `started_learners`: learners who actually began learning
- `active_learners`: learners with recent or meaningful learning activity; define the time window
- `completed_learners`: learners who reached the course completion rule
- `completion_rate`: always state whether based on paid learners, started learners, or active learners

## Progress Metrics
- `learning_depth`: how far learners progress into the course
- `chapter_coverage`: reach rate for each chapter or lesson
- `chapter_completion`: completion rate per chapter or lesson
- `learning_rhythm`: time-based pattern of continued learning, return visits, or pacing

## Follow-Up Metrics
- `follow_up_count`: total follow-up ask records
- `follow_up_learners`: distinct learners who asked at least one follow-up
- `follow_up_rate`: always state the denominator
- `avg_follow_ups_per_learner`: distinguish from total follow-up count
- `follow_up_hotspot`: chapter or lesson with unusually high follow-up volume or density

## Rating Metrics
- `rating_count`: number of rating events, not unique viewers
- `average_rating`: use with sample size; low volume weakens confidence
- `low_score_signal`: low-score concentration in specific chapters, cohorts, or complaint types

## Comparison Cautions
- never compare raw totals across very different course sizes without ratios
- never compare conversion rates with different denominators
- never interpret a small-sample average rating as a stable quality judgment
- never treat high follow-up volume as automatically negative

## AI-Shifu-specific reminder
- In AI-Shifu creator dashboard work, prefer the project-specific definitions in `ai-shifu-metric-notes.md` when they differ from generic reporting language.
- If the user gives only dashboard screenshots, avoid pretending you have follow-up learner counts, chapter-level completion, or learner personas unless that evidence is actually present.
