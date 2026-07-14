# Course Directory Specification

This page is the authoritative filesystem and generated-payload schema. It owns file roles, JSON shapes, field meanings, read-only status, and mappings between local files and import data; it does not define command sequences, conflict recovery, course-authoring content, or analytics behavior.

## Directory Structure

```text
<course>/
  README.md              # Course title from the first heading
  course-description.md  # Learner-facing listing description
  course-prompt.md       # Course-level prompt text
  course-config.json     # Read-only course-attribute snapshot
  shifu-import.json      # Generated import payload
  structure.json         # Optional chapter and lesson structure
  .shifu-sync.json       # Auto-maintained local-to-cloud revision baseline
  lessons/
    lesson-01.md         # Teaching Prompt in MarkdownFlow
    lesson-02.md
    ...
  assets/
    image-manifest.json  # Auto-maintained image metadata
    raw/                 # Recommended source-image location
```

## assets/

`assets/` stores source images and the generated `image-manifest.json`. The build output ignores this directory; image uploads use the manifest as a durable local-to-platform mapping.

`image-manifest.json` schema:

```json
{
  "images": [
    {
      "local": "assets/raw/gradient-descent.heic",
      "remote": "https://res.ai-shifu.cn/abcd…",
      "alt": "梯度下降三步示意",
      "uploaded_at": "2026-05-23T08:42:31Z",
      "bytes": 612345,
      "original_bytes": 4521000,
      "mime": "image/jpeg",
      "filename": "gradient-descent-1a2b3c4d.jpg"
    },
    {
      "source_url": "https://example.com/diagram.png",
      "remote": "https://res.ai-shifu.cn/efgh…",
      "alt": "Transformer 注意力计算流程",
      "uploaded_at": "2026-05-23T08:45:02Z"
    }
  ]
}
```

Field reference:

- `local`: source path for a file upload and its deduplication key; use a course-relative path when possible.
- `source_url`: original URL for a URL upload and its deduplication key.
- `remote`: platform-hosted URL used by Teaching Prompts.
- `alt`: source description retained for later contextual alt text.
- `uploaded_at`: UTC ISO 8601 timestamp.
- `bytes`, `original_bytes`, `mime`, `filename`: metadata for the processed file payload.

`assets/raw/` is recommended rather than required. Stable course-relative paths make the manifest portable across machines.

## .shifu-sync.json

`.shifu-sync.json` is an auto-maintained revision baseline. Do not hand-edit it. It links the local directory to one cloud course and records enough state to detect local edits and concurrent cloud changes.

Schema, abridged:

```json
{
  "schema_version": 1,
  "shifu_bid": "a1b2c3…",
  "base_url": "https://app.ai-shifu.cn",
  "course": {
    "revision": 42,
    "name": "…",
    "description": "…",
    "updated_at": "…",
    "updated_user_bid": "…"
  },
  "lessons": [
    {
      "file": "lessons/lesson-01.md",
      "outline_bid": "9a8b…",
      "name": "…",
      "parent_bid": "ch_001",
      "revision": 1187,
      "is_chapter": false,
      "content_sha256": "…"
    },
    {
      "file": null,
      "outline_bid": "ch_001",
      "name": "第一章",
      "parent_bid": "",
      "revision": null,
      "is_chapter": true
    }
  ],
  "last_pull_at": "…",
  "last_push_at": "…"
}
```

The course and lesson `revision` values are optimistic-locking baselines. `content_sha256` records the last synchronized lesson content. Chapter entries have no lesson file or revision, while lesson entries bind a file to a stable outline identifier.

## Lesson Files

Without a non-empty `structure.json#chapters` array, build discovery includes `lesson-*.md` files in sorted order and ignores other lesson filenames. With a non-empty chapters array, generated lessons come only from `chapters[].lessons[].file`; referenced custom filenames are accepted, but the current builder still requires at least one `lesson-*.md` file in the directory to pass its initial guard. That guard file does not itself need to appear in the structure.

## course-description.md

This optional UTF-8 Markdown file contains the learner-facing listing description. Its content maps to `shifu.description` in the generated import payload and to the platform description field. An absent file represents no file-provided description.

## course-prompt.md

This UTF-8 text file contains the resolved course-level prompt. Its content maps to `shifu.course_prompt` in the generated import payload and to the platform `system_prompt` field.

## structure.json

`structure.json` defines multi-chapter organization and file-to-title mapping. When the file is absent or its `chapters` array is empty, the generated payload uses one chapter containing the discovered `lesson-*.md` files.

```json
{
  "chapters": [
    {
      "title": "Chapter Title",
      "lessons": [
        {
          "file": "lesson-01.md",
          "title": "Lesson Title",
          "access": "guest",
          "hidden": false
        },
        {
          "file": "lesson-02.md",
          "title": "Another Lesson Title",
          "access": "normal",
          "hidden": false
        }
      ]
    }
  ]
}
```

Field reference:

- `chapters[].title` is the required chapter display name.
- `chapters[].lessons[]` is optional; an omitted array produces an empty chapter.
- `chapters[].lessons[].file` is the required filename under `lessons/`.
- `chapters[].lessons[].title` is optional; when omitted or empty, the builder derives the display name from the filename.
- `chapters[].lessons[].access` is a read-only platform snapshot: `guest` means no login, `trial` means logged-in trial, and `normal` means paid access. Content build and import do not apply it.
- `chapters[].lessons[].hidden` is a read-only platform snapshot. Content build and import do not apply it.

## course-config.json

`course-config.json` is a read-only snapshot of course-level attributes. Content build and import do not send this object.

```json
{
  "model": "",
  "temperature": 0.3,
  "price": 0,
  "keywords": [],
  "avatar": "",
  "use_learner_language": false,
  "tts_enabled": false,
  "tts_provider": "",
  "tts_model": "",
  "tts_voice_id": "",
  "tts_speed": 1.0,
  "tts_pitch": 0,
  "tts_emotion": "",
  "ask_enabled_status": 5101,
  "ask_model": "",
  "ask_temperature": 0.0,
  "ask_system_prompt": "",
  "ask_provider_config": {}
}
```

## shifu-import.json

`shifu-import.json` is the generated content payload accepted by import.

```json
{
  "version": "1.0",
  "exported_at": "2026-07-14T12:00:00+08:00",
  "shifu": {
    "shifu_bid": "<32-char-id>",
    "title": "Course Title",
    "keywords": "keywords",
    "description": "Description",
    "avatar_res_bid": "",
    "llm": "",
    "llm_temperature": 0,
    "course_prompt": "<resolved course prompt>",
    "ask_enabled_status": 5101,
    "ask_llm": "",
    "ask_llm_temperature": 0.0,
    "ask_llm_system_prompt": ""
  },
  "outline_items": [
    {
      "outline_item_bid": "<chapter-id>",
      "title": "Chapter Title",
      "type": 401,
      "hidden": 0,
      "parent_bid": "",
      "position": "0",
      "prerequisite_item_bids": "",
      "llm": "",
      "llm_temperature": 0,
      "course_prompt": "",
      "ask_enabled_status": 5101,
      "ask_llm": "",
      "ask_llm_temperature": 0.0,
      "ask_llm_system_prompt": "",
      "content": ""
    },
    {
      "outline_item_bid": "<lesson-id>",
      "title": "Lesson Title",
      "type": 401,
      "hidden": 0,
      "parent_bid": "<chapter-id>",
      "position": "0",
      "prerequisite_item_bids": "",
      "llm": "",
      "llm_temperature": 0,
      "course_prompt": "<resolved course prompt>",
      "ask_enabled_status": 5101,
      "ask_llm": "",
      "ask_llm_temperature": 0.0,
      "ask_llm_system_prompt": "",
      "content": "<MarkdownFlow content>"
    }
  ],
  "structure": {
    "bid": "<shifu_bid>",
    "id": 0,
    "type": "shifu",
    "children": [
      {
        "bid": "<chapter-id>",
        "id": 0,
        "type": "outline",
        "children": [
          {"bid": "<lesson-id>", "id": 0, "type": "outline", "children": [], "child_count": 0}
        ],
        "child_count": 1
      }
    ],
    "child_count": 1
  }
}
```

Field reference:

- `exported_at` is the local build timestamp in ISO format.
- `shifu.course_prompt` comes from `course-prompt.md`; `shifu.description` comes from the resolved description input.
- `outline_items[].type = 401` is emitted for both top-level chapter containers and lesson nodes.
- `outline_items[].parent_bid` is empty for a top-level chapter and contains the parent chapter identifier for a lesson.
- `outline_items[].course_prompt` and `outline_items[].content` are empty for generated chapter containers; generated lessons carry the resolved Course Prompt and their Teaching Prompt content.
- `structure` records the generated hierarchy and child counts.
- The current importer sends course `title`, `description`, and `course_prompt`; for outlines it sends `title`, the mapped parent relationship, and `content`. It uses generated outline identifiers only to map children to newly created parents. It does not submit `version`, `exported_at`, `structure`, the generated course identifier, or compatibility fields for keywords, avatar, model, temperature, Ask, type, visibility, position, or prerequisites as platform attributes.
