# CLI Reference

## Required References

None.

## Invocation

All commands use:

```bash
python3 {skillDir}/scripts/shifu-cli.py <command> [--profile <name>]
```

`--profile <name>` selects one named profile for this invocation and may appear before or after the command. Supply it at most once. Authenticated commands also accept `--token <jwt>` as a non-persistent override for this invocation. Selection is resolved once before platform access; requests, uploads, and returned course links use that same context. See [Profiles](#profiles) for selection and credential precedence. Use `{skillDir}/.env.example` as the reference when creating or editing `{skillDir}/.env`:

```dotenv
SHIFU_BASE_URL=
SHIFU_TOKEN=
```

Process environment variables take precedence over the corresponding `.env` values. An empty value does not activate temporary configuration. Before every command, the CLI initializes a missing `.env` from `.env.example` with owner-only permissions; an existing file is never replaced. Browser-issued credentials live in the user's configuration directory rather than `.env`.

## Contents

- [Update Check](#update-check)
- [Profiles](#profiles)
- [Site Selection](#site-selection)
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
- [Exit Codes](#exit-codes)
- [CLI Output & Encoding](#cli-output--encoding)

## Update Check

```bash
check-update [--force] [--dev-manifest-url <loopback-url>]
```

`check-update` reads the public Skill-version manifest and prints a compact JSON result. `--force` bypasses the local TTL. `--dev-manifest-url` accepts only a localhost or loopback URL and exists for end-to-end development checks.

## Profiles

```bash
profile set Daily --base-url cn
profile set Demo --base-url com
profile set "Client A" --base-url https://school.example:8443/training
profile list
profile default
profile default Daily
list --profile "Client A"
```

Each profile holds one service URL and independent credentials and pending authorization. Names are arbitrary, case-sensitive Unicode strings; surrounding whitespace is trimmed, and empty names or control characters are rejected. Names do not identify regions or constrain URLs. Multiple profiles may use the same service with separate accounts. The first profile becomes the default; creating or selecting another does not change the default. `profile default [name]` reads or explicitly changes that setting. Unknown names fail without fallback.

`profile set` creates or updates a profile. `cn` and `com` (case-insensitive) expand to `https://app.ai-shifu.cn` and `https://app.ai-shifu.com`; storage contains full URLs, without a region type. Custom URLs support HTTPS, ports, and path prefixes; HTTP is allowed only for loopback development. Embedded credentials, queries, and fragments are rejected. Surrounding whitespace and trailing slashes are removed. Changing a URL with saved credentials or pending authorization requires `logout` for that profile first; setting the same URL preserves authorization.

| Invocation context | Effective service and credentials |
| --- | --- |
| Explicit `--profile <name>` | That profile's URL and saved credentials; ignore `SHIFU_BASE_URL` and `SHIFU_TOKEN` from both process environment and `.env`. Explicit `--token` overrides the saved token for this command only. |
| No explicit profile, with non-empty environment configuration | Temporary mode requires a URL plus a token from `SHIFU_TOKEN` or explicit `--token`. Missing either is an error. Never borrow a saved token, persist temporary credentials, or change the default. |
| Neither of the above | The default profile's URL and credentials, with an optional non-persistent explicit `--token` override. No configured default means exit `4` before platform access. |

Browser login and continuation require a named profile, so use explicit `--profile` when temporary environment configuration is active. A missing or expired token does not select another profile. Local `build` and version checks need no profile.

### Configuration and Migration

The configuration root is `AI_SHIFU_CONFIG_DIR` when set, otherwise `$XDG_CONFIG_HOME/ai-shifu`, otherwise `~/.config/ai-shifu` on all platforms (including `%USERPROFILE%\.config\ai-shifu` on Windows). Root overrides may come from the process environment or the skill's `.env`, with process values taking precedence for the same variable. The CLI resolves this root before legacy migration and reloads temporary URL/token values after migration cleanup without replacing exported process values. `settings.json` contains:

```json
{
  "schema_version": 2,
  "default_profile": "Daily",
  "profiles": {
    "Daily": {
      "id": "<generated internal ID>",
      "base_url": "https://app.ai-shifu.cn"
    }
  }
}
```

Profile IDs are generated opaque identifiers used for safe cross-platform directories, independent of user-facing names. Each `profiles/<id>/` contains its own `credentials.json` and optional `pending-device-auth.json`. Both bind authorization to the normalized issuing `base_url`; mismatches fail before sending credentials. Writes are atomic and use owner-only permissions where supported. `profile list` returns `{"profiles": [...]}` with each entry's `name`, `base_url`, `default`, and `credentials_present`, never tokens; presence does not prove that login is valid. `profile default` returns `{"default_profile": "<name>"}`, or null when unconfigured.

On first use of legacy configuration, the CLI migrates a known saved service and matching credentials into an ordinary profile named `default`. Legacy `.env` configuration is considered with its existing precedence; process-exported tokens are never persisted. A pending request migrates only when its issuing URL matches. Credentials whose source cannot be established remain untouched and require a fresh login to the intended profile. The CLI writes and validates new files before committing version-2 settings, then removes only successfully migrated legacy credentials and `.env` fields. Migration can resume after interruption and is not repeated once completed. New `.env` values after migration remain temporary overrides.

Profile creation/updates, default changes, and migration serialize their complete read-modify-write transactions with a cross-process lock. If another command holds the lock for ten seconds, the CLI reports that configuration is busy; retry after that command finishes. A terminated process releases its lock automatically.

After the service returns a new authorization request, saving it uses the same lock to revalidate the profile's internal ID and URL. If either changed while the request was in flight, login fails without saving or displaying the stale request; retry login for the intended profile. The network request itself does not hold the configuration lock.

Authorization completion and logout also use this lock. Before storing an approved token and consuming its pending request, the CLI rechecks the profile ID, service URL, and device code. A request cleared by logout or replaced by another login cannot restore credentials; delayed denial or expiry responses cannot clear the replacement request. Polling does not hold the lock.

## Site Selection

```bash
site [--profile <name>]
site --set cn
site --set com
site --url https://your-service.example
```

`site` is the compatibility entrypoint for inspecting the effective context or configuring the selected/default profile. It prints JSON with `status=configured`, the effective `base_url`, `profile`, and official `contact_url`, or `status=selection_required` with no configured service. `profile` is null for temporary or unconfigured contexts. Contact links depend on the service address: the domestic official service uses the Chinese contact page; the international official service and custom deployments use the international contact page. Profile names do not affect this mapping. It makes no network requests or usage events.

`site --set cn/com` and `site --url <URL>` update the selected/default profile using the same URL and authorization rules as `profile set`. With no configured profile, initial setup creates an ordinary profile named `default`. Use explicit `--profile` to configure a named profile when temporary environment configuration is active.

`site` output and setup commands are internal control data. During normal setup, ask the user to select their current region with two options: China or Other countries or regions, then configure silently; do not present these URLs, fields, or commands. Custom deployment is used only when explicitly requested or already configured.

`build`, `check-update`, and `site` do not require site selection. Agent intake behavior is defined in `../authentication.md#select-site-before-connecting`.

## Authentication

```bash
verify [--profile <name>]
login [--profile <name>]
login --wait [--timeout 120] [--profile <name>]
logout [--profile <name>]
```

- `verify` exits `0` when the token is accepted, `1` when it is expired or invalid, and `2` when network, service, or response errors make its state unknown.
- `login` starts a browser authorization request, saves the pending request, prints the verification link and a pairing code, and exits immediately. It does not open a browser. The Agent opens the link in its built-in browser; terminal users open the printed link manually. The CLI prefers `verification_uri_complete`, which carries the pairing code. If unavailable, it prints `verification_uri` instead; users enter the separately printed pairing code if the page requests it.
- `login --wait` polls the pending request. It exits `0` once the request is approved and the token is stored, `1` when the request was denied, expired, or never started, and `3` while the request is still valid but nobody has approved it yet. Exit `3` means the same command can simply be run again.
- `--timeout` bounds a single `--wait` invocation in seconds; it does not shorten the request's own lifetime.
- `login` and `login --wait` use the same named profile and issuing service. Different profiles may authorize concurrently without overwriting one another's pending requests or tokens. Continuation commands carry the profile name.
- On Windows, continuation and recovery hints give a literal JSON argument list rather than assuming cmd.exe or PowerShell quoting. Pass these arguments directly to the CLI (for example through a subprocess argument array); the JSON is explicitly not a shell command. Other platforms show a POSIX-quoted command.
- `logout` removes only the selected profile's local credentials and pending request, retaining its URL, name, and default setting. It does not revoke remote tokens or affect another profile.
- Storage, URL validation, temporary configuration, and legacy migration follow [Profiles](#profiles).
- A stored token is valid for thirty days; successful authenticated API calls refresh that expiry.

Agent behavior during a login session is defined in `../authentication.md`; this section defines only CLI inputs and effects.

## Query Commands

```bash
list
show <shifu_bid>
show <shifu_bid> <outline_bid>
history <shifu_bid> <outline_bid>
export <shifu_bid> [-o file.json]
find-title <keyword>
```

- `list` prints all active courses visible to the authenticated creator.
- `show <shifu_bid>` prints course detail and the outline tree. `show <shifu_bid> <outline_bid>` prints one lesson's Teaching Prompt.
- `history` prints one lesson's Teaching Prompt revision history.
- `export` writes course JSON to stdout or the path passed with `-o`.
- `find-title` requires at least two non-whitespace characters, then matches the keyword case-insensitively after whitespace normalization against current draft and published titles. It does not match historical or renamed titles.

Course links are printed one per line with `Admin console`, `Preview URL`, and optional `Published URL` labels, without headings or explanations. `show` without an outline BID prints the admin and course preview URLs even when the outline tree is empty. A non-empty tree also includes the public learner URL, without checking publication state. `create`, `import`, and `pull` print the admin and course preview URLs; `publish` prints all three. Lesson preview URLs are not printed. Agent browser handoff follows `../session-controls.md#course-admin-handoff`.

## Analytics Query

```bash
analytics-query <shifu_bid> --dsl '<json>'
analytics-query <shifu_bid> --dsl-file query.json

credit-detail <shifu_bid> \
  [--start 2026-05-01] [--end 2026-05-15] \
  [--scene 1202,1203] [--usage-type 1101,1102] \
  [--limit 200] [--offset 200]
```

`analytics-query` accepts exactly one of `--dsl` or `--dsl-file`. The positional Shifu BID is injected into the request; an existing `shifu_bid` in the JSON must match it. The complete JSON response is printed to stdout. Exit `0` means business code `0`; exit `1` covers transport, JSON, and nonzero business errors.

`credit-detail` returns JSON containing `summary` and paginated `rows` for the server-side credit detail join. Date bounds are inclusive. `--scene` accepts a comma-separated subset of `1201`, `1202`, and `1203`; `--usage-type` accepts a subset of `1101` and `1102`; `--limit` is `1..1000`; `--offset` defaults to `0`. The summary covers the full filtered set regardless of pagination. Validation, transport, or business errors exit `1`.

## Version Sync (pull / status)

```bash
pull <shifu_bid> --course-dir ./course-a/ [--force]
status --course-dir ./course-a/ [--exit-code]
```

`pull` writes the cloud draft into the course directory: `README.md`, `course-description.md`, `course-prompt.md`, `course-config.json`, lesson files, `structure.json`, and `.shifu-sync.json`. It records course and lesson revision baselines. Before overwriting a divergent local file, it writes `<file>.local-<timestamp>.bak`; `--force` disables these backups.

`status` reads `.shifu-sync.json`, compares it with cloud revisions and local hashes, and reports:

- course metadata behind;
- lesson behind;
- locally modified lesson or course description;
- new lesson on the server;
- lesson deleted on the server.

Without `--exit-code`, divergence is reported while the command exits normally. With `--exit-code`, any divergence exits `1`. A missing sync manifest also exits `1`.

`.shifu-sync.json` is auto-maintained by the CLI. Its schema and the source-service/course identity checks applied before all network commands with a course directory are defined in `course-directory-spec.md#shifu-syncjson`. `--force` affects local backups only; it never bypasses identity checks.

## Create Commands

```bash
create --name "Title" [--description "Desc"]
add-chapter <shifu_bid> --name "Chapter Name"
add-lesson <shifu_bid> --name "Lesson Name" \
  [--teaching-prompt-file lesson.md] --parent-bid <chapter_bid>
```

- `create` creates an empty course and prints its BID and verification URLs.
- `add-chapter` creates one top-level chapter and prints its outline BID.
- `add-lesson` creates a lesson under the required parent chapter and, when a prompt file is provided, saves its MarkdownFlow content.

## Update Commands

```bash
update-meta <shifu_bid> [--name "..."] [--description "..."] \
  [--course-prompt-file prompt.md] [--course-dir ./course-a/]
update-lesson <shifu_bid> <outline_bid> \
  --teaching-prompt-file lesson.md [--course-dir ./course-a/]
rename-lesson <shifu_bid> <outline_bid> --name "New Name"
set-access <shifu_bid> <outline_bid> --access guest|trial|normal \
  [--hidden true|false] [--course-dir ./course-a/]
set-tts <shifu_bid> --enabled true|false [--speed <number>] \
  [--course-dir ./course-a/]
set-avatar <shifu_bid> --file <teacher.jpg|teacher.png> \
  [--course-dir ./course-a/]
reorder <shifu_bid> --order bid1,bid2,bid3
```

### `update-lesson` and `rename-lesson`

`update-lesson` sends the prompt file as lesson content. With a matching `.shifu-sync.json`, it uses the recorded lesson revision as the optimistic-lock baseline and updates the manifest and local file after success. Without that baseline it uses the current cloud head, so concurrent-edit detection is degraded. On a conflict with `--course-dir`, the CLI saves the attempted content as `<file>.conflict`, pulls the cloud course over local, and exits `2`.

`rename-lesson` sends only the lesson name and preserves omitted lesson fields.

### `update-meta`

The command sends only provided `name`, `description`, and Course Prompt fields. With `--course-dir`, a local `course-description.md` that differs from the sync baseline is also sent. A successful description update refreshes the local file and the recorded course revision. Omitted platform attributes are preserved by backend PATCH semantics.

With a matching sync manifest, the CLI compares the recorded course revision before writing. On conflict it stores the intended metadata in `.shifu-meta.conflict.json`, pulls the cloud course over local, and exits `2`. Without any supplied or locally changed field it prints `Nothing to update` and exits normally.

### `set-access`

The command maps `guest`, `trial`, and `normal` to the platform learning-access value and sends only that value plus optional `is_hidden`. Other lesson fields are preserved. When `--course-dir` is present and the sync mapping exists, the CLI updates the matching entry in `structure.json` as a local side effect.

### `set-tts`

Disabling sends only `tts_enabled=false`. Enabling fetches the platform TTS configuration and selects the model option the platform declares as default (`is_default`), falling back to the first option on backends without the marker, plus the first voice compatible with that model. It sends provider, model, voice, speed, normalized pitch `0`, and empty emotion; `--speed` overrides the default. Invalid or incomplete settings exit `1`.

With a matching sync manifest, the command checks the course revision before writing, then refreshes `course-config.json` and the manifest after success. On conflict it records the intended metadata, pulls the cloud course, and exits `2`.

### `set-avatar`

The command accepts a local JPG or PNG, corrects EXIF orientation, limits the longest side to 2048 px, and automatically compresses the upload to at most 2 MB. If it cannot reach the limit without excessive loss, it exits `1` so the Skill can request a replacement. A non-square image is accepted with a warning because course cards and learning pages display the avatar in a square frame; 1:1 is recommended.

After upload, the command sends only the returned resource URL as `avatar`, reads course detail back, and exits `1` if the new URL cannot be verified. With a matching sync manifest, it checks the course revision before upload, then refreshes `course-config.json` and the manifest after success. This path uses the platform APIs directly and does not require browser or Chrome control.

### `reorder`

The command sends the comma-separated outline BID sequence and changes the course outline order.

## Delete Commands

```bash
delete-lesson <shifu_bid> <outline_bid>
```

`delete-lesson` deletes the named outline.

## Bulk Import

```bash
# Flat JSON import
import <shifu_bid> --json-file course.json
import --new --json-file course.json

# Build and import from a course directory
import <shifu_bid> --course-dir ./course-a/ \
  [--title "..."] [--description "..."] [--keywords "..."] [--chapter-name "..."]
import --new --course-dir ./course-a/ \
  [--title "..."] [--description "..."] [--keywords "..."] [--chapter-name "..."]

# Offline build only
build --course-dir ./course-a/ [-o shifu-import.json] \
  [--title "..."] [--description "..."] [--keywords "..."] [--chapter-name "..."]
```

`build` performs no network calls and writes the import JSON to `-o` or `<course-dir>/shifu-import.json`. File discovery, field precedence, directory schemas, and the generated import schema are defined in `course-directory-spec.md`.

`import --new` creates a new course. `import <shifu_bid>` targets an existing course. Both forms send content fields. Existing-course import leaves omitted platform attributes unchanged; new-course import uses platform defaults for omitted attributes.

Importing into an existing course deletes and recreates every outline, so all outline BIDs are regenerated and recreated lessons receive platform-default permissions. With `--course-dir` and a matching sync manifest, an existing-course import checks the course revision first. On conflict it backs up the local tree to `.conflict-backup-<timestamp>/`, pulls the cloud course over local, and exits `2`. After a successful existing-course import it runs an automatic pull to reseed the manifest.

## Image Upload

```bash
upload-image --file <local-path> [--course-dir <dir>] [--alt "<description>"]
upload-image --url <http-or-https-url> [--course-dir <dir>] [--alt "<description>"]
```

`--file` and `--url` are mutually exclusive and one is required.

- A local file is opened with Pillow, has EXIF orientation corrected, is downscaled to a maximum side of 2048 px, and is recompressed to at most 2 MB. Transparent images remain PNG; other accepted images are uploaded as JPEG. Invalid image input exits `1`.
- A remote URL is sent to the backend for validation and re-hosting.
- Stdout contains exactly the resource URL returned by the selected deployment (preserve its host and path); diagnostics and manifest messages go to stderr.
- With `--course-dir`, the CLI upserts an entry in `assets/image-manifest.json`, keyed by service `base_url` plus `local` or `source_url`, and records the selected profile. Different services' uploads and old records without known provenance are preserved. See `course-directory-spec.md#assets`.
- `--alt` is stored in the manifest.
- `--no-process` skips local preprocessing and is a debug-only flag.

The local preprocessing dependencies are `Pillow` and `pillow-heif`.

## State Management

```bash
publish <shifu_bid>
archive <shifu_bid>
unarchive <shifu_bid>
```

- `publish` publishes the current draft and prints the course links described in [Query Commands](#query-commands).
- `archive` archives the course.
- `unarchive` restores an archived course.

## Exit Codes

- `0`: command completed successfully.
- `1`: validation, transport, file, authentication, or platform business error; `status --exit-code` also uses `1` for divergence.
- `2`: `verify` could not determine token state, or a version-aware write found a conflict and auto-pulled the cloud baseline. Interpret the command context before handling this code.

- `4`: service/profile configuration is missing or invalid; no platform request was sent. Inspect `site` or `profile list` and resolve the reported issue before authentication; do not fall back to another profile.

Commands print platform business error payloads before exiting when available.

## CLI Output & Encoding

CLI JSON uses UTF-8 and `ensure_ascii=False`. If an agent subprocess renders Chinese stdout as mojibake, redirect output to a UTF-8 file and read that file. This changes only capture behavior, not command output.

```bash
python3 scripts/shifu-cli.py analytics-query <bid> --dsl '<json>' > /tmp/shifu-result.json
```

Saved credentials remain in the selected profile's user-configuration directory; authenticated commands load only that profile's credentials.
