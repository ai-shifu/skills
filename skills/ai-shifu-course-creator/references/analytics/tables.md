# Analytics Tables & Codes

The 9 tables you can query, the fields each carries, the code/enum tables to translate raw values, the ID translation rules, and the four data traps to be aware of.

## 9 Tables at a Glance

| Table | Answers | Key fields |
|---|---|---|
| `learn_progress_records` | Learner count / completion rate / stuck lesson / recent activity / **lessons completed per learner** | `user_bid`, `outline_item_bid`, `status` (601-608, see code table), `created_at` |
| `learn_generated_blocks` | Content interaction count / likes / type popularity / **interactions per learner** / **follow-up Q&A replay** | `user_bid`, `type` (see code table), `role` (1 teacher/AI · 2 learner · 3 UI, **integer**), `liked` (-1/0/1), `generated_content` (raw text, restricted — see `dsl.md`) |
| `learn_lesson_feedbacks` | Lesson ratings / read-vs-listen mode preference / **avg rating per learner** | `user_bid`, `progress_record_bid`, `mode` (read/listen), `score` (1-5) |
| `order_orders` | Enrolments / revenue / channel distribution / refund rate / **total spend per learner** | `user_bid`, `status` (501-505, see code table; **paid** = `502`), `payment_channel` (pingxx/stripe/alipay/wechatpay/…), `paid_price` |
| `var_variable_values` | Learner profile distribution (goals / level / preferences) | `user_bid`, `variable_bid`, `value` (aggregate only — **do not select raw value**; see `privacy-and-presentation.md`) |
| `bill_usage` | Token / TTS raw usage / slow responses / **usage per learner** / **cache hit rate** / **breakdown by model/provider** | `user_bid`, `progress_record_bid`, `usage_type` (1101 LLM / 1102 TTS), **`usage_scene`** (1201 debug / 1202 preview / 1203 learner production), `input`, `input_cache` (LLM cache-hit tokens), `output`, `total` (raw units — **not credits**), `provider`, `model`, `record_level` (0 request-level / 1 segment-level — **add `= 0` when aggregating to avoid double-counting**), `billable` (1 billed / 0 not billed), `latency_ms` |
| `shifu_user_archives` | Active learner count / archive rate | `user_bid`, `archived` (0 active / 1 archived) |
| `bill_daily_usage_metrics` | **Credit consumption** (by day / model / scene) — `consumed_credits` is the authoritative billing-tier figure | `stat_date`, `usage_scene`, `usage_type`, `provider`, `model`, `consumed_credits` (**exact credits, already converted at the billing rate**), `record_count`; filterable by `stat_date` / `usage_scene` / `usage_type` / `provider` |
| `user_users` ⚠️ | **Look up nickname by known `user_bid`** / **reverse-look up `user_bid` by phone or email** | `user_bid`, `nickname` (auto PII-redacted), `user_identify` (masked, e.g. `138*****000`); restricted-access rules in `privacy-and-presentation.md` |

The 8 tables other than `user_users` are automatically scoped to the CLI-supplied `shifu_bid`; all tables except `shifu_user_archives` automatically filter `deleted = 0`. Do **not** include either in your DSL.

`user_users` is a **global** user table (no `shifu_bid` column). Its access is heavily restricted — read `privacy-and-presentation.md` before querying.

## `learn_generated_blocks` type codes

`type` (integer):

| type | Name | Source | `generated_content` selectable? |
|---|---|---|---|
| `301` | `content` — system narration | Course template | yes |
| `311` | `mdcontent` — Markdown narration | Course template | yes |
| `312` | `mdinteraction` — interaction prompt | Course template | yes |
| `321` | `mdask` — **learner follow-up question** | Learner input | yes |
| `322` | `mdanswer` — **LLM answer to follow-up** | LLM generated | yes |
| `303` input / `304` options / `309` phone / `310` checkcode etc. | Learner input widgets | Learner input | no — blocked at protocol level |

`role` (integer): `1` = teacher / AI (`assistant`) · `2` = learner (`user`) · `3` = UI widget

`liked` (integer): `-1` thumbs down · `0` no reaction · `1` thumbs up

## `learn_progress_records.status`

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

Completion rate counts `status = 603` only. "Participating learners" = `status >= 602`.

**Denominator options for completion rate (state which you used):**

- Method ① `count_distinct(user_bid)` in `learn_progress_records` — learners who entered the course (most common; answers "of those who started, how many finished")
- Method ② `order_orders status = 502` purchaser count — answers "of those who bought, how many finished" (requires two queries and agent-side division)

## `order_orders.status`

| Code | Chinese | English |
|---|---|---|
| `501` | 已创建未付款 | Created, unpaid |
| `502` | 已付款 ✅ | Paid |
| `503` | 已退款 | Refunded |
| `504` | 待支付 | Pending payment |
| `505` | 已超时 | Timed out |

**Match the filter to the user's intent:**

| User asks | Correct filter | Notes |
|---|---|---|
| "How many people paid" | `status = 502, paid_price > 0` | Strict paid, excludes ¥0 orders |
| "Free enrolments / ¥0 purchases" | `status = 502, paid_price = 0` | Paid but ¥0 |
| "All paid orders (incl. ¥0)" | `status = 502` | No price filter |
| "How many placed an order" | `status in (501, 502, 504)` | Unpaid + paid + pending |
| "How many refunds" | `status = 503` | Refunded only |
| "Full order funnel" | No status filter; `group_by status` | See distribution |

**Common mistake**: `status >= 502` includes refunded (503), pending (504), timed-out (505), inflating revenue. Use `=` or `in` — never `>=`.

## `order_orders.payment_channel`

| Value | Meaning |
|---|---|
| `pingxx` | Ping++ aggregated channel (WeChat Pay / Alipay etc.) |
| `stripe` | Stripe (international credit cards) |
| `alipay` | Alipay native |
| `wechatpay` | WeChat Pay native |
| `open_api` | Orders created via OpenAPI (not learner-initiated payments) |
| `""` (empty) | Legacy data or manually imported activity orders |

## `learn_lesson_feedbacks.mode`

| Value | Meaning |
|---|---|
| `"read"` | Reading mode (text lesson) |
| `"listen"` | Listening mode (audio) |

## `learn_lesson_feedbacks.score`

1-5 stars. Display as ⭐ or "X stars".

## `bill_usage.usage_type`

| Code | Meaning |
|---|---|
| `1101` | LLM inference call |
| `1102` | TTS speech synthesis |

> **Common misclassification**: `usage_type = 1102` (TTS) has nothing to do with learner follow-up questions.
> Follow-ups trigger LLM calls (`usage_type = 1101`); TTS is for AI-narrated audio (triggered when learners switch to listen mode). They are independent paths.
> To measure follow-up question volume, query `learn_generated_blocks(type = 321)` — **not** `bill_usage`.

## `bill_usage.usage_scene`

| Code | Meaning | Notes |
|---|---|---|
| `1201` | Debug | Author debugging in editor (rare) |
| `1202` | Preview | Author / shared teacher / admin previewing course |
| `1203` | Learner production | **Real learner learning** |

## `shifu_user_archives.archived`

| Code | Meaning |
|---|---|
| `0` | Active / enrolled |
| `1` | Archived (learner removed from bookshelf) |

## ID Field Translation Rules

All `*_bid` values are 36-char pseudo-IDs. Never display them raw. Translate as follows:

| Field | How to translate |
|---|---|
| `shifu_bid` | Use the `shifu-cli.py list` cache: `bid → name` |
| `outline_item_bid` | Use the `shifu-cli.py show <shifu_bid>` cache: recurse the outline tree to map `bid → name`; render as "Lesson X.Y: \<title\>" |
| `progress_record_bid` | Two-step: ① DSL query `learn_progress_records` with `where progress_record_bid in […]` + `select progress_record_bid, outline_item_bid` to get the mapping; ② translate `outline_item_bid` via the outline cache |
| `user_bid` | **Never show raw**. Use ordinal labels ("Learner A / B / C" or "Top 1 / Top 2"). If the user wants to know who, batch the user_bids (deduped, ≤ 50) into a `user_users` query per `privacy-and-presentation.md` and append the nickname: `Learner A (Python 学徒)` |
| `variable_bid` | No name-lookup API exists; `group_by variable_bid count_distinct user_bid` to show the distribution, then tell the user the values — **do not display the raw variable_bid** |
| `usage_bid` / `order_bid` / `lesson_feedback_bid` / `generated_block_bid` | Row-level primary keys — **never display**; used internally for deduplication / counting only |

**Absolute rule**: never paste a `bid` string verbatim in user-facing output (unless the user explicitly requests raw IDs for debugging).

## Data Traps

### Trap 1 — Duplicate rows in `learn_progress_records`

A learner can have multiple progress records for the **same lesson** (`outline_item_bid`) — e.g. after resetting and re-learning, the old record is kept and a new one is created. The endpoint auto-filters `deleted = 0` but does **not** deduplicate.

**Safe usage (count learners — recommended):**

- `count_distinct(user_bid)` + `where status = 603` → deduplication is implicit
- `count_distinct(user_bid)` group_by `outline_item_bid` → learners stuck per lesson

**Risky usage (count occurrences — use with caution):**

- `count(progress_record_bid)` + `where status = 603` → may exceed true learner count
- "lessons completed per learner" can double-count a lesson the learner re-took

**DSL limitation**: window functions are not supported, so selecting the latest record per learner per lesson is not possible. If the user needs precise "final state per learner per lesson", explain the limitation and substitute with `count_distinct(user_bid)`.

### Trap 2 — `bill_usage` mixes learner production with author previews

`bill_usage` records both **real learner consumption** and **author preview activity**. When an author previews their own course, those LLM/TTS calls are recorded under the same `shifu_bid`.

Observing `count_distinct(user_bid)` far exceeding the learner count (e.g. 82 vs 34) in `bill_usage` is **expected behaviour**, not a `shifu_bid` isolation bug.

**Always add `where usage_scene = 1203` when measuring real learner consumption.** Aggregating without this filter mixes preview activity into learner totals. See recipe 6 in `recipes.md` for the canonical learner-only query.

### Trap 3 — `bill_usage` aggregation requires `record_level = 0`

`bill_usage` stores both request-level (`record_level = 0`) and segment-level (`record_level = 1`) records. Segment records are sub-splits of a single request (long text split for processing); their `input` / `output` / `total` are rolled up into the corresponding request-level record.

**Aggregating without `record_level = 0` double-counts segment usage.** Add `where record_level = 0` whenever summing `input`, `output`, or `total` on `bill_usage`.

### Trap 4 — `billable = 1` for exact billed totals

`billable` is `0` for internal test calls that do not deduct credits. Add `where billable = 1` when measuring exact credited consumption. Safe to omit for general analysis (the vast majority of production calls are `billable = 1`).

## Three Independent "Amounts" — Never Mix

| Amount type | Source | Who pays | Queryable in DSL |
|---|---|---|---|
| **Course price / revenue** | `order_orders.paid_price` | Learner pays the creator | yes |
| **Model call credit consumption** | `bill_daily_usage_metrics.consumed_credits` | Creator's credits are deducted | yes |
| **Plan / credit pack purchases** | `bill_orders` (plan order history) | Creator recharges credits | no — not yet in DSL |

If the user asks "how much revenue did my course earn" → query `order_orders`. If the user asks "how many credits did I spend / what did it cost" → query `bill_daily_usage_metrics`. **These are completely different — do not mix them.**

## Credits vs Raw Usage — Pick the Right Field

| Field | Table | Meaning | Use directly as credits? |
|---|---|---|---|
| `consumed_credits` | `bill_daily_usage_metrics` | **Exact credit cost**, already converted at billing rate — authoritative billing/wallet figure | yes |
| `total` | `bill_usage` | Raw usage units (LLM = tokens, TTS = characters) | no — requires rate lookup to convert |

When the user asks "how many credits did my course consume", use `bill_daily_usage_metrics.consumed_credits` — **not** `bill_usage.total`.
