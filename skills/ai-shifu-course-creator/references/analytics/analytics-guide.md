# Analytics Guide

Use these capabilities to translate a course author's question into a query and a readable answer. The agent decides which queries and supporting references are needed; this page does not impose an end-to-end task sequence.

## Related Guidance

- `../authentication.md` establishes access to the intended platform context when needed.
- `query-language.md` defines query syntax; `table-and-field-reference.md` defines available fields, codes, identifier relationships, and data traps; `query-recipes.md` supplies scenario templates.
- `privacy-and-presentation.md` defines access restrictions and the Translation Gate for every user-facing result.
- `../cli/cli-reference.md#analytics-query` defines analytics invocation and output; `../cli/cli-reference.md#query-commands` covers course/outline lookups.

## When to Use

These capabilities answer course-author or admin questions about:

- learner count, completion rate, stuck lessons, recent activity
- orders, revenue, refunds, payment-channel distribution
- ratings, listen-vs-read preference
- follow-up Q&A counts or specific learner conversations
- follow-up Q&A volume by lesson
- credit consumption (per-charge detail / by day / by model / by scene / by usage type) — use `shifu-cli.py credit-detail`
- which wallet absorbed the deduction for a given course
- audience profile distribution (goals, level, preferences)
- individual learner tracking — with the privacy rules in `privacy-and-presentation.md`
- **course title resolution** — "what is my course `<title>` currently called", "did I rename it", "is the draft title diverging from the published title" (follow the Course Metadata path in `query-recipes.md`)

> Raw token counts are **not** exposed to creators. Any question about "how much was spent" maps to credits — query via `shifu-cli.py credit-detail`.

The question "how many courses do I have?" is answered by `shifu-cli.py list` without analytics queries.

## CLI-Only Rule

**All analytics traffic goes through `scripts/shifu-cli.py`. Never write raw HTTP, never read tokens directly, never compose `Authorization` / `Token` headers by hand.** Reuse the intended context and valid access under `../authentication.md`.

- `shifu-cli.py analytics-query <bid> --dsl '<json-body>'` queries the 10 whitelisted tables in `table-and-field-reference.md`. Use `--dsl-file query.json` for long bodies.
- `shifu-cli.py credit-detail <bid> [--start … --end … --scene 1203 --usage-type 1101 …]` answers credit/spend questions. Do not query `bill_daily_usage_metrics` for credit data: production daily aggregation is not enabled. Scene `1203` is learner spend; `1202` is preview and `1201` is debug.

## Query Planning

- For a DSL-backed question, construct the body from the actual syntax, table/field semantics, and relevant recipe. Recipe 0d supports a one-glance course overview; narrow questions need only their relevant queries.
- Use a known course BID in the intended account, or resolve the course from the supplied context. **When the user names a course by title**, complete the applicable Course Metadata lookup in `query-recipes.md` before querying that course. It chooses the current published-title lookup and includes the draft lookup when no published row exists, when the request asks for the draft title, or when it compares published and draft titles. `list` alone is a draft snapshot and can show historical or stale titles.
- For lesson dimensions, use `show <shifu_bid>` to establish the `outline_item_bid → name / position` mapping needed for correct filters and readable results.
- Apply the access restrictions in `privacy-and-presentation.md` to every query, including `user_users`, `generated_content`, and `var_variable_values.value`. Apply its Translation Gate before presenting any result; do not expose raw status codes or BIDs.
- Credit consumption uses `credit-detail` as specified above rather than the empty daily DSL table.

## Error Codes the CLI May Surface

When an analytics response carries a business `code`, interpret it as follows:

| Code | Meaning | Action |
| --- | --- | --- |
| `0` | Success | Parse `data.columns` / `data.rows`, then apply the Translation Gate |
| `11001` | No access to this course | Confirm the `shifu_bid` is owned by the logged-in user; switch course or stop |
| `11002` | Invalid DSL | Re-check required fields, duplicate `alias`, or leading-wildcard `like` |
| `11003` | Table not in whitelist | Use one of the 10 tables in `table-and-field-reference.md` |
| `11004` | Field not in whitelist | Check field name or pick a different table |
| `11005` | Operator not in whitelist | Use one of the 12 operators in `query-language.md` |
| `11006` | Aggregate function not in whitelist | Use one of the 6 aggregate functions in `query-language.md` |
| `11007` | `limit` or `offset` out of range | `limit ∈ [1, 1000]`, `offset ≥ 0` |
| `1001` | User not found / token expired | Apply `../authentication.md#verify-before-login`; verify before deciding whether a login is needed. |
| `1004` / `1005` | Token not logged in / expired | Apply the same verify-first authentication recovery. |

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

`role = 2` (learner) matches ALL learner input widgets — follow-up questions, form inputs, phone numbers, verification codes. To count follow-up questions specifically, filter `type = 321` (`mdask`). This is the single most common analytics mistake — full trap explanation in `table-and-field-reference.md`.

### Pitfall 2 — Credit queries: `credit-detail` vs `bill_daily_usage_metrics`

These are **different tools for different questions**:

- `shifu-cli.py credit-detail <bid>` — raw per-usage detail, server-side join, **always works**. Use for "how many credits did I spend", "what did my learners cost me", per-lesson breakdown.
- DSL against `bill_daily_usage_metrics` — daily aggregated trends by model/scene/type. **Currently empty in production** (cron not registered). Do not use for credit data — it always returns zero rows.

### Pitfall 3 — `where` must be an array, not a single object

The DSL requires `where` to be an array of filter objects, even for a single condition — a bare object is rejected with `11002`. WRONG/CORRECT examples in `query-language.md` → Syntax Gotchas.

### Pitfall 4 — Table name guessing

Do not guess table names — the schema has 10 tables and many sound-alike names. Always check the full list in `table-and-field-reference.md` first. Common wrong guesses:

- "user logs" or "user_logs" → does not exist. Use `learn_generated_blocks` for interaction data, `learn_progress_records` for progress data.
- "billing" or "usage" → `bill_daily_usage_metrics` (currently empty) or `shifu-cli.py credit-detail` for actual credit data.

### Pitfall 5 — Missing `outline_item_bid` in output

For lesson-level data (stuck lessons, follow-ups per lesson, ratings), obtain the `outline_item_bid → name` mapping with `shifu-cli.py show <shifu_bid>` before using lesson filters or presenting dimensions. Showing raw `outline_item_bid` hashes to the user is unreadable and violates the Translation Gate.

## Validation

- Queries use the intended authenticated context and a uniquely resolved course. When the user supplied a title, the applicable metadata lookup establishes its current published or explicitly identified draft meaning.
- DSL grammar, table names, fields, filters, and limits match their reference definitions. For example, "paid" uses `status = 502`, not `>= 502`; table names are never guessed.
- Credit queries use `credit-detail`. Follow-up counts use `type = 321`, not `role = 2`, and rely on the API's injected `status = 1` filter.
- User-facing results pass the Translation Gate, including course/lesson names, enum meanings, and privacy refusals for inaccessible identity fields.
- If Chinese CLI output is garbled, write output to a UTF-8 file and read it with the file-reading tool under `../cli/cli-reference.md#cli-output--encoding`.
- Report actual query results, gaps, and failed checks. An empty or failed query does not justify inventing data or substituting another course.

## What Lives Where

- `query-language.md` — DSL grammar (operators, aggregates, constraints, per-learner guard rail, auto-applied filters, creator-scoped metadata tables)
- `table-and-field-reference.md` — the 10 tables, their fields, all code/enum translation tables, ID translation rules, the duplicate-row trap, the `role = 2 ≠ follow-up` trap, and the "course title is not history" rule
- `query-recipes.md` — ready-to-run DSL templates by scenario (Course Metadata resolution, Course Overview 0d, then 23 numbered scenario recipes including follow-up four-key pairing and follow-up per lesson)
- `privacy-and-presentation.md` — `user_users` / `generated_content` / `var_variable_values` privacy rules, plus the Translation Gate for user-facing output
