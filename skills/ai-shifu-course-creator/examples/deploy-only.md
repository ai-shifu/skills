# Deploy Only Example (Phase 5)

Two distinct flows: creating a brand-new course, or updating an existing one. The local artifact is always a single `course.json` file (see `references/course-directory-spec.md` for the schema).

## Flow A: Create a brand-new course

### Prerequisites

A local `course.json` with placeholder `outline_item_bid` strings (any prefix; convention is `new:<seq>`) and empty `deployment`:

```json
{
  "version": "1.0",
  "course": { "title": "My Course", "description": "...", "course_prompt": "...", "language": "zh-CN" },
  "structure": [
    {"outline_item_bid": "new:c01", "children": [
      {"outline_item_bid": "new:l01", "children": []},
      {"outline_item_bid": "new:l02", "children": []}
    ]}
  ],
  "items": {
    "new:c01": {"type": "chapter", "title": "Chapter 1", "markdownflow_prompt": "..."},
    "new:l01": {"type": "lesson", "title": "Lesson 1", "markdownflow_prompt": "..."},
    "new:l02": {"type": "lesson", "title": "Lesson 2", "markdownflow_prompt": "..."}
  },
  "global_variables": [],
  "deployment": {}
}
```

### Deployment

```bash
# Import: creates the shifu, posts metadata, adds outlines, writes MarkdownFlow,
# reorders, then auto-pulls so course.json reflects the server's real bids.
python3 {skillDir}/scripts/shifu-cli.py import --new --course-dir ./
# Returns: shifu_bid = xyz789

# Publish to make it live
python3 {skillDir}/scripts/shifu-cli.py publish xyz789
```

After `import` succeeds, every `new:*` placeholder in `course.json` is replaced with a real UUID, and `deployment.shifu_bid` is populated.

## Flow B: Update an existing course (optimization workflow)

### Step 1: Pull authoritative state

```bash
python3 {skillDir}/scripts/shifu-cli.py pull xyz789 --to ./
```

This downloads the full course (one `GET /export` call + one `GET /draft-meta` per outline_item to capture revisions for optimistic locking).

### Step 2: Edit `course.json` locally

Edit the file directly. For long-form MarkdownFlow content, `extract` / `embed` round-trip a single field through a standalone `.md` file:

```bash
# Pull a lesson out for editing in your IDE
python3 {skillDir}/scripts/shifu-cli.py extract --course-dir ./ --outline-bid <bid> -o lesson.md
# ... edit lesson.md ...
python3 {skillDir}/scripts/shifu-cli.py embed --course-dir ./ --outline-bid <bid> --from lesson.md
```

You can also add new chapters or lessons by inserting placeholder bids in `items` and the `structure` tree.

### Step 3: Push changes

```bash
python3 {skillDir}/scripts/shifu-cli.py push --course-dir ./
```

The CLI computes a diff against the server, then applies metadata updates, adds, deletes, content updates (with optimistic locking), renames, and reorder in safe order. After all mutations succeed, it re-pulls to refresh `course.json`'s revisions.

## Common Management Commands

```bash
# List all accessible courses
python3 {skillDir}/scripts/shifu-cli.py list

# Show course detail + outline tree
python3 {skillDir}/scripts/shifu-cli.py show xyz789

# Read a single item's MarkdownFlow content
python3 {skillDir}/scripts/shifu-cli.py show xyz789 <outline_item_bid>

# Validate a local course.json without contacting the server
python3 {skillDir}/scripts/shifu-cli.py validate --course-dir ./ --mode push

# Archive when done
python3 {skillDir}/scripts/shifu-cli.py archive xyz789
```

## Acceptance Notes

- Phase 5 executed independently of the authoring pipeline (Path C / D).
- Single-file `course.json` is the only local artifact; no directory tree, no `system-prompt.md`.
- After `import` or `push`, the local file is in fully-synchronized state — every `outline_item_bid` is a real server UUID and `deployment` reflects the latest sync.
- For brand-new courses, prefer `import --new`. For existing courses, prefer `push` (do not run `import` against an existing course; ADR-001 §D9 explains why).
