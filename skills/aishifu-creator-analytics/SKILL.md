---
name: aishifu-creator-analytics
description: Use when a course author or admin on AI-Shifu (AI师傅) asks about their course analytics — learner count, completion rate, stuck lessons, orders, revenue, ratings, interactions, token costs, credit consumption, or audience profiles. Queries the creator-analytics DSL API directly via HTTP; no CLI required. Trigger on any of: "我课程的数据", "学习人数", "完成率", "积分消耗", "订单收入", "卡课节", creator analytics, aishifu-creator-analytics.
---

# AI-Shifu Course Analytics (Creator Side)

> Role: course author / admin
> Invocation: LLM makes HTTP calls directly — no CLI dependency
> Constraint: each query is scoped to one `shifu_bid`; cross-course joins are not supported — merge across courses in the LLM context

## When to Use

- User asks about any course metric — learner count, completion, stuck lessons, orders, ratings, token cost, etc.
- User asks "what courses do I have" / "how many courses" → Step 1 only; do not enter the DSL loop
- User requests learner phone / email / real name → **Refuse** (only 36-char pseudonymous `user_bid` is available)

## Setup

**Resolve credentials in this order — only ask the user if all prior steps fail:**

1. **Check the creator skill's `.env`** — read `skills/ai-shifu-course-creator/.env` and look for `SHIFU_TOKEN`. If found, use it as `AISHIFU_TOKEN`. This file is written automatically when the user logs in via the `ai-shifu-course-creator` skill, so it is usually already present.

2. **Check environment variables** — look for `AISHIFU_TOKEN` (analytics-specific) or `SHIFU_TOKEN` in the current shell environment. Either is accepted.

3. **Check the project root `.env`** — read `.env` in the working directory for the same variable names.

4. **Ask the user** — only if none of the above yields a token. Request the token once per session; do not re-prompt on every query. The token can be copied from the browser's `localStorage` → key `token`.

**Base URL (`AISHIFU_API_BASE`):** default to `https://app.ai-shifu.cn` (the same endpoint the creator skill uses). Override only if the user is on a different deployment.

**Credential lifecycle:**
- Once resolved, reuse the token for the entire session without asking again
- Tokens expire; if the API returns `1001`, inform the user and offer to re-read the `.env` file or ask for a refreshed token

All requests must carry these headers simultaneously:
- `Authorization: Bearer ${AISHIFU_TOKEN}`
- `Token: ${AISHIFU_TOKEN}`
- `Content-Type: application/json`

> Both auth headers are required — omitting either will fail.

---

## Workflow

Three-step main path (list courses → translate to DSL → query). Add Step 1.5 (fetch outline) whenever entering course-level analysis.

### Step 1 — Fetch course list

```
GET ${AISHIFU_API_BASE}/api/shifu/shifus?page_index=1&page_size=20
```

Optional query parameters:
- `archived=true|false` — filter by archive state
- `is_favorite=true|false` — filter by favourite state

Response `data.items[]`, each containing:
- `bid` → the `shifu_bid` used in DSL queries
- `name` → course title
- `state` — course state string (e.g. `"published"`)
- `is_favorite` — boolean
- `archived` — boolean

> **Cache the `bid → name` map** for translating `shifu_bid` throughout the session.
>
> If the user only asks "what courses do I have", stop here and answer using `items` + `total`.

### Step 1.5 — Fetch target course outline (required before any course-level analysis)

```
GET ${AISHIFU_API_BASE}/api/shifu/shifus/<shifu_bid>/outlines
```

Response `data[]` is a nested outline tree; each node contains:
- `bid` → the `outline_item_bid` used in DSL queries
- `name` → chapter / lesson title
- `position` → display position (e.g. `"1.2"`)
- `children` → nested child nodes

> **Recursively traverse the entire tree and cache `bid → name` + `bid → position`**. Whenever a result contains `outline_item_bid`, look it up in this cache and render it as "Lesson X.Y: \<title\>" before presenting to the user.
>
> Skipping this step makes all outline-dimension numbers (stuck lessons, lowest-rated lesson, etc.) unreadable.

### Step 2 — Translate the request to DSL

Pick one table + the filters / groupings / aggregations that match the user's question. Refer to the "9 tables" section below.

### Step 3 — Send the query

```
POST ${AISHIFU_API_BASE}/api/creator-analytics/query
Body: { shifu_bid, table, select, where, group_by, aggregate, order_by, limit, offset }
```

Response:
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

On `code != 0`, handle the error (see "Error codes" at the end). Translate results into human-readable language before presenting to the user.

Cross-course analysis: send one request per `shifu_bid` and merge results in the LLM context.

---

## 9 Tables at a Glance

| Table | Answers | Key fields |
|---|---|---|
| `learn_progress_records` | Learner count / completion rate / stuck lesson / recent activity / **lessons completed per learner** | `user_bid`, `outline_item_bid`, `status` (601-608, see code table), `created_at` |
| `learn_generated_blocks` | Content interaction count / likes / type popularity / **interactions per learner** / **follow-up Q&A replay** | `user_bid`, `type` (see code table), `role` (1 teacher/AI · 2 learner · 3 UI, **integer**), `liked` (-1/0/1), `generated_content` (raw text, restricted — see below) |
| `learn_lesson_feedbacks` | Lesson ratings / read-vs-listen mode preference / **avg rating per learner** | `user_bid`, `progress_record_bid`, `mode` (read/listen), `score` (1-5) |
| `order_orders` | Enrolments / revenue / channel distribution / refund rate / **total spend per learner** | `user_bid`, `status` (501-505, see code table; **paid** = `502`), `payment_channel` (pingxx/stripe/alipay/wechatpay/…), `paid_price` |
| `var_variable_values` | Learner profile distribution (goals / level / preferences) | `user_bid`, `variable_bid`, `value` (aggregate only — **do not select raw value**) |
| `bill_usage` | Token / TTS raw usage / slow responses / **usage per learner** / **cache hit rate** / **breakdown by model/provider** | `user_bid`, `progress_record_bid`, `usage_type` (1101 LLM / 1102 TTS), **`usage_scene`** (1201 debug / 1202 preview / 1203 learner production), `input`, `input_cache` (LLM cache-hit tokens), `output`, `total` (raw units — **not credits**), `provider`, `model`, `record_level` (0 request-level / 1 segment-level — **add `= 0` when aggregating to avoid double-counting**), `billable` (1 billed / 0 not billed), `latency_ms` |
| `shifu_user_archives` | Active learner count / archive rate | `user_bid`, `archived` (0 active / 1 archived) |
| `bill_daily_usage_metrics` 🆕 | **Credit consumption** (by day / model / scene) — `consumed_credits` is the authoritative billing-tier figure | `stat_date`, `usage_scene`, `usage_type`, `provider`, `model`, `consumed_credits` (**exact credits, already converted at the billing rate**), `record_count`; filterable by `stat_date` / `usage_scene` / `usage_type` / `provider` |
| `user_users` ⚠️ | **Look up nickname by known `user_bid`** / **reverse-look up `user_bid` by phone or email** | `user_bid`, `nickname` (auto PII-redacted), `user_identify` (masked, e.g. `138*****000`); anchor filter required: `where user_bid in/=` or `where user_identify =` (exact match only); limit ≤ 50; audited |

The 8 tables other than `user_users` are automatically filtered by `shifu_bid` and `deleted=0` (`shifu_user_archives` has no `deleted` column) — **do not include these in your DSL**.
`user_users` is a **global user table** (no `shifu_bid` column) with two uses: ① translate a known `user_bid` to a display nickname; ② reverse-look up `user_bid` from a known phone or email. Rules in the "`user_users` restricted access" section below.

### Per-learner (`user_bid`) dimension

All 7 non-`user_users` tables support per-learner grouping: `group_by ["user_bid"] + select ["user_bid"]`, typically combined with `order_by … desc + limit N` for Top-N.

**Guard rail**: when `user_bid` appears in `select`, it **must** also appear in `group_by`.
- ✅ `select=["user_bid"], group_by=["user_bid"], aggregate=[…]`
- ❌ `select=["user_bid", "status"]` (no aggregate — rejected)
- ❌ `select=["user_bid"], group_by=["status"]` (user_bid not in group_by — rejected)

`user_bid` is a 36-char pseudo-ID. **Never paste it raw in user-facing output**; use ordinal labels (Learner A / B / C) or aggregate numbers.

### `learn_generated_blocks` type codes + raw content access rules

`type` field (integer):

| type | Name | Source | `generated_content` visible? |
|---|---|---|---|
| `301` | `content` — system narration | Course template | ✅ |
| `311` | `mdcontent` — Markdown narration | Course template | ✅ |
| `312` | `mdinteraction` — interaction prompt | Course template | ✅ |
| `321` | `mdask` — **learner follow-up question** | Learner input | ✅ (can view question text) |
| `322` | `mdanswer` — **LLM answer to follow-up** | LLM generated | ✅ |
| `303` input / `304` options / `309` phone / `310` checkcode etc. | Learner input widgets | Learner input | ❌ contains PII — blocked at protocol level |

`role` field (integer): `1` = teacher/AI (`assistant`) · `2` = learner (`user`) · `3` = UI widget

#### Hard rules when selecting `generated_content`

When `select` includes `generated_content`, all of the following **must** hold:

1. `where` includes a `type` clause with values **only from** `[301, 311, 312, 321, 322]` using `op="="` or `op="in"` — otherwise 400 `invalidDsl`
2. `limit ≤ 100` — otherwise 400 `invalidLimit`
3. Every access is written to an audit log (INFO level: user_id + shifu_bid + types + limit)

Any violation causes a rejection. `303 input / 309 phone / 310 checkcode` content is inaccessible (phone numbers, verification codes, learner free-text answers).

### ⚠️ Data trap: duplicate rows in `learn_progress_records`

A learner can have multiple progress records for the **same lesson** (`outline_item_bid`) — e.g. after resetting and re-learning; the old record is kept and a new one is created. The DSL auto-filters `deleted=0` but does **not deduplicate**.

**Safe usage (count learners — recommended):**
- `count_distinct(user_bid)` + `where status=603` → ✅ deduplication is implicit
- `count_distinct(user_bid)` group_by `outline_item_bid` → ✅ learners stuck per lesson

**Risky usage (count occurrences — use with caution):**
- `count(progress_record_bid)` + `where status=603` → ❌ may exceed true learner count
- "lessons completed per learner" can double-count a lesson the learner re-took

**DSL limitation**: window functions are not supported, so selecting the latest record per learner per lesson is not possible in DSL (Admin SQL can use `ROW_NUMBER OVER PARTITION BY`). If the user needs precise "final state per learner per lesson", explain the limitation and substitute with `count_distinct(user_bid)`.

---

### ⚠️ Data trap: `bill_usage` includes learner production AND author previews

`bill_usage` records both **real learner consumption** and **author preview activity** (when an author previews their own course in the editor, those LLM/TTS calls are also recorded under the same `shifu_bid`).

Observing `count_distinct(user_bid)` far exceeding the learner count (e.g. 82 vs 34) in `bill_usage` is **expected behaviour**, not a `shifu_bid` isolation bug.

**Always add `where usage_scene = 1203` when measuring real learner consumption:**
- `1201` debug — author debugging in editor (rare)
- `1202` preview — author / shared teacher previewing course (can be large)
- `1203` production — **actual learner learning** (what you usually want)

Example — **learner-side token totals** (preview excluded):
```json
{"shifu_bid":"<bid>","table":"bill_usage",
 "where":[
   {"field":"usage_type","op":"=","value":1101},
   {"field":"usage_scene","op":"=","value":1203}],
 "aggregate":[{"fn":"sum","field":"input","alias":"in_tok"},{"fn":"sum","field":"output","alias":"out_tok"}],
 "limit":1}
```

**`billable` field**: records with `billable=0` (e.g. internal test calls) do not deduct credits. Add `where billable=1` when measuring exact credited consumption. Safe to omit for general analysis (the vast majority of production calls are `billable=1`).

Example — **compare learner vs preview token consumption** (by scene):
```json
{"shifu_bid":"<bid>","table":"bill_usage",
 "where":[{"field":"usage_type","op":"=","value":1101}],
 "select":["usage_scene"],
 "group_by":["usage_scene"],
 "aggregate":[
   {"fn":"sum","field":"input","alias":"in_tok"},
   {"fn":"count_distinct","field":"user_bid","alias":"users"}],
 "limit":10}
```

### `user_users` restricted access

**Use A**: translate pseudonymous `user_bid` to a display nickname.
**Use B**: given a learner's phone number or email, reverse-look up their `user_bid`, then query other tables with it.

**Hard rules** (any violation → 400 `invalidDsl`):

1. `select` may only include `{user_bid, nickname, user_identify}`; `avatar / name / birthday` are **permanently off-limits**
2. `where` must include one of these anchor filters (unconditional listing of all users is prohibited):
   - `user_bid`: `op` must be `=` or `in` (no `like` / range)
   - `user_identify`: `op` must be `=` (exact phone/email match only; `in`, `like`, and range are **prohibited** to prevent bulk enumeration)
3. `limit ≤ 50`
4. `group_by` and aggregates are **not allowed**
5. Server-side audit log: `user_id + shifu_bid + filter type + timestamp`
6. Automatic privacy handling:
   - `nickname`: **full redaction** — replaced with `[REDACTED-PHONE]` / `[REDACTED-EMAIL]` / `[REDACTED-IDCARD]` when a phone, email, or ID number is detected
   - `user_identify`: **masked** — first and last characters retained, middle replaced with `*****` (phone: `138*****000`, email: `te*****@example.com`)

**Use A — look up nickname by `user_bid`** (collect user_bids from another table first, then fetch display names):

```json
{"shifu_bid":"<bid>","table":"user_users",
 "select":["user_bid","nickname"],
 "where":[{"field":"user_bid","op":"in","value":["u-bid-1","u-bid-2","u-bid-3"]}],
 "limit":50}
```

Returns:
```json
{"columns":["user_bid","nickname"],
 "rows":[["u-bid-1","Python 学徒"],["u-bid-2","[REDACTED-PHONE]"],["u-bid-3","Alice"]]}
```

**Use B — reverse-look up `user_bid` from phone number** (when the author has a known phone):

```json
{"shifu_bid":"<bid>","table":"user_users",
 "select":["user_bid","nickname","user_identify"],
 "where":[{"field":"user_identify","op":"=","value":"13800138000"}],
 "limit":1}
```

Returns:
```json
{"columns":["user_bid","nickname","user_identify"],
 "rows":[["u-bid-xxx","Python 学徒","138*****000"]]}
```

> Once you have the `user_bid`, use it to query `order_orders` (purchase status), `learn_progress_records` (learning progress), `learn_generated_blocks` (follow-up questions), etc.

> Even when the nickname is redacted, **never paste the raw `user_bid` in user-facing output**. Continue using ordinals ("Learner A / Learner B") with the nickname appended: `Learner A (Python 学徒)`, `Learner B (redacted)`, `Learner C (Alice)`.

---

## DSL Syntax (compact reference)

**Operators** (`where[].op`): `=`, `!=`, `>`, `>=`, `<`, `<=`, `in`, `not_in`, `between`, `like` (no leading `%`), `is_null`, `is_not_null`

**Aggregates** (`aggregate[].fn`): `count`, `count_distinct`, `sum`, `avg`, `min`, `max` — name the output column via `alias`

**Constraints**: `limit ≤ 1000`; `select` cannot be `*`; when `aggregate` is present, `select` columns must appear in `group_by`; when `group_by` is present, explicitly `select` the grouping fields (otherwise `columns` contains only aggregate columns)

**Minimal DSL** (only `shifu_bid` + `table` + `select` or `aggregate` required):
```json
{"shifu_bid":"abc","table":"learn_progress_records","aggregate":[{"fn":"count","alias":"n"}],"limit":1}
```

---

## Starter Templates (substitute `<bid>`)

**1. Progress funnel**
```json
{"shifu_bid":"<bid>","table":"learn_progress_records",
 "select":["status"],
 "group_by":["status"],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"n"}],
 "limit":10}
```

**2. Top 20 stuck lessons**
```json
{"shifu_bid":"<bid>","table":"learn_progress_records",
 "where":[{"field":"status","op":"=","value":602}],
 "select":["outline_item_bid"],
 "group_by":["outline_item_bid"],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"stuck"}],
 "order_by":[{"field":"stuck","dir":"desc"}],
 "limit":20}
```

**3. Paid buyers (price > ¥0) and revenue**
```json
{"shifu_bid":"<bid>","table":"order_orders",
 "where":[
   {"field":"status","op":"=","value":502},
   {"field":"paid_price","op":">","value":0}],
 "aggregate":[
   {"fn":"count_distinct","field":"user_bid","alias":"buyers"},
   {"fn":"sum","field":"paid_price","alias":"revenue"}],
 "limit":1}
```

**3b. Free-enrolment count (paid but ¥0)**
```json
{"shifu_bid":"<bid>","table":"order_orders",
 "where":[
   {"field":"status","op":"=","value":502},
   {"field":"paid_price","op":"=","value":0}],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"zero_yuan"}],
 "limit":1}
```

**3c. Order status distribution (funnel view)**
```json
{"shifu_bid":"<bid>","table":"order_orders",
 "select":["status"],
 "group_by":["status"],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"n"}],
 "limit":10}
```

**4. Payment channel breakdown (paid orders only)**
```json
{"shifu_bid":"<bid>","table":"order_orders",
 "where":[{"field":"status","op":"=","value":502}],
 "select":["payment_channel"],
 "group_by":["payment_channel"],
 "aggregate":[{"fn":"count","alias":"orders"},{"fn":"sum","field":"paid_price","alias":"revenue"}],
 "limit":20}
```

**5. Lowest-rated lessons**
```json
{"shifu_bid":"<bid>","table":"learn_lesson_feedbacks",
 "select":["progress_record_bid"],
 "group_by":["progress_record_bid"],
 "aggregate":[{"fn":"avg","field":"score","alias":"avg_score"},{"fn":"count","alias":"n"}],
 "order_by":[{"field":"avg_score","dir":"asc"}],
 "limit":10}
```

**6. Total LLM token cost — learner side only**
```json
{"shifu_bid":"<bid>","table":"bill_usage",
 "where":[
   {"field":"usage_type","op":"=","value":1101},
   {"field":"usage_scene","op":"=","value":1203}],
 "aggregate":[{"fn":"sum","field":"input","alias":"in_tok"},{"fn":"sum","field":"output","alias":"out_tok"}],
 "limit":1}
```
> Omitting `usage_scene=1203` includes author preview tokens. See "⚠️ Data trap" above.
> For long-running courses, add `created_at between` to scope to a recent window (e.g. last 30 days).

**7. Active learner count**
```json
{"shifu_bid":"<bid>","table":"shifu_user_archives",
 "where":[{"field":"archived","op":"=","value":0}],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"active_n"}],
 "limit":1}
```

**8. Audience profile distribution (single variable)**
```json
{"shifu_bid":"<bid>","table":"var_variable_values",
 "where":[{"field":"variable_bid","op":"=","value":"<variable_bid>"}],
 "select":["value"],
 "group_by":["value"],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"n"}],
 "order_by":[{"field":"n","dir":"desc"}],
 "limit":20}
```

**9. Top N learners by token consumption (learner production only)**
```json
{"shifu_bid":"<bid>","table":"bill_usage",
 "where":[
   {"field":"usage_type","op":"=","value":1101},
   {"field":"usage_scene","op":"=","value":1203}],
 "select":["user_bid"],
 "group_by":["user_bid"],
 "aggregate":[
   {"fn":"sum","field":"input","alias":"in_tok"},
   {"fn":"sum","field":"output","alias":"out_tok"}],
 "order_by":[{"field":"in_tok","dir":"desc"}],
 "limit":20}
```

**10. Lessons completed per learner — Top N**
```json
{"shifu_bid":"<bid>","table":"learn_progress_records",
 "where":[{"field":"status","op":"=","value":603}],
 "select":["user_bid"],
 "group_by":["user_bid"],
 "aggregate":[{"fn":"count","alias":"completed_n"}],
 "order_by":[{"field":"completed_n","dir":"desc"}],
 "limit":20}
```

**11. Total follow-up questions + unique questioners**
```json
{"shifu_bid":"<bid>","table":"learn_generated_blocks",
 "where":[{"field":"type","op":"=","value":321}],
 "aggregate":[
   {"fn":"count","alias":"ask_count"},
   {"fn":"count_distinct","field":"user_bid","alias":"asker_users"}],
 "limit":1}
```

**12. Top N most active questioners**
```json
{"shifu_bid":"<bid>","table":"learn_generated_blocks",
 "where":[{"field":"type","op":"=","value":321}],
 "select":["user_bid"],
 "group_by":["user_bid"],
 "aggregate":[{"fn":"count","alias":"asks"}],
 "order_by":[{"field":"asks","dir":"desc"}],
 "limit":20}
```

**13. Full Q&A replay for a lesson** (raw text included, limit ≤ 100, audited)
```json
{"shifu_bid":"<bid>","table":"learn_generated_blocks",
 "where":[
   {"field":"type","op":"in","value":[321, 322]},
   {"field":"progress_record_bid","op":"=","value":"<progress_record_bid>"}],
 "select":["user_bid","generated_content","role","type","created_at"],
 "order_by":[{"field":"created_at","dir":"asc"}],
 "limit":100}
```
Returns interleaved learner questions (type=321, role=2) and LLM answers (type=322, role=1) in chronological order.

**14. All follow-up questions by a specific learner** (raw text, limit ≤ 100)
```json
{"shifu_bid":"<bid>","table":"learn_generated_blocks",
 "where":[
   {"field":"type","op":"=","value":321},
   {"field":"user_bid","op":"=","value":"<target_user_bid>"}],
 "select":["user_bid","generated_content","progress_record_bid","created_at"],
 "order_by":[{"field":"created_at","dir":"desc"}],
 "limit":100}
```

**15. Latest LLM answers (evaluate model quality)**
```json
{"shifu_bid":"<bid>","table":"learn_generated_blocks",
 "where":[{"field":"type","op":"=","value":322}],
 "select":["generated_content","progress_record_bid","created_at"],
 "order_by":[{"field":"created_at","dir":"desc"}],
 "limit":100}
```

**16. Learner vs preview token comparison (by scene)**
```json
{"shifu_bid":"<bid>","table":"bill_usage",
 "where":[{"field":"usage_type","op":"=","value":1101}],
 "select":["usage_scene"],
 "group_by":["usage_scene"],
 "aggregate":[
   {"fn":"sum","field":"input","alias":"in_tok"},
   {"fn":"sum","field":"output","alias":"out_tok"}],
 "order_by":[{"field":"usage_scene","dir":"asc"}],
 "limit":10}
```

**17. LLM cache hit rate (learner production, no double-counting)**
```json
{"shifu_bid":"<bid>","table":"bill_usage",
 "aggregate":[
   {"fn":"sum","field":"input","alias":"total_input"},
   {"fn":"sum","field":"input_cache","alias":"cached_input"}],
 "where":[
   {"field":"usage_scene","op":"=","value":1203},
   {"field":"usage_type","op":"=","value":1101},
   {"field":"record_level","op":"=","value":0}],
 "limit":1}
```
> **Method A** (this template): `cached_input / total_input × 100%` = cache as share of **input tokens** (most common)
> **Method B**: `cached_input / (total_input + output_tokens) × 100%` = cache as share of **all tokens** (smaller number)
> State which method you used when answering.

**18. Credit consumption over the last N days (LLM + TTS)**
```json
{"shifu_bid":"<bid>","table":"bill_daily_usage_metrics",
 "aggregate":[{"fn":"sum","field":"consumed_credits","alias":"total_credits"}],
 "where":[
   {"field":"usage_scene","op":"=","value":1203},
   {"field":"stat_date","op":"between","value":["2026-05-01","2026-05-14"]}],
 "limit":1}
```
> `consumed_credits` equals the exact billing deduction — no further conversion needed.

**19. Credit consumption: LLM vs TTS split**
```json
{"shifu_bid":"<bid>","table":"bill_daily_usage_metrics",
 "select":["usage_type"],
 "aggregate":[{"fn":"sum","field":"consumed_credits","alias":"credits"}],
 "where":[{"field":"usage_scene","op":"=","value":1203}],
 "group_by":["usage_type"],
 "limit":10}
```
> Returns: `usage_type=1101` (LLM) vs `1102` (TTS) credit breakdown

**20. Credit consumption by model (ranked)**
```json
{"shifu_bid":"<bid>","table":"bill_daily_usage_metrics",
 "select":["provider","model"],
 "aggregate":[{"fn":"sum","field":"consumed_credits","alias":"credits"}],
 "where":[{"field":"usage_scene","op":"=","value":1203}],
 "group_by":["provider","model"],
 "order_by":[{"field":"credits","dir":"desc"}],
 "limit":10}
```

**21. Daily credit consumption trend**
```json
{"shifu_bid":"<bid>","table":"bill_daily_usage_metrics",
 "select":["stat_date"],
 "aggregate":[{"fn":"sum","field":"consumed_credits","alias":"credits"}],
 "where":[{"field":"usage_scene","op":"=","value":1203}],
 "group_by":["stat_date"],
 "order_by":[{"field":"stat_date","dir":"asc"}],
 "limit":90}
```

---

## Credit Consumption Queries

### Three independent "amounts" on the platform (never mix them)

| Amount type | Source | Who pays | Queryable |
|---|---|---|---|
| **Course price / revenue** | `order_orders.paid_price` | Learner pays the creator | ✅ DSL supported |
| **Model call credit consumption** | `bill_daily_usage_metrics.consumed_credits` | Creator's credits are deducted | ✅ DSL supported |
| **Plan / credit pack purchases** | `bill_orders` (plan order history) | Creator recharges credits | ❌ Not yet in DSL |

> User asks "how much revenue did my course earn" → query `order_orders`.
> User asks "how many credits did I spend / what did it cost" → query `bill_daily_usage_metrics`.
> **These are completely different — do not mix them.**

### Field disambiguation (important)

| Field | Table | Meaning | Use directly as credits? |
|---|---|---|---|
| `consumed_credits` | `bill_daily_usage_metrics` | **Exact credit cost**, already converted at billing rate — authoritative billing/wallet figure | ✅ Use directly |
| `total` | `bill_usage` | Raw usage units (LLM = tokens, TTS = characters) | ❌ Requires rate lookup to convert |

**Conclusion**: when the user asks "how many credits did my course consume", use `bill_daily_usage_metrics.consumed_credits` — **not** `bill_usage.total`.

### `bill_usage` aggregation requires `record_level = 0`

`bill_usage` stores both **request-level** (`record_level=0`) and **segment-level** (`record_level=1`) records:
- Segment records are sub-splits of a single request (long text split for processing); their `input/output/total` are rolled up into the corresponding request-level record
- **Aggregating `input`/`output`/`total` without `record_level=0` double-counts segment usage**

```json
// ❌ Wrong: total is double-counted
{"table":"bill_usage","aggregate":[{"fn":"sum","field":"total","alias":"tok"}],"limit":1}

// ✅ Correct: aggregate request-level records only
{"table":"bill_usage",
 "where":[{"field":"record_level","op":"=","value":0}],
 "aggregate":[{"fn":"sum","field":"total","alias":"tok"}],"limit":1}
```

---

## Error Codes (response `code`)

| code | Meaning | Action |
|---|---|---|
| `0` | Success | Parse `data` |
| `11001` | No access to this course | Ask user to verify the `shifu_bid` is theirs, or stop |
| `11002` | Invalid DSL | Check required fields / duplicate alias / leading-wildcard `like` |
| `11003` | Table not in whitelist | Use one of the 9 tables |
| `11004` | Field not in whitelist | Check field name or switch tables |
| `11005` | Operator not in whitelist | Use one of the 12 operators |
| `11006` | Aggregate function not in whitelist | Use one of the 6 aggregate functions |
| `11007` | `limit` or `offset` out of range | `limit ∈ [1, 1000]`, `offset ≥ 0` |
| `1001` | User not found / token expired | Check: 1) both `Authorization: Bearer` and `Token` headers are present; 2) token is not expired (refresh from browser `localStorage`) |
| `1004` / `1005` | Token not logged in / expired | Ask user to provide a fresh token |

---

## 📖 Code Translation Tables (translate before presenting to user)

> The database stores status codes, integer enums, and string enums. **Never show raw values like `601`, `502`, `1101`, or `"read"` to users.** Always translate through the tables below first.

### `learn_progress_records.status` (learning progress)

| Code | Chinese | English |
|---|---|---|
| `601` | 未开始 | Not started |
| `602` | 进行中 | In progress |
| `603` | 已完成 | Completed |
| `604` | 已退款 | Refunded |
| `605` | 已锁定 | Locked |
| `606` | 不可用 | Unavailable |
| `607` | 分支跳过 | Branch-skipped |
| `608` | 已重置 | Reset |

Completion rate: count `status=603` only. "Participating learners" = `status >= 602`.

**Denominator options (state which you use):**
- **Method ①** `count_distinct(user_bid)` in `learn_progress_records` — learners who entered the course (most common; answers "of those who started, how many finished")
- **Method ②** `order_orders status=502` purchaser count — answers "of those who bought, how many finished" (requires two queries and LLM-side division)

### `order_orders.status` (order status)

| Code | Chinese | English |
|---|---|---|
| `501` | 已创建未付款 | Created, unpaid |
| `502` | 已付款 ✅ | Paid |
| `503` | 已退款 | Refunded |
| `504` | 待支付 | Pending payment |
| `505` | 已超时 | Timed out |

For "enrolment count / revenue" use `status = 502`. For "pending" use `status in (501, 504)`.

**Match filter to user intent:**

| User asks | Correct filter | Notes |
|---|---|---|
| "How many people paid" | `status = 502, paid_price > 0` | Strict paid, excludes ¥0 orders |
| "Free enrolments / ¥0 purchases" | `status = 502, paid_price = 0` | Paid but ¥0 |
| "All paid orders (incl. ¥0)" | `status = 502` | No price filter |
| "How many placed an order" | `status in (501, 502, 504)` | Unpaid + paid + pending |
| "How many refunds" | `status = 503` | Refunded only |
| "Full order funnel" | No status filter; group_by status | See distribution |

**Common mistake**: `status >= 502` includes refunded (503), pending (504), timed-out (505), inflating revenue. **Use `=` or `in` for exact matching — never `>=`.**

### `order_orders.payment_channel` (string)

| Value | Meaning |
|---|---|
| `pingxx` | Ping++ aggregated channel (WeChat Pay / Alipay etc.) |
| `stripe` | Stripe (international credit cards) |
| `alipay` | Alipay native |
| `wechatpay` | WeChat Pay native |
| `open_api` | Orders created via OpenAPI (not learner-initiated payments) |
| `""` (empty) | Legacy data or manually imported activity orders |

### `learn_generated_blocks.type` (integer)

| Code | Name | Meaning |
|---|---|---|
| `301` | content | System narration (plain) |
| `311` | mdcontent | Markdown narration |
| `312` | mdinteraction | Interaction prompt |
| `321` | mdask | **Learner follow-up question** |
| `322` | mdanswer | **LLM answer to follow-up** |
| `303` / `304` / `309` / `310` etc. | input / options / phone / checkcode | Learner input widgets — raw content inaccessible |

### `learn_generated_blocks.role` (integer)

| Code | Meaning |
|---|---|
| `1` | Teacher / AI (`assistant`) |
| `2` | Learner (`user`) |
| `3` | UI widget |

### `learn_generated_blocks.liked` (integer)

| Code | Meaning |
|---|---|
| `-1` | Thumbs down |
| `0` | No reaction (default) |
| `1` | Thumbs up |

### `learn_lesson_feedbacks.mode` (string)

| Value | Meaning |
|---|---|
| `"read"` | Reading mode (text lesson) |
| `"listen"` | Listening mode (audio) |

### `learn_lesson_feedbacks.score` (integer)

1–5 stars; display as ⭐ or "X stars".

### `bill_usage.usage_type` (integer)

| Code | Meaning |
|---|---|
| `1101` | LLM inference call |
| `1102` | TTS speech synthesis |

> ⚠️ **Common misclassification**: `usage_type=1102` (TTS) has nothing to do with learner follow-up questions.
> Follow-ups trigger LLM calls (`usage_type=1101`); TTS is for AI-narrated audio (triggered when learners switch to listen mode). They are independent paths.
> To measure follow-up question volume, query `learn_generated_blocks(type=321)` or `learn_lesson_feedbacks` — **not** `bill_usage`.

### `bill_usage.usage_scene` (integer)

| Code | Meaning | Notes |
|---|---|---|
| `1201` | Debug | Author debugging in editor (rare) |
| `1202` | Preview | Author / shared teacher / admin previewing course |
| `1203` | Learner production | **Real learner learning** |

### `shifu_user_archives.archived` (integer)

| Code | Meaning |
|---|---|
| `0` | Active / enrolled |
| `1` | Archived (learner removed from bookshelf) |

---

## 🆔 ID Field Translation Rules

All `*_bid` values are 36-char pseudo-IDs. Never display them raw. Translate as follows:

| Field | How to translate |
|---|---|
| `shifu_bid` | Use the **Step 1 cache**: `GET /api/shifu/shifus` returned `items[].bid → items[].name`; look up the course title |
| `outline_item_bid` | Use the **Step 1.5 cache**: recurse the outline tree to map `bid → name`; render as "Lesson X.Y: \<title\>" |
| `progress_record_bid` | **Two-step**: ① DSL query `learn_progress_records` with `where progress_record_bid in […]` + `select progress_record_bid, outline_item_bid` to get the mapping; ② translate `outline_item_bid` via the outline cache |
| `user_bid` | **Never show raw**. Use ordinal labels ("Learner A / B / C" or "Top 1 / Top 2"). If the user wants to know who, batch the user_bids (deduped, ≤ 50) into a `user_users` query for `nickname`; append it: `Learner A (Python 学徒)` |
| `variable_bid` | No name-lookup API exists; `group_by variable_bid count_distinct user_bid` to show the distribution, then tell the user the values — **do not display the raw variable_bid** |
| `usage_bid` / `order_bid` / `lesson_feedback_bid` / `generated_block_bid` | Row-level primary keys — **never display**; used internally for deduplication / counting only |

**Absolute rule**: never paste a `bid` string verbatim in user-facing output (unless the user explicitly requests raw IDs for debugging).

---

## Privacy

- `user_users` **restricted access**: `select {user_bid, nickname, user_identify}` only; anchor filter required (`where user_bid in/=` or `where user_identify =`); `limit ≤ 50`; audited. `nickname` is fully redacted automatically; `user_identify` is masked (`138*****000` / `te*****@example.com`). `avatar / name / birthday` are **permanently inaccessible** — refuse any request for these
- `var_variable_values.value` may contain free-text personal information entered by learners — aggregate only (`group_by value count`); never paste the raw value list to the user
- `learn_generated_blocks.generated_content` (conversation text) is partially open: **`select` is only allowed when `type ∈ [301, 311, 312, 321, 322]`**; `303 input / 309 phone / 310 checkcode` etc. are inaccessible; every access is server-side audited (`user_id + shifu_bid + timestamp`); `limit ≤ 100`. Use aggregation templates (11 / 12) by default and fetch raw content only when specifically reviewing follow-up conversations

---

## Response Pattern

Before presenting any result, pass it through the **translation gate**:

### 🔁 Translation gate (mandatory)

1. **Integer / string enums** (status, type, scene, mode) → translate via "📖 Code Translation Tables" — never show raw codes like `601`, `502`, `1101`, `"read"`
2. **ID fields** → apply "🆔 ID Field Translation Rules":
   - `shifu_bid` → course title (Step 1 cache)
   - `outline_item_bid` → "Lesson X.Y: \<title\>" (Step 1.5 cache)
   - `progress_record_bid` → two-step lookup to chapter name
   - `user_bid` → ordinal label ("Learner A / B / C"); never show 36-char ID
   - Row-level `*_bid` keys → never display
3. **Monetary values** → add currency unit (¥/CNY/USD), 2 decimal places
4. **Timestamps** (`created_at`, `updated_at` etc.) → convert to local-timezone readable format (`2026-05-12 14:23`); never show raw ISO timestamps
5. **Ratios / percentages** → use percent form ("62%" not "0.623")
6. **Token counts** → use K/M for values over 10,000 ("4.0M tokens" not "4013428")

### ❌ Bad example (do not answer like this)

> Course b9f4c2d8... `learn_progress_records`: `status=602` has 34, `status=603` has 8. Most stuck at `outline_item_bid=2a8e1f...`.

### ✅ Good example

> **《Python 入门 30 讲》** currently has **34 learners in progress** and **8 who have completed** it (completion rate ≈ 19%). The most stuck point is **Lesson 3.1 "Decorators and Closures"**.
>
> Want to see a ranked breakdown of each learner's progress?

### Answer structure

1. **Numbers + plain language**: express results in ordinary language; all codes and IDs are already translated
2. **One-line interpretation**: avoid raw data dumps — add a brief "what this means" judgement
3. **Proactive drill-down offer**: based on the current result, suggest 1–2 follow-up questions the user might want to explore
