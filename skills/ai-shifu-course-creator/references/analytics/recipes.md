# Analytics Recipes

This page is the authoritative execution-template library: it owns complete scenario query bodies, command examples, client-side joins, and metric recipes. Command syntax comes from `../cli/cli-reference.md`, query grammar from `dsl.md`, row and field meaning from `tables.md`, and disclosure and presentation from `privacy-and-presentation.md`.

Most recipes use `analytics-query`; Credit Recipes 8–13 use `credit-detail`. Substitute `<bid>` with the resolved `shifu_bid`. Query bodies omit `shifu_bid` because the CLI supplies course scope from the positional argument; use the CLI reference as the authority for flags, output, and exit codes.

## Contents

- [Course Metadata](#course-metadata-resolve-shifu_bid--current-title)
- [Course Overview](#course-overview-one-stop-popularity-dashboard)
- [Progress](#progress)
- [Orders](#orders)
- [Ratings](#ratings)
- [Credit Consumption](#credit-consumption-use-shifu-clipy-credit-detail)
- [Active Learners](#active-learners)
- [Audience Profile](#audience-profile)
- [Per-Learner Top-N](#per-learner-top-n)
- [Follow-up Q&A](#follow-up-qa)
- [Identity Lookup](#identity-lookup)

## Course Metadata (resolve `shifu_bid ↔ current title`)

> Whenever the user mentions a course by title, resolve the current `shifu_bid → title` mapping before issuing a downstream analytics query. Use Recipe 0a for a title keyword and Recipes 0b–0c only when the `shifu_bid` is already known. Current-row availability is defined by [Current Title Visibility](tables.md#current-title-visibility), and user-facing wording is defined by [Course Title Presentation](privacy-and-presentation.md#course-title-presentation).

### Recipe 0a — Resolve a title keyword across owned courses

Use the dedicated command when the user supplies a current title keyword but the course identifier is unknown:

```bash
python3 scripts/shifu-cli.py find-title <keyword>
```

The command searches every owned course, normalizes whitespace and case for matching, and groups current published and current draft matches. It never searches historical or superseded titles. If it returns no match, ask for a current title keyword or known `shifu_bid`; do not claim that an old title can be recovered through analytics.

### Recipe 0b — Confirm the current title of a known `shifu_bid`

Use this only when the `shifu_bid` is already known and the current published title must be verified:

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"shifu_published_shifus",
 "select":["title","created_user_bid","updated_at"],
 "limit":1
}'
```

> Returns at most one row (the current published title). Empty result = the course is not currently published; switch to Recipe 0c.

### Recipe 0c — Check the draft title when no published row exists

Use this only when the `shifu_bid` is already known and Recipe 0b returned no published row, or when the current editor title is explicitly requested:

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"shifu_draft_shifus",
 "select":["title","created_user_bid","updated_at"],
 "limit":1
}'
```

> When the published title and the draft title disagree, surface both according to [Course Title Presentation](privacy-and-presentation.md#course-title-presentation). Historical title lookup is unsupported.

## Course Overview (one-stop popularity dashboard)

### Recipe 0d — Course overview: learners + orders + revenue + recent activity

Use this when the user wants a high-level snapshot of a course rather than one specific metric — the same set of numbers the admin dashboard shows (学员数 / 订单数 / 营收 / 最近活跃). Run these small queries and combine client-side; do **not** look for a single "stats" REST endpoint and do **not** open the admin dashboard in a browser — every one of these numbers comes from `analytics-query`.

```bash
# 1) Learner count (distinct learners who entered the course)
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_progress_records",
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"learners"}],
 "limit":1
}'

# 1b) Most-recent activity time (latest progress record; a row query also preserves its lesson context)
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_progress_records",
 "select":["created_at"],
 "order_by":[{"field":"created_at","dir":"desc"}],
 "limit":1
}'

# 2) Successful order count + revenue (status = 502; never use >=, which mixes distinct states)
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "where":[{"field":"status","op":"=","value":502}],
 "aggregate":[
   {"fn":"count","alias":"orders"},
   {"fn":"sum","field":"paid_price","alias":"revenue"}],
 "limit":1
}'

# 3) Active (non-archived) learner count
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"shifu_user_archives",
 "where":[{"field":"archived","op":"=","value":0}],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"active_learners"}],
 "limit":1
}'
```

口径说明（present these definitions alongside the numbers so they are unambiguous):

- **学员数 (learners)** = `count_distinct(user_bid)` on `learn_progress_records` — everyone who entered the course. This is the dashboard's "学员数".
- **订单数 (orders)** = `count` of `order_orders` rows with `status = 502` — successful order rows, including ¥0 free enrolments. For strictly paid users (`paid_price > 0`) use Recipe 5; for the full funnel use Recipe 6c.
- **营收 (revenue)** = `sum(paid_price)` over the same `status = 502` rows. Round to 2 decimals (`¥5,870.70`).
- **最近活跃 (last_active)** = the `created_at` of the latest `learn_progress_records` row (query 1b). Convert to local time before presenting.
- **活跃学员 (active_learners)** = non-archived learners (`shifu_user_archives.archived = 0`); usually ≤ 学员数 because some learners archived the course.

> Want only one of these? Use the focused recipe instead: learners → Recipe 1, orders/revenue → Recipes 3–6d, active learners → Recipe 14. Recipe 0d is the bundle for "just show me everything at a glance".

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

For a completion percentage, state the denominator explicitly. Use distinct learners in `learn_progress_records` when the question is "of learners who entered, how many completed"; use paid-order purchasers when the question is "of purchasers, how many completed", which requires a separate order query and client-side division. Attempt-grain rows are not a substitute for either learner-grain denominator.

Use the distinct-learner count for `status = 603` as the completion numerator. Translate every returned status through the progress-status table in `tables.md` rather than treating the numeric codes as labels.

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

Use these definitions exactly; similar-sounding order metrics have different status sets and row grains:

| Metric | Filter | Aggregation |
|---|---|---|
| 下单人数 | `status in [501, 502, 504]` | `count_distinct(user_bid)` |
| 成功下单 | `status = 502` | `count_distinct(user_bid)` |
| 付费人数 | `status = 502` and `paid_price > 0` | `count_distinct(user_bid)` |
| 订单数 | `status = 502` | Row count |
| 退款人数 | `status = 503` | `count_distinct(user_bid)` |

### Recipe 3 — Ordering users (下单人数)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "where":[{"field":"status","op":"in","value":[501,502,504]}],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"ordering_users"}],
 "limit":1
}'
```

### Recipe 4 — Successful ordering users (成功下单)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "where":[{"field":"status","op":"=","value":502}],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"successful_ordering_users"}],
 "limit":1
}'
```

### Recipe 5 — Paid users (付费人数) and revenue

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "where":[
   {"field":"status","op":"=","value":502},
   {"field":"paid_price","op":">","value":0}],
 "aggregate":[
   {"fn":"count_distinct","field":"user_bid","alias":"paid_users"},
   {"fn":"sum","field":"paid_price","alias":"revenue"}],
 "limit":1
}'
```

### Recipe 6 — Successful order count (订单数) and revenue

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "where":[{"field":"status","op":"=","value":502}],
 "aggregate":[{"fn":"count","alias":"orders"},{"fn":"sum","field":"paid_price","alias":"revenue"}],
 "limit":1
}'
```

### Recipe 6a — Refunded users (退款人数) and refunded order count

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "where":[{"field":"status","op":"=","value":503}],
 "aggregate":[
   {"fn":"count","alias":"refunded_orders"},
   {"fn":"count_distinct","field":"user_bid","alias":"refunded_users"}],
 "limit":1
}'
```

### Recipe 6b — Free-enrolment users (successful but ¥0)

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

### Recipe 6c — Order status distribution (funnel view)

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"order_orders",
 "select":["status"],
 "group_by":["status"],
 "aggregate":[{"fn":"count_distinct","field":"user_bid","alias":"n"}],
 "limit":10
}'
```

Translate each returned state with the [order status table](tables.md#order-status). Do not add the grouped values to produce 下单人数 because one learner may have rows in more than one state; use Recipe 3 for that distinct union.

### Recipe 6d — Payment channel breakdown (successful orders only)

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

### Recipe 7 — Lowest-rated lessons and mode comparison

Apply the feedback-to-lesson relationship in `tables.md#feedback-to-lesson-relationship` with two paginated row queries and a client-side join; do not rank `progress_record_bid` values as if they were lessons.

**Step 1 — page every feedback row**

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_lesson_feedbacks",
 "select":["lesson_feedback_bid","progress_record_bid","mode","score","created_at"],
 "order_by":[{"field":"created_at","dir":"asc"},{"field":"lesson_feedback_bid","dir":"asc"}],
 "limit":1000,
 "offset":0
}'
```

Repeat with offsets `1000`, `2000`, and so on until a page returns fewer than 1000 rows.

**Step 2 — page every progress-to-lesson mapping**

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_progress_records",
 "select":["progress_record_bid","outline_item_bid","created_at"],
 "order_by":[{"field":"created_at","dir":"asc"},{"field":"progress_record_bid","dir":"asc"}],
 "limit":1000,
 "offset":0
}'
```

Advance `offset` with the same rule. Build a `progress_record_bid → outline_item_bid` lookup, then attach each feedback row to its lesson. Report the count of feedback rows that have no matching progress row instead of silently assigning them to a lesson.

**Step 3 — aggregate the joined raw rows**

- For the lesson ranking, group by `outline_item_bid` and compute `sum(score) / count(feedback rows)`.
- For the mode comparison, group by `(outline_item_bid, mode)` and compute the same weighted average and response count.
- Never average already averaged read/listen or session results; each raw feedback row must retain equal weight.
- Sort lesson results by average score ascending and include the response count so small samples remain visible.

Resolve `outline_item_bid` values with the course outline, then pass the result through `privacy-and-presentation.md` for user-facing translation.

## Credit Consumption (use `shifu-cli.py credit-detail`)

> The daily summary table is currently empty as recorded in `tables.md`, so these scenarios use the `credit-detail` command defined in `../cli/cli-reference.md#credit-detail`.

### Recipe 8 — Today's credit consumption

```bash
python3 scripts/shifu-cli.py credit-detail <bid> --start 2026-05-16 --end 2026-05-16
```

Use `data.summary.total_credits` for the requested day; use `data.rows` only when the user asks for a breakdown.

### Recipe 9 — Credits over an arbitrary date window

```bash
python3 scripts/shifu-cli.py credit-detail <bid> --start 2026-05-01 --end 2026-05-15
```

Use this form when the user supplies an inclusive reporting window.

### Recipe 10 — Production-only spend (exclude preview / debug)

```bash
python3 scripts/shifu-cli.py credit-detail <bid> --scene 1203
```

Use the learner-production scene when the question excludes author preview and debugging activity.

### Recipe 11 — LLM-only vs TTS-only

```bash
# LLM only
python3 scripts/shifu-cli.py credit-detail <bid> --usage-type 1101

# TTS only
python3 scripts/shifu-cli.py credit-detail <bid> --usage-type 1102
```

Run one or both forms according to whether the user wants LLM, TTS, or comparative consumption.

### Recipe 12 — Pagination for large windows

```bash
python3 scripts/shifu-cli.py credit-detail <bid> --start 2026-05-01 --limit 200 --offset 200
```

Advance `offset` while retaining the same filters when the user needs row-level detail beyond one page.

### Recipe 13 — Reading the response

Read `data.summary` and `data.rows` according to the `credit-detail` output contract in `../cli/cli-reference.md#credit-detail`. `data.summary.unique_wallets` is a distinct-wallet count, not a wallet identifier; wallet identities exist only as `data.rows[].wallet_creator_bid`.

For a breakdown, page through every detail row with a fixed filter set and merge the pages before grouping. Group client-side by one or more requested row dimensions: `model`, `provider`, `usage_scene`, `usage_type`, or `wallet_creator_bid`. For each group, sum the decimal `credits` values and count its rows. `usage_scene` and `usage_type` meanings come from `tables.md`.

Most courses use one wallet, but subscription, sponsorship, or proxy-payment paths can produce multiple wallets for one course. When `data.summary.unique_wallets > 1`, never label one row's `wallet_creator_bid` as the course wallet; group by `wallet_creator_bid` or describe the result as multi-wallet usage. Preserve decimal credit values until presentation, then apply `privacy-and-presentation.md#translation-gate-mandatory-before-any-answer`.

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

This execution template returns a distribution rather than learner-level values. `privacy-and-presentation.md` owns whether and how the aggregate may be disclosed.

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

> **All Recipe 17–23 templates below**: the auto-applied live-row filter is defined in `dsl.md#auto-applied-filters`, while the distinction between learner role and follow-up type is defined by the generated-block type codes in `tables.md`.

Use Recipes 17, 18, and 23 for aggregate questions; do not execute an identity lookup for these aggregate results, and replace any internal learner grouping key with an ordinal label. For row-level follow-up text from Recipes 19, 20, and 22, execute Recipe 24A for already known `user_bid` values and present each learner with a privacy-safe nickname and masked identity by default; if the user explicitly requests anonymous output, omit the identity lookup and present ordinal learner labels only. Use Recipe 22 for the common latest-follow-up list.

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

End-to-end view for "list the latest N follow-up questions with who asked, the answer, and timestamps". Uses three `analytics-query` calls, with the second and third batch values pulled from the first. The course is already fixed by `<bid>`; apply the relationship in `tables.md#follow-up-qa-relationship` when pairing questions and answers, and apply `privacy-and-presentation.md` before deciding which identity fields may be shown.

Substitute `<N>` (default 10, ≤ 100) below; cap the user_users batch to 50 dedup'd `user_bid` values.

**Step 1 — fetch the latest N follow-up questions**

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_generated_blocks",
 "where":[{"field":"type","op":"=","value":321}],
 "select":["user_bid","generated_content","progress_record_bid","outline_item_bid","position","created_at"],
 "order_by":[{"field":"created_at","dir":"desc"}],
 "limit":10
}'
```

Each row is one question and supplies the asker key, thread keys, ordering fields, text, and timestamp needed by the remaining steps.

**Step 2 — fetch the matching LLM answers**

Collect the distinct `progress_record_bid` values from Step 1 and pass them into `in`:

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_generated_blocks",
 "where":[
   {"field":"type","op":"=","value":322},
   {"field":"progress_record_bid","op":"in","value":["<prb-1>","<prb-2>","..."]}],
 "select":["generated_content","progress_record_bid","outline_item_bid","position","created_at"],
 "order_by":[{"field":"position","dir":"asc"},{"field":"created_at","dir":"asc"}],
 "limit":100,
 "offset":0
}'
```

Page answer candidates with offsets `100`, `200`, and so on until a page returns fewer than 100 rows. Apply `tables.md#follow-up-qa-relationship` exactly: partition both result sets by its thread keys, then follow its position and generation-order precedence for each question. Do not replace the owned relationship with a stricter positional predicate.

**Step 3 — fetch permitted identity fields for the askers**

Collect the distinct `user_bid` values from Step 1 (dedup, max 50) and execute Recipe 24A.

Join these rows to Step 1 by `user_bid`. The protocol behavior for returned identity fields is defined by `dsl.md`; disclosure and presentation decisions are defined only by `privacy-and-presentation.md`.

**Step 4 — assemble and present (client-side)**

Assemble the question, matched answer, asker lookup row, lesson context, and timestamps. Pass that internal result to `privacy-and-presentation.md`; that file alone decides masking, identifier replacement, timestamp formatting, and the final answer shape. The default row-level label includes the returned privacy-safe nickname and masked identity. If the user explicitly requests anonymous output, skip Step 3 and use ordinal labels only.

If Use B in `privacy-and-presentation.md` permits an exact reverse lookup, execute Recipe 24B before Step 1 and use the resulting `user_bid` as the Step-1 filter. Query validation remains governed by the restricted identity-table grammar in `dsl.md`, and disclosure remains governed by `privacy-and-presentation.md`.

### Recipe 23 — Follow-up questions per lesson

Where are learners actually asking? Group `type = 321` by `outline_item_bid` to find which lessons drive follow-up traffic:

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"learn_generated_blocks",
 "where":[{"field":"type","op":"=","value":321}],
 "select":["outline_item_bid"],
 "group_by":["outline_item_bid"],
 "aggregate":[
   {"fn":"count","alias":"asks"},
   {"fn":"count_distinct","field":"user_bid","alias":"askers"}],
 "order_by":[{"field":"asks","dir":"desc"}],
 "limit":50
}'
```

> Translate each `outline_item_bid` to "Lesson X.Y: \<title\>" via the `shifu-cli.py show <bid>` outline cache before presenting. High-ask lessons are usually candidates for content reinforcement (more concrete examples / explicit interaction). Low-ask lessons are often either very clear *or* skipped — cross-reference with `learn_progress_records` to tell which.

## Identity Lookup

These are the only identity-query recipes. Use Recipe 24A only for learner IDs already obtained from a legitimate course-scoped query, and use Recipe 24B only for an exact phone number or email supplied by the user. The restricted grammar and server masking remain authoritative in `dsl.md`; apply `privacy-and-presentation.md` before displaying any result.

Never filter by nickname, run a fuzzy identity search, or enumerate users to discover a target. If neither an already known `user_bid` nor an exact user-supplied phone number or email is available, do not run an identity query.

### Recipe 24A — Resolve permitted identity for known learner IDs

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"user_users",
 "where":[{"field":"user_bid","op":"in","value":["<u-bid-1>","<u-bid-2>","..."]}],
 "select":["user_bid","nickname","user_identify"],
 "limit":50
}'
```

### Recipe 24B — Resolve one learner from an exact phone number or email

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '{
 "table":"user_users",
 "select":["user_bid","nickname","user_identify"],
 "where":[{"field":"user_identify","op":"=","value":"<exact-phone-or-email>"}],
 "limit":1
}'
```

Keep the resolved `user_bid` internal and use it only to anchor the requested course analysis.
