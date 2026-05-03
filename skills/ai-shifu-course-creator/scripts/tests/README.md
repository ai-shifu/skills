# Tests

End-to-end smoke tests for [`shifu-cli.py`](../shifu-cli.py). Black-box: tests invoke the CLI as a subprocess; nothing is mocked.

## How to run

```bash
# Unit-only (no network, ~1 second). Run after every CLI change.
python3 test_main_flows.py

# Verbose
python3 test_main_flows.py -v

# Also run integration tests against the real platform (~25 seconds).
# Requires a valid SHIFU_TOKEN in {skillDir}/.env.
python3 test_main_flows.py --integration -v
```

Integration tests create temporary courses on the AI-Shifu platform and `archive` them in `tearDown`. Test course names start with "Smoke Test Course" so they are easy to identify if cleanup ever fails.

## Coverage matrix

The test labels map directly to the test plan tracked in [adr-001-test-scenarios.md](../../design/adr-001-test-scenarios.md):

| Class | Group | Network | What it verifies |
|---|---|---|---|
| `UnitFlows.test_M5_*` | main flow | no | `validate` accepts placeholders in import mode and real-only bids in push mode |
| `UnitFlows.test_M6_*` | main flow | no | `extract` / `embed` round-trip is byte-exact; `course_prompt` field is lowercase |
| `UnitFlows.test_E1_*` | boundary | no | duplicate `outline_item_bid` in structure → validator rejects |
| `UnitFlows.test_E2_*` | boundary | no | structure references a bid missing from `items` → validator rejects |
| `UnitFlows.test_E4_extract_*` | boundary | no | `extract` refuses to overwrite without `--force` |
| `IntegrationFlows.test_M1_*` | main flow | yes | full `import --new` → auto-pull → real bids; type distribution preserved |
| `IntegrationFlows.test_M2_*` | main flow | yes | `pull` writes complete schema with lowercase fields and revisions |
| `IntegrationFlows.test_M3_*` | main flow | yes | content `push` advances the server-side revision |
| `IntegrationFlows.test_M4_*` | main flow | yes | mixed edit (add lesson via placeholder) → `push` replaces placeholder with real bid |
| `IntegrationFlows.test_E4_pull_*` | boundary | yes | `pull` refuses to overwrite without `--force-overwrite` |
| `IntegrationFlows.test_R1_*` | regression | yes | post-pull `push` is a no-op (`No changes; nothing to push`) |

## What is NOT covered (out of scope for smoke tests)

These belong in a separate concurrency / fault-injection harness:

- D1 / D2 / D3 — concurrent conflicts (need a second client)
- D4 — publish does not change bids (writes to live state)
- G1 / G2 / G3 — server 5xx during import / push (needs HTTP mocking)
- A3 — special character handling in `course_prompt` (needs careful character-set construction)

## Adding new tests

The test fixture `minimal_valid_course()` produces a 1-chapter / 2-lesson course with all required fields and lowercase field names. Use it as the starting point for new fixtures and modify in-place rather than reconstructing from scratch.

For new integration tests that create courses, **always** append the new `shifu_bid` to `self.created_shifu_bids` so the `tearDown` can archive it.
