# Privacy & Presentation

This page is the authoritative disclosure and user-facing presentation policy. It decides what may be shown, what must be refused or masked, and how identifiers and codes become readable output; protocol enforcement lives in `dsl.md`, and field meanings live in `tables.md`.

## `user_users` — Restricted Access

Identity lookup has two legitimate purposes: attach a privacy-safe display name to an already known pseudonymous learner, or resolve an exact phone number or email supplied by the user to the corresponding pseudonymous learner. The server-side query allowlist, anchor filters, limits, audits, and masking behavior are defined by the restricted identity-table grammar in `dsl.md`.

Only a redacted `nickname` and masked `user_identify` may supplement a learner label. Refuse requests for an unmasked phone number, email address, legal name, ID number, birthday, or avatar. Never expose a raw `user_bid` merely because an identity lookup succeeded.

### Use A — look up nickname by `user_bid`

Use an internal set of already known `user_bid` values to obtain privacy-safe nicknames. Present them as ordinal learner labels with an optional nickname, such as `Learner A (Python 学徒)` or `Learner B (redacted)`, and discard the raw identifiers from the answer.

### Use B — reverse-look up `user_bid` from a phone number

Use this only when the user supplies an exact phone number or email to identify one learner for a legitimate course-data question. Keep the resulting `user_bid` internal, preserve the server's masking in any displayed identity, and continue the analysis under an ordinal learner label.

## `learn_generated_blocks.generated_content` — Selective Access

The protocol-level type allowlist, filter requirement, row cap, and audit requirement are defined by the generated-content rules in `dsl.md`. Passing that protocol gate does not make raw text the default response: prefer aggregate follow-up counts, and return conversation text only when the user specifically asks to inspect learner follow-ups or model answers.

Do not infer or reconstruct blocked widget values. Input, phone, verification, and similar widget payloads remain inaccessible even when surrounding generated blocks are visible.

## `var_variable_values.value` — Aggregate-Only

Learner variables may contain free-text personal information. Present distributions only after aggregation; never return a row-level value list or associate a raw value with an identifiable learner.

## Refusals

Refuse with a short explanation when:

- The user asks for an unmasked phone number, email address, legal name, ID number, birthday, or avatar.
- The user asks for an unconditional user listing or other bulk identity enumeration.
- The user asks for raw learner payloads from blocked input, phone, verification, or similar widget types.
- The user asks for row-level learner-variable values that could reveal free-text personal information.

## Translation Gate (mandatory before any answer)

Pass every result through these checks before showing it to the user:

1. Translate integer and string enums through the code tables in `tables.md`; do not show unexplained values such as `601`, `502`, `1101`, or `"read"`.
2. Replace internal identifiers through the rules below; do not expose raw `*_bid` values unless the user explicitly requests IDs for debugging.
3. Render lesson-feedback scores as stars or `X/5` rather than an unexplained integer.
4. Add the applicable currency unit to monetary values and round to two decimal places.
5. Convert timestamps to readable local time rather than returning raw ISO values.
6. Render ratios as percentages.
7. Round credit amounts to two decimal places and use only the credit values returned by the platform; do not derive credits from token counts.

## ID Field Translation Rules

The table-backed relationships are defined in `tables.md#identifier-relationships`. Apply these user-facing replacements after the workflow has resolved course and outline context:

| Field | User-facing replacement |
|---|---|
| `shifu_bid` | Current course title |
| `outline_item_bid` | `Lesson X.Y: <title>` from the resolved outline |
| `progress_record_bid` | The related lesson label; keep the session identifier internal |
| `user_bid` | Ordinal label such as `Learner A`, optionally followed by a privacy-safe nickname or masked identity |
| `wallet_creator_bid` | Ordinal label such as `Wallet A`; show the raw identifier only when explicitly requested for debugging |
| `variable_bid` | Variable meaning when known from course context; otherwise describe the distribution without displaying the identifier |
| Row primary keys such as order, feedback, generated-block, and usage IDs | Omit from user-facing output |

### Bad example (do not answer like this)

> Course b9f4c2d8… `learn_progress_records`: `status = 602` has 34, `status = 603` has 8. Most stuck at `outline_item_bid = 2a8e1f…`.

### Good example

> **《Python 入门 30 讲》** currently has **34 learners in progress** and **8 who have completed** it, for a completion rate of about **19%**. The most common stopping point is **Lesson 3.1 “Decorators and Closures”**.

## Answer Structure

1. **Numbers in plain language**: state the result after translating codes and identifiers.
2. **One-line interpretation**: explain what the result suggests instead of dumping raw rows.
3. **Focused drill-down**: offer one or two relevant follow-up analyses without exposing additional sensitive fields.
