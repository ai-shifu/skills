# Platform Wire Format (legacy import / export JSON)

> **Note**: This document describes the **platform wire format** — what the AI-Shifu API accepts at the legacy `/import` endpoint and returns from `/export`. **It is not the local format that authors write.** For the local single-file format, see [course-directory-spec.md](course-directory-spec.md).
>
> Most agents and authors should never need to read or write the wire format directly. The CLI's `pull` and `push` commands translate between the local `course.json` schema and this wire format transparently.

## When this format still appears

- The legacy `import --json-file <file.json>` and `import --legacy-course-dir <dir>` paths still produce / consume this format. New code should use the recommended `--course-dir <new-course-dir>` (single-file `course.json` inside) instead.
- The `build` command (legacy) still emits this format from an old course directory.
- The platform's `GET /shifus/<bid>/export` endpoint returns this exact JSON document (used by `demo_update.py` and by `cmd_pull` internally).
- ADR-001 §D9 explains why this wire format is unsuitable for direct editing of existing courses (the `import` endpoint regenerates all `outline_item_bid` values, breaking client-side bid stability).

## Schema

```json
{
  "version": "1.0",
  "exported_at": "2026-05-03T08:00:00Z",
  "shifu": {
    "shifu_bid": "<UUID>",
    "title": "Course Title",
    "description": "Description",
    "keywords": "comma,separated,or,array",
    "avatar_res_bid": "",
    "llm": "",
    "llm_temperature": 0,
    "llm_system_prompt": "<full course-level prompt>",
    "ask_enabled_status": 5101,
    "ask_llm": "",
    "ask_llm_temperature": 0,
    "ask_llm_system_prompt": "",
    "ask_provider_config": "{}",
    "price": 0.0
  },
  "outline_items": [
    {
      "outline_item_bid": "<UUID>",
      "title": "Item Title",
      "type": 400,
      "hidden": 0,
      "parent_bid": "",
      "position": "01",
      "prerequisite_item_bids": "",
      "llm": "",
      "llm_temperature": 0,
      "llm_system_prompt": "",
      "ask_enabled_status": 5101,
      "ask_llm": "",
      "ask_llm_temperature": 0,
      "ask_llm_system_prompt": "",
      "content": "<MarkdownFlow text>"
    }
  ],
  "structure": {
    "bid": "<shifu_bid>",
    "id": 0,
    "type": "shifu",
    "children": [
      {
        "bid": "<chapter_outline_item_bid>",
        "id": 0,
        "type": "outline",
        "children": [
          {
            "bid": "<lesson_outline_item_bid>",
            "id": 0,
            "type": "outline",
            "children": [],
            "child_count": 0
          }
        ]
      }
    ]
  }
}
```

## Field Notes

- **`shifu.llm_system_prompt`**: course-level prompt (called `course_prompt` locally, `system_prompt` in the `/shifus/<bid>/detail` endpoint).
- **`outline_items[].type`** (int): platform access-level encoding.
  - `400` = `"guest"` — typically used for top-level chapters.
  - `401` = `"trial"` — typically used for child lessons.
  - `402` = `"normal"` — paid content.
  Local schema collapses this into `"chapter"` (for 400) and `"lesson"` (for 401/402).
- **`outline_items[].parent_bid`**: empty string for top-level chapters; chapter's `outline_item_bid` for nested lessons.
- **`outline_items[].content`**: the MarkdownFlow text. This is the field that maps to local `items.<bid>.markdownflow_prompt`.
- **`outline_items[].position`**: server-managed ordering string (e.g. `"01"`, `"0102"`); not edited by clients.
- **`structure`**: tree mirroring the outline hierarchy. Useful for human inspection but redundant with `outline_items[].parent_bid` for reconstruction. The `id` and `child_count` fields are server-internal and should be discarded by clients.

## Behavior Quirks (relevant for ADR-001)

- The `/import` endpoint **completely regenerates** every `outline_item_bid` and does not return a client-side ID → server-side ID mapping. ADR-001 §D9 mandates an immediate `pull` after `import` to capture the new bids.
- The `/import` endpoint accepts a `shifu_bid` field in the input. If present and matches an existing shifu, all old outline_items are soft-deleted (`deleted=1`) and rebuilt — meaning even outline_item_bids that the client *had previously pulled* get replaced. This is why the new `cmd_import` only accepts `--new` and rejects updates to existing courses.
- The `/export` endpoint is a binary file download (`send_file`), not a JSON envelope (`{code, message, data}`). The CLI's `_fetch_export` helper handles this asymmetry.
