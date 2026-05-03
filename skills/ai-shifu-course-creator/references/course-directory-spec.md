# Course File Specification

A course is represented locally as a single `course.json` file. The platform is the authoritative source; the local file is an ephemeral working copy that can be regenerated at any time via `pull`.

## File Layout

```
<any-path>/course.json
```

That's it. No accompanying directory structure, no `lessons/*.md`, no `system-prompt.md`. All long-text content (course-prompt and every outline_item's MarkdownFlow script) is embedded inline as JSON strings.

For human editing comfort, the CLI provides `extract` / `embed` to round-trip a single field into a standalone `.md` file and back. These are on-demand convenience tools, not the primary editing workflow.

## Schema

```jsonc
{
  "version": "1.0",

  "course": {
    "title": "...",
    "description": "...",
    "course_prompt": "<full course-level prompt, with embedded \\n>",
    "language": "zh-CN"
  },

  "structure": [
    {
      "outline_item_bid": "<server uuid or 'new:c01' placeholder>",
      "children": [
        { "outline_item_bid": "<server uuid>", "children": [] },
        { "outline_item_bid": "<server uuid>", "children": [] }
      ]
    }
  ],

  "items": {
    "<server outline_item_bid>": {
      "type": "chapter",
      "title": "...",
      "core_question": "...",
      "markdownflow_prompt": "<full MarkdownFlow script, with embedded \\n; may be empty>",
      "used_variables": [],
      "depends_on_lessons": [],
      "source_span_map": []
    },
    "<another outline_item_bid>": {
      "type": "lesson",
      "title": "...",
      "core_question": "...",
      "markdownflow_prompt": "...",
      "used_variables": [],
      "depends_on_lessons": [],
      "source_span_map": []
    }
  },

  "global_variables": [
    { "name": "...", "collected_in": "<outline_item_bid>", "used_in": ["<outline_item_bid>"], "effect_scope": "local|cross_lesson" }
  ],

  "deployment": {
    "shifu_bid": "<server uuid>",
    "deployed_url": "https://app.ai-shifu.cn/c/<shifu_bid>?preview=true",
    "draft_last_pushed_at": "2026-05-03T08:00:00Z",
    "draft_pulled_at_revision": { "<outline_item_bid>": 12, "<outline_item_bid>": 7 },
    "published_at": "2026-05-01T08:00:00Z"
  }
}
```

## Field Semantics

### `course`

| Field | Required | Description |
|---|---|---|
| `title` | yes | Course title (non-empty string). |
| `description` | optional | Short description. |
| `course_prompt` | optional | Course-level prompt, governs the AI's role and teaching style across all lessons. Maps to platform wire field `shifu.llm_system_prompt`. May be empty. |
| `language` | optional | BCP-47 language tag (e.g. `zh-CN`, `en-US`). Free-form; not enforced by the platform. |

### `structure` (recursive tree)

A tree describing chapter / lesson hierarchy and ordering. Each node carries an `outline_item_bid` and a `children` array (possibly empty). Top-level nodes are conventionally chapters; their children are lessons. The platform does not enforce a strict depth limit, but typical courses use exactly two levels.

The structure shape is identical (modulo the field name `outline_item_bid` ↔ wire `bid`) to the platform's `ReorderOutlineDto` schema, which makes `pull` / `push` reorder nearly trivial.

### `items` (dict keyed by outline_item_bid)

Every node referenced in `structure` MUST appear as a key in `items`. Conversely, every key in `items` MUST appear somewhere in `structure`. The validator (`shifu-cli validate`) enforces both directions.

| Field | Required | Description |
|---|---|---|
| `type` | yes | `"chapter"` (platform wire 400 / "guest") or `"lesson"` (platform wire 401 / "trial"). |
| `title` | yes | Display name. |
| `markdownflow_prompt` | yes | MarkdownFlow content as a string (may be empty). Note that platform allows chapters to carry MarkdownFlow content too, not just lessons. |
| `core_question` | optional | One sentence summarizing what this item teaches; used by Phase 1/2 audit. |
| `used_variables` | optional | Variable names introduced in this item's MarkdownFlow. |
| `depends_on_lessons` | optional | List of `outline_item_bid` values this item depends on (for cross-lesson variable carry-over). |
| `source_span_map` | optional | Phase 1 segmentation traceability info. |

### `global_variables`

Optional list of cross-lesson variables. Each entry: `{name, collected_in, used_in, effect_scope}`.

### `deployment`

Synchronization metadata. Maintained by `pull` / `push`; users normally do not edit this section by hand.

| Field | Description |
|---|---|
| `shifu_bid` | Course bid on the server. Empty / missing for a freshly-authored course before `import`. |
| `deployed_url` | Convenience URL for preview. |
| `draft_last_pushed_at` | ISO 8601 timestamp of the last successful `push`. |
| `draft_pulled_at_revision` | `{outline_item_bid: int}` map. The CLI captures each item's draft revision at `pull` time and uses it as `base_revision` during the next `push` (optimistic locking on MarkdownFlow content; see ADR-001 §D6). |
| `published_at` | ISO 8601 timestamp of the most recent server-side `publish`, captured at `pull` time. Local code does not modify this. |

## Placeholder IDs

For brand-new courses (before the first `import`), or when adding new items to an existing course (before `push`), the CLI accepts placeholder `outline_item_bid` strings (convention: `new:<seq>`, e.g. `new:c01`, `new:l01`).

The specific format is purely a local convention — the platform completely ignores any `outline_item_bid` value the client submits and assigns its own UUID. After `import` or `add-chapter` / `add-lesson`, the CLI rewrites the local `course.json` to replace placeholders with real bids:

- **`import` flow**: server assigns all bids in one shot but does not return the mapping; CLI auto-pulls the entire course back to capture them.
- **`push` flow**: each `add-chapter` / `add-lesson` call returns its single new bid; CLI updates the local file in-place.

After either operation, no `new:*` strings remain in the file. See ADR-001 §D8 / §D9.

## Wire Format vs Local Format

| Local `course.json` | Platform wire (e.g. `import` payload, `export` response) |
|---|---|
| `course.title` | `shifu.title` |
| `course.description` | `shifu.description` |
| `course.course_prompt` | `shifu.llm_system_prompt` |
| `items.<bid>.type` (`chapter` / `lesson`) | `outline_items[].type` (int 400 / 401) |
| `items.<bid>.title` | `outline_items[].title` |
| `items.<bid>.markdownflow_prompt` | `outline_items[].content` |
| `structure[*].outline_item_bid` | `outline_items[].outline_item_bid` (and the `bid` field in tree responses) |

The CLI handles all wire ↔ local translation. Authors should never need to read or write the wire format directly.

## Constraints (validator-enforced)

The `shifu-cli validate --course-dir <course-dir> --mode push|import` command checks:

- All six top-level fields present (`version`, `course`, `structure`, `items`, `global_variables`, `deployment`).
- `course.title` is non-empty.
- `course.course_prompt` is a string (may be empty).
- `structure` is a recursive tree; every node has a string `outline_item_bid` and an array `children`.
- Each `outline_item_bid` appears at most once across the entire structure tree.
- The set of bids in `structure` equals the set of keys in `items` (no orphans, no dangling references).
- Each `items.<bid>.type` is `"chapter"` or `"lesson"`.
- Each `items.<bid>.markdownflow_prompt` is a string.
- In `--mode push`: no placeholder bids (`new:*`) anywhere; `draft_pulled_at_revision` keys must be present in `items`.
- In `--mode import`: placeholders are allowed (they signal "create this on the server").

## MarkdownFlow Notes

- HTML comments (`<!-- ... -->`) are silently dropped by the platform's MarkdownFlow parser. Write any authoring notes as inline plain text or keep them outside the `markdownflow_prompt` field (e.g. in a separate notes file under `design/`).
- Chapters are allowed to carry MarkdownFlow content. Even though typical authoring puts content only in lessons, the platform data model treats every outline_item the same way.
