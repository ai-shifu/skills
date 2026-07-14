# CLI Reference

This page is the authoritative command interface: it owns invocations, flags, stdout, exit codes, and filesystem or platform side effects. Course-directory and generated-payload schemas live in `course-directory-spec.md`; analytics query-body grammar lives in `../analytics/dsl.md`; scenario selection and authoring semantics are outside this command contract.

All commands use `{skillDir}/scripts/shifu-cli.py`. Prefix every call with:

```bash
python3 {skillDir}/scripts/shifu-cli.py <command>
```

## Contents

- [Authentication](#authentication)
- [Query Commands](#query-commands)
- [Analytics Query](#analytics-query)
- [Version Sync](#version-sync-pull--status)
- [Create Commands](#create-commands)
- [Update Commands](#update-commands)
- [Delete Commands](#delete-commands)
- [Bulk Import](#bulk-import)
- [Image Upload](#image-upload)
- [State Management](#state-management)
- [CLI Output & Encoding](#cli-output--encoding)

## Authentication

The token persists in `{skillDir}/.env`, is valid for seven days, and uses a sliding expiry refreshed by successful API calls.

```bash
verify
login --phone <phone>
login --phone <phone> --sms-code <4-digit-code>
```

`verify` writes a human-readable status to stdout and exits `0` for a valid token, `1` for an expired or missing token, and `2` when validity cannot be determined. `login --phone` requests an SMS and reports the platform response; adding `--sms-code` exchanges the code for a token and writes `SHIFU_TOKEN=<jwt>` to `{skillDir}/.env`.

The CLI always talks to `https://app.ai-shifu.cn`. A caller may bypass SMS by supplying `--token` or `SHIFU_TOKEN`. Conversation sequencing, retry decisions, and SMS-quota protection are outside this command contract.

## Query Commands

```bash
list                                          # List all courses
show <shifu_bid>                              # Show course details + outline tree
show <shifu_bid> <outline_bid>                # Read a lesson's Teaching Prompt
history <shifu_bid> <outline_bid>             # Teaching Prompt revision history
export <shifu_bid> [-o file.json]             # Export course as JSON
find-title <keyword>                          # Search courses by current title
```

`find-title` matches the keyword case-insensitively after whitespace normalization against current published and draft titles only, excludes historical titles, and prints matches grouped by state.

`show` without `outline_bid`, `create`, `import`, `publish`, and `pull` print a `Verification URLs:` block. `publish` and `show` include a `Published URL:` line; `create`, `import`, and `pull` omit it. Each URL is followed by a one-line Chinese `# ...` hint, and per-lesson preview URLs are not printed.

## Analytics Query

```bash
analytics-query <shifu_bid> --dsl '<json>'        # Inline DSL body
analytics-query <shifu_bid> --dsl-file query.json # DSL body from a JSON file
```

Runs a DSL query against the creator-analytics endpoint and prints the full JSON response, including success rows or a business error code, to stdout. The CLI supplies authentication headers.

The `shifu_bid` positional argument is injected into the body; if the DSL JSON already carries a `shifu_bid`, it must match the positional argument.

Exit codes:
- `0` — API responded with `code == 0` (the response carries `data.columns` / `data.rows`).
- `1` — transport failure, JSON parse failure, or business error code (e.g. `11001` no access to course, `11002`-`11007` invalid DSL, `1001` / `1004` / `1005` token expired or missing).

The full response is always printed to stdout regardless of exit code, so the agent can read the error code and either fix the DSL or guide the user to re-login. The CLI deliberately does not exit before printing analytics business errors.

The body supplied through `--dsl` or `--dsl-file` must conform to `../analytics/dsl.md`. This command transports a body; it does not choose the business scenario or presentation policy.

### credit-detail

```bash
credit-detail <shifu_bid> [--start 2026-05-01] [--end 2026-05-15] [--scene 1202,1203] [--usage-type 1101,1102] [--limit 200] [--offset 200]
```

Returns course-scoped per-usage credit ledger detail from the server-side `bill_usage` × `credit_ledger_entries` join.

Flags:

- `--start` / `--end` — inclusive ISO date bounds (`end` must be on or after `start`).
- `--scene` — comma-separated subset of `{1201, 1202, 1203}` (debug / preview / production). Use `--scene 1203` to restrict to learner-driven spend.
- `--usage-type` — comma-separated subset of `{1101, 1102}` (LLM / TTS).
- `--limit` — row count cap, 1..1000 (default 100 server-side). `--offset` — pagination offset (default 0). The `summary` block always reflects the full filtered set regardless of paging.

The command prints the full API envelope. On success, read the total from `data.summary.total_credits`; `data.summary` contains `total_records`, `total_credits`, `unique_users`, `unique_progress`, `unique_wallets`, and `time_range`. It intentionally contains no wallet identifier. Read the wallet that paid each usage from `data.rows[].wallet_creator_bid`; `data.summary.unique_wallets` can exceed one, so do not infer a single course wallet from one row. Each row also contains `usage_bid`, `created_at`, `user_bid`, `progress_record_bid`, `outline_item_bid`, `usage_type`, `usage_scene`, `provider`, `model`, and `credits`. Credit values are positive decimal strings derived from the absolute ledger amount, and the summary covers the full filtered set regardless of pagination.

## Version Sync (pull / status)

`pull` and `status` compare the local revision baseline with the cloud draft's auto-incrementing course and lesson revisions.

```bash
pull <shifu_bid> --course-dir ./course-a/ [--force]   # Cloud -> local, writes .shifu-sync.json
status --course-dir ./course-a/ [--exit-code]         # Compare local vs cloud revisions
```

- `pull` fetches the course detail, outline tree, every lesson's MarkdownFlow,
  and the course-level draft revision, writes them into the course directory
  (`README.md`, `course-description.md`, `course-prompt.md`,
  `lessons/lesson-NN.md`, `structure.json`),
  and records the cloud `revision` of each lesson + the course in
  `<course-dir>/.shifu-sync.json`. Any local file that diverges from the
  incoming cloud content is backed up to `<file>.local-<ts>.bak` first (unless
  `--force`).
- `status` reads `.shifu-sync.json`, then reports per lesson: **behind** (cloud
  revision advanced past the local baseline — run `pull`), **locally modified**
  (the local file changed since last sync — will be pushed), **new on server**,
  and **deleted on server**, plus a course-meta behind flag. `--exit-code`
  returns non-zero when anything diverged (handy for agent scripting).

`.shifu-sync.json` is **auto-maintained — do not hand-edit.** It is the local↔cloud
version link (shifu_bid + per-lesson outline_bid + revision + course revision).

**Exit-code convention** for the version-guarded write commands
(`update-lesson`, `update-meta`, `import` when given `--course-dir`):
`0` success · `2` conflict auto-pulled (redo on the new baseline) · `1` hard error.

## Create Commands

```bash
create --name "Title" [--description "Desc"]
add-chapter <shifu_bid> --name "Chapter Name"
add-lesson <shifu_bid> --name "Name" --teaching-prompt-file lesson.md --parent-bid <chapter_bid>
```

## Update Commands

```bash
update-meta <shifu_bid> [--name "..."] [--description "..."] [--course-prompt-file prompt.md] [--course-dir ./course-a/]
update-lesson <shifu_bid> <outline_bid> --teaching-prompt-file lesson.md [--course-dir ./course-a/]
rename-lesson <shifu_bid> <outline_bid> --name "New Name"
reorder <shifu_bid> --order bid1,bid2,bid3
set-access <shifu_bid> <outline_bid> --access guest|trial|normal [--hidden true|false] [--course-dir ./course-a/]
set-tts <shifu_bid> --enabled true|false [--speed SPEED] [--course-dir ./course-a/]
```

`update-meta` sends only the content fields you pass (`--name` / `--description`
/ `--course-prompt-file`), plus a locally modified `course-description.md` when
`--course-dir` is supplied; it does **not** touch course
attributes (model / price / TTS / Ask / …) — the backend preserves any field
left out. When `--course-dir` is supplied, a successful description update
writes `course-description.md` and records the new course metadata baseline in
`.shifu-sync.json`. `rename-lesson` likewise changes only the name and no longer
resets the lesson's learning permission.

`set-access` sets one lesson's **learning permission** (`guest` = 无需登录 /
`trial` = 试看·需登录 / `normal` = 需付费) without re-importing; it sends only
`type` (+ `is_hidden` when `--hidden` is given), and the backend leaves the
lesson's other fields untouched. With `--course-dir` it also writes the value
into the `structure.json` reference.

`set-tts` enables or disables course Listen Mode without re-importing. Disabling
sends only `tts_enabled=false` and leaves the stored provider/model/voice/speed
unchanged. Enabling sends the full TTS settings the backend validates:
`tts_enabled=true`, `tts_provider`, `tts_model`, `tts_voice_id`, `tts_speed`,
plus normalized `tts_pitch=0` and `tts_emotion=""`. Provider, model, voice, and
default speed come from platform defaults at `/tts/config` (the same fallback
used by the AI-Shifu settings page); `--speed` is the only optional override.
With `--course-dir` it refreshes `course-config.json` and records the new course
revision in `.shifu-sync.json`.

`update-lesson`, `update-meta`, and `set-tts` are version-aware when given `--course-dir`
(a directory with a `.shifu-sync.json` from `pull`):

- `update-lesson` uses the **recorded baseline** revision for that outline (its
  revision at last pull/push) as `base_revision`, so a concurrent edit by
  another editor is actually detected. Without `--course-dir` it falls back to
  the legacy behavior of taking the current cloud head as the baseline
  (degraded — concurrent edits are not caught). On success it writes the new
  revision back to the manifest and keeps the local lesson file in lockstep.
- `update-meta` and `set-tts` have no server-side lock, so they compare the cloud
  course-level revision against the manifest baseline before writing; any cloud
  advance is treated conservatively as a conflict.

**On conflict** these commands auto-pull the cloud copy over local, back up the un-pushed change to `<file>.conflict` for a lesson or `.shifu-meta.conflict.json` for metadata, print who changed it and when, and exit `2`. Without `--course-dir`, `update-lesson` still sends the cloud-head `base_revision`, and the server may reject the save with a raw conflict response without auto-recovery.

## Delete Commands

```bash
delete-lesson <shifu_bid> <outline_bid>
```

## Bulk Import

```bash
# Flat JSON import
import <shifu_bid> --json-file course.json
import --new --json-file course.json

# One-step build + import from course directory
import <shifu_bid> --course-dir ./course-a/ [--title "..."] [--description "..."] [--keywords "..."] [--chapter-name "..."]
import --new --course-dir ./course-a/ [--title "..."] [--description "..."] [--keywords "..."] [--chapter-name "..."]

# Local build only (offline, generates shifu-import.json)
build --course-dir ./course-a/ [-o shifu-import.json] [--title "..."] [--description "..."] [--keywords "..."] [--chapter-name "..."]
```

The `build` command works entirely offline — it reads the course directory's Teaching Prompts (one MarkdownFlow file per lesson under `lessons/`), the Course Prompt, and the SEO course description, then produces `shifu-import.json` without any network calls. The `import --course-dir` option combines build + import in one step. Description resolution order is `--description` -> `<course-dir>/course-description.md` -> empty string.

**Course attributes are not pushed by default.** The skill manages course
*content*; *attributes* (each lesson's learning permission / hidden state, and
course-level model/price/TTS/Ask/…) are left to the platform. `build`/`import`
send only content (lesson MarkdownFlow + course name/description/system prompt),
and the backend uses **PATCH semantics** — any field a write omits is preserved.
So `update-lesson` (content only) and `update-meta` (only the `--name` /
`--description` / `--course-prompt-file` you pass, plus a locally modified
`course-description.md` with `--course-dir`) never
touch attributes.

`pull` still writes the attributes into `structure.json` (`access`/`hidden`) and
`course-config.json` as a **read-only reference** for the agent. To change an
attribute, do it explicitly: `set-access` for a lesson's permission, `set-tts`
for course Listen Mode, or the platform editor for other course-level
settings.

**Version-aware import.** When re-importing into an existing course with a `.shifu-sync.json` (`import <shifu_bid> --course-dir ...`), the CLI first checks the cloud course-level revision against the manifest baseline. If another editor advanced it, the whole local tree is backed up to `.conflict-backup-<ts>/`, the cloud copy is pulled over local, and the command exits `2`. After a successful import, the manifest is re-seeded through an automatic `pull` so subsequent edits stay version-tracked.

> **Note (Phase 1):** `import` is destructive: it deletes and recreates every outline, so all `outline_bid` values are regenerated and per-lesson server history does not carry over.

Build behavior:

- **Course title** resolution order: `--title` CLI arg -> first heading in `README.md` -> directory name
- **Course description** resolution order: `--description` CLI arg -> `course-description.md` -> empty string
- **Chapter structure**: if `structure.json` exists, generates multi-chapter structure per its definition; otherwise creates a single chapter (named via `--chapter-name` or defaults to course title) containing all `lesson-*.md` files in sorted order
- **Lesson title** resolution order: `title` field in `structure.json` -> filename derived (e.g., `lesson-01.md` -> "Lesson 01")

### Import JSON Schema

The generated payload shape and field mappings are defined in `course-directory-spec.md#shifu-importjson`. The `build` command writes that schema; `import` accepts it.

## Image Upload

```bash
# Local file: preprocessed locally (max side 2048 px, ≤ 2 MB, JPEG q=85 / PNG when alpha)
upload-image --file <local-path> [--course-dir <dir>] [--alt "<description>"]

# Remote URL: backend downloads and re-hosts; no local preprocessing
upload-image --url <http(s)-url> [--course-dir <dir>] [--alt "<description>"]
```

Stdout is **one line** — the resulting `https://res.ai-shifu.cn/<uuid32>` URL. Diagnostic / manifest messages go to stderr, so a shell pipeline can capture the URL cleanly:

```bash
URL=$(python3 scripts/shifu-cli.py upload-image --file diagram.png --course-dir ./my-course/ --alt "Transformer 单层结构")
```

Behavior:

- `--file`: opens with Pillow (HEIC/HEIF via `pillow-heif`), corrects EXIF orientation, downscales to longest-side 2048 px, recompresses JPEG until ≤ 2 MB; transparent images output PNG. Non-image inputs (e.g. `.pdf`, `.txt`) raise an error in the preprocessing stage and exit with code 1.
- `--url`: posts directly to `/api/shifu/url-upfile`; the backend validates the response is `image/*` and re-hosts the file.
- `--course-dir`: when provided, an entry is upserted into `<course-dir>/assets/image-manifest.json` keyed by `local` (for file uploads) or `source_url` (for URL uploads). Re-uploading the same path updates the entry rather than appending.
- `--alt`: short source description stored in the manifest; it is not automatically rendered into a Teaching Prompt.
- `--no-process` (debug only): skip preprocessing and upload bytes as-is. Use only when investigating a backend issue; will fail for HEIC and oversize files.

Dependencies: `Pillow`, `pillow-heif`. First-run failures suggest `pip install -r scripts/requirements.txt`.

This command ends after returning the platform URL and updating the optional manifest. It does not edit a Teaching Prompt or choose image placement.

## State Management

```bash
publish <shifu_bid>       # Publish course (makes it live)
archive <shifu_bid>       # Archive course
unarchive <shifu_bid>     # Restore archived course
```

## CLI Output & Encoding

### Known issue: Chinese characters garbled in agent environments

When running CLI commands (especially `list` and `show`) from an agent's Bash tool, Chinese characters in stdout may appear garbled (mojibake) even with `PYTHONIOENCODING=utf-8` set. This is caused by the agent's subprocess pipe not inheriting the correct locale settings.

**Recommended workaround** — write JSON output to a UTF-8 file, then read it with the agent's file-reading tool:

```bash
# Instead of reading garbled stdout directly:
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '<json>' > /tmp/shifu_result.json
# Then read /tmp/shifu_result.json with the agent's file reader
```

For `list` and `show`, which output formatted tables (not JSON), pipe through a JSON serialization helper or redirect to file:

```bash
python3 -c "
import subprocess, json, sys
result = subprocess.run(
    ['python3', 'scripts/shifu-cli.py', 'show', '<bid>'],
    capture_output=True, text=True, encoding='utf-8'
)
print(result.stdout)
" > /tmp/shifu_show.txt
```

### For analytics-query and credit-detail

These already output JSON via `json.dumps(ensure_ascii=False)`, so they work correctly when redirected to a file. The garbling only affects the pipe encoding — the JSON data itself is UTF-8.

### Token persistence

The token is saved to `{skillDir}/.env` after a successful login, subsequent commands read it automatically, and a later successful login overwrites it in place. Commands surface expired-token codes `1001`, `1004`, or `1005`; conversation recovery remains outside this command contract.
