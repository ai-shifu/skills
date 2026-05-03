# Output Contract

The skill's final, persistent deliverable is a single `course.json` file (see [course-directory-spec.md](course-directory-spec.md) for the schema). Every Phase contributes specific fields of that file. Phase 1–4 also produce in-context intermediate structures (segments, transfer signals, audit reports) that are not persisted unless the user explicitly captures them — they exist only for the next phase to consume.

## Final Deliverable: `course.json`

```jsonc
{
  "version": "1.0",
  "course":            { ... },              // Phase 2 fills title / description / course_prompt / language
  "structure":         [ ... ],              // Phase 2 (chapter / lesson hierarchy + ordering)
  "items":             { "<bid>": { ... } }, // Phase 3 fills markdownflow_prompt + per-item metadata
  "global_variables":  [ ... ],              // Phase 2/3 fills based on Phase 1 transfer signals
  "deployment":        { ... }               // Phase 5 fills shifu_bid + revisions + timestamps
}
```

The skill never produces independent files like `lesson_mdf_scripts.json` or `course_index.json` as final output. Those names refer to in-context Phase products, materialized into specific `course.json` fields by the time Phase 5 runs.

## Phase → course.json Field Map

### Phase 2 (Orchestration) writes

| course.json field | Source (Phase 2 logic) |
|---|---|
| `course.title` | Course-level title resolved from input or generated |
| `course.description` | Short summary |
| `course.course_prompt` | Course-level system prompt (governs AI role across all lessons) |
| `course.language` | Resolved per `language-resolution.md` |
| `structure[]` | Recursive tree describing chapter / lesson hierarchy. Each node carries an `outline_item_bid` (placeholder `new:<seq>` until imported). |
| `global_variables[]` | Cross-lesson variables (`{name, collected_in, used_in, effect_scope}`) |

### Phase 3 (Generation) writes

For each `outline_item_bid` referenced by `structure`, Phase 3 populates `items.<bid>`:

| `items.<bid>` field | Required | Source |
|---|---|---|
| `type` | yes | `"chapter"` or `"lesson"` |
| `title` | yes | Display name |
| `markdownflow_prompt` | yes | Full MarkdownFlow text (string; may be empty for placeholder containers) |
| `core_question` | optional | Single sentence Phase 1 captured for this item |
| `used_variables` | optional | Variable names introduced in this `markdownflow_prompt` |
| `depends_on_lessons` | optional | List of `outline_item_bid` values whose variables this item references |
| `source_span_map` | optional | Phase 1 traceability info, list of `{source_id, start, end}` |

### Phase 5 (Deployment) writes

After successful `import` or `push`, Phase 5 ensures `deployment` is populated:

| `deployment` field | Description |
|---|---|
| `shifu_bid` | Course bid (server UUID) |
| `deployed_url` | `https://app.ai-shifu.cn/c/<shifu_bid>?preview=true` |
| `draft_last_pushed_at` | ISO 8601 timestamp |
| `draft_pulled_at_revision` | `{outline_item_bid: int}` map for optimistic locking |
| `published_at` | ISO 8601 timestamp of last server publish (read-only from local code) |

## In-Context Intermediate Products (Phase 1–4)

These structures live only in the agent's context. They are inputs to subsequent phases, not files on disk.

### Phase 1 (Segmentation)

- `structured_segments_json[]` — ordered semantic units (`segment_id`, `segment_type`, `core_point`, `preserve_block`, `source_span`).
- `preserve_block_index[]` — indices of code / image / table blocks that must be preserved verbatim.
- `lesson_cut_candidates[]` — proposed lesson boundaries (`segment_ids`, `core_question`).
- Transfer signals — `learner_hook` / `evidence_type` / `visual_cue` / `concept_conflict` / `boundary_cue` / `action_cue` / `density_cue` / `quote_cue` / `visual_text_pair_cue` / `interaction_intent_cue` / `compare_cue`.

These feed Phase 2 / 3. Their content ends up implicitly inside `items.<bid>.markdownflow_prompt` (the actual teaching script) and `items.<bid>.source_span_map` (traceability) — they do not appear as standalone fields in `course.json`.

### Phase 4 (Optimization)

- `risk_and_issue_report` — `{overall_risk, blocking_issues, suggestions, coverage_status}`.
- `change_list` — `[{issue_class, change}]`.

These are surfaced to the user as part of the Phase 4 audit response and used to mutate `items.<bid>.markdownflow_prompt` and surrounding fields. They are not persisted in `course.json` itself.

## Minimal Final Output Example

```json
{
  "version": "1.0",
  "course": {
    "title": "Core Loop Setup",
    "description": "Set up a stable production loop.",
    "course_prompt": "你是一位实践型导师...",
    "language": "zh-CN"
  },
  "structure": [
    {
      "outline_item_bid": "new:c01",
      "children": [
        { "outline_item_bid": "new:l01", "children": [] }
      ]
    }
  ],
  "items": {
    "new:c01": {
      "type": "chapter",
      "title": "Core Loop Setup",
      "markdownflow_prompt": ""
    },
    "new:l01": {
      "type": "lesson",
      "title": "Goal & Choice",
      "core_question": "What makes this loop stable in production?",
      "markdownflow_prompt": "## Objective\n...\n?[%{{learner_goal}} Option A | Option B]\n...",
      "used_variables": ["learner_goal"],
      "depends_on_lessons": [],
      "source_span_map": [{ "source_id": "doc-1", "start": 120, "end": 286 }]
    }
  },
  "global_variables": [
    {
      "name": "learner_goal",
      "collected_in": "new:l01",
      "used_in": ["new:l01"],
      "effect_scope": "local"
    }
  ],
  "deployment": {}
}
```

After running `import --new --course-dir ./`, the CLI auto-pulls and the file becomes:

```json
{
  "version": "1.0",
  "course": { /* unchanged */ },
  "structure": [
    {
      "outline_item_bid": "8f1a...real-uuid",
      "children": [
        { "outline_item_bid": "3c92...real-uuid", "children": [] }
      ]
    }
  ],
  "items": {
    "8f1a...real-uuid": { "type": "chapter", "title": "Core Loop Setup", "markdownflow_prompt": "" },
    "3c92...real-uuid": { /* same fields, real bid as key */ }
  },
  "global_variables": [
    { "name": "learner_goal", "collected_in": "3c92...real-uuid", "used_in": ["3c92...real-uuid"], "effect_scope": "local" }
  ],
  "deployment": {
    "shifu_bid": "abc123-real-shifu-uuid",
    "deployed_url": "https://app.ai-shifu.cn/c/abc123-real-shifu-uuid?preview=true",
    "draft_last_pushed_at": "2026-05-03T08:00:00Z",
    "draft_pulled_at_revision": { "8f1a...real-uuid": 1, "3c92...real-uuid": 1 },
    "published_at": null
  }
}
```

## Delivery Guarantees

- **Stable schema across reruns.** The same input course material yields the same `course.json` field shape; only string content varies.
- **Deterministic placeholder bids.** Phase 2/3 should generate consistent placeholders (`new:c01`, `new:l01` …) so reruns produce stable diffs before `import`.
- **Partial rerun support.** Updating one `items.<bid>.markdownflow_prompt` is a localized change; `push` will diff and submit only that update via the platform's optimistic-locking endpoint.
- **No lost fidelity at sync boundary.** `pull` writes the same structure that `push` reads; round-trip pull → push is a no-op in the absence of edits.

## Wire Format Note

The platform's `/import` and `/export` endpoints use a different wire format with field names like `llm_system_prompt`, `outline_items[].content`, `outline_items[].type` (int 400 / 401), and a separate `structure` shape. See [import-json-format.md](import-json-format.md) for that wire format. The CLI's `pull` / `push` / `import` / `export` commands handle local ↔ wire translation transparently; agents and authors should think only in terms of `course.json` field paths.
