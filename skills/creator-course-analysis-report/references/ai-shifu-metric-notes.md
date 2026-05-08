# AI-Shifu Metric Notes

This file records the current project-specific metric meanings inferred from code and product specs.

## Course scope

Creator dashboard data is course-scoped by `shifu_bid`.
Entry-level totals are restricted to courses visible to the current creator or collaborator.

## Learner set

### Current learner_count meaning
In current AI-Shifu dashboard logic, learner-related counts are not purely “progress learners only”.

The learner set includes:
- users with at least one non-reset `LearnProgressRecord` for the course
- users with a successful manual-import order for the course (`payment_channel == "manual"`)

This means `learner_count` can include imported or manually opened learners even if their in-course progress is limited.

## Order metrics

### `order_count`
- counts successful, non-deleted course orders
- detail page uses all successful orders for the course
- entry page uses date-range filtered successful orders when a time filter is applied

### `order_amount`
- sum of `paid_price` for successful, non-deleted orders
- use as actual paid amount, not list price

## Completion metrics

### `chapter_count`
- current detail page uses visible leaf outline count from published outline items
- hidden outlines are excluded
- the visible leaf count acts as the required lesson count baseline

### `completed_learner_count`
A learner is considered completed when the learner has completion coverage across all visible leaf outlines under current dashboard logic.

Use caution:
- this is outline-level completion, not deeper block-level mastery
- it is suitable for creator reporting, but should not be described as fine-grained mastery

### `completion_rate`
- current implementation is `completed_learner_count / learner_count`
- always state that denominator is the dashboard learner set

## Activity metrics

### `active_learner_count_last_7_days`
- distinct learners with non-reset progress records updated in the last 7 days
- this is recent in-course activity, not broader site activity

### `last_active_at`
- current entry page uses the latest progress `updated_at` as course last-active proxy
- use it as learning activity signal, not revenue activity signal

## Follow-up metrics

### `total_follow_up_count`
- counts student follow-up ask blocks only
- source is `LearnGeneratedBlock`
- filter is effectively `type = MDASK` and `role = student`
- it is a question count, not an answer count and not a distinct learner count

### `avg_follow_up_count_per_learner`
- current implementation is `total_follow_up_count / learner_count`
- describe carefully as an average over the current dashboard learner set

## Learning duration

### `avg_learning_duration_seconds`
- current implementation approximates per-learner duration as:
  - `max(updated_at) - min(created_at)` across that learner's non-reset progress records in the course
- dashboard then averages those learner durations across the learner set

Use caution:
- this is an approximation of learning span, not actual active watch time or active reading time
- call it “average learning span” or explain the approximation when precision matters

## Data-confidence guidance

### High confidence
- order_count
- order_amount
- learner_count
- total_follow_up_count

### Medium confidence
- completion_rate
- completed_learner_count
- active_learner_count_last_7_days

### Lower-confidence / approximation-based
- avg_learning_duration_seconds
- any chapter-level diagnosis inferred without direct chapter tables
- any learner persona conclusion inferred without learner-level drill-down inputs
