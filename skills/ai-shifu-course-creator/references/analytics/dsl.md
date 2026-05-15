# Analytics DSL Syntax

All examples are CLI invocations. Read `overview.md` first if you have not already.

## Body Shape

```json
{
  "table": "<one of the 8 tables>",
  "select":    ["<field>", "..."],
  "where":     [{ "field": "<f>", "op": "<op>", "value": <value> }],
  "group_by":  ["<field>", "..."],
  "aggregate": [{ "fn": "<fn>", "field": "<f>", "alias": "<name>" }],
  "order_by":  [{ "field": "<f>", "dir": "asc" | "desc" }],
  "limit":  <1..1000>,
  "offset": <int>
}
```

`shifu_bid` is **not** required in the body — the CLI injects it from the positional `<shifu_bid>` argument. If you write `shifu_bid` in the body, it must match the positional argument or the CLI errors out.

## Operators (`where[].op`)

| Operator | Notes |
|---|---|
| `=`, `!=` | Equality |
| `>`, `>=`, `<`, `<=` | Numeric / date comparison |
| `in` | `value` is a list |
| `not_in` | `value` is a list |
| `between` | `value` is a two-element list `[lo, hi]` (inclusive) |
| `like` | Trailing `%` only; leading-wildcard `like` is rejected |
| `is_null`, `is_not_null` | `value` ignored |

## Aggregate Functions (`aggregate[].fn`)

| Fn | Use |
|---|---|
| `count` | Row count |
| `count_distinct` | Distinct values of `field` |
| `sum`, `avg`, `min`, `max` | Numeric aggregates |

Every aggregate must carry an `alias` — the output column is named after it.

## Constraints (enforced server-side; violations → `11002` / `11007`)

- `limit ≤ 1000`
- `select` cannot be `*`
- When `aggregate` is present, every column in `select` **must** also appear in `group_by`
- When `group_by` is present, explicitly add each grouping field to `select` (otherwise the response `columns` carry only the aggregate aliases)
- `like` cannot start with `%` (anti-enumeration)

## Per-Learner (`user_bid`) Dimension

6 of the 8 tables support per-learner grouping (everything except `user_users`, which has its own rules in `privacy-and-presentation.md`, and `bill_daily_usage_metrics`, which has no `user_bid` column).

**Guard rail**: when `user_bid` appears in `select`, it **must** also appear in `group_by`.

- Correct: `select=["user_bid"], group_by=["user_bid"], aggregate=[…]`
- Rejected: `select=["user_bid", "status"]` (no aggregate)
- Rejected: `select=["user_bid"], group_by=["status"]` (`user_bid` not in `group_by`)

`user_bid` is a 36-char pseudonymous ID. **Never paste it raw in user-facing output** — use ordinal labels (Learner A / B / C) per the Translation Gate in `privacy-and-presentation.md`.

## Minimal DSL Example

The smallest legal body is `table` plus either `select` or `aggregate`:

```bash
python3 scripts/shifu-cli.py analytics-query <shifu_bid> --dsl '{
  "table": "learn_progress_records",
  "aggregate": [{"fn":"count","alias":"n"}],
  "limit": 1
}'
```

## `generated_content` Hard Rules

When `select` includes `generated_content` (only meaningful on `learn_generated_blocks`), all three must hold or the API rejects with `11002`:

1. `where` carries a `type` clause with values **only from** `[301, 311, 312, 321, 322]` using `op = "="` or `op = "in"`
2. `limit ≤ 100`
3. Every access is audited server-side (the CLI does not show this — it happens in the backend)

The remaining `type` values (`303` input, `309` phone, `310` checkcode, etc.) contain learner PII and are blocked at the protocol level. Full type-code table is in `tables.md`.

## Auto-Applied Filters

The endpoint automatically applies these filters — do **not** add them to your DSL:

- All 7 non-`user_users` tables are scoped to the CLI-supplied `shifu_bid`.
- All tables except `shifu_user_archives` automatically filter `deleted = 0` (`shifu_user_archives` has no `deleted` column).

`user_users` is a global user table (no `shifu_bid` column) with its own restricted-access rules in `privacy-and-presentation.md`.
