# CLI Reference

All commands use `{skillDir}/scripts/shifu-cli.py`. Prefix every call with:

```bash
python3 {skillDir}/scripts/shifu-cli.py <command>
```

Always go through the CLI. Never call platform HTTP / API endpoints directly.

## Authentication

Run login once — the token persists in `{skillDir}/.env` for subsequent commands:

```bash
# Step 1: send SMS code
login --phone 13800138000

# Step 2: complete login with the 4-digit code
login --phone 13800138000 --sms-code 1234
```

The CLI always talks to `https://app.ai-shifu.cn`. To skip the SMS flow, set `SHIFU_TOKEN` in `.env` or pass `--token` explicitly.

### Agent login flow

When no valid token is available, walk the user through:

1. Ask for their registered phone number.
2. `login --phone <phone>` to send the SMS.
3. Ask the user for the 4-digit code they received.
4. `login --phone <phone> --sms-code <code>` to finalize. Token is saved automatically.

## Single-File Workflow Commands (recommended)

These commands operate on a single `course.json` file (see `course-directory-spec.md` for the schema). They are the recommended path for authoring and synchronization.

### `pull` — server → local

```bash
pull <shifu_bid> --to <path/> [--force-overwrite]
```

Downloads a course as a single `course.json`. Internally calls `GET /export` once for shifu metadata + all outline_items (with content embedded) + structure tree, then `GET /draft-meta` once per outline_item for the optimistic-locking revision (O(1+N) total).

By default refuses to overwrite an existing file; pass `--force-overwrite` to replace.

### `push` — local → server

```bash
push --course-dir <path/>
```

Diffs the local file against the current server state and applies fine-grained mutations: metadata update → add new chapters → add new lessons → delete obsolete items → rename → update MarkdownFlow content (with optimistic locking) → reorder. After all mutations succeed, automatically re-pulls to refresh local revisions.

`push` requires the file to already have `deployment.shifu_bid` set (i.e. a course that came from a previous `pull` or `import`). For brand-new courses, use `import --new` instead.

Conflict handling:

- **MarkdownFlow content**: server-side optimistic locking on `base_revision`. If another client modified an item since you pulled, the platform returns a conflict and `push` aborts; re-`pull` and try again.
- **Metadata** (`title` / `description` / `course_prompt` / outline titles): no server-side concurrency control; last write wins. The diff layer surfaces these changes but does not gate them.

### `extract` / `embed` — round-trip a single field

For human editing in an external `.md` editor.

```bash
extract --course-dir <course-dir> --course-prompt -o <path.md> [--force]
extract --course-dir <course-dir> --outline-bid <bid> -o <path.md> [--force]

embed --course-dir <course-dir> --course-prompt --from <path.md>
embed --course-dir <course-dir> --outline-bid <bid> --from <path.md>
```

Pure local file ops, no platform calls. `embed` writes back via atomic `temp + rename`. `extract` refuses to overwrite without `--force`.

### `validate` — schema check

```bash
validate --course-dir <course-dir> --mode push|import
```

Runs the local schema validator. `push` mode rejects placeholder `new:*` bids; `import` mode allows them. Returns exit 0 on valid, 1 on errors (each printed with a JSON path).

### `import --new` — create a brand-new course

```bash
import --new --course-dir <path/>
```

Creates a new course on the platform from a local `course.json` containing placeholder bids. Internally: `PUT /shifus` (empty shifu) → `update-meta` → `add-chapter` × N → `add-lesson` × N → `update-mdflow` × N → `reorder` → **auto `pull --force-overwrite`** to refresh the local file with real bids and revisions.

`import` is brand-new-only. To update an existing course, use `push`. The legacy `import <existing-shifu-bid>` mode has been removed (ADR-001 §D9).

## Read-only Commands

```bash
list                                          # List all courses you can access
show <shifu_bid>                              # Course detail + outline tree
show <shifu_bid> <outline_bid>                # Read a single item's MarkdownFlow content
history <shifu_bid> <outline_bid>             # MarkdownFlow revision history
export <shifu_bid> [-o file.json]             # Export wire-format JSON (legacy; pull is preferred)
```

## Granular Mutation Commands

These are the building blocks `push` uses internally. Most agents should prefer `push` since it diffs and applies all changes atomically. Use the granular commands only when scripting one-off changes.

```bash
create --name "..." [--description "..."]                                    # Create empty shifu (no outlines)
update-meta <shifu_bid> [--name "..."] [--description "..."] [--system-prompt-file file.md]
add-chapter <shifu_bid> --name "..."                                          # Create top-level outline (type=chapter)
add-lesson <shifu_bid> --name "..." --parent-bid <chapter_bid> [--markdownflow-file ...]
update-lesson <shifu_bid> <outline_bid> --markdownflow-file <file.md>                  # Save MarkdownFlow with optimistic lock
rename-lesson <shifu_bid> <outline_bid> --name "..."
delete-lesson <shifu_bid> <outline_bid>
reorder <shifu_bid> --tree-file <tree.json>     # Submit complete outlines tree
reorder <shifu_bid> --json '<inline-json>'      # Same, inline string
```

Reorder schema (matches platform `ReorderOutlineDto`):

```json
[
  {"bid": "<chapter-bid>", "children": [
    {"bid": "<lesson-bid>", "children": []},
    {"bid": "<lesson-bid>", "children": []}
  ]}
]
```

The reorder endpoint supports cross-chapter moves: a lesson's bid can appear under a different chapter's `children` and the platform updates positions accordingly.

## Legacy Commands (kept for compatibility)

```bash
import --new --json-file <flat.json>                       # Old wire-format JSON import
import --new --legacy-course-dir <dir>                     # Old multi-file course directory format
build --course-dir <dir> [-o file.json]                    # Build wire-format JSON from an old multi-file course directory
```

`--legacy-course-dir` accepts the **old** multi-file layout (`README.md` + `system-prompt.md` + `lessons/lesson-*.md` + optional `structure.json`) — distinct from the new single-file `course.json` mode that the recommended `--course-dir` flag uses. New code should always use the recommended single-file path. See ADR-001 for the migration rationale.

`build` no longer has a recommended use case for new courses; the single-file `course.json` is the canonical local format. Keep `build` only for legacy scripts that still depend on the wire-format JSON output.

## State Management

```bash
publish <shifu_bid>       # Publish (Draft → Published; no bid changes)
archive <shifu_bid>       # Archive (hides from active listing; data preserved)
unarchive <shifu_bid>     # Restore an archived course
```

## Field-Name Glossary (local ↔ wire)

| Local `course.json` | Wire (export / import / detail) |
|---|---|
| `course.title` | `shifu.title` (export) / `name` (detail) |
| `course.description` | `shifu.description` / `description` |
| `course.course_prompt` | `shifu.llm_system_prompt` / `system_prompt` |
| `items.<bid>.type` | `outline_items[].type` (int 400 / 401) |
| `items.<bid>.markdownflow_prompt` | `outline_items[].content` |
| `structure[*].outline_item_bid` | `outline_items[].outline_item_bid` and tree-node `bid` |

The CLI handles translation transparently; agents authoring `course.json` only see the local names.
