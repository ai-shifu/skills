# Analytics Tables & Codes

This page is the authoritative analytics data dictionary. It owns table row grain, fields, enum meanings, relationships, and data-cardinality facts; it does not define DSL syntax, query sequences, privacy decisions, presentation rules, or CLI selection.

## 10 Tables at a Glance

| Table | Row grain | Key fields and invariants |
|---|---|---|
| `learn_progress_records` | One learner-lesson attempt record | `user_bid`, `outline_item_bid`, `progress_record_bid`, `status`, `created_at`; resets can leave more than one active record for the same learner and lesson |
| `learn_generated_blocks` | One generated or interactive block within a learner-lesson session | `user_bid`, `progress_record_bid`, `outline_item_bid`, `type`, `role`, `status`, `position`, `liked`, `generated_content` |
| `learn_lesson_feedbacks` | One lesson-feedback record | `user_bid`, `progress_record_bid`, `mode`, `score` |
| `order_orders` | One course order | `user_bid`, `status`, `payment_channel`, `paid_price` |
| `var_variable_values` | One stored learner-variable value | `user_bid`, `variable_bid`, `value`; values may contain free text |
| `shifu_user_archives` | One learner-course archive state | `user_bid`, `archived` |
| `bill_daily_usage_metrics` | One pre-aggregated creator/day/usage dimension | `stat_date`, `creator_bid`, `usage_scene`, `usage_type`, `provider`, `model`, `billing_metric`, `consumed_credits`, `record_count`; currently empty in production because its aggregation job is not registered |
| `user_users` | One global user identity row | `user_bid`, `nickname`, `user_identify`; this is the only table without course scope and its identity fields are sensitive |
| `shifu_published_shifus` | One published-course snapshot | `title`, `created_user_bid`, `created_at`, `updated_at`; the active row represents the current published title |
| `shifu_draft_shifus` | One draft-course snapshot | `title`, `created_user_bid`, `created_at`, `updated_at`; the active row represents the current editor title |

Nine tables carry course-scoped data; `user_users` is global. Raw token counts are not part of the creator analytics surface. Credit amounts appear either in the currently unpopulated daily summary or in the separate per-usage credit ledger result exposed by the platform.

## Field Capability Matrix

This matrix is the authority for which fields may appear in `select`, `where`, `group_by`, or `aggregate`. Aggregate suffixes abbreviate `count`/`count_distinct` as `count*`, numeric `count|sum|avg|min|max` as `numeric`, and timestamp `count|min|max` as `time`.

| Table | Selectable | Filterable | Groupable | Aggregatable |
|---|---|---|---|---|
| `learn_progress_records` | `progress_record_bid`, `user_bid`, `outline_item_bid`, `status`, `block_position`, `created_at`, `updated_at` | `user_bid`, `outline_item_bid`, `status`, `block_position`, `created_at`, `updated_at` | `user_bid`, `outline_item_bid`, `status`, `block_position` | `progress_record_bid` count*; `user_bid` count*; `outline_item_bid` count*; `created_at` time; `updated_at` time |
| `learn_generated_blocks` | `generated_block_bid`, `user_bid`, `progress_record_bid`, `outline_item_bid`, `type`, `role`, `status`, `position`, `liked`, `created_at`, `generated_content` | `user_bid`, `progress_record_bid`, `outline_item_bid`, `type`, `role`, `status`, `position`, `liked`, `created_at` | `user_bid`, `outline_item_bid`, `type`, `role`, `status`, `liked` | `generated_block_bid` count*; `user_bid` count*; `outline_item_bid` count*; `liked` numeric; `created_at` time |
| `learn_lesson_feedbacks` | `lesson_feedback_bid`, `user_bid`, `progress_record_bid`, `mode`, `score`, `created_at` | `user_bid`, `progress_record_bid`, `mode`, `score`, `created_at` | `user_bid`, `progress_record_bid`, `mode`, `score` | `lesson_feedback_bid` count*; `user_bid` count*; `score` numeric; `created_at` time |
| `order_orders` | `order_bid`, `user_bid`, `status`, `payment_channel`, `paid_price`, `created_at` | `user_bid`, `status`, `payment_channel`, `paid_price`, `created_at` | `user_bid`, `status`, `payment_channel` | `order_bid` count*; `user_bid` count*; `paid_price` numeric; `created_at` time |
| `var_variable_values` | `variable_value_bid`, `user_bid`, `variable_bid`, `value`, `updated_at` | `user_bid`, `variable_bid`, `value`, `updated_at` | `user_bid`, `variable_bid`, `value` | `variable_value_bid` count*; `user_bid` count*; `updated_at` time |
| `shifu_user_archives` | `user_bid`, `archived`, `archived_at`, `created_at` | `user_bid`, `archived`, `archived_at`, `created_at` | `user_bid`, `archived` | `user_bid` count*; `archived_at` time; `created_at` time |
| `bill_daily_usage_metrics` | `stat_date`, `creator_bid`, `usage_scene`, `usage_type`, `provider`, `model`, `billing_metric`, `consumed_credits`, `record_count` | `stat_date`, `usage_scene`, `usage_type`, `provider`, `model`, `billing_metric` | `stat_date`, `creator_bid`, `usage_scene`, `usage_type`, `provider`, `model`, `billing_metric` | `consumed_credits` numeric; `record_count` numeric; `stat_date` time; `billing_metric` count* |
| `user_users` | `user_bid`, `nickname`, `user_identify` | `user_bid`, `user_identify` | none | none |
| `shifu_published_shifus` | `title`, `created_user_bid`, `created_at`, `updated_at` | `title`, `created_user_bid`, `created_at`, `updated_at` | none | none |
| `shifu_draft_shifus` | `title`, `created_user_bid`, `created_at`, `updated_at` | `title`, `created_user_bid`, `created_at`, `updated_at` | none | none |

## Course title is "current published", not "history"

A single `shifu_bid` can have multiple saved snapshots over time. Interpret the rows by state rather than by whichever title happens to match a remembered string:

- **Current published title**: the active row in `shifu_published_shifus`; at most one active row exists for a course.
- **Current draft title**: the active row in `shifu_draft_shifus`; it may lead the published title after an editor rename.
- **Historical title**: a superseded snapshot; it is not the current course name.

The published title is the authority for a live course. A draft title is the authority only when no published row exists or when explicitly describing an unpublished editor state. A title that appeared in an earlier conversation turn is not evidence that it is still current.

## `learn_generated_blocks` type codes

`type` is an integer:

| Type | Name | Source | `generated_content` field class |
|---|---|---|---|
| `301` | `content` — system narration | Course template | Narration text |
| `311` | `mdcontent` — Markdown narration | Course template | Narration text |
| `312` | `mdinteraction` — interaction prompt | Course template | Prompt text |
| `321` | `mdask` — learner follow-up question | Learner input | Follow-up text |
| `322` | `mdanswer` — LLM answer to follow-up | LLM generated | Answer text |
| `303` input / `304` options / `309` phone / `310` checkcode and similar widget types | Learner input widgets | Learner input | Sensitive widget payload |

`role` is an integer: `1` = teacher or AI (`assistant`), `2` = learner (`user`), and `3` = UI widget. A learner role is not a follow-up subtype: `role = 2` also covers input, phone, verification, and other learner widgets, while `type = 321` specifically identifies a follow-up question.

`status` is an integer: `1` = current live row and `0` = a row superseded by reroll.

`position` is the block index within a `progress_record_bid`. `liked` is an integer: `-1` = thumbs down, `0` = no reaction, and `1` = thumbs up.

## Follow-up Q&A Relationship

Resolve follow-up pairs only within one already fixed `shifu_bid`. Inside that course scope, a question and candidate answer belong to the same thread when they share `progress_record_bid` and `outline_item_bid`.

`position` is the lesson anchor and ordering value, not a strictly increasing question-to-answer sequence. A `type = 321` question and its `type = 322` answer normally have the same position. Within one thread, first narrow candidates to the question's position when that value is present, then use generation order or `created_at` to choose the first answer after the question. If position is unavailable, use the same thread keys and later generation order alone.

Never require `answer.position > question.position`; that condition excludes the normal same-position pair.

This section owns the relationship fact. Scenario recipes own the queries and client-side pairing procedure.

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

## `order_orders.status`

| Code | Chinese | English |
|---|---|---|
| `501` | 已创建未付款 | Created, unpaid |
| `502` | 已付款 | Paid |
| `503` | 已退款 | Refunded |
| `504` | 待支付 | Pending payment |
| `505` | 已超时 | Timed out |

These codes describe distinct states rather than an ordered severity scale; numeric range comparisons do not express payment intent.

## `order_orders.payment_channel`

| Value | Meaning |
|---|---|
| `pingxx` | Ping++ aggregated channel such as WeChat Pay or Alipay |
| `stripe` | Stripe international card payment |
| `alipay` | Alipay native |
| `wechatpay` | WeChat Pay native |
| `open_api` | Order created through OpenAPI rather than a learner payment |
| `""` | Legacy data or manually imported activity order |

## `learn_lesson_feedbacks.mode`

| Value | Meaning |
|---|---|
| `"read"` | Reading mode |
| `"listen"` | Listening mode |

## `learn_lesson_feedbacks.score`

The score is an integer from 1 through 5.

## Feedback-to-Lesson Relationship

`learn_lesson_feedbacks` records the `progress_record_bid` of the rated learner session and does not expose `outline_item_bid`. Resolve a feedback row's lesson by matching its `progress_record_bid` to `learn_progress_records.progress_record_bid` and reading that progress row's `outline_item_bid`.

This section owns the relationship fact. Rating recipes own retrieval, client-side joins, and aggregation.

## `bill_daily_usage_metrics.usage_type`

| Code | Meaning |
|---|---|
| `1101` | LLM inference call |
| `1102` | TTS speech synthesis |

LLM follow-up generation and TTS audio generation are independent usage paths.

## `bill_daily_usage_metrics.usage_scene`

| Code | Meaning |
|---|---|
| `1201` | Author debugging |
| `1202` | Author, shared-teacher, or admin preview |
| `1203` | Learner production |

## `bill_daily_usage_metrics.billing_metric`

| Code | Meaning |
|---|---|
| `7451` | LLM input tokens |
| `7452` | LLM cache-hit tokens |
| `7453` | LLM output tokens |

The three billing metrics are components of one model's usage; a model-level total includes all three.

## `shifu_user_archives.archived`

| Code | Meaning |
|---|---|
| `0` | Active or enrolled |
| `1` | Archived from the learner's bookshelf |

## Identifier Relationships

These relationships define identifier meaning and row grain. User-facing replacement and masking belong to the presentation policy.

| Field | Data relationship |
|---|---|
| `shifu_bid` | Course identifier |
| `outline_item_bid` | Chapter or lesson identifier within a course outline |
| `progress_record_bid` | Learner-lesson session identifier linking progress, feedback, generated blocks, and credit detail |
| `user_bid` | Pseudonymous learner identifier shared across learner-scoped tables |
| `variable_bid` | Variable-definition identifier for a stored learner value |
| `order_bid` / `lesson_feedback_bid` / `generated_block_bid` / `daily_usage_metric_bid` | Row primary keys used for identity and deduplication |

## Data Trap — Duplicate rows in `learn_progress_records`

A learner can have multiple progress records for the same lesson after resetting or relearning. The rows represent attempts, not a unique learner-lesson final state. Counts at learner grain therefore differ from counts at attempt grain, and a lesson-completion count can include the same lesson more than once for one learner.

The analytics surface has no window-function result that selects the latest attempt for every learner and lesson. Any result that substitutes a distinct-learner count for final-state reconstruction must state that limitation.

## Three Independent "Amounts" — Never Mix

| Amount | Data source | Unit and payer | Availability |
|---|---|---|---|
| Course price or revenue | `order_orders.paid_price` | Currency paid by the learner to the creator | Queryable |
| Model-call credit consumption | Per-usage credit ledger; future daily summary in `bill_daily_usage_metrics.consumed_credits` | Creator account credits | Per-usage detail available; daily summary currently empty |
| Plan or credit-pack purchase | Internal billing data | Currency paid by the creator to recharge | Not exposed |

Credit values are account-credit amounts, not raw token counts, and do not require token-based re-derivation.

## Tables That Do NOT Exist (common wrong guesses)

Only the ten tables listed above are valid. These common guesses are not schema names:

| Wrong name | Canonical data source |
|---|---|
| `user_logs` / `logs` / `event_logs` | `learn_generated_blocks` for interaction blocks or `learn_progress_records` for progress attempts |
| `billing` / `usage` | `bill_daily_usage_metrics` for the defined daily-summary schema |
| `credits` / `credit_logs` | No DSL table for current per-usage credit detail |
| `users` | `user_users` |
| `lessons` / `courses` | Metadata snapshots for course titles or `learn_progress_records` for learner activity |
