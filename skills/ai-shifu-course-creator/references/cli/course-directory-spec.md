# Course Directory Specification

## Directory Structure

```
<course>/
  README.md            # Course metadata (title from first heading)
  course-prompt.md     # Course-level prompt (AI role and teaching style)
  shifu-import.json    # Generated import file (output of build)
  structure.json       # Chapter structure (optional, for multi-chapter courses)
  lessons/
    lesson-01.md       # Teaching Prompt (MarkdownFlow)
    lesson-02.md
    ...
```

## Lesson Files

When `structure.json` is not present, `build` auto-discovers only `lesson-*.md` files (e.g., `lesson-01.md`, `lesson-02.md`) and ignores other filenames. When `structure.json` is present, lesson files are taken from `chapters[].lessons[].file` and any filename is accepted as long as it exists.

## course-prompt.md

Defines the AI engine's role, teaching style, and interaction rules at the course level. The `build` command reads this file and populates `shifu.course_prompt` in the import JSON automatically (which the CLI maps to the platform API field `system_prompt` on import).

Authoring rules and a fillable template live in `../course-prompt.md`.

Note: MarkdownFlow files do not support HTML comments (`<!-- -->`). The parser discards them entirely, so the AI engine never sees them. Write instructions as plain text directly in the Course Prompt content.

## structure.json

Defines multi-chapter course structure. If this file exists, `build` uses it to organize lessons into chapters; otherwise all lessons are placed under a single auto-generated chapter.

Schema:

```json
{
  "chapters": [
    {
      "title": "Chapter Title",
      "lessons": [
        {"file": "lesson-01.md", "title": "Lesson Title"},
        {"file": "lesson-02.md"}
      ]
    }
  ]
}
```

Field reference:

- `chapters[].title` (required): Chapter display name
- `chapters[].lessons[]` (required): Array of lesson objects
- `chapters[].lessons[].file` (required): Filename in the `lessons/` directory (must exist)
- `chapters[].lessons[].title` (optional): Lesson display name. If omitted, auto-extracted from the Teaching Prompt (`lesson_title: ...` line in the MarkdownFlow content) or derived from filename
