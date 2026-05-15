# Analytics Recipes

21 ready-to-run DSL templates, grouped by scenario. Every example is a `shifu-cli.py analytics-query` invocation — substitute `<bid>` with the actual `shifu_bid` from `shifu-cli.py list`. Read `dsl.md` and `tables.md` first for grammar and field meanings.

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

### Recipe 3b — Free-enrolment count (paid but ¥0)

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

### Recipe 3c — Order status distribution (funnel view)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "select":["status"],
 "group_by":["status"],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"n"}],
 "limit":10
}'
```

### Recipe 4 — Payment channel breakdown (paid orders only)

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

### Recipe 5 — Lowest-rated lessons

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

## Token Usage (raw counts, not credits)

### Recipe 6 — Total LLM tokens, learner side only

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"bill_usage",
 "where":[
   {"field":"usage_type","op":"=","value":1101},
   {"field":"usage_scene","op":"=","value":1203},
   {"field":"record_level","op":"=","value":0}],
 "aggregate":[{"fn":"sum","field":"input","alias":"in_tok"},{"fn":"sum","field":"output","alias":"out_tok"}],
 "limit":1
}'
```

> Omitting `usage_scene = 1203` mixes preview tokens in. Omitting `record_level = 0` double-counts segment-level records. Both filters together are essential — see Traps 2 and 3 in `tables.md`.
> For long-running courses, add `created_at between` to scope to a recent window (e.g. last 30 days).

### Recipe 9 — Top N learners by token consumption (learner production only)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"bill_usage",
 "where":[
   {"field":"usage_type","op":"=","value":1101},
   {"field":"usage_scene","op":"=","value":1203},
   {"field":"record_level","op":"=","value":0}],
 "select":["user_bid"],
 "group_by":["user_bid"],
 "aggregate":[
   {"fn":"sum","field":"input","alias":"in_tok"},
   {"fn":"sum","field":"output","alias":"out_tok"}],
 "order_by":[{"field":"in_tok","dir":"desc"}],
 "limit":20
}'
```

### Recipe 16 — Learner vs preview token comparison (by scene)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"bill_usage",
 "where":[
   {"field":"usage_type","op":"=","value":1101},
   {"field":"record_level","op":"=","value":0}],
 "select":["usage_scene"],
 "group_by":["usage_scene"],
 "aggregate":[
   {"fn":"sum","field":"input","alias":"in_tok"},
   {"fn":"sum","field":"output","alias":"out_tok"}],
 "order_by":[{"field":"usage_scene","dir":"asc"}],
 "limit":10
}'
```

### Recipe 17 — LLM cache hit rate (learner production)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"bill_usage",
 "aggregate":[
   {"fn":"sum","field":"input","alias":"total_input"},
   {"fn":"sum","field":"input_cache","alias":"cached_input"}],
 "where":[
   {"field":"usage_scene","op":"=","value":1203},
   {"field":"usage_type","op":"=","value":1101},
   {"field":"record_level","op":"=","value":0}],
 "limit":1
}'
```

> **Method A** (this template): `cached_input / total_input × 100%` = cache as a share of **input tokens** (most common).
> **Method B**: `cached_input / (total_input + output_tokens) × 100%` = cache as a share of **all tokens** (smaller number).
> State which method you used when answering.

## Credit Consumption (use `bill_daily_usage_metrics`)

### Recipe 18 — Total credits over the last N days (LLM + TTS)

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

> `consumed_credits` is the exact billing deduction — no further conversion needed.

### Recipe 19 — Credits: LLM vs TTS split

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

### Recipe 20 — Credits by model (ranked)

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

### Recipe 21 — Daily credit trend

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

## Active Learners

### Recipe 7 — Active learner count

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"shifu_user_archives",
 "where":[{"field":"archived","op":"=","value":0}],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"active_n"}],
 "limit":1
}'
```

## Audience Profile

### Recipe 8 — Single-variable distribution

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

### Recipe 10 — Lessons completed per learner — Top N

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

> See Trap 1 in `tables.md` — `count` on `learn_progress_records` can double-count re-taken lessons. State this caveat when presenting Top-N.

## Follow-up Q&A

### Recipe 11 — Total follow-up questions + unique questioners

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

### Recipe 12 — Top N most active questioners

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

### Recipe 13 — Full Q&A replay for a single lesson (audited, `limit ≤ 100`)

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

### Recipe 14 — All follow-up questions by one learner (raw text, `limit ≤ 100`)

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

### Recipe 15 — Latest LLM answers (evaluate model quality)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_generated_blocks",
 "where":[{"field":"type","op":"=","value":322}],
 "select":["generated_content","progress_record_bid","created_at"],
 "order_by":[{"field":"created_at","dir":"desc"}],
 "limit":100
}'
```
