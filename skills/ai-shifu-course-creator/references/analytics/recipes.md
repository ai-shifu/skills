# Analytics Recipes

Ready-to-run DSL templates, grouped by scenario. Every example is a `shifu-cli.py analytics-query` invocation — substitute `<bid>` with the actual `shifu_bid` from `shifu-cli.py list`. Read `dsl.md` and `tables.md` first for grammar and field meanings.

The DSL bodies omit `shifu_bid` — the CLI injects it from the positional argument.

## Progress

### Recipe 1 — Progress funnel

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_progress_records",
 "select":["status"],
 "group_by":["status"],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"n"}],
 "limit":10
}'
```

### Recipe 2 — Top 20 stuck lessons

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_progress_records",
 "where":[{"field":"status","op":"=","value":602}],
 "select":["outline_item_bid"],
 "group_by":["outline_item_bid"],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"stuck"}],
 "order_by":[{"field":"stuck","dir":"desc"}],
 "limit":20
}'
```

## Orders

### Recipe 3 — Paid buyers (price > ¥0) and revenue

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "where":[
   {"field":"status","op":"=","value":502},
   {"field":"paid_price","op":">","value":0}],
 "aggregate":[
   {"fn":"count_distinct","field":"user_bid","alias":"buyers"},
   {"fn":"sum","field":"paid_price","alias":"revenue"}],
 "limit":1
}'
```

### Recipe 4 — Free-enrolment count (paid but ¥0)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "where":[
   {"field":"status","op":"=","value":502},
   {"field":"paid_price","op":"=","value":0}],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"zero_yuan"}],
 "limit":1
}'
```

### Recipe 5 — Order status distribution (funnel view)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "select":["status"],
 "group_by":["status"],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"n"}],
 "limit":10
}'
```

### Recipe 6 — Payment channel breakdown (paid orders only)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "where":[{"field":"status","op":"=","value":502}],
 "select":["payment_channel"],
 "group_by":["payment_channel"],
 "aggregate":[{"fn":"count","alias":"orders"},{"fn":"sum","field":"paid_price","alias":"revenue"}],
 "limit":20
}'
```

## Ratings

### Recipe 7 — Lowest-rated lessons

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_lesson_feedbacks",
 "select":["progress_record_bid"],
 "group_by":["progress_record_bid"],
 "aggregate":[{"fn":"avg","field":"score","alias":"avg_score"},{"fn":"count","alias":"n"}],
 "order_by":[{"field":"avg_score","dir":"asc"}],
 "limit":10
}'
```

> Each row's `progress_record_bid` must be translated to a chapter/lesson name via the two-step lookup in `tables.md` (ID Field Translation Rules).

## Credit Consumption (use `bill_daily_usage_metrics`)

> `consumed_credits` is the authoritative wallet-deduction figure — already rate-adjusted by the billing settlement job. No further conversion needed. Always add `where usage_scene = 1203` when measuring real learner-driven spend (1202 = author preview, 1201 = author debug).

### Recipe 8 — Total credits over a date range

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"bill_daily_usage_metrics",
 "aggregate":[{"fn":"sum","field":"consumed_credits","alias":"total_credits"}],
 "where":[
   {"field":"usage_scene","op":"=","value":1203},
   {"field":"stat_date","op":"between","value":["2026-05-01","2026-05-14"]}],
 "limit":1
}'
```

### Recipe 9 — Credits: LLM vs TTS split

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"bill_daily_usage_metrics",
 "select":["usage_type"],
 "aggregate":[{"fn":"sum","field":"consumed_credits","alias":"credits"}],
 "where":[{"field":"usage_scene","op":"=","value":1203}],
 "group_by":["usage_type"],
 "limit":10
}'
```

> Returns: `usage_type = 1101` (LLM) vs `1102` (TTS) credit breakdown.

### Recipe 10 — Credits by model (ranked)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"bill_daily_usage_metrics",
 "select":["provider","model"],
 "aggregate":[{"fn":"sum","field":"consumed_credits","alias":"credits"}],
 "where":[{"field":"usage_scene","op":"=","value":1203}],
 "group_by":["provider","model"],
 "order_by":[{"field":"credits","dir":"desc"}],
 "limit":10
}'
```

### Recipe 11 — Daily credit trend

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"bill_daily_usage_metrics",
 "select":["stat_date"],
 "aggregate":[{"fn":"sum","field":"consumed_credits","alias":"credits"}],
 "where":[{"field":"usage_scene","op":"=","value":1203}],
 "group_by":["stat_date"],
 "order_by":[{"field":"stat_date","dir":"asc"}],
 "limit":90
}'
```

### Recipe 12 — Input vs cache vs output credit split

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"bill_daily_usage_metrics",
 "select":["billing_metric"],
 "aggregate":[{"fn":"sum","field":"consumed_credits","alias":"credits"}],
 "where":[
   {"field":"usage_scene","op":"=","value":1203},
   {"field":"usage_type","op":"=","value":1101}],
 "group_by":["billing_metric"],
 "order_by":[{"field":"credits","dir":"desc"}],
 "limit":10
}'
```

> Returns three rows for LLM (`usage_type = 1101`): `billing_metric = 7451` (input), `7452` (cache-hit, typically the cheapest), `7453` (output). Use this to identify whether output tokens or uncached input is the dominant cost driver.

### Recipe 13 — Single-day deep-dive (locate an unusually expensive day)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"bill_daily_usage_metrics",
 "select":["provider","model","usage_scene","usage_type","billing_metric"],
 "aggregate":[
   {"fn":"sum","field":"consumed_credits","alias":"credits"},
   {"fn":"sum","field":"record_count","alias":"calls"}],
 "where":[{"field":"stat_date","op":"=","value":"2026-05-13"}],
 "group_by":["provider","model","usage_scene","usage_type","billing_metric"],
 "order_by":[{"field":"credits","dir":"desc"}],
 "limit":50
}'
```

> Use this when a single day's total jumps unexpectedly. The full provider × model × scene × metric breakdown surfaces which combination drove the spike. Note that `usage_scene = 1202` rows here are author-side previews, not learner activity.

## Active Learners

### Recipe 14 — Active learner count

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"shifu_user_archives",
 "where":[{"field":"archived","op":"=","value":0}],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"active_n"}],
 "limit":1
}'
```

## Audience Profile

### Recipe 15 — Single-variable distribution

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"var_variable_values",
 "where":[{"field":"variable_bid","op":"=","value":"<variable_bid>"}],
 "select":["value"],
 "group_by":["value"],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"n"}],
 "order_by":[{"field":"n","dir":"desc"}],
 "limit":20
}'
```

> `value` may contain free-text PII — always aggregate, never `select` raw values without `group_by`. See `privacy-and-presentation.md`.

## Per-Learner Top-N

### Recipe 16 — Lessons completed per learner — Top N

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_progress_records",
 "where":[{"field":"status","op":"=","value":603}],
 "select":["user_bid"],
 "group_by":["user_bid"],
 "aggregate":[{"fn":"count","alias":"completed_n"}],
 "order_by":[{"field":"completed_n","dir":"desc"}],
 "limit":20
}'
```

> See the duplicate-row trap in `tables.md` — `count` on `learn_progress_records` can double-count re-taken lessons. State this caveat when presenting Top-N.

## Follow-up Q&A

### Recipe 17 — Total follow-up questions + unique questioners

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_generated_blocks",
 "where":[{"field":"type","op":"=","value":321}],
 "aggregate":[
   {"fn":"count","alias":"ask_count"},
   {"fn":"count_distinct","field":"user_bid","alias":"asker_users"}],
 "limit":1
}'
```

### Recipe 18 — Top N most active questioners

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_generated_blocks",
 "where":[{"field":"type","op":"=","value":321}],
 "select":["user_bid"],
 "group_by":["user_bid"],
 "aggregate":[{"fn":"count","alias":"asks"}],
 "order_by":[{"field":"asks","dir":"desc"}],
 "limit":20
}'
```

### Recipe 19 — Full Q&A replay for a single lesson (audited, `limit ≤ 100`)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_generated_blocks",
 "where":[
   {"field":"type","op":"in","value":[321, 322]},
   {"field":"progress_record_bid","op":"=","value":"<progress_record_bid>"}],
 "select":["user_bid","generated_content","role","type","created_at"],
 "order_by":[{"field":"created_at","dir":"asc"}],
 "limit":100
}'
```

> Returns interleaved learner questions (`type = 321, role = 2`) and LLM answers (`type = 322, role = 1`) in chronological order. Every access is audited server-side.

### Recipe 20 — All follow-up questions by one learner (raw text, `limit ≤ 100`)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_generated_blocks",
 "where":[
   {"field":"type","op":"=","value":321},
   {"field":"user_bid","op":"=","value":"<target_user_bid>"}],
 "select":["user_bid","generated_content","progress_record_bid","created_at"],
 "order_by":[{"field":"created_at","dir":"desc"}],
 "limit":100
}'
```

### Recipe 21 — Latest LLM answers (evaluate model quality)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_generated_blocks",
 "where":[{"field":"type","op":"=","value":322}],
 "select":["generated_content","progress_record_bid","created_at"],
 "order_by":[{"field":"created_at","dir":"desc"}],
 "limit":100
}'
```

### Recipe 22 — Latest follow-ups with asker identity (3-step combo)

End-to-end view for "list the latest N follow-up questions with **who asked**, the answer, and timestamps". Uses three `analytics-query` calls — the second and third batch values pulled from the first — and is joined client-side by `user_bid` and `progress_record_bid`. `user_identify` always comes back masked (`138*****000`); a `nickname` containing a phone / email / ID number is redacted to `[REDACTED-XXX]`. Plain-text phone numbers are not retrievable through this API — see `privacy-and-presentation.md`.

Substitute `<N>` (default 10, ≤ 100) below; cap the user_users batch to 50 dedup'd `user_bid` values.

**Step 1 — fetch the latest N follow-up questions**

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_generated_blocks",
 "where":[{"field":"type","op":"=","value":321}],
 "select":["user_bid","generated_content","progress_record_bid","created_at"],
 "order_by":[{"field":"created_at","dir":"desc"}],
 "limit":10
}'
```

Each row is one question: `(user_bid, question_text, progress_record_bid, asked_at)`.

**Step 2 — fetch the matching LLM answers**

Collect the distinct `progress_record_bid` values from Step 1 and pass them into `in`:

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_generated_blocks",
 "where":[
   {"field":"type","op":"=","value":322},
   {"field":"progress_record_bid","op":"in","value":["<prb-1>","<prb-2>","..."]}],
 "select":["generated_content","progress_record_bid","created_at"],
 "order_by":[{"field":"created_at","dir":"asc"}],
 "limit":100
}'
```

> Pairing rule: for each Step-1 question with `(progress_record_bid = P, asked_at = T)`, the answer is the earliest Step-2 row with the same `progress_record_bid = P` and `created_at > T`. A lesson may have multiple Q&A turns under the same `progress_record_bid`; the time-ordering is what distinguishes them.

**Step 3 — resolve the askers' nicknames and (masked) phones**

Collect the distinct `user_bid` values from Step 1 (dedup, max 50):

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"user_users",
 "where":[{"field":"user_bid","op":"in","value":["<u-bid-1>","<u-bid-2>","..."]}],
 "select":["user_bid","nickname","user_identify"],
 "limit":50
}'
```

Returns `(user_bid, nickname, user_identify)` rows. `nickname` is auto-redacted when it embeds a phone / email / ID; `user_identify` is always masked (phone → `138*****000`, email → `te*****@example.com`).

**Step 4 — assemble and present (client-side)**

Apply the Translation Gate in `privacy-and-presentation.md`:

- Never paste the raw `user_bid`; replace with ordinal labels (`Learner A / B / C`).
- Translate `progress_record_bid` to a chapter/lesson name via the two-step lookup in `tables.md`.
- Convert `created_at` to local-timezone (`2026-05-13 21:42`).
- Display the masked `user_identify` as-is — do not strip the `*****`.

Final shape per row:

> **Learner A (Python 学徒 · 138\*\*\*\*\*000)** asked in **Lesson 3.1 装饰器与闭包** at `2026-05-13 21:42`: "闭包和装饰器啥区别?" → AI answer: "闭包是…"

If the user starts from a phone number and wants to know which learner asked, run `privacy-and-presentation.md` Use B (`user_identify = "13800138000"` exact match) to get the `user_bid` first, then filter Step 1 by that `user_bid` (`{"field":"user_bid","op":"=","value":"<u-bid>"}`) — `in` / `like` / range on `user_identify` are rejected to prevent enumeration.
