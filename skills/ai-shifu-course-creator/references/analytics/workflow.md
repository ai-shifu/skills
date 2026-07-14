# Course Analytics

## Analytics

This page is the sole orchestration authority for post-deployment analytics. It controls stage order and handoffs while delegating planning, query bodies, privacy, schema, and command details to their owning references.

### CLI-Only Rule

All analytics traffic goes through `scripts/shifu-cli.py`. Never construct raw HTTP requests, read tokens directly, or compose authentication headers by hand.

### Workflow

1. **Resolve credentials** — complete `../authentication.md` and stop if authentication cannot be established.
2. **Plan the question** — use `overview.md` to select one canonical recipe, define the metric grain, and identify whether course, outline, or learner context is required.
3. **Resolve the course** — use Course Metadata Recipe 0a (`find-title`) when the user supplies a current title keyword, and use Recipes 0b–0c only when the `shifu_bid` is already known. Use `list` when enumerating owned courses. Historical or superseded title lookup is unsupported; ask for a current title keyword or known `shifu_bid` instead.
4. **Resolve the outline when needed** — use `show` before any lesson-level analysis and retain the outline-to-title mapping for presentation.
5. **Load the execution contract** — read the selected section of `recipes.md`; it names the lower-level DSL, table, privacy, and CLI contracts required by that scenario.
6. **Execute** — run the prescribed CLI command, inspect its complete response, and correct only errors covered by the owning command or DSL contract.
7. **Present** — pass the result through `privacy-and-presentation.md`, add the metric definition and relevant data limitation, then offer only focused drill-downs.

### References

- `overview.md` — intent classification and recipe selection.
- `recipes.md` — complete scenario query and command templates.
- `privacy-and-presentation.md` — disclosure, refusal, masking, identifier translation, and answer format.
- `dsl.md` — query-body grammar and validation errors.
- `tables.md` — table row grain, fields, enums, relationships, and availability facts.
- `../cli/cli-reference.md` — command arguments, output, exit codes, and side effects.

### Validation

- Authentication was resolved through `../authentication.md`.
- The course identity is current, and lesson-level results have an outline mapping.
- The selected recipe matches the user's question and states the metric grain.
- An order request distinguishes 下单人数, 成功下单, 付费人数, 订单数, and 退款 and uses the exact status filter and row grain owned by the selected recipe.
- Any adapted body conforms to `dsl.md` and uses fields defined by `tables.md`.
- Sensitive access and every user-facing value pass `privacy-and-presentation.md`.
- Row-level follow-up output includes a privacy-safe nickname and masked identity by default, or ordinal labels only when the user explicitly requests anonymous output.
- Credit, revenue, learner count, and attempt count remain distinct metrics.
- When CLI output appears garbled in a shell tool, redirect it to a UTF-8 file and read that file as described in `../cli/cli-reference.md#cli-output--encoding`.
