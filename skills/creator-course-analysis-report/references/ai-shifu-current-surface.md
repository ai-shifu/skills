# AI-Shifu Current Surface

This file describes the current creator-facing analytics surface that already exists in AI-Shifu.

## Current creator dashboard routes

Current live routes are:
- `/api/dashboard/entry`
- `/api/dashboard/shifus/<shifu_bid>/detail`

Current frontend pages are:
- `src/cook-web/src/app/admin/dashboard/page.tsx`
- `src/cook-web/src/app/admin/dashboard/[shifu_bid]/page.tsx`

## What the current entry page exposes

### Entry summary
- `course_count`
- `learner_count`
- `order_count`
- `order_amount`

### Per-course row
- `shifu_bid`
- `shifu_name`
- `learner_count`
- `order_count`
- `order_amount`
- `last_active_at`
- `last_active_at_display`

## What the current course detail page exposes

### Basic info
- `course_name`
- `created_at`
- `chapter_count`
- `learner_count`

### Detail metrics
- `order_count`
- `order_amount`
- `completed_learner_count`
- `completion_rate`
- `active_learner_count_last_7_days`
- `total_follow_up_count`
- `avg_follow_up_count_per_learner`
- `avg_learning_duration_seconds`

## Important current limitations

- The current creator dashboard does **not** yet expose live learner drill-down rows.
- The current creator dashboard does **not** yet expose follow-up detail lists in the live UI.
- The current dashboard charts are still placeholders in the current frontend page.
- If the user asks for learner-level pain points or follow-up detail analysis, expect to need extra inputs such as screenshots, exports, SQL results, or manually prepared tables.

## Best use of this skill right now

Use this skill in two modes:
- `dashboard-supported mode`: when the creator only needs report sections supported by current dashboard metrics
- `extended evidence mode`: when the creator also provides learner detail, chapter detail, follow-up samples, rating samples, or offline analysis tables

When only current dashboard metrics are available, keep the report high-level and do not invent chapter-level or learner-level findings.

## What can still be analyzed from offline report inputs

Even though the live dashboard is currently limited, this skill can still analyze deeper creator questions when the user supplies extra evidence such as:
- learner variable exports
- chapter coverage tables
- follow-up detail samples
- ratings or qualitative feedback
- manually prepared analysis notes

That means the skill can still produce sections such as learner personas, repeated pain points, or follow-up topic clusters, but only when the evidence is explicitly provided.
