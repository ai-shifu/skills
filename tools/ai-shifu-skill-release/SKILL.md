---
name: ai-shifu-skill-release
description: "Release AI-Shifu skills using the maintained release.py workflow: open version-bump PRs, build and verify channel packages, run preflight checks, publish to ClawHub and SkillHub, prepare and record manual WorkBuddy/QClaw/Doubao uploads, and open website manifest activation PRs. Use for skill version upgrades, packaging, release checks, publication, or manifest activation. Source and website PRs require human merge; never bypass that workflow by editing local business-skill source."
---

## Execution Environment

All release operations go through this tool's `scripts/release.py`. Do not duplicate packaging logic or call platform publication commands directly.

1. Locate the directory containing **this** `SKILL.md`. In `ai-shifu/skills`, it is `tools/ai-shifu-skill-release/`, not the Git repository root. Use it as the working directory for the commands below. A standalone copy uses the same sibling layout.
2. Confirm that `scripts/release.py` and `channels/workbuddy/.codebuddy-plugin/plugin.json` exist there. Stop if the intended tool cannot be located.
3. Read `python3 scripts/release.py --help` if the implementation may have changed. Read [Publishing Environment](references/publishing.md) for runtime, publisher configuration, and authentication requirements.
4. Before packaging, check `git status --short` and `git log -1 --oneline` in the enclosing repository when present. The builder supports standalone copies without Git and records unavailable provenance as null; do not claim a clean repository without evidence.
5. GitHub `ai-shifu/skills` remote `main` is the only source of business skills. Sharing a repository with the tool does not make local skill edits build inputs. GitHub is not a publication target.

Building and publishing do not modify skill source. Version changes go through `bump`, which opens a source-repository PR for human review and merge. Only the primary source skill's `SKILL.md` stores the release version; all five channel versions derive from it, with no independent version under this tool directory. If the user specifies a version, compare it with `release.json`. Stop on a mismatch and explain that the target version must first reach remote `main` through a merged bump PR.

## Safety Rules

- Use the exact release directory printed by `build`, or explicitly identified by the user. Do not guess which `dist/` directory is newest.
- `build`, `verify`, `check`, and `manual-plan` do not upload packages and do not require publication authorization.
- Before real publication, confirm the tool's enclosing worktree is clean, verification succeeds, and all selected automated channels report `ready`. For a standalone copy, do not treat unavailable Git provenance as proof of a clean worktree.
- Before `publish ... --execute`, show the release ID, source commit, skill and plugin versions, artifact hashes, selected targets, and preflight results. Obtain explicit authorization for that candidate and those channels.
- Packaging, checking, preparation, or inspection requests do not authorize publication.
- Never request or print platform tokens. If authentication is missing, provide the login command and wait for the user to authenticate locally.
- Do not commit or push the current checkout without an explicit user request. `bump` and `activate-manifest` require an explicit request for those operations and only push dedicated branches and open PRs. Never merge their PRs or push directly to `main`.
- If GitHub `main` has advanced, do not delete existing artifacts. Rebuild and use the new output directory.
- Only accept `release.json` schema 4. Rebuild schema 3 or older candidates.
- Do not record a manual channel as `verified` without a platform URL and confirmation of independent validation.

## Choose the Workflow

| User intent | Steps | Stop point |
| --- | --- | --- |
| Upgrade a version | `bump` | Return the source PR and wait for human merge |
| Build or package | `build`, then `verify` | Report artifacts |
| Check or dry-run | Build if needed, then `verify` and `check` | Report channel readiness |
| Publish automated channels | Build if needed, verify, check, obtain authorization, publish | Report channel results |
| Prepare manual channels | Build if needed, then `verify` and `manual-plan` | Return exact upload paths and hashes |
| Record manual results | Verify the specified release, then `record-manual` | Report the updated ledger |
| Activate the website manifest | After channel gates pass, `activate-manifest` | Return the website PR and wait for human merge and deployment |
| Complete a full release | Follow applicable stages in order | Stop at each human gate |

Automated targets are `clawhub` and `skillhub`. Manual targets are `workbuddy`, `qclaw`, and `doubao`. Doubao does not block website manifest activation.

## Upgrade the Skill Version

```bash
python3 scripts/release.py bump --skill-name ai-shifu-course-creator \
  --skill-version <X.Y.Z>
```

Use `--level major|minor|patch` instead of an explicit version when requested. `--draft` creates a draft PR; `--no-pr` pushes the branch without opening a PR. `--changelog <text>` optionally adds a CHANGELOG entry.

`bump` modifies the frontmatter version in a temporary source-repository clone without changing the skill body, pushes a branch, and uses `gh` to create a PR. It does not edit the current checkout. **Never merge the PR.** Return its URL for human review; only after merge can `build` read the version from remote `main`. SSH write access is required. If `gh` is missing, the branch is still pushed and a PR must be created manually.

## Build and Verify

For each new packaging request, first read and show the primary source skill's version on remote `main`, then confirm whether to keep it or upgrade and to which version. Do not ask again when the user has already specified that choice for the current request. All five channels use that version; do not edit local source or introduce an independent plugin version to satisfy a mismatch.

After confirmation:

```bash
python3 scripts/release.py build --skill-name ai-shifu-course-creator
```

Record the exact output directory as `RELEASE_DIR` and verify it:

```bash
python3 scripts/release.py verify "$RELEASE_DIR"
```

The default output is `dist/` relative to the caller's working directory. With the standard working directory above, that is the tool's own `dist/`. Explicit `--output` paths retain their existing semantics.

Read `$RELEASE_DIR/release.json` and report:

- The release ID and recorded SHA-256.
- The source repository, remote `main` commit, and skill version.
- Paths, versions, and hashes for ClawHub, SkillHub, WorkBuddy, QClaw, and Doubao.
- Source-body consistency across channels. For Doubao, also report the source manifests for all embedded skills, the allowlisted `version_management` / `label` / empty `icon` changes, and static package validation.
- Whether the builder's enclosing worktree had uncommitted changes, or whether provenance was unavailable.

If the user only requested packaging, stop here.

## Check the ClawHub Registry Version

Before ClawHub publication, inspect version history:

```bash
npx --yes clawhub@latest inspect ai-shifu-course-creator --versions --json
```

ClawHub requires Node 22. The publisher resolves npx from `CLAWHUB_NPX` or `--clawhub-npx`, then PATH, then the nvm Node 22 fallback; see [Publishing Environment](references/publishing.md).

Publishing an existing version can overwrite that version's content. Point out the existing version and obtain explicit confirmation before proceeding.

## Check Automated Channels

```bash
python3 scripts/release.py check "$RELEASE_DIR" --target all
python3 scripts/release.py check "$RELEASE_DIR" --target clawhub
python3 scripts/release.py check "$RELEASE_DIR" --target skillhub
```

Choose the applicable target. `check` verifies authentication, confirms that remote `main` still matches the candidate, and performs registry dry runs. It must not upload.

If authentication fails, have the user run the appropriate local command:

```bash
skillhub login --key <API_TOKEN>
npx --yes clawhub@latest login
```

Do not ask the user to send credentials. After login, recheck failed channels. Do not publish while any selected automated target is not `ready`.

## Publish Automated Channels

After satisfying the safety rules and obtaining explicit authorization:

```bash
python3 scripts/release.py publish "$RELEASE_DIR" --target all --execute
```

Use `--target clawhub` or `--target skillhub` when only one channel is authorized. Read `release-report.json` afterward and report each channel independently as `published` or `failed`. Automated publication does not perform platform lookup or fresh-install verification; do not describe accepted uploads as `verified`.

After partial failure, keep the same immutable release directory. Diagnose the failure and retry only failed channels. Rebuild only if remote `main` has advanced.

## Prepare and Record Manual Publication

```bash
python3 scripts/release.py manual-plan "$RELEASE_DIR" --target all
```

Use `--target workbuddy`, `--target qclaw`, or `--target doubao` for a single manual channel. Give the user the exact `upload_path`, plugin version, embedded skill version, and artifact SHA-256. The user uploads on the platform.

Record the user's result with:

```bash
python3 scripts/release.py record-manual "$RELEASE_DIR" \
  --target <workbuddy|qclaw|doubao> \
  --status <submitted|verified|failed> \
  --url <platform-url> \
  --note <optional-note>
```

Both `submitted` and `verified` require `--url`. Only `failed`, when no platform page exists, may omit it. Doubao also requires testing its three recommended instructions in the platform's authoring tool and uploading the test report; retain separate coverage of the embedded learning-report capability.

## Activate the Website Manifest

The gate requires ClawHub and SkillHub to be `published`, and WorkBuddy and QClaw to be `submitted` or `verified`. Doubao is recorded independently.

```bash
python3 scripts/release.py activate-manifest "$RELEASE_DIR" \
  [--notes <text>] [--auto-notes] [--draft] [--no-pr]
```

`--notes` and `--auto-notes` are mutually exclusive:

1. `--auto-notes` gathers PR titles from squash-merge commits touching this skill between the previous manifest version and the release source commit, excludes the version-bump commit, and joins them into an English summary capped at 500 characters. The output `changes` field contains the original list.
2. Prefer a reviewed, concise Chinese summary for the Chinese website, supplied with `--notes`. If using `--auto-notes` to obtain the list, remember that the command still creates or updates a branch/PR: it is not a read-only preview and requires authorization for manifest activation.
3. With neither option, notes default to `Release <version>`.

The command opens a `codex/` branch PR in `ai-shifu-website`, updating `zh/skill-manifests/<skill_name>.json`. It validates SemVer, `min_supported <= latest`, and an HTTPS `update_url`. **Never merge the PR.** If channel readiness is insufficient, it refuses and reports the missing channels.

Only when the user explicitly chooses to handle a manual channel offline may `--allow-pending workbuddy|qclaw` waive that channel's gate. The waiver is recorded in command output and the PR description.

After the user merges the PR, the website image must still be rebuilt and deployed. Once deployment is complete:

```bash
python3 scripts/release.py activate-manifest "$RELEASE_DIR" --check-online
```

Edge caching can take about five minutes. If `active` is false, check again later without claiming activation.

## Completion Report

Read `release-report.json` and summarize the release ID and source commit, automated channel outcomes, manual outcomes and evidence URLs, blocked or failed actions, and work that remains outside the tool.

State the limits accurately: manual channels require upload and platform validation; automated uploads do not include fresh-install verification; bump and manifest commands create PRs but never merge them; website activation still requires production deployment and online readback. Stop at the human gates rather than treating success at one stage as permission for the next.
