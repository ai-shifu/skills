# Analytics Overview

Use this page to classify analytics intent and plan the query after `workflow.md` selects the analytics path. Read the deeper references on demand.

## Required References

None.

## When to Use

Enter the analytics path when a course author or admin asks about:

- learner count, completion rate, stuck lessons, recent activity
- orders, revenue, refunds, payment-channel distribution
- ratings, listen-vs-read preference
- follow-up Q&A counts or specific learner conversations
- follow-up Q&A volume by lesson
- credit consumption (per-charge detail / by day / by model / by scene / by usage type) — use `shifu-cli.py credit-detail`
- which wallet absorbed the deduction for a given course
- audience profile distribution (goals, level, preferences)
- individual learner tracking — with the privacy rules in `privacy-and-presentation.md`
- **course title resolution** — "what is my course `<title>` currently called", "did I rename it", "is the draft title diverging from the published title" (use the Course Metadata recipes 0a–0c in `recipes.md`)

> Raw token counts are **not** exposed to creators. Any question about "how much was spent" maps to credits — query via `shifu-cli.py credit-detail`.

Do **not** enter the analytics path when the user asks only "how many courses do I have?" — that is a `shifu-cli.py list` call. When the user names a course by title, plan the applicable Course Metadata recipe before the downstream query and apply the current-title semantics in `tables.md#course-title-is-current-published-not-history`.

## Execution Contract

Apply the execution contract in `workflow.md#cli-only-rule`. Use this overview to translate the user's question into the appropriate CLI command and DSL query plan.

## Query Planning

1. For a DSL-backed question, translate the user's request into a DSL body using `dsl.md` (syntax), `tables.md` (which table answers which question + which fields exist), and `recipes.md` (Course Metadata 0a–0c, Course Overview 0d, + 23 numbered scenario recipes).
2. Apply the privacy rules in `privacy-and-presentation.md` if the query touches `user_users`, `generated_content`, or `var_variable_values.value`.
3. Apply the Translation Gate in `privacy-and-presentation.md` before presenting any result.
4. **If the user mentioned a course by title**, run Course Metadata Recipe 0a / 0b first and interpret the result through `tables.md#course-title-is-current-published-not-history`.
5. **If the user asks about credit consumption**, use `shifu-cli.py credit-detail` instead of issuing a DSL query against `bill_daily_usage_metrics` — that table is empty in production pending the daily aggregation cron.

## Error Codes the CLI May Surface

When an analytics response carries a non-zero business `code`, interpret it as follows:

| Code | Meaning | Action |
| --- | --- | --- |
| `0` | Success | Parse `data.columns` / `data.rows`, then apply the Translation Gate |
| `11001` | No access to this course | Confirm the `shifu_bid` is owned by the logged-in user; switch course or stop |
| `11002` | Invalid DSL | Re-check required fields, duplicate `alias`, or leading-wildcard `like` |
| `11003` | Table not in whitelist | Use one of the 10 tables in `tables.md` |
| `11004` | Field not in whitelist | Check field name or pick a different table |
| `11005` | Operator not in whitelist | Use one of the 12 operators in `dsl.md` |
| `11006` | Aggregate function not in whitelist | Use one of the 6 aggregate functions in `dsl.md` |
| `11007` | `limit` or `offset` out of range | `limit ∈ [1, 1000]`, `offset ≥ 0` |
| `1001` | User not found / token expired | Run `shifu-cli.py login` again to refresh the token |
| `1004` / `1005` | Token not logged in / expired | Same as `1001` — re-login |

## Scope Reminder

Each query is scoped to one `shifu_bid`. The endpoint does not support cross-course joins; merge across courses in the agent context, not in the DSL.

## Quick Question → Table Lookup

Before constructing any DSL, identify the correct table. Use this map:

| User asks about... | Table | Key filter | Key field |
| --- | --- | --- | --- |
| **Course overview (high-level snapshot, not one metric)** | `learn_progress_records` + `order_orders` + `shifu_user_archives` | see **Recipe 0d** | bundles learners + orders + revenue + recent activity |
| Learner count / completion / stuck lessons | `learn_progress_records` | `status = 603` (completed), `602` (stuck) | `outline_item_bid`, `status` |
| **Follow-up questions / Q&A** | `learn_generated_blocks` | **`type = 321`** (NOT `role = 2`!) | `type`, `generated_content` |
| Teaching Agent answers to follow-ups | `learn_generated_blocks` | `type = 322` | `generated_content`, `position` |
| Lesson ratings / read vs listen | `learn_lesson_feedbacks` | — | `score`, `mode` |
| Orders / revenue / payment channel | `order_orders` | `status = 502` (paid) | `paid_price`, `payment_channel` |
| Audience profile distribution | `var_variable_values` | — | `variable_bid`, `value` (aggregate only!) |
| Active learner count / archive rate | `shifu_user_archives` | `archived = 0` | `user_bid` |
| Credit consumption (by day/model/scene) | `bill_daily_usage_metrics` ⚠️ currently empty — use `credit-detail` | `usage_scene = 1203` (learner production) | `consumed_credits`, `stat_date` |
| **Credit consumption (raw detail)** | **`shifu-cli.py credit-detail`** | `--scene 1203` | CLI command, NOT a DSL query |
| Look up learner nickname | `user_users` | — | `nickname`, `user_identify` |
| Current course title | `shifu_published_shifus` | `deleted = 0` (auto-injected) | `title` |
| Draft course title | `shifu_draft_shifus` | `deleted = 0` (auto-injected) | `title` |

## Common Query Pitfalls

These are the mistakes that most commonly cause repeated failed queries and wasted time:

### Pitfall 1 — Follow-up questions: use `type = 321`, NOT `role = 2`

`role = 2` (learner) matches ALL learner input widgets — follow-up questions, form inputs, phone numbers, verification codes. To count follow-up questions specifically, filter `type = 321` (`mdask`). This is the single most common analytics mistake — full trap explanation in `tables.md`.

### Pitfall 2 — Credit queries: `credit-detail` vs `bill_daily_usage_metrics`

These are **different tools for different questions**:

- `shifu-cli.py credit-detail <bid>` — raw per-usage detail, server-side join, **always works**. Use for "how many credits did I spend", "what did my learners cost me", per-lesson breakdown.
- DSL against `bill_daily_usage_metrics` — daily aggregated trends by model/scene/type. **Currently empty in production** (cron not registered). Do not use for credit data — it always returns zero rows.

### Pitfall 3 — `where` must be an array, not a single object

The DSL requires `where` to be an array of filter objects, even for a single condition — a bare object is rejected with `11002`. WRONG/CORRECT examples in `dsl.md` → Syntax Gotchas.

### Pitfall 4 — Table name guessing

Do not guess table names — the schema has 10 tables and many sound-alike names. Always check the full list in `tables.md` first. Common wrong guesses:

- "user logs" or "user_logs" → does not exist. Use `learn_generated_blocks` for interaction data, `learn_progress_records` for progress data.
- "billing" or "usage" → `bill_daily_usage_metrics` (currently empty) or `shifu-cli.py credit-detail` for actual credit data.

### Pitfall 5 — Missing `outline_item_bid` in output

When querying lesson-level data (stuck lessons, follow-ups per lesson, ratings), you must run `shifu-cli.py show <shifu_bid>` first to build the `outline_item_bid → name` mapping. Showing raw `outline_item_bid` hashes to the user is unreadable and violates the Translation Gate.

## What Lives Where

- `dsl.md` — DSL grammar (operators, aggregates, constraints, per-learner guard rail, auto-applied filters, creator-scoped metadata tables)
- `tables.md` — the 10 tables, their fields, all code/enum translation tables, ID translation rules, the duplicate-row trap, the `role = 2 ≠ follow-up` trap, and the "course title is not history" rule
- `recipes.md` — ready-to-run DSL templates by scenario (Course Metadata 0a–0c, Course Overview 0d, then 23 numbered scenario recipes including follow-up four-key pairing and follow-up per lesson)
- `privacy-and-presentation.md` — `user_users` / `generated_content` / `var_variable_values` privacy rules, plus the Translation Gate for user-facing output
