# Analytics DSL Syntax

This page is the authoritative query-body grammar and server-validation contract. It consumes field and enum definitions from `tables.md`; it does not choose business scenarios, define disclosure policy, prescribe presentation, or document CLI flags.

## Body Shape

```json
{
  "table": "<one of the 10 tables>",
  "select": ["<field>", "..."],
  "where": [{"field": "<field>", "op": "<operator>", "value": "<value>"}],
  "group_by": ["<field>", "..."],
  "aggregate": [{"fn": "<function>", "field": "<field>", "alias": "<name>"}],
  "order_by": [{"field": "<field-or-alias>", "dir": "<asc|desc>"}],
  "limit": 100,
  "offset": 0
}
```

The smallest legal body contains `table` and at least one of `select` or `aggregate`. Course scope is supplied by the transport adapter. If a body also carries `shifu_bid`, it must equal the outer course scope.

## Operators (`where[].op`)

| Operator | Value contract |
|---|---|
| `=`, `!=` | Scalar equality or inequality |
| `>`, `>=`, `<`, `<=` | Numeric or date comparison |
| `in`, `not_in` | List value |
| `between` | Inclusive two-element list `[lo, hi]` |
| `like` | Trailing `%` only; a leading wildcard is rejected |
| `is_null`, `is_not_null` | Omit `value` (or pass JSON `null`); any non-null value is rejected |

## Aggregate Functions (`aggregate[].fn`)

| Function | Result |
|---|---|
| `count` | Row count |
| `count_distinct` | Distinct values of `field` |
| `sum`, `avg` | Numeric aggregate |
| `min`, `max` | Numeric or timestamp aggregate when the table capability matrix allows it |

`alias` is optional; the server derives one when omitted. Every explicit or derived alias must be a unique safe identifier and becomes the output column name.

## Constraints (enforced server-side; see [Validation Error Codes](#validation-error-codes))

- `limit` is between 1 and 1000; `offset` is non-negative.
- `select` cannot be `*`.
- When `aggregate` is present, every field in `select` must also appear in `group_by`.
- When `group_by` is present, add each grouping field to `select` if it must appear in response columns.
- `like` cannot start with `%`.
- Table names and fields must exist in the data dictionary.

## Per-Learner (`user_bid`) Dimension

Six tables support per-learner grouping. The exclusions are `user_users`, which has a restricted row-lookup grammar; `bill_daily_usage_metrics`, which has no `user_bid`; and the two course-metadata tables, whose row grain is course snapshot.

Raw learner-ID listing is blocked by default. `user_bid` may be used in exactly these ways:

- As an aggregate target without selecting it, such as `count_distinct(user_bid)`.
- In `select` and `group_by` together on an aggregate query, producing one aggregate row per learner.
- In audited conversation-detail mode when `generated_content` is also selected and its hard rules pass.
- In a restricted `user_users` lookup anchored by known identity values.

For every other row query, `select=["user_bid", ...]` without `group_by=["user_bid"]` is rejected. Grouping by another field does not satisfy the guard.

## Minimal DSL Example

```json
{
  "table": "learn_progress_records",
  "aggregate": [{"fn": "count", "alias": "n"}],
  "limit": 1
}
```

## `generated_content` Hard Rules

When `select` includes `generated_content`, all of these protocol constraints apply:

1. The table is `learn_generated_blocks`.
2. `where` contains a `type` condition using `=` or `in` whose values are drawn only from `[301, 311, 312, 321, 322]`.
3. `limit` is at most 100.
4. The server audits the access.

Types such as `303`, `309`, and `310` are blocked because their widget payloads can contain learner personal information.

## `user_users` Restricted Grammar

`user_users` is a global identity table and accepts only anchored row lookups:

1. `select` may contain only `user_bid`, `nickname`, and `user_identify`.
2. `where` must contain either `user_bid` with `=` or `in`, or `user_identify` with exact `=`.
3. `limit` is at most 50.
4. `group_by` and `aggregate` are not allowed.
5. The server audits the lookup.

Unconditional listing, partial identity matching, ranges, and bulk enumeration are rejected. Returned `nickname` values are replaced with a redaction marker when they contain a phone number, email address, or ID number; returned `user_identify` values are masked.

## Auto-Applied Filters

The endpoint injects scope and lifecycle filters; omit them from query bodies:

- All tables except `user_users` are scoped to the outer `shifu_bid`.
- All tables except `shifu_user_archives` filter `deleted = 0`.
- `learn_generated_blocks` filters `status = 1` so rerolled history does not affect results.
- `shifu_published_shifus` and `shifu_draft_shifus` filter `created_user_bid` to the caller.

## Creator-Scoped Tables (`shifu_published_shifus` / `shifu_draft_shifus`)

These tables support row lookup only: no aggregates, no `group_by`, limit at most 50, and `title like` only with at least two non-wildcard characters and a trailing wildcard. Selectable fields are limited to the metadata allowlist; author-secret fields such as system prompts, Ask configuration, keywords, and descriptions are not exposed.

## Validation Error Codes

| Code | Contract violation |
|---|---|
| `11002` | Invalid body shape, table-specific rule, alias, filter, or grouping combination |
| `11003` | Table not in the whitelist |
| `11004` | Field not allowed for the selected table |
| `11005` | Operator not in the whitelist |
| `11006` | Aggregate function not in the whitelist |
| `11007` | `limit` or `offset` out of range |

## Syntax Gotchas (common DSL construction mistakes)

### `aggregate` (singular), not `aggregates`

The key is the singular `aggregate`, whose value is an array of aggregate objects.

Wrong:

```json
{"aggregates": [{"fn": "count", "alias": "n"}]}
```

Correct:

```json
{"aggregate": [{"fn": "count", "alias": "n"}]}
```

### `where` is always an array

Wrong:

```json
{"where": {"field": "type", "op": "=", "value": 321}}
```

Correct:

```json
{"where": [{"field": "type", "op": "=", "value": 321}]}
```

### `order_by` uses `field` + `dir`, not `column` + `direction`

Wrong:

```json
{"order_by": [{"column": "asks", "direction": "desc"}]}
```

Correct:

```json
{"order_by": [{"field": "asks", "dir": "desc"}]}
```

### Every `select` field must appear in `group_by` when `aggregate` is present

Wrong:

```json
{"select": ["outline_item_bid"], "group_by": [], "aggregate": [{"fn": "count", "alias": "n"}]}
```

Correct:

```json
{"select": ["outline_item_bid"], "group_by": ["outline_item_bid"], "aggregate": [{"fn": "count", "alias": "n"}]}
```

### `shifu_bid` in body must match the outer scope

Omit `shifu_bid` from the body unless a caller explicitly requires it. When present, it must equal the course scope supplied alongside the query.
