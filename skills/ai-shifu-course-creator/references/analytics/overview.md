# Analytics Overview

Use this page as the entry point for any analytics task. The deeper references on this page are read on demand.

## When to Use

Enter the analytics path when a course author or admin asks about:

- learner count, completion rate, stuck lessons, recent activity
- orders, revenue, refunds, payment-channel distribution
- ratings, listen-vs-read preference
- follow-up Q&A counts or specific learner conversations
- credit consumption (by day, model, scene, usage type, billing metric)
- audience profile distribution (goals, level, preferences)
- individual learner tracking — with the privacy rules in `privacy-and-presentation.md`

> Raw token counts are **not** exposed to creators. Any question about "how much was spent" maps to credits via `bill_daily_usage_metrics.consumed_credits`.

Do **not** enter the analytics path when the user asks only "what courses do I have?" or "how many courses?" — that is answered by `shifu-cli.py list` alone.

## CLI-Only Rule

**All analytics operations go through `scripts/shifu-cli.py`. Never write raw HTTP, never read tokens directly, never handle the analytics endpoint's auth headers by hand.** The CLI is the single source of truth for authentication and transport; the agent's job is to translate a user question into a DSL JSON body and hand it to the CLI.

If you find yourself drafting a `POST` request or composing `Authorization: Bearer` / `Token:` headers, stop — use `analytics-query` instead.

## Workflow (3 Steps)

### Step 1 — Resolve the course

Run once per session to map `shifu_bid` ↔ course name:

```bash
python3 scripts/shifu-cli.py list
```

Cache the `shifu_bid → name` mapping in your context. The CLI's `list` output already exists for this purpose; do not call any analytics API for course metadata.

### Step 2 — Resolve the outline (only for course-level analysis)

When the query involves lesson-level dimensions (stuck lessons, lowest-rated lesson, lesson-by-lesson breakdown), fetch the outline tree:

```bash
python3 scripts/shifu-cli.py show <shifu_bid>
```

Cache `outline_item_bid → name` and `outline_item_bid → position` from the outline tree. Whenever a DSL result contains `outline_item_bid`, render it as "Lesson X.Y: <title>" before presenting. Skipping this makes outline-dimension numbers unreadable.

### Step 3 — Run the DSL query

```bash
python3 scripts/shifu-cli.py analytics-query <shifu_bid> --dsl '<json-body>'
```

Or, when the body is long or you want to reuse it:

```bash
python3 scripts/shifu-cli.py analytics-query <shifu_bid> --dsl-file query.json
```

The CLI injects `shifu_bid` into the body, handles authentication, and prints the full JSON response. The response shape on success is:

```json
{
  "code": 0,
  "data": {
    "columns": ["status", "n"],
    "rows": [[602, 124], [603, 87]],
    "limit": 100,
    "offset": 0
  }
}
```

Cross-course analysis: send one `analytics-query` per `shifu_bid` and merge results in the agent context (the endpoint does not support cross-course joins).

## Picking the Right DSL

1. Translate the user's question into a DSL body using `dsl.md` (syntax), `tables.md` (which table answers which question + which fields exist), and `recipes.md` (21 ready-to-use templates).
2. Apply the privacy rules in `privacy-and-presentation.md` if the query touches `user_users`, `generated_content`, or `var_variable_values.value`.
3. Apply the Translation Gate in `privacy-and-presentation.md` before presenting any result.

## Error Codes the CLI May Surface

The CLI prints the full response on every call. When the response carries a non-zero `code`, react as follows:

| Code | Meaning | Action |
|---|---|---|
| `0` | Success | Parse `data.columns` / `data.rows`, then apply the Translation Gate |
| `11001` | No access to this course | Confirm the `shifu_bid` is owned by the logged-in user; switch course or stop |
| `11002` | Invalid DSL | Re-check required fields, duplicate `alias`, or leading-wildcard `like` |
| `11003` | Table not in whitelist | Use one of the 8 tables in `tables.md` |
| `11004` | Field not in whitelist | Check field name or pick a different table |
| `11005` | Operator not in whitelist | Use one of the 12 operators in `dsl.md` |
| `11006` | Aggregate function not in whitelist | Use one of the 6 aggregate functions in `dsl.md` |
| `11007` | `limit` or `offset` out of range | `limit ∈ [1, 1000]`, `offset ≥ 0` |
| `1001` | User not found / token expired | Run `shifu-cli.py login` again to refresh the token |
| `1004` / `1005` | Token not logged in / expired | Same as `1001` — re-login |

The CLI exits non-zero on any of the above except `code == 0`, but the full payload is always printed first — read it, fix the DSL or guide the user to re-login, then retry.

## Scope Reminder

Each query is scoped to one `shifu_bid`. The endpoint does not support cross-course joins; merge across courses in the agent context, not in the DSL.

## What Lives Where

- `dsl.md` — DSL grammar (operators, aggregates, constraints, per-learner guard rail)
- `tables.md` — the 8 tables, their fields, all code/enum translation tables, ID translation rules, and the duplicate-row trap
- `recipes.md` — ready-to-run DSL templates by scenario
- `privacy-and-presentation.md` — `user_users` / `generated_content` / `var_variable_values` privacy rules, plus the Translation Gate for user-facing output
