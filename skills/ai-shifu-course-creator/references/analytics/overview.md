# Analytics Query Planning

This page is the intent-to-execution decision index. It selects the appropriate recipe and required context; it does not repeat the route workflow, DSL grammar, table schema, privacy policy, or CLI command contract.

## When to Use

Use analytics planning for observed facts from an existing course, including learner progress, stopping points, orders, revenue, ratings, follow-up activity, credit consumption, audience distributions, learner-level analysis, and current course-title resolution.

Do not use analytics merely to count or list courses, design a course, choose lesson structure, or author content. Those tasks have no observed learner or business dataset to query.

## Quick Question → Recipe Lookup

Use this index to choose execution guidance without restating its query body:

| User intent | Canonical execution | Context required before execution |
|---|---|---|
| Resolve a current published or draft title | Course Metadata Recipes 0a–0c in `recipes.md`, or the `find-title` command | A title keyword or known course identifier |
| Get a high-level course dashboard | Course Overview Recipe 0d | Resolved course |
| Measure progress, completion, or stopping points | Progress Recipes 1–2 | Resolved course; outline mapping for lesson results |
| Measure orders, revenue, funnel state, or payment channel | Order Recipes 3–6 | Resolved course; explicit paid/free/refund intent |
| Find low-rated lessons or compare ratings by learning mode | Rating Recipe 7 | Resolved course and outline mapping |
| Inspect credit consumption | Credit Recipes 8–13 | Resolved course; requested date scope and any model, provider, scene, usage-type, or wallet breakdown |
| Count active learners | Active Learner Recipe 14 | Resolved course |
| Summarize learner-variable distributions | Audience Profile Recipe 15 | Resolved variable meaning and privacy gate |
| Rank learner progress | Per-Learner Recipe 16 | Resolved course and privacy gate |
| Count or inspect follow-up questions and answers | Follow-up Recipes 17–23 | Resolved course; outline mapping for lesson results; privacy gate for raw text or identity |

## Picking the Right DSL

1. Start from the matching scenario in `recipes.md` rather than inventing a table or query shape.
2. Verify any adaptation against `dsl.md` and the fields in `tables.md`.
3. If the plan touches identity, generated text, learner variables, or any raw identifier, include `privacy-and-presentation.md` before execution and presentation.
4. If no recipe matches, construct the smallest query supported by the grammar and data dictionary, then document the chosen metric grain.

## Decision Rules

- A title supplied by the user is a lookup key, not proof of the current course name; resolve it before downstream analysis.
- A lesson-level result requires an outline mapping so identifiers can become readable lesson labels.
- Credit consumption uses the dedicated credit recipes while the daily DSL summary remains unavailable.
- Cross-course analysis is a set of course-scoped executions merged after retrieval, not a cross-course DSL join.
- A request for one learner's activity still passes through the same identity and disclosure policy as an aggregate query.

## Error Codes the CLI May Surface

For DSL validation failures `11002` through `11007`, use the canonical meanings in `dsl.md#validation-error-codes`. For command invocation, transport, authentication, stdout, and exit-code behavior, use `../cli/cli-reference.md`; this planning page does not redefine those contracts.

## Scope Reminder

Plan each analytics execution around one resolved course. If the user asks for a portfolio comparison, run the selected recipe once for each course and merge only metrics with the same definition and grain.

## Common Pitfalls (read this before your first query)

- **Follow-up activity**: choose the follow-up recipes; do not substitute a generic learner-role count.
- **Credits**: choose Credit Recipes 8–13; do not reinterpret revenue or token fields as credits.
- **Audience variables**: choose Recipe 15 and aggregate before disclosure.
- **Learner identity**: choose the identity-aware follow-up path and delegate every disclosure decision to the presentation gate.
- **Unknown schema names or fields**: stop and check `tables.md` and `dsl.md` rather than trying sound-alike names.
- **Repeated progress attempts**: use a recipe whose grain matches the question and state the duplicate-attempt limitation when relevant.

## What Lives Where

- `recipes.md` owns complete scenario query and command templates.
- `privacy-and-presentation.md` owns disclosure, masking, refusals, and user-facing translation.
- `dsl.md` owns query grammar and server validation.
- `tables.md` owns row grain, fields, enums, and data relationships.
- `../cli/cli-reference.md` owns command syntax, output, exit codes, and side effects.
